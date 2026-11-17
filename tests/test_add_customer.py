"""Adding a customer: plan first, then apply. Only temp folders and temp profiles are used."""
import tempfile
import unittest
from pathlib import Path

import yaml

from sfal import api
from sfal.profile import ProfileError, load_profile

PROFILE = """# test profile
owner:
  name: Tester, Pat
data_dir: {data}
workspace:
  root: {root}
  account_folder_level: {level}
accounts:
- name: Globex
  kind: customer
  aliases: [GLX]
"""


class TestAddCustomer(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / "ws"
        (self.root / "Malaysia").mkdir(parents=True)
        (self.root / "Vietnam").mkdir()
        (self.root / "_SFActivityLog").mkdir()

    def profile(self, level=2):
        p = self.tmp / "profile.yaml"
        p.write_text(PROFILE.format(data=self.tmp / "data", root=self.root, level=level))
        return str(p)

    def test_customer_folder_needs_a_country_and_lists_the_choices(self):
        r = api.account_add("ACME Bank", profile=self.profile())
        self.assertFalse(r["ok"])
        self.assertEqual(r["need"], "country")
        self.assertEqual(r["choices"], ["Malaysia", "Vietnam"])     # no _SFActivityLog

    def test_plan_writes_nothing(self):
        path = self.profile()
        before = Path(path).read_text()
        r = api.account_add("ACME Bank", profile=path, country="Malaysia", aliases=["ACME"])
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "plan")
        self.assertEqual(r["folder"]["action"], "create")
        self.assertEqual(Path(path).read_text(), before)
        self.assertFalse((self.root / "Malaysia" / "ACME Bank").exists())

    def test_confirm_adds_entry_keeps_others_and_creates_the_layout(self):
        path = self.profile()
        r = api.account_add("ACME Bank", profile=path, country="Malaysia", aliases=["ACME"],
                            domains=["acme.com"], confirm=True)
        self.assertEqual(r["status"], "added")
        self.assertTrue(Path(r["backup"]).exists())
        self.assertTrue((self.root / "Malaysia" / "ACME Bank" / "_ActivityLogging").is_dir())
        accounts = load_profile(path).accounts
        self.assertEqual([a["name"] for a in accounts], ["Globex", "ACME Bank"])
        self.assertEqual(accounts[1], {"name": "ACME Bank", "kind": "customer", "aliases": ["ACME"],
                                       "domains": ["acme.com"]})
        self.assertTrue(Path(path).read_text().startswith("# test profile"))   # comment kept
        self.assertEqual(yaml.safe_load(Path(path).read_text())["owner"]["name"], "Tester, Pat")
        self.assertTrue((self.tmp / "data" / "ledger" / "audit.log").exists())

    def test_existing_folder_is_reused_and_its_files_are_untouched(self):
        folder = self.root / "Malaysia" / "ACME Bank"
        folder.mkdir()
        (folder / "keep.txt").write_text("mine")
        r = api.account_add("ACME Bank", profile=self.profile(), country="Malaysia", confirm=True)
        self.assertEqual(r["folder"]["action"], "reuse")
        self.assertEqual(r["folders_created"], [str((folder / "_ActivityLogging").resolve())])
        self.assertEqual((folder / "keep.txt").read_text(), "mine")

    def test_name_or_alias_already_in_use_is_refused(self):
        path = self.profile()
        with self.assertRaisesRegex(ProfileError, 'already belongs to the account "Globex"'):
            api.account_add("globex", profile=path, country="Malaysia")
        with self.assertRaises(ProfileError):
            api.account_add("ACME Bank", profile=path, country="Malaysia", aliases=["GLX"])

    def test_folder_outside_the_workspace_is_refused(self):
        with self.assertRaises(ProfileError):
            api.account_add("ACME Bank", profile=self.profile(), folder="../escape", confirm=True)

    def test_bad_kind_is_refused(self):
        with self.assertRaisesRegex(ProfileError, "customer or partner"):
            api.account_add("ACME Bank", profile=self.profile(), kind="prospect", country="Malaysia")

    def test_no_folder_adds_the_profile_entry_only(self):
        path = self.profile()
        r = api.account_add("ACME Bank", profile=path, make_folder=False, confirm=True)
        self.assertIsNone(r["folder"])
        self.assertFalse((self.root / "ACME Bank").exists())
        self.assertIn("ACME Bank", [a["name"] for a in load_profile(path).accounts])

    def test_level_one_puts_the_folder_at_the_root_and_extra_folders_are_created(self):
        r = api.account_add("ACME Bank", profile=self.profile(level=1), extra_folders=["Proposals"], confirm=True)
        self.assertEqual(r["folder"]["layout"], ["_ActivityLogging", "Proposals"])
        self.assertTrue((self.root / "ACME Bank" / "Proposals").is_dir())


if __name__ == "__main__":
    unittest.main()
