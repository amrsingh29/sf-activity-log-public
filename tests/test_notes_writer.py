"""/log-activity-note: targets, safe save, round trip into the weekly notes source."""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

from sfal import notes_writer as W
from sfal.accounts import Registry
from sfal.prepare import match_accounts
from sfal.profile import load_profile
from sfal.rules import load_rules
from sfal.sources import notes as N

RULES = load_rules()
NOTE = {"title": "ACME Bank - incident summarisation demo", "topic": "incident summarisation demo",
        "account": "ACME Bank", "activity_date": "2026-10-15",
        "summary": "Demoed incident summarisation to the ACME ITSM team.",
        "activities": [{"title": "Incident summarisation demo", "what": "Live demo on the ACME sandbox.",
                        "duration_hours": 1.5, "hours_source": "user", "hours_quote": "an hour and a half",
                        "people": [{"name": "Lim Wei", "role": "ACME ITSM lead"}], "evidence": []}],
        "follow_ups": ["Send pricing by Friday"]}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        ws = self.tmp / "ws"
        for d in ["Singapore/ACME Bank/ACME-RFP-2026", "Singapore/ACME-Archive", "Malaysia/Initech/Globex", "Tools"]:
            (ws / d).mkdir(parents=True)
        (ws / "Singapore/ACME Bank/_ActivityLogging").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def profile(self, save_to="central", root=True):
        data = {"owner": {"name": "Lee, Sam", "email_domains": ["mycompany.example"]}, "data_dir": str(self.tmp / "data"),
                "mirror_to": None, "workspace": {"root": str(self.tmp / "ws") if root else None},
                "sources": {"calendar": {"enabled": False}, "notes": {"enabled": True, "save_to": save_to}},
                "accounts": [{"name": "ACME Bank", "kind": "customer", "aliases": ["ACME"]},
                             {"name": "Globex", "kind": "customer"}, {"name": "Initech", "kind": "partner"}]}
        (self.tmp / "p.yaml").write_text(yaml.safe_dump(data))
        return load_profile(str(self.tmp / "p.yaml"))


class TestTargets(Base):
    def test_central_mode(self):
        t = W.targets(self.profile("central"), RULES, "ACME Bank")
        self.assertEqual((t["mode"], t["recommended"]["target"]), ("central", "central"))

    def test_customer_folder_prefers_folder_with_notes(self):
        t = W.targets(self.profile("customer_folder"), RULES, "ACME Bank")
        self.assertEqual(t["recommended"]["where"], "Singapore/ACME Bank/_ActivityLogging")
        wheres = [o["where"] for o in t["options"]]
        self.assertIn("Singapore/ACME Bank/ACME-RFP-2026/_ActivityLogging", wheres)  # sub-project offered
        self.assertIn("Singapore/ACME-Archive/_ActivityLogging", wheres)       # alias ACME
        self.assertEqual(t["options"][-1]["target"], "central")

    def test_nested_customer_under_partner(self):
        t = W.targets(self.profile("customer_folder"), RULES, "Globex")
        self.assertEqual(t["recommended"]["where"], "Malaysia/Initech/Globex/_ActivityLogging")

    def test_ambiguous_asks(self):
        shutil.rmtree(self.tmp / "ws/Singapore/ACME Bank/_ActivityLogging")
        (self.tmp / "ws/Malaysia/ACME Bank").mkdir()
        t = W.targets(self.profile("customer_folder"), RULES, "ACME Bank")
        self.assertIsNone(t["recommended"])
        self.assertIn("ask", t)

    def test_unknown_account_goes_central(self):
        t = W.targets(self.profile("customer_folder"), RULES, "Umbrella Corp")
        self.assertEqual(t["recommended"]["target"], "central")
        self.assertIn("note", t)


