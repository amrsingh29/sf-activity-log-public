"""Common evidence format shared by every source.

Every source returns a list of dicts with these keys (missing values are None/[]):
  id           stable id, prefixed by source ("cal:…", "mail:…", "file:…", "note:…", "imp:…")
  source       calendar | email | files | notes | imports | gbrain
  kind         meeting | email | file | note | other
  date         ISO date the evidence belongs to
  start, end   ISO datetimes with offset (meetings), else None
  hours        exact hours if the source states them (calendar duration), else None
  title        subject / meeting title / file name
  people       display names (bounded)
  domains      external email domains involved
  account_hint {name, kind, via} filled by account matching, or None
  flags        list of short machine flags (e.g. "broadcast", "rsvp_unknown")
  excluded     reason string when the engine drops it as noise, else None
  completeness complete | partial
  raw_ref      pointer back into the cached raw data
"""
from __future__ import annotations

import hashlib


def make_id(prefix: str, *parts: str) -> str:
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{h}"


def item(**kw) -> dict:
    base = {
        "id": None, "source": None, "kind": "other", "date": None, "start": None, "end": None,
        "hours": None, "title": "", "people": [], "domains": [], "account_hint": None,
        "flags": [], "excluded": None, "completeness": "complete", "raw_ref": None,
    }
    base.update(kw)
    return base
