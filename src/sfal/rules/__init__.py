"""Org rule pack loader."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import yaml

from ..profile import ProfileError

RULES_DIR = Path(__file__).resolve().parent
DEFAULT_PACK = "example-rules-1.0.yaml"


@dataclass
class RulePack:
    data: dict

    @property
    def version(self) -> str:
        return self.data["version"]

    @property
    def internal_account(self) -> str:
        return self.data["internal_account"]

    @cached_property
    def type_codes(self) -> dict[str, str]:
        """num -> ledger code, e.g. '07' -> '07 · Product Demo'."""
        return {t["num"]: f'{t["num"]} · {t["name"]}' for t in self.data["activity_types"]}

    def type_num(self, code: str) -> str | None:
        """Accept '07 · Product Demo', '07', or 'Product Demo'; return '07' or None."""
        if not code:
            return None
        code = str(code).strip()
        for t in self.data["activity_types"]:
            if code in (t["num"], t["name"], f'{t["num"]} · {t["name"]}', f'{t["num"]} - {t["name"]}'):
                return t["num"]
        return None

    def __getattr__(self, name):
        try:
            return self.__dict__["data"][name]
        except KeyError:
            raise AttributeError(name) from None


class RulePackError(ProfileError):
    """The rule pack named in the profile cannot be used."""


def load_rules(pack: str | None = None) -> RulePack:
    """Load a rule pack: the bundled default, or your own file.

    `pack` is None (the bundled default), the name of a bundled file, or a path to a YAML file
    (starts with ~ or contains a /). The profile setting `rules_pack` supplies it.
    """
    pack = str(pack).strip() if pack else DEFAULT_PACK
    own = pack.startswith("~") or "/" in pack
    path = Path(pack).expanduser() if own else RULES_DIR / pack
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError:
        raise RulePackError(f"rules_pack: cannot read {path}") from None
    except yaml.YAMLError as e:
        raise RulePackError(f"rules_pack: {path} is not valid YAML ({e})") from None
    missing = [k for k in ("version", "internal_account", "activity_types", "routing") if not isinstance(data, dict) or k not in data]
    if missing:
        raise RulePackError(f"rules_pack: {path} is missing {', '.join(missing)}; start from the bundled pack")
    return RulePack(data)
