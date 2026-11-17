"""Ledger - the single source of truth, and its only writer.

Rules:
  * Rows are never deleted. A correction voids the old row (voided/voided_by are the
    only fields ever changed after a row is written) and appends a superseding row.
  * Every write is recorded in ledger/audit.log (JSON lines).
  * A lock file guards against two writers (e.g. two Macs syncing via OneDrive).
"""
from __future__ import annotations

import csv
import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

COLUMNS = [
    "entry_id", "owner", "account_name", "account_kind", "activity_type", "opportunity",
    "no_opp_reason", "status", "activity_date", "start_date", "activity_hours", "prep_hours",
    "notes", "solution_area", "timezone", "evidence_refs", "consolidation_key",
    "rule_pack_version", "voided", "voided_by", "supersedes", "run_id", "to_confirm",
    "confidence", "added_on",
]
LIST_FIELDS = ("solution_area", "evidence_refs")
TO_CONFIRM = "[to confirm]"


class LedgerError(Exception):
    pass


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Ledger:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir) / "ledger"
        self.path = self.dir / "ledger.csv"
        self.audit = self.dir / "audit.log"

    # ---------- reading ----------
    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, newline="", encoding="utf-8") as f:
            return [self._decode(r) for r in csv.DictReader(f)]

    def active(self) -> list[dict]:
        return [r for r in self.rows() if not r["voided"]]

    def get(self, entry_id: str) -> dict | None:
        return next((r for r in self.rows() if r["entry_id"] == entry_id), None)

    @staticmethod
    def _decode(r: dict) -> dict:
        r = dict(r)
        for k in LIST_FIELDS:
            r[k] = [x for x in (r.get(k) or "").split(";") if x]
        r["voided"] = (r.get("voided") or "").lower() == "true"
        for k in ("activity_hours", "prep_hours"):
            v = r.get(k) or ""
            try:
                r[k] = float(v) if v not in ("", TO_CONFIRM) else (TO_CONFIRM if v == TO_CONFIRM else 0.0)
            except ValueError:
                r[k] = v
        return r

    @staticmethod
    def _encode(r: dict) -> dict:
        out = {}
        for k in COLUMNS:
            v = r.get(k, "")
            if k in LIST_FIELDS and isinstance(v, (list, tuple)):
                v = ";".join(str(x) for x in v)
            elif k == "voided":
                v = "true" if v else "false"
            elif isinstance(v, float):
                v = f"{v:g}"
            out[k] = "" if v is None else v
        return out

    # ---------- writing ----------
    @contextmanager
    def _locked(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / ".lock", "w") as lk:
            try:
                fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise LedgerError("ledger is locked by another process; try again") from None
            try:
                yield
            finally:
                fcntl.flock(lk, fcntl.LOCK_UN)

    def _write_all(self, rows: list[dict]) -> None:
        tmp = self.path.with_suffix(".csv.tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            for r in rows:
                w.writerow(self._encode(r))
        os.replace(tmp, self.path)

    def _log(self, event: dict) -> None:
        with open(self.audit, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": _now(), **event}, ensure_ascii=False) + "\n")

    @staticmethod
    def _next_id(rows: list[dict]) -> str:
        nums = [int(r["entry_id"][1:]) for r in rows if r["entry_id"][1:].isdigit()]
        return f"A{(max(nums) + 1 if nums else 1):04d}"

    def apply(self, changes: list[dict], *, run_id: str, owner: str, timezone: str,
              rule_pack_version: str) -> list[dict]:
        """Apply approved changes atomically.

        Each change: {"action": "new"|"extend"|"void", "row": {...}, "supersedes": id, "entry_id": id, "reason": str}
        Returns the written/affected rows.
        """
        with self._locked():
            rows = self.rows()
            by_id = {r["entry_id"]: r for r in rows}
            written = []
            for c in changes:
                action = c["action"]
                if action == "void":
                    old = by_id.get(c["entry_id"])
                    if not old or old["voided"]:
                        raise LedgerError(f"cannot void {c['entry_id']}: missing or already void")
                    old["voided"], old["voided_by"] = True, c.get("reason") and f"manual: {c['reason']}" or "manual"
                    written.append(old)
                    self._log({"op": "void", "entry_id": old["entry_id"], "reason": c.get("reason"), "run_id": run_id})
                    continue

                row = {k: "" for k in COLUMNS}
                row.update({k: v for k, v in c["row"].items() if k in COLUMNS})
                row.update({
                    "entry_id": self._next_id(rows), "owner": owner, "timezone": timezone,
                    "rule_pack_version": rule_pack_version, "run_id": run_id,
                    "voided": False, "voided_by": "", "added_on": _now(),
                })
                if action == "extend":
                    old = by_id.get(c["supersedes"])
                    if not old or old["voided"]:
                        raise LedgerError(f"cannot extend {c['supersedes']}: missing or already void")
                    old["voided"], old["voided_by"] = True, row["entry_id"]
                    row["supersedes"] = old["entry_id"]
                elif action != "new":
                    raise LedgerError(f"unknown action {action}")
                rows.append(row)
                by_id[row["entry_id"]] = row
                written.append(row)
                self._log({"op": action, "entry_id": row["entry_id"], "supersedes": row.get("supersedes"),
                           "run_id": run_id})
            self._write_all(rows)
            return written
