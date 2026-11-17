"""Rule pack choice: the bundled default, or your own file named in the profile. Temp files only."""
import tempfile
import unittest
from pathlib import Path

import yaml

from sfal import api
from sfal.profile import ProfileError
from sfal.rules import DEFAULT_PACK, RULES_DIR, RulePackError, load_rules

PROFILE = """owner:
  name: Tester, Pat
data_dir: {data}
{extra}accounts:
- name: Globex
  kind: customer
"""


class TestRulePack(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)

    def own_pack(self, **change):
        data = yaml.safe_load((RULES_DIR / DEFAULT_PACK).read_text(encoding="utf-8"))
        data.update(version="mine-1.0", internal_account="Initech Corp (999)", **change)
        path = self.tmp / "mine.yaml"
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return path

    def profile(self, pack=None):
        extra = f"rules_pack: {pack}\n" if pack else ""
        p = self.tmp / "profile.yaml"
        p.write_text(PROFILE.format(data=self.tmp / "data", extra=extra))
        return str(p)

    def test_default_is_the_bundled_pack(self):
        self.assertEqual(load_rules().version, load_rules(DEFAULT_PACK).version)

    def test_a_path_loads_your_own_pack(self):
        r = load_rules(str(self.own_pack()))
        self.assertEqual((r.version, r.internal_account), ("mine-1.0", "Initech Corp (999)"))

    def test_tilde_paths_are_expanded(self):
        home = Path.home()
        pack = self.own_pack()
        try:
            rel = "~/" + str(pack.relative_to(home))
        except ValueError:
            self.skipTest("temp folder is outside the home folder")
        self.assertEqual(load_rules(rel).version, "mine-1.0")

    def test_missing_unreadable_or_incomplete_packs_are_refused(self):
        with self.assertRaisesRegex(RulePackError, "cannot read"):
            load_rules(str(self.tmp / "nope.yaml"))
        bad = self.tmp / "bad.yaml"
        bad.write_text("version: x\n")
        with self.assertRaisesRegex(RulePackError, "missing"):
            load_rules(str(bad))
        bad.write_text("a: [unclosed\n")
        with self.assertRaisesRegex(RulePackError, "not valid YAML"):
            load_rules(str(bad))
        self.assertTrue(issubclass(RulePackError, ProfileError))   # the CLI already reports these

    def test_the_profile_picks_the_pack(self):
        self.assertEqual(api.rules(self.profile(self.own_pack()))["version"], "mine-1.0")
        self.assertEqual(api.rules(self.profile())["version"], load_rules().version)

    def test_doctor_reports_a_pack_that_cannot_be_read(self):
        report = api.doctor(self.profile(self.tmp / "nope.yaml"))
        self.assertFalse(report["ok"])
        self.assertIn("cannot read", report["rules_pack"])

    def test_add_customer_uses_the_internal_account_of_your_pack(self):
        profile = self.profile(self.own_pack())
        with self.assertRaisesRegex(ProfileError, "already belongs"):
            api.account_add("Initech Corp (999)", profile=profile, make_folder=False)


if __name__ == "__main__":
    unittest.main()