class TestSave(Base):
    def test_central_save_and_round_trip(self):
        p = self.profile("central")
        r = W.save(p, RULES, NOTE, "central")
        path = Path(r["path"])
        self.assertEqual(path.parent.resolve(), (self.tmp / "data/notes/2026/10").resolve())
        self.assertRegex(path.name, r"^2026-10-15_\d{4}_acme-bank_incident-summarisation-demo_activity-note\.md$")
        n = N.parse_note(path, 2026)
        self.assertEqual((n["date"], n["hours"], n["account"]), (date(2026, 10, 15), 1.5, "ACME Bank"))
        text = path.read_text()
        self.assertIn("- [ ] Send pricing by Friday", text)
        self.assertIn("**Duration:** 1.5 h", text)
        self.assertIn("you said: \"an hour and a half\"", text)
        self.assertIn("| Lim Wei | ACME ITSM lead |", text)

    def test_never_overwrites(self):
        p = self.profile("central")
        a, b = W.save(p, RULES, NOTE, "central"), W.save(p, RULES, NOTE, "central")
        self.assertNotEqual(a["path"], b["path"])
        self.assertTrue(Path(a["path"]).exists() and Path(b["path"]).exists())

    def test_customer_folder_save(self):
        p = self.profile("customer_folder")
        target = W.targets(p, RULES, "ACME Bank")["recommended"]["target"]
        r = W.save(p, RULES, NOTE, target)
        self.assertEqual(Path(r["path"]).parent, (self.tmp / "ws/Singapore/ACME Bank/_ActivityLogging").resolve())

    def test_refuses_paths_not_matched_to_the_account(self):
        p = self.profile("customer_folder")
        for bad in [str(self.tmp / "ws/Tools"), str(self.tmp / "ws/Malaysia/Initech/Globex"), "/tmp", str(self.tmp)]:
            with self.assertRaises(W.NoteError):
                W.save(p, RULES, NOTE, bad)

    def test_required_fields(self):
        p = self.profile("central")
        with self.assertRaises(W.NoteError):
            W.save(p, RULES, dict(NOTE, summary=""), "central")
        with self.assertRaises(W.NoteError):
            W.save(p, RULES, dict(NOTE, activity_date="15 Oct"), "central")
        with self.assertRaises(W.NoteError):
            W.save(p, RULES, dict(NOTE, activities=[]), "central")


class TestWeeklyRunReadsNotes(Base):
    def test_central_note_with_declared_account(self):
        p = self.profile("central", root=False)
        W.save(p, RULES, NOTE, "central")
        raw = self.tmp / "raw"
        raw.mkdir()
        items, rep = N.collect(p, RULES, date(2026, 10, 12), date(2026, 10, 18), raw)
        self.assertEqual(len(items), 1)
        match_accounts(items, Registry(p.accounts, RULES.internal_account), [])
        self.assertEqual(items[0]["account_hint"]["name"], "ACME Bank")
        self.assertEqual(items[0]["account_hint"]["via"], ["note:account"])
        self.assertEqual(items[0]["hours"], 1.5)

    def test_no_notes_anywhere_is_not_an_error(self):
        p = self.profile("central", root=False)
        raw = self.tmp / "raw"
        raw.mkdir()
        items, rep = N.collect(p, RULES, date(2026, 10, 12), date(2026, 10, 18), raw)
        self.assertEqual(items, [])

    def test_context_lists_notes_written_that_day(self):
        p = self.profile("central")
        W.save(p, RULES, dict(NOTE, activity_date=date.today().isoformat()), "central")
        ctx = W.context(p, RULES, date.today())
        self.assertEqual(ctx["today"], [])  # all sources off
        self.assertEqual(len(ctx["notes_already_written"]), 1)
        self.assertEqual(ctx["save_to"], "central")


class TestProfileValidation(Base):
    def test_save_to_values(self):
        data = {"owner": {"name": "Lee, Sam"}, "data_dir": str(self.tmp / "d"),
                "sources": {"notes": {"save_to": "somewhere"}}}
        (self.tmp / "bad.yaml").write_text(yaml.safe_dump(data))
        from sfal.profile import ProfileError
        with self.assertRaises(ProfileError):
            load_profile(str(self.tmp / "bad.yaml"))


if __name__ == "__main__":
    unittest.main()


