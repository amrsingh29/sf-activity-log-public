"""Docs stay in sync with the code: links resolve, pages stay short, generated pages are current,
and every check, CLI command, MCP tool and profile setting is documented."""
import asyncio
import importlib.util
import re
import unittest
from pathlib import Path

from sfal.profile import DEFAULTS
from sfal.validate import CHECKS

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MAX_LINES = 160
LONG_OK = {"maintainers"}  # design, decisions, changelog may be long
LINK = re.compile(r"\]\(([^)#\s]+)(#[^)]*)?\)")


def pages():
    # docs, plus the root files (README, AGENTS, CONTRIBUTING, SECURITY...) and .github templates
    return sorted(DOCS.rglob("*.md")) + sorted(ROOT.glob("*.md")) + sorted((ROOT / ".github").rglob("*.md"))


class TestDocs(unittest.TestCase):
    def test_links_resolve(self):
        broken = []
        for p in pages():
            for target, _ in LINK.findall(p.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (p.parent / target).resolve().exists():
                    broken.append(f"{p.relative_to(ROOT)} -> {target}")
        self.assertEqual(broken, [])

    def test_pages_are_short(self):
        long = [f"{p.relative_to(ROOT)} ({n} lines)" for p in pages()
                if p.parent.name not in LONG_OK and (n := len(p.read_text().splitlines())) > MAX_LINES]
        self.assertEqual(long, [])

    def test_every_page_is_linked_from_the_index(self):
        index = (DOCS / "README.md").read_text()
        missing = [str(p.relative_to(DOCS)) for p in DOCS.rglob("*.md")
                   if p.name != "README.md" and str(p.relative_to(DOCS)) not in index]
        self.assertEqual(missing, [])

    def test_task_pages_follow_the_template(self):
        """start/ and use/ pages: title, a '>' purpose line, and a closing 'Next:' line."""
        bad = []
        for p in sorted((DOCS / "start").glob("*.md")) + sorted((DOCS / "use").glob("*.md")):
            lines = [l for l in p.read_text().splitlines() if l.strip()]
            if not (lines[0].startswith("# ") and lines[1].startswith("> ") and lines[-1].startswith("Next:")):
                bad.append(str(p.relative_to(DOCS)))
        self.assertEqual(bad, [])

    def test_rules_page_is_generated_and_current(self):
        spec = importlib.util.spec_from_file_location("gen_docs", ROOT / "scripts" / "gen_docs.py")
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        self.assertEqual((DOCS / "reference" / "rules.md").read_text(), gen.render(),
                         "run: .venv/bin/python scripts/gen_docs.py")
        for code in CHECKS:
            self.assertIn(code, gen.render())

    def test_every_profile_setting_is_documented(self):
        text = (DOCS / "reference" / "configuration.md").read_text()
        keys = set(DEFAULTS) | set(DEFAULTS["owner"]) | set(DEFAULTS["workspace"]) | \
            {k for s in DEFAULTS["sources"].values() for k in s} | set(DEFAULTS["policy_overrides"]) | \
            {f"docs_mirror.{k}" for k in DEFAULTS["docs_mirror"]}
        missing = sorted(k for k in keys if k not in text)
        self.assertEqual(missing, [])

    def test_every_cli_command_and_mcp_tool_is_documented(self):
        text = (DOCS / "reference" / "commands.md").read_text()
        cli = re.findall(r'add_parser\("([a-z-]+)"', (ROOT / "src" / "sfal" / "cli.py").read_text())
        self.assertEqual([c for c in cli if not re.search(rf"`[^`]*\b{re.escape(c)}\b", text)], [])
        from sfal import mcp_server
        tools = [t.name for t in asyncio.run(mcp_server.server.list_tools())]
        self.assertEqual([t for t in tools if f"`{t}`" not in text], [])

    def test_no_real_customer_names_in_user_docs(self):
        # user-facing docs use fictional examples (ACME Bank, Globex, Initech)
        real = re.compile(r"\b(PROSEWARE|WOODGROVE|CONTOSO|WINGTIP|FABRIKAM|Alex|Ravi|Menon)\b", re.I)
        hits = [str(p.relative_to(ROOT)) for p in pages()
                if p.parent.name != "maintainers" and real.search(p.read_text())]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
