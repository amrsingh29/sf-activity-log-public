"""Phase 2 tests: email, imports, notes, files, cross-source steps. No Mail.app / EventKit needed."""
import csv
import os
import shutil
import tempfile
import time
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from sfal import prepare as P
from sfal.accounts import Registry
from sfal.evidence import item
from sfal.profile import load_profile
from sfal.rules import load_rules
from sfal.sources import email as E
from sfal.sources import files as F
from sfal.sources import imports as I
from sfal.sources import notes as N
from sfal.textdates import duration_hours, find_dates, time_range
from sfal.validate import Validator

RULES = load_rules()
TZ = ZoneInfo("Asia/Singapore")
US, RS = E.US, E.RS


def make_profile(tmp: Path, **extra) -> object:
    data = {
        "owner": {"name": "Tester, Pat", "email": "pat@mycompany.example", "email_domains": ["mycompany.example"]},
        "timezone": "Asia/Singapore", "data_dir": str(tmp / "data"), "mirror_to": None,
        "workspace": {"root": str(tmp / "ws"), "account_folder_level": 2, "ignore": ["_ActivityLogging/*"],
                      "internal_folders": ["_Internal"]},
        "sources": {"calendar": {"enabled": True}, "email": {"enabled": True, "ignore_subjects": ["*pto*"]},
                    "files": {"enabled": True, "burst_min_files": 4}, "notes": {"enabled": True},
                    "imports": {"enabled": True}},
        "accounts": [{"name": "PROSEWARE", "kind": "customer", "domains": ["proseware.com"]},
                     {"name": "WOODGROVE", "kind": "customer", "domains": ["woodgrove.com"]},
                     {"name": "FABRIKAM", "kind": "customer"},
                     {"name": "WINGTIP", "kind": "partner"}],
    }
    data.update(extra)
    (tmp / "ws").mkdir(exist_ok=True)
    p = tmp / "profile.yaml"
    p.write_text(yaml.safe_dump(data))
    return load_profile(str(p))


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.profile = make_profile(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)


