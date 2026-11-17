"""Phase 3 tests: output folder rules, Excel workbook, deltas, history, legacy migration."""
import json
import unittest
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from sfal.period import classify, resolve
from sfal.render import compute_deltas, render

from test_engine import RULES, Env

T = date(2026, 10, 14)  # Wednesday


class TestClassify(unittest.TestCase):
    """The folder depends on the dates the prompt resolves to, not on the words typed."""

    def kind(self, text):
        return classify(*resolve(text, T))

    def test_prompt_to_folder(self):
        self.assertEqual(self.kind("today")["relpath"], "2026/days/2026-10-14")
        self.assertEqual(self.kind("yesterday")["relpath"], "2026/days/2026-10-13")
        self.assertEqual(self.kind("last week")["relpath"], "2026/weeks/2026-W41_2026-10-05_to_2026-10-11")
        self.assertEqual(self.kind("2026-10-05 to 2026-10-11"), self.kind("last week"))
        self.assertEqual(self.kind("October")["relpath"], "2026/months/2026-10_October")
        self.assertEqual(self.kind("2026-10-01 to 2026-10-31"), self.kind("October"))
        self.assertEqual(self.kind("this month")["kind"], "month")
        self.assertEqual(self.kind("last 7 days")["relpath"], "2026/ranges/2026-10-08_to_2026-10-14")
        self.assertEqual(self.kind("2026-10-06 to 2026-10-12")["kind"], "range")  # Tue-Mon is not a week

    def test_year_boundary(self):
        c = classify(date(2026, 12, 28), date(2027, 1, 3))
        self.assertEqual(c["relpath"], "2026/weeks/2026-W53_2026-12-28_to_2027-01-03")


