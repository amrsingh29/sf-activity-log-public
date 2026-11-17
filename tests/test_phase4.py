"""Phase 4 tests: owner aliases, setup scan/save, API, MCP server."""
import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from sfal import api, setup
from sfal.profile import ProfileError, load_profile
from sfal.sources.calendar import normalize

from test_engine import PROFILE, RAW, RULES, ev


class TestAliases(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        prof = dict(PROFILE, data_dir=str(self.tmp / "d"))
        prof["owner"] = dict(PROFILE["owner"], aliases=["pat_tester@second.example"], email_domains=["mycompany.example", "second.example"])
        (self.tmp / "p.yaml").write_text(yaml.safe_dump(prof))
        self.p = load_profile(str(self.tmp / "p.yaml"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_is_me(self):
        self.assertTrue(self.p.is_me(None, "PAT_TESTER@second.example"))
        self.assertTrue(self.p.is_me("Tester, Pat", "other@x.com"))
        self.assertTrue(self.p.is_me("Someone", "x@y.com", flagged=True))
        self.assertFalse(self.p.is_me("Bukowski, Greg", "greg@second.example"))

    def test_alias_attendee_is_not_other_person(self):
        raw = {"events": [ev("a1", "2026-10-06T09:30:00+08:00", "2026-10-06T10:30:00+08:00", "Focus block",
                             [("Tester, Pat", "pat_tester@second.example")]),
                          ev("a2", "2026-10-06T11:00:00+08:00", "2026-10-06T12:00:00+08:00", "Team sync",
                             [("Tester, Pat", "pat_tester@second.example"), ("Bukowski, Greg", "greg@second.example")])]}
        items = {x["title"]: x for x in normalize(raw, self.p, RULES)}
        self.assertIn("solo", items["Focus block"]["flags"])
        self.assertEqual(items["Team sync"]["people"], ["Bukowski, Greg"])
        self.assertIn("internal_only", items["Team sync"]["flags"])  # second.example is internal
        self.assertEqual(items["Team sync"]["domains"], [])


class TestSetup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_scan_folders_regional(self):
        for d in ["Singapore/WOODGROVE", "Singapore/CONTOSO-2025-RFP", "Malaysia/Proseware", "_Internal", "_SFActivityLog", "Tools"]:
            (self.tmp / d).mkdir(parents=True)
        f = setup.scan_folders(self.tmp)
        self.assertEqual(f["suggested_account_folder_level"], 2)
        self.assertEqual(f["regional_folders"], ["Malaysia", "Singapore"])
        names = {c["name"]: c["suggested_account"] for c in f["account_folder_candidates"]}
        self.assertEqual(names["CONTOSO-2025-RFP"], "CONTOSO")
        self.assertEqual(f["suggested_internal_folders"], ["_Internal"])
        self.assertIn("_SFActivityLog", f["system_folders_skipped"])

    def test_scan_folders_flat(self):
        for d in ["WOODGROVE", "Proseware", "CONTOSO"]:
            (self.tmp / d).mkdir()
        self.assertEqual(setup.scan_folders(self.tmp)["suggested_account_folder_level"], 1)

    def test_save_profile_validates_and_backs_up(self):
        dest = self.tmp / "profile.yaml"
        with self.assertRaises(ProfileError):
            setup.save_profile({"owner": {"name": ""}, "data_dir": str(self.tmp / "d")}, profile=str(dest))
        self.assertFalse(dest.exists())
        good = {"owner": {"name": "Tester, Pat", "email_domains": ["mycompany.example"]}, "data_dir": str(self.tmp / "d"),
                "accounts": [{"name": "WOODGROVE", "kind": "customer"}]}
        r1 = setup.save_profile(good, profile=str(dest))
        self.assertIsNone(r1["backup"])
        self.assertTrue((self.tmp / "d").is_dir())
        r2 = setup.save_profile(good, profile=str(dest))
        self.assertTrue(Path(r2["backup"]).exists())
        self.assertEqual(load_profile(str(dest)).owner, "Tester, Pat")


class TestMCP(unittest.TestCase):
    def test_tools_and_error_shape(self):
        from sfal import mcp_server
        tools = asyncio.run(mcp_server.server.list_tools())
        names = {t.name for t in tools}
        self.assertEqual(names, {"sfal_doctor", "sfal_rules", "sfal_profile_show", "sfal_resolve_period",
                                 "sfal_prepare", "sfal_validate", "sfal_commit", "sfal_render", "sfal_read_output",
                                 "sfal_ledger", "sfal_setup_scan", "sfal_setup_save_profile", "sfal_ask",
                                 "sfal_note_context", "sfal_note_detail", "sfal_note_targets", "sfal_note_save",
                                 "sfal_catalog", "sfal_account_add", "sfal_docs_sync", "sfal_docs_status"})
        self.assertIn("Hard rules", mcp_server._instructions())
        self.assertEqual(mcp_server.sfal_resolve_period("last week" if False else "2026-10-05 to 2026-10-11")["kind"], "week")
        err = mcp_server.sfal_resolve_period("whenever")
        self.assertFalse(err["ok"])
        self.assertIn("cannot understand period", err["error"])

    def test_validate_rejects_bad_proposal_shape(self):
        with self.assertRaises(api.ApiError):
            tmp = Path(tempfile.mkdtemp())
            try:
                prof = dict(PROFILE, data_dir=str(tmp / "d"))
                (tmp / "p.yaml").write_text(yaml.safe_dump(prof))
                rd = tmp / "d" / "cache" / "r1"
                rd.mkdir(parents=True)
                (rd / "evidence.json").write_text(json.dumps({"period": {"from": "2026-10-05", "to": "2026-10-11"}, "items": []}))
                api.validate("r1", proposal={"rows": []}, profile=str(tmp / "p.yaml"))
            finally:
                shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()


class TestDecisions(unittest.TestCase):
    def test_defaults_by_flag(self):
        from sfal import decisions as D
        ev = [
            {"id": "cal:1", "source": "calendar", "date": "2026-10-06", "start": "2026-10-06T21:00:00+08:00", "hours": 0.5,
             "title": "Proseware sync", "flags": ["declined_by_email"], "account_hint": {"name": "PROSEWARE", "kind": "customer"}},
            {"id": "cal:2", "source": "calendar", "date": "2026-10-07", "hours": 0.5, "title": "WOODGROVE sync",
             "flags": ["rsvp_unknown"], "account_hint": {"name": "WOODGROVE", "kind": "customer"}},
            {"id": "cal:3", "source": "calendar", "date": "2026-10-07", "hours": 1, "title": "Clean meeting",
             "flags": [], "account_hint": {"name": "WOODGROVE", "kind": "customer"}},
            {"id": "mail:4", "source": "email", "date": "2026-10-08", "title": "PTO", "flags": ["internal_only"],
             "account_hint": {"name": "Example Corp (12345678)", "kind": "internal"}},
        ]
        d = D.build(ev, [{"id": "file:5", "source": "files", "date": "2026-10-09", "title": "CONTOSO files", "flags": ["gap"]}])
        got = {x["id"]: x["default"] for x in d}
        self.assertEqual(got, {"cal:1": "Skip", "cal:2": "Log", "mail:4": "Skip", "file:5": "Skip"})
        self.assertNotIn("cal:3", got)  # nothing to decide
        self.assertEqual([x["n"] for x in d], [1, 2, 3, 4])
        self.assertIn('reply "ok"', D.compact_table(d))
