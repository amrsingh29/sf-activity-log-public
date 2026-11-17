"""Add one customer or partner: a profile entry, and its folder with the default layout.

Two steps, both explicit. add() without confirm only plans: it checks the name, the aliases and
the folder, and writes nothing. With confirm it backs up the profile, appends the entry, then
creates the folder and its layout. Existing folders and files are never changed.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml

from .accounts import Registry
from .ledger import Ledger, _now
from .profile import ProfileError, load_profile
from .rules import load_rules

DEFAULT_LAYOUT = ("_ActivityLogging",)  # where activity notes for this account are saved
KINDS = ("customer", "partner")
HIDDEN = re.compile(r"^[._~]")


def _clean_list(values) -> list[str]:
    return [v.strip() for v in (values or []) if v and v.strip()]


def _check_account(profile, name: str, kind: str, aliases: list[str]) -> None:
    if not name:
        raise ProfileError("name is required, e.g. ACME Bank")
    if "/" in name:
        raise ProfileError("name cannot contain '/'")
    if kind not in KINDS:
        raise ProfileError("kind must be customer or partner")
    registry = Registry(profile.accounts, load_rules(profile.data.get("rules_pack")).internal_account)
    for n in [name, *aliases]:
        hit = registry.canonical(n)
        if hit:
            raise ProfileError(f'"{n}" already belongs to the account "{hit}". '
                               "Use that account, or pick a name that is not in use.")


def _countries(profile) -> list[str]:
    internal = set(profile.data["workspace"].get("internal_folders") or [])
    return sorted(d.name for d in profile.workspace_root.iterdir()
                  if d.is_dir() and not HIDDEN.match(d.name) and d.name not in internal)


def _inside(root: Path, rel: str) -> Path:
    parts = Path(rel).parts
    if not parts or Path(rel).is_absolute() or any(p in ("..", ".") or HIDDEN.match(p) for p in parts):
        raise ProfileError(f"folder '{rel}' must be a plain path inside the workspace, not starting with _ or .")
    final = (root / rel).resolve()
    if root.resolve() not in final.parents:
        raise ProfileError(f"folder '{rel}' is outside the workspace root")
    return final


def _folder_plan(profile, name: str, country: str | None, folder: str | None, extra: list[str]):
    root = profile.workspace_root
    if folder:
        rel = folder.strip().strip("/")
    elif (profile.data["workspace"].get("account_folder_level") or 1) == 2:
        if not country:
            return {"need": "country", "choices": _countries(profile)}
        rel = f"{country.strip()}/{name}"
    else:
        rel = name
    final = _inside(root, rel)
    if final.exists() and not final.is_dir():
        raise ProfileError(f"{final} exists and is a file, not a folder")
    layout = list(DEFAULT_LAYOUT) + [x for x in extra if x not in DEFAULT_LAYOUT]
    for x in layout:
        if "/" in x or x in ("..", "."):
            raise ProfileError(f"layout folder '{x}' must be a single folder name")
    to_create = [] if final.exists() else [str(final)]
    to_create += [str(final / x) for x in layout if not (final / x).exists()]
    return {"path": str(final), "action": "reuse" if final.exists() else "create",
            "layout": layout, "to_create": to_create}


def _header(text: str) -> str:
    """Keep the comment lines at the top of the profile (safe_dump drops them)."""
    lines = []
    for line in text.splitlines(keepends=True):
        if not (line.startswith("#") or not line.strip()):
            break
        lines.append(line)
    return "".join(lines)


def _apply(profile, plan: dict) -> dict:
    path = profile.path
    backup = path.with_name(f"{path.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(path, backup)
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text) or {}
    raw["accounts"] = (raw.get("accounts") or []) + [plan["account"]]
    path.write_text(_header(text) + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    try:
        load_profile(str(path))
    except ProfileError:
        shutil.copy2(backup, path)  # put the profile back exactly as it was
        raise
    created = []
    if plan["folder"]:
        for d in plan["folder"]["to_create"]:
            Path(d).mkdir(parents=True, exist_ok=True)
            created.append(d)
    audit = Ledger(profile.data_dir).audit
    audit.parent.mkdir(parents=True, exist_ok=True)
    with open(audit, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": _now(), "event": "account_added",
                            "account": plan["account"]["name"], "folders_created": created},
                           ensure_ascii=False) + "\n")
    return {**plan, "status": "added", "backup": str(backup), "folders_created": created}


def add(name: str, *, profile: str | None = None, kind: str = "customer", country: str | None = None,
        aliases=None, domains=None, folder: str | None = None, extra_folders=None,
        make_folder: bool = True, confirm: bool = False) -> dict:
    p = load_profile(profile)
    name = (name or "").strip()
    aliases = _clean_list(aliases)
    domains = _clean_list(domains)
    _check_account(p, name, kind, aliases)
    entry: dict = {"name": name, "kind": kind}
    if aliases:
        entry["aliases"] = aliases
    if domains:
        entry["domains"] = domains
    folder_plan = None
    if make_folder and p.workspace_root:
        folder_plan = _folder_plan(p, name, country, folder, _clean_list(extra_folders))
        if "need" in folder_plan:
            return {"ok": False, "need": "country", "choices": folder_plan["choices"],
                    "question": "Which country folder should the new customer go in?"}
    plan = {"ok": True, "status": "plan", "account": entry, "folder": folder_plan, "profile": str(p.path)}
    if not confirm:
        return plan
    return _apply(p, plan)