class TestOutput(Env):
    P = (date(2026, 10, 5), date(2026, 10, 11))

    def test_layout_and_workbook(self):
        self.commit(self.good_demo(), self.poc_row())
        res = render(self.profile, RULES, *self.P)
        folder = Path(res["folder"])
        self.assertEqual(folder, self.profile.data_dir / "output/2026/weeks/2026-W41_2026-10-05_to_2026-10-11")
        names = sorted(p.name for p in folder.iterdir())
        self.assertEqual(names, [".snapshot.json", "Salesforce_Activity_Log_2026-10-05_to_2026-10-11.md",
                                 "Salesforce_Activity_Log_2026-10-05_to_2026-10-11.xlsx", "runs.md"])
        wb = load_workbook(res["xlsx"])
        self.assertEqual(wb.sheetnames, ["Summary", "Paste-Ready", "Period Ledger", "Per-Customer Deltas",
                                         "To-Confirm", "Evidence Trail"])
        pr = wb["Paste-Ready"]
        self.assertEqual([c.value for c in pr[1]], ["ID"] + list(RULES.form_fields))
        self.assertEqual(pr.max_row, 2)  # one ready row (POC row is held)
        self.assertEqual(pr["I2"].value, 1.5)  # Activity Hours is a number
        self.assertEqual(wb["To-Confirm"].max_row, 2)
        self.assertEqual(wb["Period Ledger"].max_row, 3)
        self.assertIn("First version", wb["Per-Customer Deltas"]["A1"].value)
        # only the xlsx goes to the mirror
        self.assertEqual([p.name for p in (self.tmp / "mirror").iterdir()],
                         ["Salesforce_Activity_Log_2026-10-05_to_2026-10-11.xlsx"])

    def test_workbook_xml_is_excel_valid(self):
        """Regression: a sheet must not reference a pane it does not have (Excel 'repair' dialog)."""
        import re
        import zipfile
        self.commit(self.good_demo(), self.poc_row())
        res = render(self.profile, RULES, *self.P)
        with zipfile.ZipFile(res["xlsx"]) as z:
            for name in z.namelist():
                if not name.startswith("xl/worksheets/sheet"):
                    continue
                xml = z.read(name).decode()
                panes = set(re.findall(r'<pane [^>]*activePane="(\w+)"', xml))
                for ref in re.findall(r'<selection [^>]*pane="(\w+)"', xml):
                    self.assertIn(ref, panes, f"{name}: selection refers to missing pane {ref}")
                self.assertNotIn("<autoFilter/>", xml)

    def test_rerender_unchanged_keeps_no_history(self):
        self.commit(self.good_demo())
        render(self.profile, RULES, *self.P)
        res = render(self.profile, RULES, *self.P)
        self.assertEqual(res["changes"], "no change")
        self.assertFalse((Path(res["folder"]) / "history").exists())
        self.assertEqual(len(Path(res["folder"], "runs.md").read_text().strip().splitlines()), 6)  # 4 header lines + 2 renders

    def test_change_archives_previous_and_shows_deltas(self):
        first = self.commit(self.poc_row(no_opp_reason="Opportunity not created yet"))[0]
        render(self.profile, RULES, *self.P)
        self.commit({"action": "extend", "supersedes": first["entry_id"],
                     "row": dict(self.poc_row(no_opp_reason="Opportunity not created yet")["row"],
                                 activity_hours=3, activity_date="2026-10-07",
                                 evidence_refs=[self.eid("PROSEWARE OMA POC working session"), "user:1h on 7 Oct"])},
                    self.good_demo())
        res = render(self.profile, RULES, *self.P)
        hist = sorted(p.name for p in (Path(res["folder"]) / "history").iterdir())
        self.assertEqual(len(hist), 2)
        self.assertTrue(all("_2026" in h for h in hist))
        wb = load_workbook(res["xlsx"])
        rows = {r[0].value: [c.value for c in r] for r in wb["Per-Customer Deltas"].iter_rows(min_row=2)
                if r[0].value and r[1].value is not None}
        self.assertEqual(rows["PROSEWARE"][5], 1.0)  # 2h -> 3h
        self.assertIn("replaced by", rows["PROSEWARE"][7])
        self.assertEqual(rows["WOODGROVE"][6], "new")

    def test_legacy_flat_files_are_moved(self):
        out = self.profile.data_dir / "output"
        out.mkdir(parents=True)
        (out / "Salesforce_Activity_Log_2026-10-05_to_2026-10-11.md").write_text("old")
        res = render(self.profile, RULES, *self.P)
        self.assertEqual(res["migrated_legacy_files"],
                         ["output/2026/weeks/2026-W41_2026-10-05_to_2026-10-11/history/"
                          "Salesforce_Activity_Log_2026-10-05_to_2026-10-11_legacy.md"])
        self.assertEqual([p.name for p in out.iterdir()], ["2026"])

    def test_day_and_month_views_share_one_ledger(self):
        self.commit(self.good_demo())
        day = render(self.profile, RULES, date(2026, 10, 7), date(2026, 10, 7))
        month = render(self.profile, RULES, date(2026, 10, 1), date(2026, 10, 31))
        self.assertIn("/days/2026-10-07", day["folder"])
        self.assertIn("/months/2026-10_October", month["folder"])
        self.assertEqual((day["ready"], month["ready"]), (1, 1))


class TestDeltas(unittest.TestCase):
    def test_compute(self):
        before = [{"entry_id": "A1", "account": "X", "activity_hours": 1.0, "supersedes": ""}]
        now = [{"entry_id": "A2", "account": "X", "activity_hours": 2.0, "supersedes": "A1"},
               {"entry_id": "A3", "account": "Y", "activity_hours": 1.0, "supersedes": ""}]
        d = {x["account"]: x for x in compute_deltas(before, now)}
        self.assertEqual((d["X"]["change_h"], d["X"]["details"]), (1.0, "A1 replaced by A2"))
        self.assertEqual((d["Y"]["status"], d["Y"]["details"]), ("new", "added A3"))


if __name__ == "__main__":
    unittest.main()
