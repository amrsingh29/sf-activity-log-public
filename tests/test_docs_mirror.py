"""Docs mirror: text copies per account, incremental runs, removals and the safety rules.
Only temp folders, temp profiles and generated fixture documents are used."""
import json
import os
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

import docx
import openpyxl
from pypdf import PdfWriter

from sfal import api, docs_mirror
from sfal.profile import load_profile

PROFILE = """owner:
  name: Tester, Pat
data_dir: {data}
workspace:
  root: {root}
  ignore: ["_SFActivityLog/*"]
  internal_folders: [_Internal]
accounts:
- {{name: ACME Bank, kind: customer, aliases: [ACME Bank Berhad, ACME tender]}}
- {{name: Globex, kind: customer}}
- {{name: Initech, kind: partner}}
docs_mirror:
  enabled: {enabled}
  output: {out}
  accounts: {accounts}
  exclude_accounts: {exclude}
  extra_folders: {extra}
  gbrain_import: {gbrain}
"""


def make_docx(path: Path, heading: str, text: str):
    d = docx.Document()
    d.add_heading(heading, level=1)
    d.add_paragraph(text)
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Requirement", "Answer"
    t.cell(1, 0).text, t.cell(1, 1).text = "Ariba sync", "Integration Studio connector"
    path.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(path))


def make_pptx(path: Path, title: str, body: str, notes: str):
    ns = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')

    def sp(ph, text):
        phx = f'<p:ph type="{ph}"/>' if ph else ""
        return (f'<p:sp><p:nvSpPr><p:nvPr>{phx}</p:nvPr></p:nvSpPr>'
                f'<p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>')
    slide = f'<p:sld {ns}><p:cSld><p:spTree>{sp("title", title)}{sp(None, body)}</p:spTree></p:cSld></p:sld>'
    note = f'<p:notes {ns}><p:cSld><p:spTree>{sp("body", notes)}</p:spTree></p:cSld></p:notes>'
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId2" Type="x" Target="../notesSlides/notesSlide1.xml"/></Relationships>')
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("ppt/slides/slide1.xml", slide)
        z.writestr("ppt/slides/_rels/slide1.xml.rels", rels)
        z.writestr("ppt/notesSlides/notesSlide1.xml", note)


def make_xlsx(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Requirements"
    ws.append(["ID", "Requirement", "Compliance"])
    ws.append(["R1", "Single sign-on", "Yes"])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))


