"""Account resolution against the profile's account registry (the source of truth).

Folder structure is only a hint; matching uses all text of an evidence item
(title, path segments) plus email domains. No match or ambiguity -> unresolved,
which the workflow turns into `[to confirm]`. Accounts are never guessed.
"""
from __future__ import annotations

import re


def _pattern(alias: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])")


class Registry:
    def __init__(self, accounts: list[dict], internal_account: str):
        self.internal_account = internal_account
        self.entries = []
        for a in accounts:
            names = [a["name"]] + list(a.get("aliases") or [])
            self.entries.append({
                "name": a["name"],
                "kind": a.get("kind", "customer"),
                "patterns": [(n, _pattern(n)) for n in names if n],
                "domains": [d.lower() for d in a.get("domains") or []],
            })

    def kind_of(self, name: str) -> str | None:
        if name == self.internal_account:
            return "internal"
        for e in self.entries:
            if e["name"] == name:
                return e["kind"]
        return None

    def canonical(self, name: str) -> str | None:
        """Registry spelling for a case-insensitive match on the account name or an alias,
        e.g. 'Wingtip' -> 'WINGTIP', 'adatum' -> 'adatum Group Sdn Bhd'."""
        low = (name or "").strip().lower()
        if low == self.internal_account.lower():
            return self.internal_account
        return next((e["name"] for e in self.entries
                     if low in (n.lower() for n, _ in e["patterns"])), None)

    def match(self, texts: list[str], domains: list[str], internal_only: bool = False,
              folder_hint: str | None = None) -> dict | None:
        hits: dict[str, dict] = {}
        doms = [d.lower() for d in domains or []]
        for e in self.entries:
            via = []
            if any(d == ed or d.endswith("." + ed) for d in doms for ed in e["domains"]):
                via.append("domain")
            for alias, pat in e["patterns"]:
                if folder_hint and pat.search(folder_hint.lower()):
                    via.append(f"folder:{alias}")
                    break
                if any(pat.search((t or "").lower()) for t in texts):
                    via.append(f"keyword:{alias}")
                    break
            if via:
                hits[e["name"]] = {"name": e["name"], "kind": e["kind"], "via": via}

        if not hits:
            if internal_only:
                return {"name": self.internal_account, "kind": "internal", "via": ["internal_only"],
                        "certain": False}
            return None

        customers = [h for h in hits.values() if h["kind"] == "customer"]
        partners = [h for h in hits.values() if h["kind"] == "partner"]
        if len(customers) == 1:
            out = dict(customers[0], certain=True)
            if partners:
                out["partners"] = [p["name"] for p in partners]
                out["via"] = out["via"] + ["routing:partner_deal_to_customer"]
            return out
        if len(customers) > 1:
            # A folder hint or a domain match breaks the tie; otherwise ambiguous.
            strong = [c for c in customers if any(v == "domain" or v.startswith("folder:") for v in c["via"])]
            if len(strong) == 1:
                return dict(strong[0], certain=True, also_mentioned=[c["name"] for c in customers if c is not strong[0]])
            return {"name": None, "kind": None, "via": ["ambiguous"], "certain": False,
                    "candidates": sorted(c["name"] for c in customers)}
        if len(partners) == 1:
            return dict(partners[0], certain=False, note="partner only: enablement -> partner; deal -> customer")
        return {"name": None, "kind": None, "via": ["ambiguous"], "certain": False,
                "candidates": sorted(p["name"] for p in partners)}
