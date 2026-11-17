"""Account names: the full name and any alias resolve to the registry spelling."""
import unittest

from sfal.accounts import Registry

ACCOUNTS = [{"name": "adatum Group Sdn Bhd", "kind": "customer", "aliases": ["adatum"]},
            {"name": "WINGTIP", "kind": "customer"}]


class TestCanonical(unittest.TestCase):
    def setUp(self):
        self.reg = Registry(ACCOUNTS, "Example Corp")

    def test_full_name_any_case(self):
        self.assertEqual(self.reg.canonical("adatum group sdn bhd"), "adatum Group Sdn Bhd")

    def test_alias_resolves_to_full_name(self):
        self.assertEqual(self.reg.canonical("adatum"), "adatum Group Sdn Bhd")
        self.assertEqual(self.reg.canonical("ADATUM"), "adatum Group Sdn Bhd")

    def test_unknown_and_empty_names(self):
        self.assertIsNone(self.reg.canonical("LITWARE"))
        self.assertIsNone(self.reg.canonical(""))

    def test_internal_account(self):
        self.assertEqual(self.reg.canonical("example corp"), "Example Corp")


if __name__ == "__main__":
    unittest.main()
