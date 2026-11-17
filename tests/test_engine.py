"""Engine tests - run with: .venv/bin/python -m unittest discover -s tests -v

No EventKit needed: calendar tests feed the helper's JSON shape straight into normalize().
"""
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

from sfal.accounts import Registry
from sfal.ledger import TO_CONFIRM, Ledger
from sfal.period import PeriodError, resolve
from sfal.profile import ProfileError, load_profile
from sfal.render import render as render_md
from sfal.rules import load_rules
from sfal.safety import BoundaryError, write_text
from sfal.sources.calendar import normalize
from sfal.validate import Validator, approval_code

RULES = load_rules()
INTERNAL = RULES.internal_account


def ev(ext, start, end, title, attendees=(), my_status="accepted", cancelled=False, all_day=False, org_me=False):
    return {"external_id": ext, "start": start, "end": end, "title": title, "all_day": all_day,
            "cancelled": cancelled, "recurring": False, "location": "", "calendar": "Calendar",
            "source": "Exchange", "my_status": my_status, "timezone": "Asia/Singapore",
            "organizer": {"name": "Org", "email": "org@mycompany.example", "is_me": org_me},
            "attendees": [{"name": n, "email": m, "status": "accepted", "is_me": False, "role": 1}
                          for n, m in attendees]}


RAW = {"status": "ok", "events": [
    ev("e1", "2026-10-06T10:00:00+08:00", "2026-10-06T12:00:00+08:00", "PROSEWARE OMA POC working session",
       [("Ali", "ali@proseware.com.my")]),
    ev("e2", "2026-10-06T09:00:00+08:00", "2026-10-06T10:00:00+08:00", "PROSEWARE demo prep",
       [("Bee", "bee@mycompany.example")]),
    ev("e3", "2026-10-07T14:00:00+08:00", "2026-10-07T15:30:00+08:00", "WOODGROVE HelixGPT demo",
       [("Tan", "tan@woodgrove.com")]),
    ev("e4", "2026-10-07T12:30:00+08:00", "2026-10-07T13:30:00+08:00", "Lunch Time"),
    ev("e5", "2026-10-08T10:00:00+08:00", "2026-10-08T11:00:00+08:00", "Canceled: CONTOSO sync", cancelled=True),
    ev("e6", "2026-10-08T11:00:00+08:00", "2026-10-08T12:00:00+08:00", "EPF discovery", my_status="declined"),
    ev("e7", "2026-10-09T00:00:00+08:00", "2026-10-10T00:00:00+08:00", "Holiday", all_day=True),
    ev("e8", "2026-10-09T15:00:00+08:00", "2026-10-09T16:00:00+08:00", "APAC all hands",
       [(f"P{i}", f"p{i}@mycompany.example") for i in range(60)]),
    ev("e9", "2026-10-09T10:00:00+08:00", "2026-10-09T11:00:00+08:00", "NORTHWIND TAILSPIN ITSM workshop",
       [("Lim", "lim@northwind.com.sg")]),
]}

PROFILE = {
    "owner": {"name": "Tester, Pat", "email": "pat@mycompany.example", "email_domains": ["mycompany.example"]},
    "timezone": "Asia/Singapore",
    "sources": {"calendar": {"enabled": True, "ignore_titles": ["lunch time"], "broadcast_threshold": 40}},
    "accounts": [
        {"name": "PROSEWARE", "kind": "customer", "aliases": ["Proseware OMA"], "domains": ["proseware.com.my"]},
        {"name": "WOODGROVE", "kind": "customer", "domains": ["woodgrove.com"]},
        {"name": "TAILSPIN", "kind": "customer"},
        {"name": "CONTOSO", "kind": "customer"},
        {"name": "NORTHWIND", "kind": "partner", "domains": ["northwind.com.sg"]},
        {"name": "WINGTIP", "kind": "partner"},
    ],
}