# ---------------------------------------------------------------- textdates
class TestTextDates(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(find_dates("on 01-Sep and 2026-10-07", 2026), [date(2026, 9, 1), date(2026, 10, 7)])
        self.assertEqual(find_dates("7th Oct 2026", 2026), [date(2026, 10, 7)])
        self.assertEqual(find_dates("Oct 7, 2026", 2026), [date(2026, 10, 7)])
        self.assertEqual(find_dates("07/10/2026", 2026), [date(2026, 10, 7)])  # day-first
        self.assertEqual(find_dates("(07-Oct-26)", 2026), [date(2026, 10, 7)])
        self.assertEqual(find_dates("Note — 08-10-2026 · session", 2026), [date(2026, 10, 8)])
        self.assertEqual(find_dates("2026-10-08", 2026), [date(2026, 10, 8)])

    def test_time_and_duration(self):
        self.assertEqual(str(time_range("11:00-12:30")), "(datetime.time(11, 0), datetime.time(12, 30))")
        self.assertEqual(time_range("9:30am – 10:15am")[0].hour, 9)
        self.assertEqual(time_range("1:00 to 2:00pm")[0].hour, 13)
        self.assertEqual(duration_hours("1.5h"), 1.5)
        self.assertEqual(duration_hours("90 min"), 1.5)
        self.assertEqual(duration_hours("1 hr 30 min"), 1.5)
        self.assertEqual(duration_hours("2"), 2.0)
        self.assertIsNone(duration_hours("soon"))


# ---------------------------------------------------------------- email
def mail_out(*msgs, oldest="2026-07-01T09:00:00"):
    recs = [f"OLDEST{US}{oldest}"]
    for m in msgs:
        recs.append(US.join([m.get("id", "x"), m["date"], m["subject"], m.get("sender", "Pat <pat@mycompany.example>"),
                             ",".join(m.get("to", [])), ",".join(m.get("cc", [])), "|".join(m.get("att", [])),
                             m.get("preview", "")]))
    return RS.join(recs) + RS


class TestEmail(Tmp):
    def test_parse_and_normalize(self):
        raw = E.parse_output(mail_out(
            {"id": "1", "date": "2026-10-06T10:00:00", "subject": "Example Corp - Order Management Demo",
             "to": ["ali@proseware.com"], "att": ["image001.png", "OM.pptx"]},
            {"id": "2", "date": "2026-10-06T15:00:00", "subject": "RE: Example Corp - Order Management Demo",
             "to": ["ali@proseware.com"]},
            {"id": "3", "date": "2026-10-06T16:00:00", "subject": "Accepted: Proseware Requirements Sync"},
            {"id": "4", "date": "2026-10-07T09:00:00", "subject": "Weekly digest", "sender": "noreply@x.com"},
            {"id": "5", "date": "2026-10-07T09:00:00", "subject": "Automatic reply: hello"},
            {"id": "6", "date": "2026-10-07T09:00:00", "subject": "All hands", "to": [f"p{i}@mycompany.example" for i in range(30)]},
            {"id": "7", "date": "2026-10-07T09:00:00", "subject": "Pat - PTO", "to": ["boss@mycompany.example"]},
        ))
        self.assertEqual(raw["oldest"], "2026-07-01T09:00:00")
        items = E.normalize({"Sent Items": raw}, self.profile)
        by = {}
        for x in items:
            by.setdefault(x["excluded"] or x["kind"], []).append(x)
        threads = by["email"]
        self.assertEqual(len(threads), 1)  # RE: grouped into the same thread/day
        t = threads[0]
        self.assertEqual(t["message_count"], 2)
        self.assertEqual(t["domains"], ["proseware.com"])
        self.assertEqual(t["attachments"], ["OM.pptx"])  # inline image dropped
        self.assertIn("sent_by_me", t["flags"])
        self.assertEqual(by["rsvp_signal"][0]["rsvp"], "accepted")
        self.assertEqual(by["rsvp_signal"][0]["rsvp_subject"], "Proseware Requirements Sync")
        for reason in ("automated_sender", "auto_reply", "mass_mail", "ignored_subject"):
            self.assertIn(reason, by, reason)

    def test_thread_subject(self):
        self.assertEqual(E.thread_subject("RE: FW: Re:  Hello   world"), "Hello world")


# ---------------------------------------------------------------- imports
class TestImports(Tmp):
    def test_csv_table(self):
        f = self.tmp / "cal.csv"
        with open(f, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Date", "Time", "Meeting", "Organizer", "Customer"])
            w.writerow(["06-Oct", "10:00-11:30", "PROSEWARE OM demo", "Ali", "Proseware"])
            w.writerow(["06-Oct", "10:00-11:30", "PROSEWARE OM demo", "Ali", "Proseware"])  # repeated
            w.writerow(["20-Oct", "10:00-11:00", "Out of period", "Ali", ""])
            w.writerow(["", "", "No date row", "", ""])
        items, rep = I.parse_document(f, date(2026, 10, 5), date(2026, 10, 11), TZ)
        self.assertEqual(len(items), 1)
        x = items[0]
        self.assertEqual((x["kind"], x["date"], x["hours"], x["account_text"]), ("meeting", "2026-10-06", 1.5, "Proseware"))
        self.assertEqual(x["start"], "2026-10-06T10:00:00+08:00")
        self.assertEqual(x["completeness"], "partial")
        self.assertEqual(rep["duplicates_removed"], 1)

    def test_docx_table_prose_and_count(self):
        import docx
        d = docx.Document()
        d.add_paragraph("Copilot found 3 meetings in this period.")
        d.add_paragraph("On 7 Oct 2026 sent the CONTOSO RFP response 14:00-16:00 to procurement.")
        t = d.add_table(rows=1, cols=3)
        for c, h in zip(t.rows[0].cells, ["Date", "Duration", "Subject"]):
            c.text = h
        for r in (["2026-10-06", "1h", "WOODGROVE HelixGPT demo"], ["2026-10-08", "30 min", "FABRIKAM sync"]):
            cells = t.add_row().cells
            for c, v in zip(cells, r):
                c.text = v
        f = self.tmp / "copilot.docx"
        d.save(f)
        items, rep = I.parse_document(f, date(2026, 10, 5), date(2026, 10, 11), TZ)
        titles = {x["title"]: x for x in items}
        self.assertEqual(titles["WOODGROVE HelixGPT demo"]["hours"], 1.0)
        self.assertEqual(titles["FABRIKAM sync"]["hours"], 0.5)
        prose = [x for x in items if x["kind"] == "other"][0]
        self.assertEqual((prose["date"], prose["hours"]), ("2026-10-07", 2.0))
        self.assertIn("count_mismatch", rep)  # states 3 meetings, table has 2

    def test_xlsx(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Subject", "Start Date", "Start Time", "End"])
        ws.append(["EPF discovery", datetime(2026, 10, 9), "15:00-16:00", ""])
        f = self.tmp / "export.xlsx"
        wb.save(f)
        items, _ = I.parse_document(f, date(2026, 10, 5), date(2026, 10, 11), TZ)
        self.assertEqual((items[0]["title"], items[0]["date"], items[0]["hours"]), ("EPF discovery", "2026-10-09", 1.0))


# ---------------------------------------------------------------- notes
NOTE = """---
title: Activity Note — FABRIKAM
date: '2026-10-13'
---
**Activity:** FABRIKAM partner discovery with Wingtip Edge (06-Oct-2026)
**Duration:** 1.5h

## Summary
Walked through AIOps and ITSM options with the partner.
"""


NOTE_INLINE = """---
title: Activity Note — Wingtip Edge ITAM enablement
date: '2026-10-13'
---
**Activity date:** 07-Oct-2026 (Wed) · **Duration:** 3.0 h · **Venue:** KL

## Summary
ITAM and HAM partner enablement.
"""


NOTE_FM = """---
title: Activity Note — 08-10-2026 · HeiTech Padu session
activity-date: 2026-10-08T00:00:00.000Z
logged: 2026-10-13T00:00:00.000Z
---
## Summary
Session ran ~3.0h.
"""


class TestNotes(Tmp):
    def test_frontmatter_activity_date(self):
        f = self.tmp / "n.md"
        f.write_text(NOTE_FM)
        n = N.parse_note(f, 2026)
        self.assertEqual((n["date"], n["created"]), (date(2026, 10, 8), date(2026, 10, 13)))

    def test_inline_fields(self):
        d = self.tmp / "ws" / "Malaysia" / "WINGTIP" / "_ActivityLogging"
        d.mkdir(parents=True)
        f = d / "2026-10-13_0706_activity-note.md"
        f.write_text(NOTE_INLINE)
        n = N.parse_note(f, 2026)
        self.assertEqual((n["date"], n["hours"], n["created"]), (date(2026, 10, 7), 3.0, date(2026, 10, 13)))

    def test_note_date_from_title_and_hours(self):
        d = self.tmp / "ws" / "Malaysia" / "WINGTIP" / "FABRIKAM" / "_ActivityLogging"
        d.mkdir(parents=True)
        (d / "2026-10-13_0710_activity-note.md").write_text(NOTE)
        (self.tmp / "ws" / "_ActivityLogging").mkdir()
        (self.tmp / "ws" / "_ActivityLogging" / "runbook.md").write_text("Runbook 12 Oct 2026")  # ignored
        raw = self.tmp / "raw"
        raw.mkdir()
        items, rep = N.collect(self.profile, RULES, date(2026, 10, 5), date(2026, 10, 11), raw)
        self.assertEqual(rep["notes_scanned"], 1)
        x = items[0]
        self.assertEqual((x["date"], x["note_created"], x["hours"]), ("2026-10-06", "2026-10-13", 1.5))
        self.assertEqual(x["folder"], "Malaysia/WINGTIP/FABRIKAM")
        self.assertIn("AIOps", x["preview"])


# ---------------------------------------------------------------- files
class TestFiles(Tmp):
    def _file(self, rel, when, author=None):
        p = self.tmp / "ws" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".docx":
            import docx
            d = docx.Document()
            d.core_properties.title = "Order Management overview"
            if author:
                d.core_properties.last_modified_by = author
            d.save(p)
        else:
            p.write_text("x")
        ts = datetime.fromisoformat(when).replace(tzinfo=TZ).timestamp()
        os.utime(p, (ts, ts))
        return p

    def test_sessions_authorship_bursts(self):
        self._file("Malaysia/Proseware/OM/overview.docx", "2026-10-06T10:00", author="Lee, Someone")
        self._file("Malaysia/Proseware/OM/mine.docx", "2026-10-06T11:00", author="Tester, Pat")
        self._file("Malaysia/WINGTIP/FABRIKAM/plan.docx", "2026-10-07T09:00", author="Pat Tester")
        for i, acct in enumerate(["A", "B", "C", "D"]):  # sync burst: 4 files, 4 folders, same minute
            self._file(f"Singapore/{acct}/f{i}.txt", "2026-10-08T09:47")
        self._file("Singapore/Old/old.txt", "2026-09-01T09:00")  # outside period (birth time is now, though)
        raw = self.tmp / "raw"
        raw.mkdir()
        items, rep = F.collect(self.profile, RULES, date(2026, 10, 5), date(2026, 10, 11), raw)
        self.assertEqual(rep["sync_burst_files_dropped"], 4)
        by = {x["title"].split(":")[0]: x for x in items}
        pet = next(x for x in items if x["date"] == "2026-10-06")
        self.assertEqual(pet["file_count"], 2)
        signals = {f["file"].rsplit("/", 1)[-1]: f["signal"] for f in pet["files"]}
        self.assertEqual(signals, {"overview.docx": "other_author", "mine.docx": "authored"})
        fabrikam = next(x for x in items if x["date"] == "2026-10-07")
        self.assertIn("FABRIKAM", fabrikam["title"])  # grouped by matched account, not the partner folder
        self.assertIn("authored_by_me", fabrikam["flags"])  # "Pat Tester" = "Tester, Pat"


# ---------------------------------------------------------------- cross-source
class TestCrossSource(Tmp):
    def test_rsvp_applies_to_next_occurrence(self):
        m1 = item(id="cal:1", source="calendar", kind="meeting", date="2026-10-06", start="2026-10-06T21:00",
                  title="Proseware Requirements Sync", flags=["rsvp_unknown"])
        m2 = item(id="cal:2", source="calendar", kind="meeting", date="2026-10-07", start="2026-10-07T21:00",
                  title="Proseware Requirements Sync", flags=["rsvp_unknown"])
        r = item(id="mail:r", source="email", kind="rsvp", date="2026-10-06", excluded="rsvp_signal",
                 rsvp="declined", rsvp_subject="Proseware Requirements Sync")
        P.apply_rsvps([m1, m2, r])
        self.assertIn("declined_by_email", m1["flags"])
        self.assertIn("rsvp_unknown", m2["flags"])

    def test_imports_merge_into_calendar(self):
        c = item(id="cal:1", source="calendar", kind="meeting", date="2026-10-06", title="WOODGROVE HelixGPT demo")
        i1 = item(id="imp:1", source="imports", kind="meeting", date="2026-10-06", title="WOODGROVE - HelixGPT demo")
        i2 = item(id="imp:2", source="imports", kind="meeting", date="2026-10-06", title="EPF discovery")
        self.assertEqual(P.dedupe_imports([c, i1, i2]), 1)
        self.assertEqual(i1["excluded"], "duplicate_of:cal:1")
        self.assertIsNone(i2["excluded"])

    def test_file_links_and_gaps(self):
        reg = Registry(self.profile.accounts, RULES.internal_account)
        meet = item(id="cal:1", source="calendar", kind="meeting", date="2026-10-07", title="PROSEWARE demo")
        prep = item(id="file:1", source="files", kind="file", date="2026-10-06", title="files", path_texts=["Proseware"])
        gap = item(id="file:2", source="files", kind="file", date="2026-10-06", title="files", path_texts=["WOODGROVE"])
        items = [meet, prep, gap]
        P.match_accounts(items, reg, [])
        P.link_files(items, [], 3)
        self.assertEqual(prep["links"], [{"id": "cal:1", "as": "prep_for", "days": 1}])
        self.assertIn("gap", gap["flags"])

    def test_internal_folder(self):
        reg = Registry(self.profile.accounts, RULES.internal_account)
        n = item(id="note:1", source="notes", kind="note", date="2026-10-06", title="Tooling", folder="_Internal")
        P.match_accounts([n], reg, ["_Internal"])
        self.assertEqual(n["account_hint"]["name"], RULES.internal_account)

    def test_stated_hours_count_for_validator(self):
        n = item(id="note:1", source="notes", kind="note", date="2026-10-06", hours=1.5, title="FABRIKAM discovery")
        ev = {"period": {"from": "2026-10-05", "to": "2026-10-11"}, "items": [n]}
        row = {"account_name": "FABRIKAM", "account_kind": "customer", "activity_type": "02 · Discovery Call",
               "no_opp_reason": "Opportunity not created yet", "status": "Completed", "activity_date": "2026-10-06",
               "activity_hours": 1.5, "prep_hours": 0, "notes": "Discovery with partner on AIOps and ITSM options.",
               "evidence_refs": ["note:1"], "confidence": "Medium"}
        res = Validator(self.profile, RULES, ev, []).run({"changes": [{"action": "new", "row": row}]})
        self.assertTrue(res["ok"], res["errors"])
        row["activity_hours"] = 2
        res = Validator(self.profile, RULES, ev, []).run({"changes": [{"action": "new", "row": row}]})
        self.assertIn("C04", {e["code"] for e in res["errors"]})


if __name__ == "__main__":
    unittest.main()