def make_pdf(path: Path, text: str, password: str | None = None, owner_only: int | None = None):
    """A one-page PDF with a real text layer (hand-written content stream)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    if password or owner_only is not None:
        w = PdfWriter(clone_from=str(path))
        if password:
            w.encrypt(password)
        else:                       # opens without a password; owner_only = permission flags
            w.encrypt(user_password="", owner_password="owner", permissions_flag=owner_only)
        with path.open("wb") as f:
            w.write(f)


class _Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.root = self.tmp / "ws"
        self.out = self.tmp / "mirror"
        acme = self.root / "Malaysia" / "Partner" / "ACME Bank" / "2026" / "ESM"
        make_docx(acme / "Solution-Design.docx", "Integration", "We connect to Ariba.")
        make_pptx(acme / "Workshop.pptx", "Why ACME Bank", "Faster changes", "Say hello first")
        make_pdf(acme / "RFP-Pack.pdf", "Real-time PO sync with Ariba via standard APIs " * 8)
        make_xlsx(acme / "Compliance-Matrix.xlsx")
        make_xlsx(acme / "Pricing.xlsx")
        make_docx(self.root / "Globex" / "Proposal.docx", "Proposal", "Globex text")
        make_docx(self.root / "Misc" / "Training.docx", "Training", "No account here")
        make_docx(self.root / "_Internal" / "Plan.docx", "Plan", "Internal")
        make_docx(self.root / "_SFActivityLog" / "ignored.docx", "Log", "Never")
        make_docx(self.root / "ACME Bank" / "Archive" / "Old-Design.docx", "Old", "Skipped folder")

    def profile(self, enabled="true", accounts="[ACME Bank]", exclude="[]", extra="[]", out=None, gbrain="false"):
        p = self.tmp / "profile.yaml"
        p.write_text(PROFILE.format(data=self.root / "_SFActivityLog", root=self.root, enabled=enabled,
                                    out=out or self.out, accounts=accounts, exclude=exclude, extra=extra, gbrain=gbrain))
        return str(p)

    def copy(self, rel):
        return self.out / "ACME Bank" / "2026" / "ESM" / rel


class TestDocsMirror(_Fixture):
    def test_converts_each_type_under_the_account_with_a_header(self):
        r = api.docs_sync(profile=self.profile())
        self.assertTrue(r["ok"])
        self.assertEqual(r["converted"], 4)                                   # docx, pptx, pdf, compliance xlsx
        design = self.copy("Solution-Design.docx.md").read_text()
        self.assertIn("account: ACME Bank", design)
        self.assertIn("original_rel: Malaysia/Partner/ACME Bank/2026/ESM/Solution-Design.docx", design)
        self.assertIn("## Integration", design)
        self.assertIn("| Ariba sync | Integration Studio connector |", design)
        deck = self.copy("Workshop.pptx.md").read_text()
        self.assertIn("## Slide 1: Why ACME Bank", deck)
        self.assertIn("Speaker notes:", deck)
        self.assertIn("Say hello first", deck)
        self.assertIn("Real-time PO sync", self.copy("RFP-Pack.pdf.md").read_text())
        self.assertIn("| R1 | Single sign-on | Yes |", self.copy("Compliance-Matrix.xlsx.md").read_text())
        self.assertFalse(self.copy("Pricing.xlsx.md").exists())               # Excel name not matched
        self.assertIn("excel name not matched", r["skipped_by_reason"])
        self.assertFalse((self.out / "Globex").exists())                      # account not selected
        self.assertFalse(list(self.out.rglob("Old-Design*")))                 # skip_folders
        self.assertFalse(list(self.out.rglob("ignored*")))                    # workspace ignore + data_dir
        self.assertTrue((self.out / "_manifest.json").exists())
        self.assertIn("Converted: 4", (self.out / "_report.md").read_text())

    def test_second_run_converts_only_changed_files(self):
        path = self.profile()
        api.docs_sync(profile=path)
        r = api.docs_sync(profile=path)
        self.assertEqual((r["converted"], r["unchanged"]), (0, 4))
        src = self.root / "Malaysia/Partner/ACME Bank/2026/ESM/Solution-Design.docx"
        make_docx(src, "Integration", "Now with a new section.")
        os.utime(src, (src.stat().st_atime, src.stat().st_mtime + 5))
        r = api.docs_sync(profile=path)
        self.assertEqual((r["converted"], r["unchanged"]), (1, 3))
        self.assertIn("new section", self.copy("Solution-Design.docx.md").read_text())

    def test_rename_and_delete_remove_old_copies(self):
        path = self.profile()
        api.docs_sync(profile=path)
        src = self.root / "Malaysia/Partner/ACME Bank/2026/ESM"
        (src / "Solution-Design.docx").rename(src / "Solution-Design-FINAL.docx")
        (src / "Workshop.pptx").unlink()
        r = api.docs_sync(profile=path)
        self.assertEqual((r["converted"], r["removed"]), (1, 2))
        self.assertTrue(self.copy("Solution-Design-FINAL.docx.md").exists())
        self.assertFalse(self.copy("Solution-Design.docx.md").exists())
        self.assertFalse(self.copy("Workshop.pptx.md").exists())

    def test_different_layouts_and_aliases_land_in_the_same_account(self):
        make_docx(self.root / "Customers" / "ACME Bank Berhad" / "Bids" / "Notes.docx", "N", "alias layout")
        make_docx(self.root / "Work" / "2026 Deals" / "ACME tender" / "Scope.docx", "S", "deal-name alias")
        api.docs_sync(profile=self.profile())
        self.assertTrue((self.out / "ACME Bank" / "Bids" / "Notes.docx.md").exists())
        self.assertTrue((self.out / "ACME Bank" / "Scope.docx.md").exists())

    def test_unassigned_and_internal_files_are_not_copied(self):
        r = api.docs_sync(profile=self.profile(accounts="[all]", exclude="[Globex]"))
        self.assertFalse((self.out / "_unassigned").exists())
        self.assertFalse((self.out / "_internal").exists())
        self.assertFalse((self.out / "Globex").exists())                      # excluded from [all]
        self.assertTrue(any(k.startswith("unassigned") for k in r["skipped_by_reason"]))

    def test_dry_run_writes_nothing(self):
        r = api.docs_sync(profile=self.profile(), dry_run=True)
        self.assertEqual(r["converted"], 4)
        self.assertFalse(self.out.exists())

    def test_one_account_only_and_unknown_account(self):
        path = self.profile(accounts="[ACME Bank, Globex]")
        r = api.docs_sync(profile=path, account="globex")
        self.assertEqual((r["account"], r["converted"]), ("Globex", 1))
        self.assertFalse((self.out / "ACME Bank").exists())
        with self.assertRaises(api.ApiError):
            api.docs_sync(profile=path, account="Nobody Corp")

    def test_deselecting_an_account_removes_its_copies(self):
        api.docs_sync(profile=self.profile(accounts="[ACME Bank, Globex]"))
        r = api.docs_sync(profile=self.profile(accounts="[ACME Bank]"))
        self.assertEqual(r["removed"], 1)
        self.assertFalse((self.out / "Globex").exists())

    def test_protected_and_encrypted_files_are_skipped(self):
        acme = self.root / "Malaysia/Partner/ACME Bank/2026/ESM"
        (acme / "Secret.docx").write_bytes(docs_mirror.OLE_MAGIC + b"\0" * 100)
        make_pdf(acme / "Locked.pdf", "secret", password="pw")
        make_pdf(acme / "NoCopy.pdf", "secret", owner_only=0b1111_1111_1111_1111_1111_1111_1110_1100)   # copy bit off
        make_pdf(acme / "VendorGuide.pdf", "Readable guide text " * 20, owner_only=-1)                   # all allowed
        for dry in (True, False):                                             # dry run reports the same
            r = api.docs_sync(profile=self.profile(), dry_run=dry)
            skipped = r["skipped_by_reason"]["protected (encrypted or rights-managed)"]["files"]
            self.assertEqual(sorted(Path(f).name for f in skipped), ["Locked.pdf", "NoCopy.pdf", "Secret.docx"])
        self.assertFalse(self.copy("Secret.docx.md").exists())
        self.assertIn("Readable guide text", self.copy("VendorGuide.pdf.md").read_text())

    def test_extra_folder_name_counts_for_the_account(self):
        shared = self.tmp / "shared" / "Globex - AIOps 2027"
        make_docx(shared / "Design.docx", "D", "shared by a colleague")
        api.docs_sync(profile=self.profile(accounts="[Globex]", extra=f"['{shared}']"))
        self.assertTrue((self.out / "Globex" / "Design.docx.md").exists())

    def test_same_file_name_from_two_folders_keeps_both(self):
        make_docx(self.root / "Globex" / "a" / "Globex" / "Proposal.docx", "P", "second")
        r = api.docs_sync(profile=self.profile(accounts="[Globex]"))
        self.assertEqual(r["converted"], 2)
        self.assertEqual(len(list((self.out / "Globex").glob("Proposal.docx*.md"))), 2)

    def test_mass_removal_is_held_unless_rebuild(self):
        for i in range(24):
            make_docx(self.root / "Globex" / f"Doc{i}.docx", "D", "x")
        path = self.profile(accounts="[Globex]")
        api.docs_sync(profile=path)
        r = api.docs_sync(profile=self.profile(accounts="[ACME Bank]"))
        self.assertEqual(r["removed"], 0)
        self.assertIn("warning", r)
        self.assertTrue((self.out / "Globex" / "Doc0.docx.md").exists())
        r = api.docs_sync(profile=self.profile(accounts="[ACME Bank]"), rebuild=True)
        self.assertEqual(r["removed"], 25)
        self.assertFalse((self.out / "Globex").exists())

    def test_output_must_stay_out_of_synced_and_source_folders(self):
        for bad in (self.root / "mirror", self.root / "_SFActivityLog" / "m",
                    Path.home() / "Library/CloudStorage/OneDrive-ACME/mirror"):
            with self.assertRaises(api.ApiError):
                api.docs_sync(profile=self.profile(out=bad))

    def test_off_by_default_and_missing_root(self):
        with self.assertRaises(api.ApiError):
            api.docs_sync(profile=self.profile(enabled="false"))
        path = self.profile()
        api.docs_sync(profile=path)
        os.rename(self.root, self.tmp / "gone")
        with self.assertRaises(api.ApiError):                                 # OneDrive not running: nothing removed
            api.docs_sync(profile=path)
        self.assertTrue(self.copy("RFP-Pack.pdf.md").exists())

    def test_status_reports_copies_per_account(self):
        path = self.profile()
        api.docs_sync(profile=path)
        s = api.docs_status(profile=path)
        self.assertEqual(s["per_account"], {"ACME Bank": 4})
        self.assertIn("Converted: 4", s["last_report"])
        manifest = json.loads((self.out / "_manifest.json").read_text())
        self.assertTrue(all(v["sha256"].startswith("sha256:") for v in manifest["files"].values()))

    def test_profile_rejects_a_non_list_setting(self):
        p = Path(self.profile())
        p.write_text(p.read_text().replace("accounts: [ACME Bank]", "accounts: ACME Bank"))
        with self.assertRaises(Exception):
            load_profile(str(p))


if __name__ == "__main__":
    unittest.main()


class TestDocsMirrorGBrain(_Fixture):
    """gbrain_import: the mirror becomes a local git repo and `gbrain sync` is asked to read it.
    A fake gbrain script stands in for the real one; it records each call."""

    def setUp(self):
        super().setUp()
        self.calls = self.tmp / "gbrain-calls.txt"
        self.fake = self.tmp / "fake-gbrain"
        self.fake_exit(0)
        os.environ["SFAL_GBRAIN"] = str(self.fake)
        self.addCleanup(os.environ.pop, "SFAL_GBRAIN", None)

    def fake_exit(self, code):
        self.fake.write_text(f'#!/bin/sh\necho "$@" >> "{self.calls}"\n'
                             f'[ {code} -eq 0 ] && echo "synced 3 entries" || echo "storage_error" >&2\n'
                             f'exit {code}\n')
        self.fake.chmod(0o755)

    def run_sync(self, **kw):
        return api.docs_sync(profile=self.profile(gbrain="true"), **kw)

    def ncalls(self):
        return len(self.calls.read_text().splitlines()) if self.calls.exists() else 0

    def test_off_means_no_git_and_no_gbrain_call(self):
        res = api.docs_sync(profile=self.profile())
        self.assertNotIn("gbrain", res)
        self.assertIn("gbrain_import", res["next"])
        self.assertFalse((self.out / ".git").exists())
        self.assertEqual(self.ncalls(), 0)

    def test_sync_commits_and_updates_gbrain_once_per_change(self):
        res = self.run_sync()
        self.assertEqual(res["gbrain"]["status"], "updated")
        self.assertTrue((self.out / ".git").exists())
        self.assertIn("_manifest.json", (self.out / ".gitignore").read_text())
        self.assertIn(".gbrain-owner.json", (self.out / ".gitignore").read_text())
        self.assertEqual(self.calls.read_text().split(), ["sync", "--source", "docs", "--no-embed", "--no-pull"])
        self.assertEqual(self.run_sync()["gbrain"]["status"], "up_to_date")     # nothing changed
        self.assertEqual(self.ncalls(), 1)
        make_docx(self.root / "ACME Bank" / "New.docx", "New", "fresh")
        self.assertEqual(self.run_sync()["gbrain"]["status"], "updated")
        self.assertEqual(self.ncalls(), 2)

    def test_gbrain_marker_already_committed_is_untracked(self):
        import subprocess
        self.run_sync()
        (self.out / ".gbrain-owner.json").write_text("{}")
        (self.out / ".gitignore").write_text("_manifest.json\n_report.md\n")      # an older mirror
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], cwd=self.out, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "old"], cwd=self.out, check=True)
        self.run_sync()
        tracked = subprocess.run(["git", "ls-files"], cwd=self.out, capture_output=True, text=True).stdout
        self.assertNotIn(".gbrain-owner.json", tracked)
        self.assertTrue((self.out / ".gbrain-owner.json").exists())

    def test_gbrain_failure_keeps_the_sync_ok_and_retries_next_time(self):
        self.fake_exit(1)
        res = self.run_sync()
        self.assertTrue(res["ok"])
        self.assertEqual(res["gbrain"]["status"], "failed")
        self.assertIn("gbrain sources add docs", res["gbrain"]["fix"])
        self.assertTrue(self.copy("Solution-Design.docx.md").exists())
        self.fake_exit(0)
        self.assertEqual(self.run_sync()["gbrain"]["status"], "updated")       # retried with no new changes
        self.assertTrue(api.docs_status(profile=self.profile(gbrain="true"))["gbrain_last_ok"])

    def test_dry_run_never_touches_gbrain(self):
        self.run_sync(dry_run=True)
        self.assertEqual(self.ncalls(), 0)
        self.assertFalse((self.out / ".git").exists())

    def test_missing_gbrain_is_skipped_not_an_error(self):
        with unittest.mock.patch.object(docs_mirror, "gbrain_bin", return_value=None):
            res = self.run_sync()
        self.assertTrue(res["ok"])
        self.assertEqual(res["gbrain"]["status"], "skipped")
        self.assertNotIn("fix", res["gbrain"])
        self.assertNotIn("sources add", res["gbrain"]["reason"])

    def test_no_gbrain_installed_means_no_gbrain_hint(self):
        with unittest.mock.patch.object(docs_mirror, "gbrain_bin", return_value=None):
            res = api.docs_sync(profile=self.profile())
        self.assertNotIn("next", res)
        self.assertNotIn("gbrain", res)

    def test_bad_source_id_is_rejected(self):
        p = self.profile(gbrain="true")
        Path(p).write_text(Path(p).read_text() + "  gbrain_source: Docs Mirror!\n")
        with self.assertRaises(Exception):
            load_profile(p)
