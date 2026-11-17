"""Every host command and skill file has a YAML header that parses and has a description.
A stray ': ' in a description breaks the header and the AI tool silently drops the command."""
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


class TestHostFrontmatter(unittest.TestCase):
    def test_headers_parse(self):
        files = sorted(REPO.glob("hosts/**/*.md")) + sorted(REPO.glob("skill/*.md"))
        self.assertTrue(files)
        for f in files:
            text = f.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            with self.subTest(file=str(f.relative_to(REPO))):
                head = yaml.safe_load(text.split("---", 2)[1])
                self.assertIsInstance(head, dict)
                self.assertTrue(head.get("description"))


if __name__ == "__main__":
    unittest.main()
