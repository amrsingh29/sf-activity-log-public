"""A note keeps its identity when it moves: already logged stays logged, never offered twice."""
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

from sfal import notes_writer as W
from sfal.ledger import Ledger
from sfal.prepare import prepare, run_dir
from sfal.profile import load_profile
from sfal.rules import load_rules
from sfal.sources import notes as N
from sfal.validate import Validator

RULES = load_rules()
NOTE = {"title": "ACME Bank - incident summarisation demo", "account": "ACME Bank", "activity_date": "2026-10-15",
        "summary": "Demoed incident summarisation.",
        "activities": [{"title": "Demo", "what": "Live demo.", "duration_hours": 1.5, "hours_source": "user",
                        "hours_quote": "an hour and a half", "evidence": []}]}
LEGACY_NOTE = "# Globex recap\n\n**Activity date:** 14-Oct-2026 · **Duration:** 2h\n\n## Summary\n\nWorkshop.\n"


def row(account, refs):
    return {"action": "new", "row": {
        "account_name": account, "account_kind": "customer", "activity_type": "07 · Product Demo",
        "status": "Completed", "activity_date": "2026-10-15", "activity_hours": "1.5", "prep_hours": "0",
        "notes": "Demo.", "no_opp_reason": "Early stage", "solution_area": ["ITSM"], "evidence_refs": refs,
        "confidence": "High"}}


class TestNoteIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.kdn = self.tmp / "ws" / "Malaysia" / "ACME Bank" / "_ActivityLogging"
        self.kdn.mkdir(parents=True)
        (self.tmp / "ws" / "Partners").mkdir()
        data = {"owner": {"name": "Lee, Sam", "email_domains": ["corp.example"]}, "data_dir": str(self.tmp / "data"),
                "mirror_to": None, "workspace": {"root": str(self.tmp / "ws")},
                "sources": {"calendar": {"enabled": False}, "email": {"enabled": False},
                            "files": {"enabled": False}, "notes": {"enabled": True}},
                "accounts": [{"name": "ACME Bank", "kind": "customer"}, {"name": "Globex", "kind": "customer"}]}
        (self.tmp / "p.yaml").write_text(yaml.safe_dump(data))
        self.p = load_profile(str(self.tmp / "p.yaml"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def week(self):
        res = prepare(self.p, RULES, date(2026, 10, 12), date(2026, 10, 18), only=["notes"])
        ev = json.loads((run_dir(self.p, res["run_id"]) / "evidence.json").read_text())
        return res, ev

    def test_new_notes_carry_a_note_id(self):
        path = Path(W.save(self.p, RULES, NOTE, "central")["path"])
        n = N.parse_note(path, 2026)
        self.assertRegex(n["note_id"], r"^[0-9a-f]{16}$")

    def test_moved_logged_note_is_not_offered_again(self):
        path = Path(W.save(self.p, RULES, NOTE, "central")["path"])
        _, ev = self.week()
        old_id = ev["items"][0]["id"]
        Ledger(self.p.data_dir).apply([row("ACME Bank", [old_id])], run_id="r1", owner="Lee, Sam",
                                      timezone="Asia/Singapore", rule_pack_version="t")
        shutil.move(path, self.kdn / path.name)                       # moved into a customer folder
        res, ev2 = self.week()
        self.assertEqual(ev2["items"][0]["id"], old_id)               # same id: it is the note's own
        self.assertEqual([x["entry_id"] for x in res["already_logged"]], ["A0001"])
        self.assertEqual(res["new_evidence"], [])

    def test_legacy_note_logged_by_path_survives_a_folder_move(self):
        (self.kdn / "2026-10-14_0900_globex-recap.md").write_text(LEGACY_NOTE)   # no note-id: older note
        legacy_path_id = N.make_id("note", "Malaysia/ACME Bank/_ActivityLogging/2026-10-14_0900_globex-recap.md")
        Ledger(self.p.data_dir).apply([row("Globex", [legacy_path_id])], run_id="r1", owner="Lee, Sam",
                                      timezone="Asia/Singapore", rule_pack_version="t")
        self.week()                                                   # the scan records the current path
        shutil.move(self.tmp / "ws" / "Malaysia" / "ACME Bank", self.tmp / "ws" / "Partners" / "ACME Bank")
        res, ev = self.week()
        self.assertEqual([x["entry_id"] for x in res["already_logged"]], ["A0001"])
        self.assertEqual(res["already_logged_summary"]["records"], 1)
        # and logging it again is refused (C16), even under its new id
        result = Validator(self.p, RULES, ev, Ledger(self.p.data_dir).rows()).run(
            {"changes": [row("Globex", [ev["items"][0]["id"]])]})
        self.assertTrue(any(e["code"] == "C16" for e in result["errors"]))

    def test_copied_note_falls_back_to_path_ids(self):
        path = Path(W.save(self.p, RULES, NOTE, "central")["path"])
        shutil.copy(path, self.kdn / path.name)                       # same note-id twice
        ids = [r["id"] for r in N.identify(self.p, 2026)]
        self.assertEqual(len(set(ids)), 2)


if __name__ == "__main__":
    unittest.main()
