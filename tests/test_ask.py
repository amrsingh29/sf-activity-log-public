"""sfal_ask round trip through a real MCP client over stdio (as Goose connects), both protocol generations."""
import asyncio
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from mcp import Client, StdioServerParameters, types

from test_engine import PROFILE

DECISIONS = [
    {"n": 1, "id": "cal:1", "when": "Tue 06 Oct 21:00", "hours": 0.5, "title": "Proseware Requirements Sync",
     "account": "PROSEWARE", "reason": "declined by email", "options": ["Skip", "Log", "Hours"], "default": "Skip"},
    {"n": 2, "id": "mail:2", "when": "Fri 09 Oct", "hours": None, "title": "Helix solution for AI Data Center",
     "account": "Hooli", "reason": "email only, hours unknown", "options": ["Skip", "Hours"], "default": "Skip"},
    {"n": 3, "id": "cal:3", "when": "Thu 08 Oct 15:30", "hours": 0.75, "title": "PG Kick-Off Call",
     "account": "Hooli", "reason": "broadcast", "options": ["Skip", "Log", "Hours"], "default": "Skip"},
]


class TestAsk(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        prof = dict(PROFILE, data_dir=str(self.tmp / "d"))
        (self.tmp / "p.yaml").write_text(yaml.safe_dump(prof))
        rd = self.tmp / "d" / "cache" / "r1"
        rd.mkdir(parents=True)
        (rd / "candidates.json").write_text(json.dumps({"decisions": DECISIONS}))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_ask(self, callback, mode="auto", args=None):
        exe = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "sfal-mcp"
        env = dict(os.environ, SFAL_PROFILE=str(self.tmp / "p.yaml"))

        async def go():
            async with Client(StdioServerParameters(command=str(exe), env=env),
                              elicitation_callback=callback, mode=mode) as c:
                r = await c.call_tool("sfal_ask", args or {"run_id": "r1"})
                return json.loads(r.content[0].text)
        return asyncio.run(go())

    def _answer(self, mode):
        seen = []

        async def cb(context, params):
            seen.append(params)
            props = params.requested_schema["properties"]
            names = list(props)
            self.assertEqual(names[0], "1 · Tue 06 Oct 21:00 · Proseware Requirements Sync")
            self.assertEqual(names[-1], "Details (optional)")
            self.assertEqual(props[names[0]]["enum"], ["Skip", "Log", "Hours"])
            self.assertEqual(props[names[0]]["default"], "Skip")
            # user typing: lowercase, a first letter, and an empty Enter (= default)
            return types.ElicitResult(action="accept", content={names[0]: "log", names[1]: "h", names[2]: "",
                                                                "Details (optional)": "2: 1h"})

        out = self.run_ask(cb, mode)
        self.assertTrue(out["ok"], out)
        self.assertEqual([a["answer"] for a in out["answers"]], ["Log", "Hours", "Skip"])
        self.assertEqual(out["details"], "2: 1h")
        self.assertNotIn("unclear", out)
        self.assertEqual(len(seen), 1)

    def test_modern_protocol(self):
        self._answer("auto")

    def test_legacy_protocol(self):
        self._answer("legacy")

    def test_only_subset_and_unclear_answer(self):
        async def cb(context, params):
            names = list(params.requested_schema["properties"])
            self.assertEqual(len(names), 2)  # one decision + details
            return types.ElicitResult(action="accept", content={names[0]: "maybe"})

        out = self.run_ask(cb, args={"run_id": "r1", "only": [3]})
        self.assertEqual(out["unclear"][0]["n"], 3)

    def test_durations_as_answers(self):
        async def cb(context, params):
            n = list(params.requested_schema["properties"])
            return types.ElicitResult(action="accept", content={n[0]: "45m", n[1]: "1.5h", n[2]: "20"})

        out = self.run_ask(cb)
        a = {x["n"]: x for x in out["answers"]}
        self.assertEqual((a[1]["answer"], a[1]["hours"]), ("Hours", 0.75))
        self.assertEqual((a[2]["answer"], a[2]["hours"]), ("Hours", 1.5))
        self.assertEqual(a[3]["hours"], 20.0)  # bare 20 on a 0.75h meeting
        self.assertEqual([u["n"] for u in out["unclear"]], [3])
        self.assertIn("minutes", out["unclear"][0]["why"])

    def test_user_cancels(self):
        async def cb(context, params):
            return types.ElicitResult(action="cancel")

        self.assertEqual(self.run_ask(cb)["stopped"], "cancel")


if __name__ == "__main__":
    unittest.main()
