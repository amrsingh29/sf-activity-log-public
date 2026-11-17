"""Docs mirror - text copies of customer documents (Word, PowerPoint, PDF, Excel) for search.

Optional and off by default (profile `docs_mirror`). Reads the workspace (and `extra_folders`)
read-only, decides each file's account with the same registry as every other source, and writes
a Markdown copy under `<output>/<account>/...`. Only changed files are converted; copies whose
original is gone or out of scope are removed. Nothing is decrypted, nothing is downloaded, and
nothing is written outside `output`. The ledger and notes are never touched.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat as statmod
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml

from . import __version__
from .accounts import Registry
from .sources.files import SKIP_DIRS, SKIP_FILES, _ignored

MANIFEST = "_manifest.json"
REPORT = "_report.md"
UNASSIGNED = "_unassigned"
INTERNAL = "_internal"
TYPES = {".docx": "docx", ".docm": "docx", ".pptx": "pptx", ".pptm": "pptx",
         ".xlsx": "xlsx", ".xlsm": "xlsx", ".pdf": "pdf"}
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"     # encrypted / IRM-protected Office files are OLE, not zip
SF_DATALESS = 0x40000000                          # macOS: OneDrive "online-only" placeholder
LOW_TEXT_CHARS = 200
XLSX_MAX_ROWS = 500
XLSX_MAX_COLS = 30
MASS_REMOVE_MIN = 20                              # removing more than half of >= this many copies needs --rebuild
REPORT_LIST_MAX = 30
GBRAIN_TIMEOUT_S = 600
GIT_IGNORE = (MANIFEST, REPORT, ".gbrain-owner.json")    # sfal bookkeeping + the marker GBrain writes


class MirrorError(Exception):
    pass


# --- settings and safety -----------------------------------------------------------------------

def settings(profile) -> dict:
    return profile.data.get("docs_mirror") or {}


def _resolve(p) -> Path:
    return Path(os.path.expanduser(str(p))).resolve()


def output_dir(profile) -> Path:
    """The only folder the mirror writes to. Refused when it sits in a synced or source folder."""
    cfg = settings(profile)
    out = _resolve(cfg.get("output") or "~/.sf-activity-log/docs-mirror")
    s = str(out)
    if "/Library/CloudStorage/" in s or "/OneDrive" in s or "/Library/Mobile Documents/" in s:
        raise MirrorError(f"docs_mirror.output must not be in a synced cloud folder: {out}")
    guarded = [("workspace.root", profile.workspace_root), ("data_dir", profile.data_dir)]
    guarded += [("extra_folders", _resolve(f)) for f in cfg.get("extra_folders") or []]
    for label, g in guarded:
        if g and (out == g or g in out.parents or out in g.parents):
            raise MirrorError(f"docs_mirror.output must be outside {label} ({g}): {out}")
    if out == Path.home() or out == Path("/"):
        raise MirrorError(f"docs_mirror.output must be a dedicated folder, not {out}")
    return out


def _inside(out: Path, path: Path) -> Path:
    path = path.resolve()
    if out not in path.parents:
        raise MirrorError(f"refusing to write outside docs_mirror.output: {path}")
    return path


# --- scanning and routing ----------------------------------------------------------------------

def _roots(profile) -> list[tuple[Path, str]]:
    """(folder, label) pairs to scan: workspace.root, then extra_folders (label = folder name)."""
    roots = []
    if profile.workspace_root:
        roots.append((profile.workspace_root, ""))
    for f in settings(profile).get("extra_folders") or []:
        roots.append((_resolve(f), _resolve(f).name))
    return roots


def _walk(root: Path, ignore, skip_names: set[str], exclude: set[Path]):
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        rel_dir = dp.relative_to(root).as_posix() if dp != root else ""
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                             and d.lower() not in skip_names and (dp / d).resolve() not in exclude
                             and not _ignored(f"{rel_dir}/{d}".lstrip("/") + "/", ignore))
        for fn in sorted(filenames):
            if fn.startswith(SKIP_FILES) or fn.startswith("."):
                continue
            rel = f"{rel_dir}/{fn}".lstrip("/")
            if not _ignored(rel, ignore):
                yield dp / fn, rel


def _route(registry: Registry, internal_folders: set[str], rel: str) -> tuple[str, str, str | None]:
    """(bucket, path below the account folder, why-unassigned). bucket = account name, _internal or _unassigned."""
    parts = rel.split("/")
    dirs, stem = parts[:-1], parts[-1].rsplit(".", 1)[0]
    if dirs and dirs[0].lower() in internal_folders:
        return INTERNAL, "/".join(parts[1:]), None
    m = registry.match(dirs + [stem], [])
    if not m or not m.get("name"):
        why = "ambiguous: " + ", ".join(m["candidates"]) if m and m.get("candidates") else "no account"
        return UNASSIGNED, rel, why
    if m["kind"] == "partner" and not m.get("certain"):
        return UNASSIGNED, rel, f"partner only: {m['name']}"
    # keep the sub-path below the deepest folder that names the account
    entry = next(e for e in registry.entries if e["name"] == m["name"])
    cut = 0
    for i, d in enumerate(dirs):
        if any(p.search(d.lower()) for _, p in entry["patterns"]):
            cut = i + 1
    return m["name"], "/".join(parts[cut:]), None


def _selected(cfg: dict, account: str, only: str | None) -> bool:
    if account in (UNASSIGNED, INTERNAL):          # never mirrored; unassigned files are reported
        return False
    if only:
        return account == only
    chosen = cfg.get("accounts") or []
    if any(str(a).lower() == "all" for a in chosen):
        return account not in (cfg.get("exclude_accounts") or [])
    return account in chosen


def _eligible(cfg: dict, path: Path, kind: str) -> str | None:
    """None when the type is in scope, else the reason it is skipped."""
    include = {str(t).lower().lstrip(".") for t in cfg.get("include") or []}
    if kind == "xlsx" and kind not in include:
        words = [w.lower() for w in cfg.get("excel_name_match") or []]
        return None if any(w in path.name.lower() for w in words) else "excel name not matched"
    return None if kind in include else "type not included"


# --- conversion --------------------------------------------------------------------------------

PDF_EXTRACT = 1 << 4      # permission bit 5: copy / extract text


def _pdf_reader(path: Path):
    """A readable PdfReader, or PermissionError. Encrypted PDFs are read only when they open
    without a password AND their permissions allow copying text (common for vendor guides);
    a password or a copy restriction is respected, never worked around."""
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        if not reader.decrypt(""):
            raise PermissionError("password required")
        if not reader.user_access_permissions & PDF_EXTRACT:
            raise PermissionError("copying text not allowed")
    return reader


def _protected(path: Path, kind: str) -> bool:
    if kind == "pdf":
        try:
            _pdf_reader(path)
            return False
        except PermissionError:
            return True
    with path.open("rb") as f:
        return f.read(8) == OLE_MAGIC


def _md_table(rows: list[list[str]]) -> list[str]:
    rows = [[(c or "").replace("|", "\\|").replace("\n", " ").strip() for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return out + [""]


def convert_docx(path: Path) -> str:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    d = docx.Document(str(path))
    out = []
    for block in d.element.body.iterchildren():
        tag = block.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(block, d)
            text = p.text.strip()
            if not text:
                continue
            style = (p.style.name if p.style is not None else "") or ""
            level = re.match(r"Heading (\d)", style)
            if style == "Title":
                out += [f"# {text}", ""]
            elif level:
                out += [f"{'#' * min(int(level.group(1)) + 1, 6)} {text}", ""]
            elif style.startswith("List"):
                out.append(f"- {text}")
            else:
                out += [text, ""]
        elif tag == "tbl":
            t = Table(block, d)
            out += _md_table([[c.text for c in row.cells] for row in t.rows])
    return "\n".join(out)


_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def _shape_paragraphs(xml: bytes) -> tuple[str | None, list[str]]:
    """(title, other paragraphs) of one slide or notes page."""
    root = ET.fromstring(xml)
    title, lines = None, []
    for sp in root.iter(f"{_P}sp"):
        ph = sp.find(f".//{_P}nvPr/{_P}ph")
        kind = ph.get("type") if ph is not None else None
        paras = ["".join(t.text or "" for t in p.iter(f"{_A}t")).strip() for p in sp.iter(f"{_A}p")]
        paras = [p for p in paras if p]
        if kind in ("title", "ctrTitle") and paras and title is None:
            title = " ".join(paras)
        elif kind not in ("sldNum", "dt", "ftr"):
            lines += paras
    for tbl in root.iter(f"{_A}tbl"):
        rows = [["".join(t.text or "" for t in tc.iter(f"{_A}t")) for tc in tr.iter(f"{_A}tc")]
                for tr in tbl.iter(f"{_A}tr")]
        lines += _md_table(rows)
    return title, lines


def convert_pptx(path: Path) -> str:
    out = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        slides = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                        key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
        for i, s in enumerate(slides, 1):
            title, lines = _shape_paragraphs(z.read(s))
            out += [f"## Slide {i}" + (f": {title}" if title else ""), ""]
            out += [f"- {l}" if l and not l.startswith("|") else l for l in lines]
            rels = s.replace("slides/", "slides/_rels/") + ".rels"
            if rels in names:
                m = re.search(r'Target="\.\./notesSlides/(notesSlide\d+\.xml)"', z.read(rels).decode("utf-8", "replace"))
                if m and f"ppt/notesSlides/{m.group(1)}" in names:
                    _, notes = _shape_paragraphs(z.read(f"ppt/notesSlides/{m.group(1)}"))
                    notes = [n for n in notes if not n.isdigit()]
                    if notes:
                        out += ["", "Speaker notes:", *notes]
            out.append("")
    return "\n".join(out)


def convert_xlsx(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out = []
    try:
        for ws in wb.worksheets:
            rows, cut = [], False
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i >= XLSX_MAX_ROWS:
                    cut = True
                    break
                rows.append(["" if v is None else str(v) for v in row[:XLSX_MAX_COLS]])
            table = _md_table(rows)
            if table:
                out += [f"## Sheet: {ws.title}", ""] + table
                if cut:
                    out += [f"_(first {XLSX_MAX_ROWS} rows only)_", ""]
    finally:
        wb.close()
    return "\n".join(out)


def convert_pdf(path: Path) -> str:
    reader = _pdf_reader(path)
    out = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            out += [f"## Page {i}", "", text, ""]
    return "\n".join(out)


CONVERTERS = {"docx": convert_docx, "pptx": convert_pptx, "xlsx": convert_xlsx, "pdf": convert_pdf}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _render(body: str, meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n" + body.strip() + "\n"


# --- the run -----------------------------------------------------------------------------------

def _load_manifest(out: Path) -> dict:
    try:
        return json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "files": {}}


def _write(out: Path, path: Path, text: str) -> None:
    path = _inside(out, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _remove(out: Path, rel: str) -> None:
    path = _inside(out, out / rel)
    if path.exists():
        path.unlink()
    parent = path.parent
    while parent != out and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def sync(profile, rules, *, account: str | None = None, dry_run: bool = False, rebuild: bool = False) -> dict:
    cfg = settings(profile)
    if not cfg.get("enabled"):
        raise MirrorError("docs mirror is off: set docs_mirror.enabled: true and pick docs_mirror.accounts in your profile")
    out = output_dir(profile)
    roots = _roots(profile)
    missing = [str(r) for r, _ in roots if not r.exists()]
    if missing:
        raise MirrorError(f"folder not found (is OneDrive running?): {', '.join(missing)} - nothing changed")
    registry = Registry(profile.accounts, rules.internal_account)
    if account:
        canon = registry.canonical(account)
        if not canon:
            raise MirrorError(f"unknown account '{account}' - use a name or alias from your profile")
        account = canon
    ignore = list(profile.data["workspace"].get("ignore") or [])
    internal = {f.lower() for f in profile.data["workspace"].get("internal_folders") or []}
    skip_names = {s.lower() for s in cfg.get("skip_folders") or []}
    max_bytes = float(cfg.get("max_size_mb") or 20) * 1024 * 1024
    exclude = {out, profile.data_dir} if profile.data_dir else {out}
    want_all = any(str(a).lower() == "all" for a in cfg.get("accounts") or [])

    manifest = _load_manifest(out) if out.exists() else {"version": 1, "files": {}}
    old = manifest.get("files") or {}
    new_files: dict[str, dict] = {}
    claimed: dict[str, str] = {}
    counts = {"converted": 0, "unchanged": 0, "removed": 0, "skipped": 0}
    skipped: dict[str, list[str]] = {}
    converted, low_text, errors = [], [], []
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    def skip(reason: str, shown: str):
        counts["skipped"] += 1
        skipped.setdefault(reason, []).append(shown)

    for root, label in roots:
        for path, rel in _walk(root, ignore, skip_names, exclude):
            kind = TYPES.get(path.suffix.lower())
            if not kind:
                continue
            shown = f"{label}/{rel}" if label else rel
            bucket, sub, why = _route(registry, internal, shown)   # an extra folder's own name counts
            if not _selected(cfg, bucket, account):
                if bucket == UNASSIGNED and not account and want_all:      # with a short list they are just noise
                    skip(f"unassigned ({why})", shown)
                continue
            reason = _eligible(cfg, path, kind)
            if reason:
                skip(reason, shown)
                continue
            key = str(path)
            prev = old.get(key)
            try:
                st = path.stat()
            except OSError as e:
                skip("unreadable", f"{shown} ({e.strerror})")
                continue
            if getattr(st, "st_flags", 0) & SF_DATALESS:
                if prev:                                    # converted while it was local: keep the copy
                    new_files[key] = prev
                    claimed[prev["copy"]] = key
                    counts["unchanged"] += 1
                else:
                    skip("online-only (not downloaded)", shown)
                continue
            if st.st_size > max_bytes:
                skip(f"larger than {cfg.get('max_size_mb') or 20} MB", shown)
                continue
            copy = f"{bucket}/{sub}.md" if sub else f"{bucket}/{path.name}.md"
            if claimed.get(copy, key) != key:               # same name from another folder: keep both
                copy = f"{copy[:-3]}.{hashlib.sha1(key.encode()).hexdigest()[:6]}.md"
            claimed[copy] = key
            if prev and not rebuild and prev.get("size") == st.st_size and prev.get("mtime") == st.st_mtime \
                    and prev.get("copy") == copy and (out / copy).exists():
                new_files[key] = prev
                counts["unchanged"] += 1
                continue
            try:
                if _protected(path, kind):
                    raise PermissionError("protected")
                fp = _sha256(path)
                if prev and not rebuild and prev.get("sha256") == fp and prev.get("copy") == copy \
                        and (out / copy).exists():
                    new_files[key] = dict(prev, size=st.st_size, mtime=st.st_mtime)
                    counts["unchanged"] += 1
                    continue
                body = "" if dry_run else CONVERTERS[kind](path)
            except PermissionError:
                skip("protected (encrypted or rights-managed)", shown)
                continue
            except Exception as e:                           # one bad file never stops the run
                errors.append(f"{shown}: {type(e).__name__}: {str(e)[:120]}")
                skip("could not convert", shown)
                continue
            entry = {"copy": copy, "account": bucket, "type": kind, "size": st.st_size, "mtime": st.st_mtime,
                     "sha256": fp, "converted_at": now}
            if not dry_run:
                if len(body.strip()) < LOW_TEXT_CHARS:
                    entry["low_text"] = True
                    low_text.append(shown)
                meta = {"title": path.stem, "account": bucket, "original": str(path), "original_rel": shown,
                        "file_type": kind,
                        "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).astimezone().isoformat(timespec="seconds"),
                        "fingerprint": fp, "converted_by": f"sfal docs {__version__}"}
                _write(out, out / copy, _render(body, meta))
                if prev and prev.get("copy") != copy:
                    _remove(out, prev["copy"])
            new_files[key] = entry
            converted.append(shown)
            counts["converted"] += 1

    # copies whose original is gone, moved out of scope, or whose account was deselected
    gone = [k for k, v in old.items() if k not in new_files and (not account or v.get("account") == account)]
    kept_aside = {k: v for k, v in old.items() if account and v.get("account") != account}
    held = 0
    if not rebuild and len(old) >= MASS_REMOVE_MIN and len(gone) > len(old) / 2:
        held = len(gone)                                     # likely a missing folder or a profile mistake
        new_files.update({k: old[k] for k in gone})
        gone = []
    for k in gone:
        if not dry_run:
            _remove(out, old[k]["copy"])
        counts["removed"] += 1
    new_files.update(kept_aside)

    result = {"ok": True, "dry_run": dry_run, "output": str(out), "account": account, **counts,
              "converted_files": converted[:REPORT_LIST_MAX],
              "skipped_by_reason": {r: {"count": len(v), "files": v[:REPORT_LIST_MAX]} for r, v in sorted(skipped.items())},
              "low_text": low_text[:REPORT_LIST_MAX], "errors": errors[:REPORT_LIST_MAX],
              "removed_files": [old[k]["copy"] for k in gone][:REPORT_LIST_MAX]}
    if held:
        result["warning"] = (f"{held} of {len(old)} copies would be removed - more than half. "
                             "Nothing was removed. If that is intended (accounts deselected), run with --rebuild.")
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)
        _write(out, out / REPORT, report_text(result, now))
        gbrain_ok = manifest.get("gbrain_ok")
        if cfg.get("gbrain_import"):
            result["gbrain"] = gbrain_update(out, cfg.get("gbrain_source") or "docs",
                                             retry=not manifest.get("gbrain_ok"))
            gbrain_ok = result["gbrain"]["status"] in ("updated", "up_to_date")
        elif gbrain_bin():                                   # no GBrain on this Mac -> say nothing about it
            result["next"] = ("To make the copies searchable in GBrain after every sync, set "
                              "docs_mirror.gbrain_import: true in your profile.")
        manifest = {"version": 1, "last_run": now, "files": new_files, "gbrain_ok": gbrain_ok}
        _write(out, out / MANIFEST, json.dumps(manifest, indent=1, ensure_ascii=False))
    return result


# --- GBrain update (optional: docs_mirror.gbrain_import) ----------------------------------------
# The shared `gbrain serve` holds GBrain's database lock, so `gbrain import` cannot run beside it.
# `gbrain sync` hands the work to the running server, but it reads a git repo - so the mirror
# folder is kept as a local git repo (no remote) and each sync commits its changes first.

def _run(argv: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess:
    env = dict(os.environ, GBRAIN_NO_UPDATE_CHECK="1",
               PATH=os.pathsep.join([str(Path.home() / ".bun" / "bin"), "/opt/homebrew/bin",
                                     "/usr/local/bin", os.environ.get("PATH", "/usr/bin:/bin")]))
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def gbrain_bin() -> str | None:
    if os.environ.get("SFAL_GBRAIN"):
        return os.environ["SFAL_GBRAIN"]
    found = shutil.which("gbrain") or str(Path.home() / ".bun" / "bin" / "gbrain")
    return found if Path(found).exists() else None


def _git_commit(out: Path) -> bool:
    """Commit the mirror's changes to its own local repo. True when something changed."""
    git = ["git", "-c", "user.name=sfal", "-c", "user.email=sfal@localhost", "-c", "commit.gpgsign=false"]
    if not (out / ".git").exists():
        _run(git + ["init", "-q"], out).check_returncode()
    ignore = out / ".gitignore"
    have = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
    missing = [n for n in GIT_IGNORE if n not in have]
    if missing:
        _write(out, ignore, "\n".join(have + missing) + "\n")
        _run(git + ["rm", "-q", "--cached", "--ignore-unmatch"] + missing, out).check_returncode()
    _run(git + ["add", "-A"], out).check_returncode()
    if _run(git + ["diff", "--cached", "--quiet"], out).returncode == 0:
        return False
    _run(git + ["commit", "-q", "-m", "sfal docs sync"], out).check_returncode()
    return True


