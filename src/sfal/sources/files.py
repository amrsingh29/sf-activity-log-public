"""Project files - scan of the workspace root (read-only).

For each file created or modified in the period:
  * authorship: Office "last modified by" vs you  -> authored | other_author | unknown
  * origin: macOS where-from / quarantine metadata -> received (downloaded / saved attachment)
  * created vs modified (macOS birth time)
  * light title peek: Office core title or first slide heading (never full content)
OneDrive sync bursts (many files across accounts in the same minute, or at configured
times) are dropped. Remaining files collapse into one work session per folder per day.
Files never produce hours on their own.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..evidence import item, make_id

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".obsidian", ".venv", ".Trash"}
SKIP_FILES = ("~$", ".~lock", ".DS_Store", "Icon\r", "desktop.ini", "Thumbs.db")
OFFICE = {".docx", ".pptx", ".xlsx", ".docm", ".pptm", ".xlsm"}
FILES_PER_SESSION = 10


def _ignored(rel: str, patterns) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(name, p) or rel.startswith(p.rstrip("*/") + "/")
               for p in patterns if p)


def office_meta(path: Path) -> dict:
    """lastModifiedBy, creator, title (core props) + first slide heading for pptx."""
    out = {}
    try:
        with zipfile.ZipFile(path) as z:
            if "docProps/core.xml" in z.namelist():
                core = z.read("docProps/core.xml").decode("utf-8", "replace")
                for tag, key in (("cp:lastModifiedBy", "last_modified_by"), ("dc:creator", "creator"),
                                 ("dc:title", "title")):
                    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", core, re.S)
                    if m and m.group(1).strip():
                        out[key] = m.group(1).strip()
            if path.suffix.lower().startswith(".ppt") and "title" not in out and "ppt/slides/slide1.xml" in z.namelist():
                s1 = z.read("ppt/slides/slide1.xml").decode("utf-8", "replace")
                texts = re.findall(r"<a:t>(.*?)</a:t>", s1)
                if texts:
                    out["title"] = " ".join(texts[:3])[:120]
    except (zipfile.BadZipFile, OSError, KeyError):
        pass
    return out


def where_from(path: Path) -> str | None:
    """Download origin (Spotlight kMDItemWhereFroms, set by browsers and Mail). OneDrive's
    quarantine flag is NOT used: it is set on synced files and would mark your own work as received."""
    try:
        r = subprocess.run(["mdls", "-raw", "-name", "kMDItemWhereFroms", str(path)],
                           capture_output=True, text=True, timeout=5)
        out = r.stdout.strip()
        if r.returncode == 0 and out and out != "(null)":
            urls = re.findall(r'"([^"]+)"', out)
            return urls[0] if urls else "downloaded"
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def owner_names(profile) -> set[str]:
    n = (profile.owner or "").strip()
    names = {n.lower()}
    if "," in n:
        last, first = [x.strip() for x in n.split(",", 1)]
        names |= {f"{first} {last}".lower(), f"{last} {first}".lower()}
    email = (profile.data["owner"].get("email") or "").lower()
    if email:
        names |= {email, email.split("@")[0]}
    return {x for x in names if x}


def scan(root: Path, d0: date, d1: date, tz: ZoneInfo, ignore, exclude_dirs) -> list[dict]:
    lo = datetime.combine(d0, datetime.min.time(), tz).timestamp()
    hi = datetime.combine(d1, datetime.max.time(), tz).timestamp()
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        rel_dir = dp.relative_to(root).as_posix() if dp != root else ""
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                       and (dp / d).resolve() not in exclude_dirs
                       and not _ignored(f"{rel_dir}/{d}".lstrip("/") + "/", ignore)]
        for fn in filenames:
            if fn.startswith(SKIP_FILES) or fn.startswith("."):
                continue
            rel = f"{rel_dir}/{fn}".lstrip("/")
            if _ignored(rel, ignore):
                continue
            try:
                st = (dp / fn).stat()
            except OSError:
                continue
            born = getattr(st, "st_birthtime", st.st_mtime)
            if lo <= st.st_mtime <= hi or lo <= born <= hi:
                found.append({"rel": rel, "path": dp / fn, "mtime": st.st_mtime, "born": born,
                              "created_in_period": lo <= born <= hi, "size": st.st_size})
    return found


def mark_bursts(files: list[dict], tz: ZoneInfo, min_files: int, burst_times, account_of) -> None:
    by_minute = defaultdict(list)
    for f in files:
        by_minute[datetime.fromtimestamp(f["mtime"], tz).strftime("%Y-%m-%d %H:%M")].append(f)
    for minute, fs in by_minute.items():
        accounts = {account_of(f["rel"]) for f in fs}
        if (len(fs) >= min_files and len(accounts) >= 2) or minute[11:] in (burst_times or []):
            for f in fs:
                f["burst"] = minute


def collect(profile, rules, d0: date, d1: date, raw_dir: Path):
    root = profile.workspace_root
    if not root or not root.exists():
        raise RuntimeError(f"files source: workspace.root not found ({root})")
    cfg = profile.source("files")
    tz = ZoneInfo(profile.timezone)
    ws = profile.data["workspace"]
    level = ws.get("account_folder_level")
    ignore = list(ws.get("ignore") or [])
    me = owner_names(profile)

    def account_folder(rel: str) -> str:
        parts = rel.split("/")[:-1]
        if level and len(parts) >= level:
            return "/".join(parts[:level])
        return "/".join(parts[:2]) if parts else ""

    files = scan(root, d0, d1, tz, ignore, {profile.data_dir.resolve()})
    mark_bursts(files, tz, int(cfg.get("burst_min_files") or 4), cfg.get("burst_times"), account_folder)

    from ..accounts import Registry
    registry = Registry(profile.accounts, rules.internal_account)

    def session_key(rel: str) -> tuple[str, str]:
        """(account name or folder, folder) - per-file account match so customers nested
        under a partner folder get their own sessions."""
        parts = rel.split("/")
        folder = account_folder(rel)
        m = registry.match(parts[:-1] + [parts[-1].rsplit(".", 1)[0]], [], folder_hint=None)
        if m and m.get("name") and m.get("certain"):
            return m["name"], folder
        return folder, folder

    sessions = defaultdict(list)
    bursts = 0
    for f in files:
        if f.get("burst"):
            bursts += 1
            continue
        mday = datetime.fromtimestamp(f["mtime"], tz).date()
        day = mday if d0 <= mday <= d1 else datetime.fromtimestamp(f["born"], tz).date()
        if not (d0 <= day <= d1):
            continue
        meta = office_meta(f["path"]) if f["path"].suffix.lower() in OFFICE else {}
        lmb = (meta.get("last_modified_by") or "").lower()
        origin = where_from(f["path"])
        if lmb and (lmb in me or any(n in lmb for n in me if len(n) > 3)):
            signal = "authored"
        elif origin:
            signal = "received"
        elif lmb:
            signal = "other_author"
        else:
            signal = "unknown"
        key, _ = session_key(f["rel"])
        sessions[(key, day.isoformat())].append({
            "file": f["rel"], "signal": signal, "created": f["created_in_period"],
            "title": meta.get("title"), "last_modified_by": meta.get("last_modified_by"),
            "from": origin if origin and origin != "downloaded" else None,
            "time": datetime.fromtimestamp(f["mtime"], tz).strftime("%H:%M")})

    items = []
    for (folder, day), fs in sorted(sessions.items()):
        fs.sort(key=lambda x: x["time"])
        dirs = sorted({x["file"].rsplit("/", 1)[0] for x in fs if "/" in x["file"]})
        signals = {x["signal"] for x in fs}
        flags = []
        if "authored" in signals:
            flags.append("authored_by_me")
        if "received" in signals:
            flags.append("received")
        if signals <= {"other_author"}:
            flags.append("others_edits_only")
        if any(x["created"] for x in fs):
            flags.append("new_files")
        names = [x["file"].rsplit("/", 1)[-1] for x in fs]
        title = f"{len(fs)} file(s) in {folder or '(root)'}: " + ", ".join(names[:4]) + ("…" if len(names) > 4 else "")
        items.append(item(
            id=make_id("file", folder, day), source="files", kind="file", date=day, title=title,
            flags=flags, folder=folder, files=fs[:FILES_PER_SESSION], file_count=len(fs),
            path_texts=folder.split("/") + [seg for d in dirs for seg in d.split("/")] +
                       [n.rsplit(".", 1)[0] for n in names] +
                       [x["title"] for x in fs if x.get("title")],
            raw_ref=f"files:{folder}@{day}"))
    (raw_dir / "files.json").write_text(json.dumps(
        [{k: (str(v) if isinstance(v, Path) else v) for k, v in f.items()} for f in files], indent=1), encoding="utf-8")
    return items, {"source": "files", "method": "workspace scan", "files_in_period": len(files),
                   "sync_burst_files_dropped": bursts, "work_sessions": len(items), "completeness": "complete"}