class TestQualityCase(Base):
    """Golden case from 14 Oct: a right-sizing sync known only from sent emails, plus a 0.5h calendar sync."""

    def setUp(self):
        super().setUp()
        self.p = self.profile("customer_folder")
        cache = W._cache_file(self.p, date(2026, 10, 14))
        cache.parent.mkdir(parents=True)
        import json
        cache.write_text(json.dumps([
            {"id": "cal:sync", "source": "calendar", "title": "Weekly sync up - ACME & R&D", "hours": 0.5,
             "start": "2026-10-14T14:30:00+08:00", "end": "2026-10-14T15:00:00+08:00",
             "organizer_name": "Tan, Joe", "my_status": "accepted", "location": "",
             "attendees": [{"name": "Tan, Mei", "status": "accepted"}, {"name": "Shah, D", "status": "declined"}],
             "description": "Agenda:\n1. On-prem sizing status\n2. UAT findings"},
            {"id": "mail:psr", "source": "email", "title": "ACME - Help Required for On-Prem Right-Sizing",
             "mailboxes": ["Sent Items"]}]))

    def note(self, **act):
        a = {"title": "Right-sizing sync", "what": "Sought PSR sizing guidance.", "evidence": ["mail:psr"]}
        a.update(act)
        return {"title": "ACME Bank - on-prem right-sizing (PSR guidance)", "topic": "helixgpt right-sizing psr sync",
                "account": "ACME Bank", "activity_date": "2026-10-14", "summary": "Sizing guidance from PSR.",
                "activities": [a], "to_confirm": ["Exact meeting time"]}

    def test_detail_gives_invite_and_attendee_status(self):
        d = W.detail(self.p, RULES, date(2026, 10, 14), ["cal:sync", "cal:nope"])
        item = d["items"][0]
        self.assertIn("On-prem sizing status", item["description"])
        self.assertEqual(item["attendees"][1], {"name": "Shah, D", "status": "declined"})
        self.assertEqual(d["missing"], ["cal:nope"])

    def test_hours_must_match_the_meeting(self):
        bad = self.note(duration_hours=1.0, evidence=["cal:sync"])          # the old failure: 1.0h for a 0.5h meeting
        self.assertTrue(any("meeting is 0.5h" in e for e in W.validate(self.p, bad)))
        self.assertEqual(W.validate(self.p, self.note(duration_hours=0.5, evidence=["cal:sync"])), [])
        no_meeting = self.note(duration_hours=1.0)                             # email-only, hours invented
        self.assertTrue(any("no meeting behind it" in e for e in W.validate(self.p, no_meeting)))
        self.assertEqual(W.validate(self.p, self.note(duration_hours="[to confirm]")), [])
        self.assertTrue(any("hours_quote" in e for e in W.validate(self.p, self.note(duration_hours=1.0, hours_source="user"))))
        ok = self.note(duration_hours=1.0, hours_source="user", hours_quote="about an hour")
        self.assertEqual(W.validate(self.p, ok), [])
        self.assertIn('1 h (you said: "about an hour")', W.render_note(ok))

    def test_merged_activity_is_refused(self):
        # the 23:43 failure: a 'weekly sync' note built from a different email thread, not citing the meeting
        mixed = self.note(title="ACME weekly sync - on-prem sizing", duration_hours="[to confirm]")
        errs = W.validate(self.p, mixed)
        self.assertTrue(any("looks like the meeting cal:sync" in e for e in errs), errs)
        self.assertEqual(W.validate(self.p, dict(mixed, activities=[dict(mixed["activities"][0], evidence=["cal:sync"])])), [])
        self.assertEqual(W.validate(self.p, dict(mixed, activities=[dict(mixed["activities"][0], not_meetings=["cal:sync"])])), [])
        # generic words alone are not a match
        self.assertEqual(W.validate(self.p, self.note(title="Globex weekly sync", duration_hours="[to confirm]")), [])

    def test_rendered_note_is_structured_and_readable_by_weekly_run(self):
        n = self.note(duration_hours="[to confirm]", context=["Per the invite: growth in knowledge articles"],
                      discussed=["CPU / memory sizing"], outcomes=["Bigger-team call on 15 Oct"],
                      people=[{"name": "Menon, Ravi", "role": "PSR - accepted"}])
        n["follow_ups"] = ["Run the bigger-team call"]
        n["background"] = [{"text": "POC phase 1 runs in parallel", "source": "singapore/acme/account-plan"}]
        target = W.targets(self.p, RULES, "ACME Bank")["recommended"]["target"]
        path = Path(W.save(self.p, RULES, n, target)["path"])
        self.assertRegex(path.name, r"^2026-10-14_\d{4}_helixgpt-right-sizing-psr-sync_activity-note\.md$")
        text = path.read_text()
        for part in ("## Summary", "## Right-sizing sync", "**Context**", "**Discussed**", "**Outcomes & decisions**",
                     "| Menon, Ravi | PSR - accepted |", "## Follow-ups", "- [ ] Run the bigger-team call",
                     "## Background", "`singapore/acme/account-plan`", "## To confirm", "**Duration:** [to confirm]"):
            self.assertIn(part, text)
        parsed = N.parse_note(path, 2026)
        self.assertEqual((parsed["date"], parsed["account"], parsed["hours"]), (date(2026, 10, 14), "ACME Bank", None))

    def test_internal_work_goes_to_internal_folder(self):
        (self.tmp / "ws/_Internal").mkdir()
        p = self.profile("customer_folder")
        p.data["workspace"]["internal_folders"] = ["_Internal"]
        t = W.targets(p, RULES, RULES.internal_account)
        self.assertEqual(t["recommended"]["where"], "_Internal/_ActivityLogging")


class TestHelpers(unittest.TestCase):
    def test_slug_word_boundary(self):
        self.assertEqual(W.slug("WOODGROVE weekly sync on HelixGPT on-prem sizing discussion"), "woodgrove-weekly-sync-on-helixgpt-on")
        self.assertEqual(W.slug("x" * 80, chars=20), "note")

    def test_clean_body(self):
        body = ("Thank you Ravi. I have shared the invite.\n\nRegards,\nAmar\nMobile +65\n\n"
                "From: Menon, Ravi <s@x.com>\nDate: Wednesday\nTo: me\n\nOld quoted text")
        self.assertEqual(W.clean_body(body), "Thank you Ravi. I have shared the invite.")
        teams = "Agenda below\n" + "_" * 40 + "\nMicrosoft Teams meeting\nJoin: https://x\n" + "_" * 40
        self.assertEqual(W.clean_body(teams), "Agenda below")
