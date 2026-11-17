"""Personal profile: the only file a user edits (setup writes it)."""
from __future__ import annotations

import copy
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

PROFILE_ENV = "SFAL_PROFILE"
DEFAULT_PROFILE = Path("~/.sf-activity-log/profile.yaml").expanduser()

SOURCES = ("calendar", "email", "files", "notes", "imports", "gbrain")
ACTIVITY_SOURCES = ("calendar", "email", "notes", "imports")

DEFAULTS: dict = {
    "owner": {"name": None, "email": None, "aliases": [], "email_domains": []},
    "timezone": "Asia/Singapore",
    "data_dir": None,
    "mirror_to": "~/Downloads",
    "workspace": {"root": None, "account_folder_level": None, "ignore": [], "internal_folders": ["_Internal"]},
    "sources": {
        "calendar": {"enabled": True, "eventkit_source": "Exchange",
                     "ignore_titles": [], "broadcast_threshold": 40},
        "email": {"enabled": False, "account": "Exchange", "mailboxes": ["Sent Items"], "ignore_subjects": []},
        "files": {"enabled": False, "burst_min_files": 4, "burst_times": [], "link_window_days": 3},
        "notes": {"enabled": False, "path": None, "save_to": "central"},
        "imports": {"enabled": False},
        "gbrain": {"enabled": False},
    },
    "rules_pack": None,
    "accounts": [],
    "policy_overrides": {"demo_inside_poc_logs_separately": True},
    "docs_mirror": {"enabled": False, "output": "~/.sf-activity-log/docs-mirror", "accounts": [],
                    "exclude_accounts": [], "include": ["docx", "pdf", "pptx"],
                    "excel_name_match": ["rfp", "compliance", "requirement", "clarification"],
                    "max_size_mb": 20, "skip_folders": ["Archive", "Old", "Drafts"], "extra_folders": [],
                    "gbrain_import": False, "gbrain_source": "docs"},
}


class ProfileError(Exception):
    pass


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _path(p) -> Path | None:
    return Path(os.path.expanduser(str(p))).resolve() if p else None


@dataclass
class Profile:
    data: dict
    path: Path

    # --- core ---
    @property
    def owner(self) -> str:
        return self.data["owner"]["name"]

    @property
    def my_emails(self) -> set[str]:
        o = self.data["owner"]
        return {e.lower() for e in [o.get("email")] + list(o.get("aliases") or []) if e}

    def is_me(self, name: str | None, email: str | None, flagged: bool = False) -> bool:
        """macOS does not flag every address of yours (e.g. a second company domain) as 'me'."""
        if flagged:
            return True
        if email and email.lower() in self.my_emails:
            return True
        return bool(name and self.owner and name.strip().lower() == self.owner.strip().lower())

    @property
    def internal_domains(self) -> list[str]:
        return [d.lower() for d in self.data["owner"].get("email_domains") or []]

    @property
    def timezone(self) -> str:
        return self.data["timezone"]

    @property
    def data_dir(self) -> Path:
        return _path(self.data["data_dir"])

    @property
    def mirror_to(self) -> Path | None:
        return _path(self.data.get("mirror_to"))

    @property
    def workspace_root(self) -> Path | None:
        return _path(self.data["workspace"].get("root"))

    @property
    def accounts(self) -> list[dict]:
        return self.data.get("accounts") or []

    @property
    def policy(self) -> dict:
        return self.data.get("policy_overrides") or {}

    # --- sources ---
    def source(self, name: str) -> dict:
        return self.data["sources"].get(name) or {}

    def enabled_sources(self, only: list[str] | None = None, without: list[str] | None = None) -> list[str]:
        if only:
            bad = [s for s in only if s not in SOURCES]
            if bad:
                raise ProfileError(f"unknown source(s) in --only: {', '.join(bad)}")
            chosen = list(only)
        else:
            chosen = [s for s in SOURCES if self.source(s).get("enabled")]
        chosen = [s for s in chosen if s not in (without or [])]
        if not any(s in ACTIVITY_SOURCES for s in chosen):
            raise ProfileError(
                "no activity-producing source enabled; enable at least one of: "
                + ", ".join(ACTIVITY_SOURCES))
        return chosen


def validate(data: dict) -> list[str]:
    errs = []
    if not data["owner"].get("name"):
        errs.append("owner.name is required (used as Salesforce Primary Owner)")
    if not data.get("data_dir"):
        errs.append("data_dir is required")
    if data.get("rules_pack") is not None and not isinstance(data["rules_pack"], str):
        errs.append("rules_pack must be a path to a YAML file, e.g. ~/my-rules.yaml")
    for s in data["sources"]:
        if s not in SOURCES:
            errs.append(f"sources.{s}: unknown source (valid: {', '.join(SOURCES)})")
    for i, a in enumerate(data.get("accounts") or []):
        if not a.get("name"):
            errs.append(f"accounts[{i}]: name is required")
        if a.get("kind", "customer") not in ("customer", "partner"):
            errs.append(f"accounts[{i}] {a.get('name')}: kind must be customer or partner")
    if data["sources"].get("files", {}).get("enabled") and not data["workspace"].get("root"):
        errs.append("sources.files is enabled but workspace.root is not set")
    save_to = data["sources"].get("notes", {}).get("save_to", "central")
    if save_to not in ("central", "customer_folder"):
        errs.append("sources.notes.save_to must be central or customer_folder")
    if save_to == "customer_folder" and not data["workspace"].get("root"):
        errs.append("sources.notes.save_to is customer_folder but workspace.root is not set")
    dm = data.get("docs_mirror") or {}
    for key in ("accounts", "exclude_accounts", "include", "excel_name_match", "skip_folders", "extra_folders"):
        if not isinstance(dm.get(key) or [], list):
            errs.append(f"docs_mirror.{key} must be a list, e.g. [a, b]")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", str(dm.get("gbrain_source") or "docs")):
        errs.append("docs_mirror.gbrain_source must be a short id: lowercase letters, digits, - or _")
    if dm.get("enabled") and not data["workspace"].get("root") and not dm.get("extra_folders"):
        errs.append("docs_mirror is enabled but workspace.root is not set")
    return errs


def profile_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    if os.environ.get(PROFILE_ENV):
        return Path(os.environ[PROFILE_ENV]).expanduser()
    return DEFAULT_PROFILE


def load_profile(explicit: str | None = None) -> Profile:
    p = profile_path(explicit)
    if not p.exists():
        raise ProfileError(f"profile not found at {p}; run setup (sfal profile init) first")
    with open(p, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    data = _merge(DEFAULTS, raw)
    errs = validate(data)
    if errs:
        raise ProfileError("profile invalid:\n  - " + "\n  - ".join(errs))
    return Profile(data=data, path=p)