def _tail(text: str, lines: int = 3) -> str:
    keep = [ln for ln in (text or "").strip().splitlines() if ln.strip() and "UPGRADE_AVAILABLE" not in ln]
    return " ".join(keep[-lines:])[:400]


def gbrain_update(out: Path, source: str, retry: bool = False) -> dict:
    """Commit the mirror and ask GBrain to sync it. Never fails the docs sync itself."""
    register = (f'gbrain sources add {source} --path "{out}" --name "Docs mirror" --federated')
    if not shutil.which("git"):
        return {"status": "skipped", "reason": "git is not installed (needed to hand changes to GBrain)"}
    try:
        changed = _git_commit(out)
    except (subprocess.SubprocessError, OSError) as e:
        return {"status": "failed", "reason": f"could not record changes for GBrain: {e}"}
    exe = gbrain_bin()
    if not exe:
        return {"status": "skipped", "reason": "GBrain isn't installed, so gbrain_import has nothing to "
                "update. Set docs_mirror.gbrain_import: false to stop this line."}
    if not changed and not retry:
        return {"status": "up_to_date", "source": source}
    try:
        r = _run([exe, "sync", "--source", source, "--no-embed", "--no-pull"],
                 out, timeout=GBRAIN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "source": source,
                "reason": f"GBrain did not finish within {GBRAIN_TIMEOUT_S // 60} minutes; the next sync retries"}
    except OSError as e:
        return {"status": "failed", "source": source, "reason": f"could not start GBrain: {e}"}
    if r.returncode == 0:
        return {"status": "updated", "source": source, "detail": _tail(r.stdout or r.stderr, 1)}
    return {"status": "failed", "source": source, "reason": _tail(r.stderr or r.stdout),
            "fix": (f"If the '{source}' source is not registered yet, run once in Terminal: {register} "
                    "- the next sync then updates GBrain on its own.")}


