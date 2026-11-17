"""Catalog: every note (customer folders + central), every record, every period - one page."""
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

from sfal import api, catalog
from sfal import notes_writer as W
from sfal.evidence import make_id
from sfal.ledger import Ledger
from sfal.profile import load_profile
from sfal.render import render
from sfal.rules import load_rules

RULES = load_rules()
NOTE = {"title": "ACME Bank - incident summarisation demo", "topic": "incident summarisation demo",
        "account": "ACME Bank", "activity_date": "2026-10-15",
        "summary": "Demoed incident summarisation to the ACME ITSM team.",
        "activities": [{"title": "Incident summarisation demo", "what": "Live demo on the ACME sandbox.",
                        "duration_hours": 1.5, "hours_source": "user", "hours_quote": "an hour and a half",
                        "evidence": []}],
        "follow_ups": ["Send pricing by Friday"]}
FOLDER_NOTE = """# Globex discovery recap

**Activity date:** 14-Oct-2026 · **Duration:** 2h

## Summary

Discovery workshop with the Globex service desk team.

## Next steps

- [ ] Share the CMDB questionnaire
"""


def row(account, refs, hours="1.5", **kw):
    r = {"account_name": account, "account_kind": "customer", "activity_type": "07 · Product Demo",
         "status": "Completed", "activity_date": "2026-10-15", "activity_hours": hours, "prep_hours": "0",
         "notes": "Demo.", "no_opp_reason": "Early stage", "solution_area": ["ITSM"], "evidence_refs": refs,
         "confidence": "High"}
    r.update(kw)
    return {"action": "new", "row": r}


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        folder = self.tmp / "ws" / "Malaysia" / "Globex" / "_ActivityLogging"
        folder.mkdir(parents=True)
        (folder / "2026-10-14_0900_globex-discovery.md").write_text(FOLDER_NOTE)
        (self.tmp / "ws" / "_ActivityLogging").mkdir()
        (self.tmp / "ws" / "_ActivityLogging" / "runbook.md").write_text("# old pipeline runbook\n")
        data = {"owner": {"name": "Lee, Sam", "email_domains": ["corp.example"]}, "data_dir": str(self.tmp / "data"),
                "mirror_to": None, "workspace": {"root": str(self.tmp / "ws"), "ignore": ["_ActivityLogging/*"]},
                "sources": {"calendar": {"enabled": False}, "notes": {"enabled": True}},
                "accounts": [{"name": "ACME Bank", "kind": "customer", "aliases": ["ACME"]},
                             {"name": "Globex", "kind": "customer"}]}
        (self.tmp / "p.yaml").write_text(yaml.safe_dump(data))
        self.p = load_profile(str(self.tmp / "p.yaml"))
        self.saved = Path(W.save(self.p, RULES, NOTE, "central")["path"])
        self.acme_id = make_id("note", "central/" + self.saved.relative_to(self.p.data_dir / "notes").as_posix())
        led = Ledger(self.p.data_dir)
        led.apply([row("ACME Bank", [self.acme_id]), row("Globex", [], hours="[to confirm]")],
                  run_id="r1", owner="Lee, Sam", timezone="Asia/Singapore", rule_pack_version="t")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_every_note_from_both_locations(self):
        d = catalog.collect(self.p, RULES)
        titles = {n["title"]: n for n in d["notes"]}
        self.assertEqual(set(titles), {"ACME Bank - incident summarisation demo", "Globex discovery recap"})
        self.assertEqual(titles["ACME Bank - incident summarisation demo"]["where"], "central")
        g = titles["Globex discovery recap"]
        self.assertEqual((g["where"], g["account"], g["date"], g["hours"]),
                         ("customer folder", "Globex", "2026-10-14", 2.0))   # account from the folder
        self.assertEqual(g["follow_ups"], ["Share the CMDB questionnaire"])

    def test_logged_badge_comes_from_ledger_evidence(self):
        d = catalog.collect(self.p, RULES)
        by = {n["title"]: n for n in d["notes"]}
        self.assertEqual(by["ACME Bank - incident summarisation demo"]["logged_by"], ["A0001"])
        self.assertEqual(by["Globex discovery recap"]["logged_by"], [])
        recs = {r["id"]: r for r in d["records"]}
        acme = by["ACME Bank - incident summarisation demo"]
        self.assertEqual(recs["A0001"]["note_ids"], [acme["id"]])     # old path id maps to the note
        self.assertIn(self.acme_id, acme["legacy_ids"])
        self.assertFalse(recs["A0001"]["held"])
        self.assertTrue(recs["A0002"]["held"])                                # hours [to confirm]

    def test_voided_rows_are_kept_and_marked(self):
        Ledger(self.p.data_dir).apply([{"action": "void", "entry_id": "A0001", "reason": "duplicate"}],
                                      run_id="r2", owner="Lee, Sam", timezone="Asia/Singapore", rule_pack_version="t")
        d = catalog.collect(self.p, RULES)
        self.assertTrue({r["id"]: r for r in d["records"]}["A0001"]["voided"])
        self.assertEqual({n["title"]: n for n in d["notes"]}["ACME Bank - incident summarisation demo"]["logged_by"], [])

    def test_periods_from_rendered_output(self):
        render(self.p, RULES, date(2026, 10, 12), date(2026, 10, 18), mirror=False)
        per = catalog.collect(self.p, RULES)["periods"]
        self.assertEqual(len(per), 1)
        self.assertEqual((per[0]["kind"], per[0]["from"], per[0]["to"], per[0]["records"], per[0]["held"]),
                         ("week", "2026-10-12", "2026-10-18", 2, 1))
        self.assertTrue(per[0]["xlsx"].startswith("file://"))

    def test_page_is_written_inside_the_log_folder_and_safe(self):
        res = catalog.build(self.p, RULES)
        path = Path(res["path"])
        self.assertEqual(path, (self.p.data_dir / "catalog" / "index-modern.html").resolve())
        self.assertFalse((self.p.data_dir / "catalog" / "index.html").exists())  # retired
        text = path.read_text()
        self.assertNotIn("onclick=", text)                      # one delegated listener, no inline handlers
        self.assertIn('data-t="calendar"', text)                # Calendar tab
        for col in ("date", "account", "type"):                # sortable Records columns
            self.assertIn(f'["{col}",', text)
        data = json.loads(text.split('<script type="application/json" id="data">')[1].split("</script>")[0])
        self.assertEqual(len(data["notes"]), 2)

    def test_html_in_notes_cannot_break_the_page(self):
        self.saved.write_text(self.saved.read_text() + "\n</script><script>alert(1)</script>\n")
        text = Path(catalog.build(self.p, RULES)["path"]).read_text()
        self.assertNotIn("</script><script>alert(1)", text)

    def test_moving_a_logged_note_keeps_it_logged(self):
        catalog.collect(self.p, RULES)                           # first scan records today's paths
        dest = self.tmp / "ws" / "Malaysia" / "Globex" / "_ActivityLogging" / self.saved.name
        shutil.move(self.saved, dest)                            # a central note moved into a folder
        by = {n["title"]: n for n in catalog.collect(self.p, RULES)["notes"]}
        moved = by["ACME Bank - incident summarisation demo"]
        self.assertEqual(moved["where"], "customer folder")
        self.assertEqual(moved["logged_by"], ["A0001"])

    def test_folder_note_survives_a_folder_rename(self):
        Ledger(self.p.data_dir).apply([row("Globex", [{n["title"]: n for n in catalog.collect(self.p, RULES)["notes"]}["Globex discovery recap"]["id"]])],
                                      run_id="r3", owner="Lee, Sam", timezone="Asia/Singapore", rule_pack_version="t")
        old = self.tmp / "ws" / "Malaysia" / "Globex"
        (self.tmp / "ws" / "Partners").mkdir()
        shutil.move(old, self.tmp / "ws" / "Partners" / "Globex")
        g = {n["title"]: n for n in catalog.collect(self.p, RULES)["notes"]}["Globex discovery recap"]
        self.assertEqual(g["folder"], "Partners/Globex")
        self.assertEqual(g["logged_by"], ["A0003"])

    def test_note_save_rebuilds_the_catalog(self):
        old = self.tmp / "p.yaml"
        res = api.note_save(dict(NOTE, title="ACME Bank - pricing follow-up"), "central", profile=str(old))
        self.assertTrue(res["catalog"].endswith("catalog/index-modern.html"))
        self.assertIn("ACME Bank - pricing follow-up", Path(res["catalog"]).read_text())


if __name__ == "__main__":
    unittest.main()