class Env(unittest.TestCase):
    """Temp data dir + profile + one prepared run built from RAW."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        prof = dict(PROFILE, data_dir=str(self.tmp / "data"), mirror_to=str(self.tmp / "mirror"))
        self.ppath = self.tmp / "profile.yaml"
        self.ppath.write_text(yaml.safe_dump(prof))
        self.profile = load_profile(str(self.ppath))
        self.items = normalize(RAW, self.profile, RULES)
        reg = Registry(self.profile.accounts, INTERNAL)
        for x in self.items:
            if not x["excluded"]:
                x["account_hint"] = reg.match([x["title"]], x["domains"], "internal_only" in x["flags"])
        self.evidence = {"run_id": "r1", "period": {"from": "2026-10-05", "to": "2026-10-11"}, "items": self.items}
        self.by_title = {x["title"]: x for x in self.items}
        self.ledger = Ledger(self.profile.data_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def eid(self, title):
        return self.by_title[title]["id"]

    def validate(self, *changes):
        return Validator(self.profile, RULES, self.evidence, self.ledger.rows()).run({"changes": list(changes)})

    def codes(self, res):
        return {e["code"] for e in res["errors"]}

    def wcodes(self, res):
        return {e["code"] for e in res["warnings"]}

    def good_demo(self, **over):
        row = {"account_name": "WOODGROVE", "account_kind": "customer", "activity_type": "07 · Product Demo",
               "no_opp_reason": "Opportunity not created yet", "status": "Completed",
               "activity_date": "2026-10-07", "activity_hours": 1.5, "prep_hours": 0,
               "notes": "Delivered HelixGPT demo to the WOODGROVE ITSM team covering incident summarisation.",
               "solution_area": ["ITSM"], "evidence_refs": [self.eid("WOODGROVE HelixGPT demo")], "confidence": "High"}
        row.update(over)
        return {"action": "new", "row": row}

    def poc_row(self, **over):
        row = {"account_name": "PROSEWARE", "account_kind": "customer", "activity_type": "09 · POC/POV",
               "no_opp_reason": TO_CONFIRM, "status": "In Progress", "activity_date": "2026-10-06",
               "start_date": "2026-10-06", "activity_hours": 2, "prep_hours": 0,
               "notes": "OMA POC working session: configured event ingestion and validated success criteria 1-3.",
               "solution_area": ["AIOps"], "evidence_refs": [self.eid("PROSEWARE OMA POC working session")],
               "consolidation_key": "POC|PROSEWARE|OMA", "confidence": "High"}
        row.update(over)
        return {"action": "new", "row": row}

    def commit(self, *changes, run_id="r1"):
        res = self.validate(*changes)
        self.assertTrue(res["ok"], res["errors"])
        return self.ledger.apply(list(changes), run_id=run_id, owner=self.profile.owner,
                                 timezone=self.profile.timezone, rule_pack_version=RULES.version)


# ---------------------------------------------------------------- period
class TestPeriod(unittest.TestCase):
    T = date(2026, 10, 14)  # Wednesday

    def test_weeks(self):
        self.assertEqual(resolve("last week", self.T), (date(2026, 10, 5), date(2026, 10, 11)))
        self.assertEqual(resolve("this week", self.T), (date(2026, 10, 12), date(2026, 10, 18)))

    def test_months_and_ranges(self):
        self.assertEqual(resolve("September", self.T), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual(resolve("november", self.T), (date(2025, 11, 1), date(2025, 11, 30)))
        self.assertEqual(resolve("2026-10-01 to 2026-10-03", self.T), (date(2026, 10, 1), date(2026, 10, 3)))
        self.assertEqual(resolve("last 7 days", self.T), (date(2026, 10, 8), date(2026, 10, 14)))

    def test_bad(self):
        with self.assertRaises(PeriodError):
            resolve("whenever", self.T)
        with self.assertRaises(PeriodError):
            resolve("2026-10-05 to 2026-10-01", self.T)


# ---------------------------------------------------------------- profile
class TestProfile(Env):
    def test_only_without(self):
        self.assertEqual(self.profile.enabled_sources(), ["calendar"])
        with self.assertRaises(ProfileError):
            self.profile.enabled_sources(without=["calendar"])
        with self.assertRaises(ProfileError):
            self.profile.enabled_sources(only=["gbrain"])  # context-only source cannot run alone
        with self.assertRaises(ProfileError):
            self.profile.enabled_sources(only=["nonsense"])

    def test_missing_owner(self):
        bad = self.tmp / "bad.yaml"
        bad.write_text(yaml.safe_dump({"data_dir": "/tmp/x"}))
        with self.assertRaises(ProfileError):
            load_profile(str(bad))


# ---------------------------------------------------------------- calendar
class TestCalendar(Env):
    def test_exclusions(self):
        ex = {x["title"]: x["excluded"] for x in self.items}
        self.assertEqual(ex["Lunch Time"], "ignored_title")
        self.assertEqual(ex["Canceled: CONTOSO sync"], "cancelled")
        self.assertEqual(ex["EPF discovery"], "declined")
        self.assertEqual(ex["Holiday"], "all_day")
        self.assertIsNone(ex["WOODGROVE HelixGPT demo"])

    def test_flags_and_hours(self):
        self.assertIn("broadcast", self.by_title["APAC all hands"]["flags"])
        self.assertIn("internal_only", self.by_title["APAC all hands"]["flags"])
        self.assertIn("prep_title", self.by_title["PROSEWARE demo prep"]["flags"])
        self.assertIn("demo_title", self.by_title["WOODGROVE HelixGPT demo"]["flags"])
        self.assertEqual(self.by_title["WOODGROVE HelixGPT demo"]["hours"], 1.5)
        self.assertEqual(self.by_title["WOODGROVE HelixGPT demo"]["domains"], ["woodgrove.com"])

    def test_stable_ids(self):
        again = normalize(RAW, self.profile, RULES)
        self.assertEqual([x["id"] for x in again], [x["id"] for x in self.items])


# ---------------------------------------------------------------- accounts
class TestAccounts(Env):
    def test_matching(self):
        reg = Registry(self.profile.accounts, INTERNAL)
        self.assertEqual(reg.match(["WOODGROVE HelixGPT demo"], [])["name"], "WOODGROVE")
        self.assertEqual(reg.match(["random"], ["woodgrove.com"])["via"], ["domain"])
        self.assertIsNone(reg.match(["random"], []))
        self.assertEqual(reg.match(["random"], [], internal_only=True)["name"], INTERNAL)

    def test_partner_deal_routes_to_customer(self):
        m = self.by_title["NORTHWIND TAILSPIN ITSM workshop"]["account_hint"]
        self.assertEqual(m["name"], "TAILSPIN")
        self.assertEqual(m["partners"], ["NORTHWIND"])

    def test_ambiguous(self):
        reg = Registry(self.profile.accounts, INTERNAL)
        m = reg.match(["WOODGROVE and CONTOSO joint session"], [])
        self.assertIsNone(m["name"])
        self.assertEqual(m["candidates"], ["CONTOSO", "WOODGROVE"])

    def test_alias_word_boundary(self):
        reg = Registry(self.profile.accounts, INTERNAL)
        self.assertIsNone(reg.match(["WOODGROVEX meeting"], []))
        self.assertEqual(reg.match(["proseware oma review"], [])["name"], "PROSEWARE")


# ---------------------------------------------------------------- validator
class TestValidator(Env):
    def test_good_row_passes(self):
        res = self.validate(self.good_demo())
        self.assertTrue(res["ok"], res["errors"])
        self.assertTrue(res["approval_code"])

    def test_c01_c02(self):
        self.assertIn("C01", self.codes(self.validate(self.good_demo(activity_type="Demo"))))
        self.assertIn("C02", self.codes(self.validate(self.good_demo(status="Done"))))

    def test_c03_hours(self):
        self.assertIn("C03", self.codes(self.validate(self.good_demo(activity_hours=0))))
        res = self.validate(self.good_demo(activity_hours=TO_CONFIRM))
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["held"]), 1)

    def test_c04_hours_capped_by_evidence(self):
        self.assertIn("C04", self.codes(self.validate(self.good_demo(activity_hours=3))))
        ok = self.validate(self.good_demo(activity_hours=3, evidence_refs=[self.eid("WOODGROVE HelixGPT demo"),
                                                                           "user:confirmed 3h incl. follow-up"]))
        self.assertTrue(ok["ok"], ok["errors"])

    def test_c04_prep_meeting_is_not_delivery(self):
        row = self.good_demo(account_name="PROSEWARE", activity_date="2026-10-06", activity_hours=3, prep_hours=0,
                             evidence_refs=[self.eid("PROSEWARE OMA POC working session"),
                                            self.eid("PROSEWARE demo prep")])
        self.assertIn("C04", self.codes(self.validate(row)))
        row["row"].update(activity_hours=2, prep_hours=1)
        self.assertTrue(self.validate(row)["ok"])

    def test_c05_routing(self):
        self.assertIn("C05", self.codes(self.validate(self.good_demo(account_name="NORTHWIND", account_kind="partner"))))
        self.assertIn("C05", self.codes(self.validate(self.good_demo(account_name="Acme", account_kind="customer"))))
        self.assertIn("C05", self.codes(self.validate(self.good_demo(account_name=INTERNAL, account_kind="customer"))))
        self.assertIn("C05", self.codes(self.validate(self.good_demo(account_name="woodgrove"))))
        enable = self.good_demo(account_name="NORTHWIND", account_kind="partner", activity_type="16 · Enablement - Partner")
        self.assertTrue(self.validate(enable)["ok"])

    def test_c06_c07_opportunity(self):
        self.assertIn("C06", self.codes(self.validate(self.good_demo(no_opp_reason=""))))
        held = self.validate(self.good_demo(no_opp_reason=TO_CONFIRM))
        self.assertTrue(held["ok"])
        self.assertTrue(held["held"])
        poc = self.poc_row()
        self.assertIn("C07", self.wcodes(self.validate(poc)))

    def test_c08_one_record_per_poc(self):
        self.assertIn("C08", self.codes(self.validate(self.poc_row(consolidation_key=""))))
        self.commit(self.poc_row())
        again = self.poc_row(evidence_refs=["user:another session on 8 Oct"], activity_date="2026-10-08")
        self.assertIn("C08", self.codes(self.validate(again)))

    def test_c09_value_review_dates_and_latest_date(self):
        value_review = self.poc_row(activity_type="08 · Value Review", consolidation_key="Value Review|PROSEWARE|2026",
                           notes="Structured value review workshop with the PROSEWARE IT leadership team.")
        self.assertIn("C09", self.codes(self.validate(value_review)))
        value_review["row"]["notes"] += " Start 2026-10-06, end 2026-10-20."
        self.assertTrue(self.validate(value_review)["ok"])
        self.assertIn("C09", self.codes(self.validate(self.poc_row(start_date="2026-10-09"))))

    def test_c10_demo_inside_poc(self):
        bad = self.poc_row(evidence_refs=[self.eid("PROSEWARE OMA POC working session"), self.eid("WOODGROVE HelixGPT demo")],
                           activity_date="2026-10-07", activity_hours=3.5)
        self.assertIn("C10", self.codes(self.validate(bad)))

    def test_c11_pet_admin_demo_prep(self):
        row = self.good_demo(activity_type="22 · Team Administration", account_name=INTERNAL, account_kind="internal")
        self.assertIn("C11", self.wcodes(self.validate(row)))

    def test_c12_evidence(self):
        self.assertIn("C12", self.codes(self.validate(self.good_demo(evidence_refs=[]))))
        self.assertIn("C12", self.codes(self.validate(self.good_demo(evidence_refs=["cal:doesnotexist"]))))
        self.assertIn("C12", self.codes(self.validate(self.good_demo(evidence_refs=[self.eid("Lunch Time")],
                                                                     activity_date="2026-10-07"))))

    def test_c13_date_backed_by_evidence(self):
        self.assertIn("C13", self.codes(self.validate(self.good_demo(activity_date="2026-10-08"))))
        self.assertIn("C13", self.codes(self.validate(self.good_demo(activity_date="7 Oct"))))

    def test_c14_solution_area(self):
        self.assertIn("C14", self.codes(self.validate(self.good_demo(solution_area=["Cloud"]))))
        self.assertIn("C14", self.codes(self.validate(self.good_demo(solution_area=["Other"]))))
        ok = self.good_demo(solution_area=["Other"])
        ok["row"]["notes"] += " Other: observability for GPUs."
        self.assertTrue(self.validate(ok)["ok"])

    def test_c15_c18(self):
        self.assertIn("C15", self.codes(self.validate(self.good_demo(notes="demo"))))
        self.assertIn("C18", self.codes(self.validate(self.good_demo(confidence="Sure"))))

    def test_c16_already_logged(self):
        self.commit(self.good_demo())
        self.assertIn("C16", self.codes(self.validate(self.good_demo())))

    def test_c17_outside_period(self):
        row = self.good_demo(activity_date="2026-10-01", evidence_refs=["user:demo was on 1 Oct"])
        self.assertIn("C17", self.wcodes(self.validate(row)))

    def test_c21_overlapping_rows(self):
        a = self.good_demo(account_name="PROSEWARE", activity_date="2026-10-06", activity_hours=2,
                           activity_type="09 · POC/POV", consolidation_key="POC|PROSEWARE|OMA",
                           evidence_refs=[self.eid("PROSEWARE OMA POC working session")])
        b = self.good_demo(account_name="PROSEWARE", activity_date="2026-10-06", activity_hours=0.5,
                           activity_type="02 · Discovery Call",
                           evidence_refs=["user:30 min call 11:00", self.eid("PROSEWARE demo prep")])
        self.assertNotIn("C21", self.wcodes(self.validate(a, b)))  # 09:00-10:00 vs 10:00-12:00 touch only
        raw = dict(RAW, events=RAW["events"] + [ev("x1", "2026-10-06T11:00:00+08:00", "2026-10-06T11:30:00+08:00",
                                                    "WOODGROVE catch-up", [("Tan", "tan@woodgrove.com")])])
        self.items = normalize(raw, self.profile, RULES)
        self.evidence["items"] = self.items
        self.by_title = {x["title"]: x for x in self.items}
        c = self.good_demo(activity_date="2026-10-06", activity_hours=0.5, evidence_refs=[self.eid("WOODGROVE catch-up")])
        self.assertIn("C21", self.wcodes(self.validate(a, c)))

    def test_approval_code_changes_with_proposal(self):
        a = approval_code({"changes": [self.good_demo()]})
        b = approval_code({"changes": [self.good_demo(activity_hours=1)]})
        self.assertNotEqual(a, b)


# ---------------------------------------------------------------- ledger
class TestLedger(Env):
    def test_extend_voids_and_supersedes(self):
        first = self.commit(self.poc_row())[0]
        ext = {"action": "extend", "supersedes": first["entry_id"],
               "row": dict(self.poc_row()["row"], activity_hours=3.5, activity_date="2026-10-07",
                           evidence_refs=[self.eid("PROSEWARE OMA POC working session"), "user:1.5h config on 7 Oct"])}
        new = self.commit(ext)[0]
        rows = {r["entry_id"]: r for r in self.ledger.rows()}
        self.assertTrue(rows[first["entry_id"]]["voided"])
        self.assertEqual(rows[first["entry_id"]]["voided_by"], new["entry_id"])
        self.assertEqual(rows[new["entry_id"]]["supersedes"], first["entry_id"])
        self.assertEqual(len(self.ledger.active()), 1)
        self.assertEqual(len(self.ledger.rows()), 2)  # nothing deleted

    def test_void_and_audit(self):
        row = self.commit(self.good_demo())[0]
        self.ledger.apply([{"action": "void", "entry_id": row["entry_id"], "reason": "duplicate"}],
                          run_id="r2", owner="x", timezone="x", rule_pack_version="x")
        self.assertEqual(self.ledger.active(), [])
        self.assertEqual(len(self.ledger.rows()), 1)
        log = [json.loads(l) for l in self.ledger.audit.read_text().splitlines()]
        self.assertEqual([e["op"] for e in log], ["new", "void"])

    def test_engine_fields(self):
        row = self.commit(self.good_demo())[0]
        r = self.ledger.get(row["entry_id"])
        self.assertEqual(r["owner"], "Tester, Pat")
        self.assertEqual(r["timezone"], "Asia/Singapore")
        self.assertEqual(r["rule_pack_version"], RULES.version)
        self.assertEqual(r["entry_id"], "A0001")
        self.assertEqual(r["solution_area"], ["ITSM"])


# ---------------------------------------------------------------- render + safety
class TestRender(Env):
    def test_render_paste_ready_and_held(self):
        self.commit(self.good_demo(), self.poc_row())
        res = render_md(self.profile, RULES, date(2026, 10, 5), date(2026, 10, 11))
        text = Path(res["md"]).read_text()
        self.assertEqual(res["ready"], 1)
        self.assertEqual(res["held"], 1)  # POC row has no_opp_reason [to confirm]
        self.assertIn("WOODGROVE", text.split("## To Confirm")[0])
        self.assertTrue(Path(res["mirrored_to"]).exists())

    def test_write_boundary(self):
        with self.assertRaises(BoundaryError):
            write_text(self.profile, self.tmp / "elsewhere.txt", "x")


if __name__ == "__main__":
    unittest.main()