def report_text(res: dict, when: str) -> str:
    L = [f"# Docs mirror - {when}", "",
         f"Converted: {res['converted']}   Unchanged: {res['unchanged']}   "
         f"Removed: {res['removed']}   Skipped: {res['skipped']}", ""]
    if res.get("warning"):
        L += [f"**Warning:** {res['warning']}", ""]
    if res["skipped_by_reason"]:
        L.append("## Skipped")
        for reason, v in res["skipped_by_reason"].items():
            L.append(f"- {reason}: {v['count']}")
            L += [f"  - {f}" for f in v["files"][:10]]
        L.append("")
    for title, key in (("Probably scanned (little text)", "low_text"), ("Errors", "errors")):
        if res[key]:
            L += [f"## {title}"] + [f"- {f}" for f in res[key]] + [""]
    return "\n".join(L)


def status(profile) -> dict:
    cfg = settings(profile)
    out = output_dir(profile)
    manifest = _load_manifest(out) if out.exists() else {"files": {}}
    files = manifest.get("files") or {}
    per: dict[str, int] = {}
    for v in files.values():
        per[v["account"]] = per.get(v["account"], 0) + 1
    size = sum(p.stat().st_size for p in out.rglob("*.md") if ".git" not in p.parts) if out.exists() else 0
    report = out / REPORT
    return {"ok": True, "enabled": bool(cfg.get("enabled")), "output": str(out),
            "accounts_selected": cfg.get("accounts") or [], "last_run": manifest.get("last_run"),
            "copies": len(files), "per_account": dict(sorted(per.items())),
            "mirror_size_mb": round(size / 1024 / 1024, 1),
            "gbrain_import": bool(cfg.get("gbrain_import")), "gbrain_source": cfg.get("gbrain_source") or "docs",
            "gbrain_last_ok": manifest.get("gbrain_ok"),
            "last_report": report.read_text(encoding="utf-8") if report.exists() else None}
