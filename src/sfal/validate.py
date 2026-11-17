"""Validator - checks every proposed change against the org rule pack (logging guide v1.0).

Hard errors block commit. Warnings are shown at review. Rows whose hours or account are
`[to confirm]` are valid but HELD: kept in the ledger, excluded from Paste-Ready.

Check ids (documented in docs/RULES.md):
  C01 activity type valid            C11 setup for a demo -> 07 (warn)
  C02 status valid                   C12 evidence refs exist / not excluded
  C03 hours > 0 or [to confirm]      C13 activity date backed by evidence
  C04 hours within evidence; prep    C14 solution area valid; Other detail in Notes
      separated                      C15 notes present and descriptive
  C05 account routing                C16 evidence already logged elsewhere
  C06 no opportunity -> reason       C17 activity date inside period (warn)
  C07 opp expected (warn)            C18 confidence valid
  C08 one record per Value Review/POC/RFP     C19 extend targets an active, matching record
  C09 long-running dates; Value Review dates  C20 primary owner present
  C10 demo logged separately         C21 overlapping meetings logged twice (warn)
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime

from .accounts import Registry
from .ledger import TO_CONFIRM

# Every check, for docs/reference/rules.md (generated) and the docs-coverage test.
# level: block = stops the commit; warn = shown at review; hold = valid but kept out of Paste-Ready.
CHECKS = {
    "C01": ("block", "Activity type is one of the 22 logging guide types"),
    "C02": ("block", "Status is Completed, In Progress, Planned or Cancelled"),
    "C03": ("block", "Activity Hours above 0 - or '[to confirm]', which holds the row"),
    "C04": ("block", "Hours are within the evidence; prep-titled meetings count only as prep; user-confirmed hours need a user: ref"),
    "C05": ("block", "Account routing: exact registry name; internal = Example Corp; partner deals go to the customer"),
    "C06": ("block", "No opportunity means a 'Reason (no opportunity)' - or '[to confirm]', which holds the row"),
    "C07": ("warn", "RFP/RFI, Value Review and POC/POV should link an opportunity"),
    "C08": ("block", "One record per Value Review / POC-POV / RFP: needs a consolidation key; extend instead of duplicating"),
    "C09": ("block", "Long-running records: Activity Date = latest date; Value Review Notes state start and end dates"),
    "C10": ("block", "A demo inside a POC/POV or Quick Start is logged separately as 07 Product Demo"),
    "C11": ("warn", "Environment prep for one demo is 07 Product Demo, not 22 Team Administration"),
    "C12": ("block", "Every row cites evidence that exists and was not filtered out as noise"),
    "C13": ("block", "Activity Date matches a date in the cited evidence"),
    "C14": ("block", "Solution Area values are valid; 'Other' needs 'Other: ...' in Notes"),
    "C15": ("block", "Notes describe what was done, in detail"),
    "C16": ("block", "Evidence already logged in another row cannot be logged again"),
    "C17": ("warn", "Activity Date lies outside the run period"),
    "C18": ("block", "Confidence is High, Medium or Low"),
    "C19": ("block", "Extend/void targets an active record with the same consolidation key"),
    "C20": ("block", "Primary Owner is set (from the profile)"),
    "C21": ("warn", "Two rows cite meetings that overlap in time"),
}

DATE_IN_TEXT = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[ -/](?:[A-Za-z]{3,9}|\d{1,2})[ -/]\d{2,4}\b|\b\d{1,2} [A-Za-z]{3,9}\b")
TOLERANCE_H = 0.01
CONFIDENCE = ("High", "Medium", "Low")


def approval_code(proposal: dict) -> str:
    canon = json.dumps(proposal.get("changes", []), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:8]


def _num(v):
    if v in (None, ""):
        return 0.0
    if v == TO_CONFIRM:
        return TO_CONFIRM
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _union_hours(items: list[dict]) -> float:
    """Time covered by timed items (overlaps counted once) + stated hours of untimed items."""
    stated = sum(float(x["hours"]) for x in items if x.get("hours") and not (x.get("start") and x.get("end")))
    return round(_span_hours(items) + stated, 2)


def _span_hours(items: list[dict]) -> float:
    spans = sorted((datetime.fromisoformat(x["start"]), datetime.fromisoformat(x["end"]))
                   for x in items if x.get("start") and x.get("end"))
    total, cur_s, cur_e = 0.0, None, None
    for s, e in spans:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return round(total / 3600, 2)


class Validator:
    def __init__(self, profile, rules, evidence: dict, ledger_rows: list[dict]):
        self.p, self.r = profile, rules
        self.ev = {x["id"]: x for x in evidence.get("items", [])}
        self.period = (date.fromisoformat(evidence["period"]["from"]), date.fromisoformat(evidence["period"]["to"]))
        self.rows = {r["entry_id"]: r for r in ledger_rows}
        self.active = [r for r in ledger_rows if not r["voided"]]
        self.logged = {ref: r["entry_id"] for r in self.active for ref in r["evidence_refs"]}
        self.registry = Registry(profile.accounts, rules.internal_account)

    def run(self, proposal: dict) -> dict:
        errors, warnings, held = [], [], []
        keys_new: dict[str, int] = {}
        changes = proposal.get("changes") or []
        if not changes:
            errors.append({"change": None, "code": "C00", "message": "proposal has no changes"})
        for i, c in enumerate(changes):
            e, w, h = self._check(i, c, keys_new)
            errors += e
            warnings += w
            held += h
        warnings += self._overlaps(changes)
        ok = not errors
        return {"ok": ok, "errors": errors, "warnings": warnings, "held": held,
                "approval_code": approval_code(proposal) if ok else None,
                "summary": {"changes": len(changes), "errors": len(errors), "warnings": len(warnings),
                            "held": len(held)}}

    def _overlaps(self, changes: list[dict]) -> list[dict]:
        """C21: two rows citing calendar items that overlap in time -> same hours counted twice."""
        cited = []
        for i, c in enumerate(changes):
            for ref in (c.get("row") or {}).get("evidence_refs") or []:
                x = self.ev.get(ref)
                if x and x.get("start") and x.get("end"):
                    cited.append((i, x))
        out, seen = [], set()
        for a_i, (i, a) in enumerate(cited):
            for j, b in cited[a_i + 1:]:
                if i == j or (i, j) in seen:
                    continue
                if a["start"] < b["end"] and b["start"] < a["end"]:
                    seen.add((i, j))
                    out.append({"change": j, "code": "C21",
                                "message": f"overlaps change {i} ('{a['title']}' vs '{b['title']}'); "
                                           "confirm with the user which one happened or split the hours"})
        return out

    # ------------------------------------------------------------------
    def _check(self, i: int, c: dict, keys_new: dict):
        E, W, H = [], [], []

        def err(code, msg):
            E.append({"change": i, "code": code, "message": msg})

        def warn(code, msg):
            W.append({"change": i, "code": code, "message": msg})

        action = c.get("action")
        if action == "void":
            r = self.rows.get(c.get("entry_id"))
            if not r or r["voided"]:
                err("C19", f"void target {c.get('entry_id')} missing or already void")
            if not c.get("reason"):
                err("C19", "void needs a reason")
            return E, W, H
        if action not in ("new", "extend"):
            err("C00", f"unknown action '{action}' (use new | extend | void)")
            return E, W, H

        row = c.get("row") or {}
        R = self.r
        num = R.type_num(row.get("activity_type", ""))
        prev = None

        # C20 owner (engine fills from profile; check it exists)
        if not self.p.owner:
            err("C20", "profile owner.name missing (Primary Owner is required)")

        # C01 / C02
        if not num:
            err("C01", f"activity_type '{row.get('activity_type')}' is not one of the 22 types")
        status = row.get("status") or R.default_status
        if status not in R.statuses:
            err("C02", f"status '{status}' not in {R.statuses}")

        # C12 evidence
        refs = list(row.get("evidence_refs") or [])
        if not refs:
            err("C12", "evidence_refs is empty - every row needs evidence")
        user_refs = [x for x in refs if x.startswith("user:")]
        if action == "extend":
            prev = self.rows.get(c.get("supersedes"))
        prev_refs = set(prev["evidence_refs"]) if prev else set()
        ev_items = []
        for ref in refs:
            if ref.startswith("user:") or ref in prev_refs:
                continue
            x = self.ev.get(ref)
            if not x:
                err("C12", f"evidence {ref} not found in this run's evidence")
            elif x.get("excluded"):
                err("C12", f"evidence {ref} was excluded as noise ({x['excluded']}); confirm with user and cite user: ref instead")
            else:
                ev_items.append(x)
                # C16
                owner_entry = next((self.logged[i] for i in [ref] + list(x.get("legacy_ids") or [])
                                    if i in self.logged), None)
                if owner_entry and not (prev and owner_entry == prev["entry_id"]):
                    err("C16", f"evidence {ref} is already logged in {owner_entry}; extend or void that row instead")

        # C03 / C04 hours
        ah, ph = _num(row.get("activity_hours")), _num(row.get("prep_hours"))
        if ah is None or ph is None:
            err("C03", "activity_hours / prep_hours must be numbers or '[to confirm]'")
        elif ah == TO_CONFIRM:
            H.append({"change": i, "reason": "activity_hours [to confirm]"})
        elif ah <= 0:
            err("C03", "activity_hours must be > 0 (Salesforce rule); use '[to confirm]' if unknown")
        if isinstance(ah, float) and isinstance(ph, float) and not user_refs:
            delivery = [x for x in ev_items if "prep_title" not in x["flags"]]
            prep = [x for x in ev_items if "prep_title" in x["flags"]]
            base_a = prev["activity_hours"] if prev and isinstance(prev["activity_hours"], float) else 0.0
            base_p = prev["prep_hours"] if prev and isinstance(prev["prep_hours"], float) else 0.0
            cap_a = base_a + _union_hours(delivery)
            cap_total = base_a + base_p + _union_hours(ev_items)
            if ah > cap_a + TOLERANCE_H:
                err("C04", f"activity_hours {ah:g} exceeds delivery evidence {cap_a:g}h "
                           "(prep-titled meetings count only as prep). Cite a user: ref if the user confirmed more.")
            if ah + ph > cap_total + TOLERANCE_H:
                err("C04", f"activity+prep {ah + ph:g}h exceeds evidenced time {cap_total:g}h; "
                           "cite a user: ref for user-confirmed hours or use '[to confirm]'")
            if prev and ah + TOLERANCE_H < base_a:
                warn("C19", f"extended record's activity_hours decreased ({base_a:g} -> {ah:g})")

        # C05 account routing
        acct, kind = row.get("account_name"), row.get("account_kind")
        if acct == TO_CONFIRM or not acct:
            H.append({"change": i, "reason": "account [to confirm]"})
        else:
            if kind not in ("customer", "partner", "internal"):
                err("C05", "account_kind must be customer | partner | internal")
            if kind == "internal" and acct != R.internal_account:
                err("C05", f"internal activities go to '{R.internal_account}'")
            if acct == R.internal_account and kind != "internal":
                err("C05", f"'{R.internal_account}' must have account_kind internal")
            known = self.registry.kind_of(acct)
            canon = self.registry.canonical(acct)
            if known is None and canon:
                err("C05", f"account '{acct}': use the exact registry name '{canon}'")
            elif known is None:
                err("C05", f"account '{acct}' is not in the profile account registry; add it or use '[to confirm]'")
            elif kind and known != kind:
                err("C05", f"account '{acct}' is a {known} in the registry, not {kind}")
            if kind == "partner" and num in R.deal_types:
                err("C05", f"partner account with deal type {num}: partner deals are logged under the CUSTOMER")
            elif kind == "partner" and num not in R.partner_enablement_types:
                warn("C05", "partner account: confirm this is partner enablement (else log under the customer)")

        # C06 / C07 opportunity
        if not row.get("opportunity"):
            if not row.get("no_opp_reason"):
                err("C06", "no opportunity: 'no_opp_reason' is mandatory (or '[to confirm]')")
            elif row.get("no_opp_reason") == TO_CONFIRM:
                H.append({"change": i, "reason": "no-opportunity reason [to confirm]"})
            if num in R.opportunity_expected_types:
                warn("C07", f"type {num} should always link an opportunity")

        # C08 consolidation
        if num in R.consolidated_types:
            key = row.get("consolidation_key")
            if not key:
                err("C08", f"type {num} needs a consolidation_key (one record per Value Review/POC/RFP)")
            else:
                existing = [r for r in self.active if r["consolidation_key"] == key]
                if action == "new" and existing:
                    err("C08", f"record for '{key}' already exists ({existing[0]['entry_id']}); use action extend")
                if action == "new":
                    if key in keys_new:
                        err("C08", f"two new rows share consolidation_key '{key}' (change {keys_new[key]}); merge them")
                    keys_new[key] = i

        # C19 extend target
        if action == "extend":
            if not prev or prev["voided"]:
                err("C19", f"extend target {c.get('supersedes')} missing or already void")
            elif prev["consolidation_key"] and row.get("consolidation_key") != prev["consolidation_key"]:
                err("C19", "extend must keep the same consolidation_key")

        # C09 / C13 dates
        ad = row.get("activity_date")
        try:
            ad_d = date.fromisoformat(ad)
        except (TypeError, ValueError):
            err("C13", f"activity_date '{ad}' is not YYYY-MM-DD")
            ad_d = None
        ev_dates = {x["date"] for x in ev_items if x.get("date")}
        if prev and prev.get("activity_date"):
            ev_dates.add(prev["activity_date"])
        if ad_d and ev_dates and not user_refs:
            if num in R.consolidated_types:
                if ad != max(ev_dates):
                    err("C09", f"long-running record: activity_date must be the latest date ({max(ev_dates)})")
            elif ad not in ev_dates:
                err("C13", f"activity_date {ad} matches no cited evidence date {sorted(ev_dates)}")
        sd = row.get("start_date")
        if sd and ad and sd > ad:
            err("C09", "start_date is after activity_date")
        if num in R.dates_in_notes_types and len(DATE_IN_TEXT.findall(row.get("notes") or "")) < 2:
            err("C09", "Value Review notes must state the start and end dates")
        if ad_d and action == "new" and not (self.period[0] <= ad_d <= self.period[1]):
            warn("C17", f"activity_date {ad} is outside the run period")

        # C10 / C11 demos
        demo_ev = [x["id"] for x in ev_items if "demo_title" in x["flags"]]
        if demo_ev and num in R.demo_separate_types:
            if num == "20" or self.p.policy.get("demo_inside_poc_logs_separately", True):
                err("C10", f"demo evidence {demo_ev} inside a {num} record: log the demo separately as 07 · Product Demo")
        if demo_ev and num == "22":
            warn("C11", "environment prep for one demo counts as 07 · Product Demo, not 22")

        # C14 solution area
        sa = row.get("solution_area") or []
        if isinstance(sa, str):
            sa = [s.strip() for s in sa.split(";") if s.strip()]
        bad = [s for s in sa if s not in R.solution_areas]
        if bad:
            err("C14", f"solution_area {bad} not in {R.solution_areas}")
        if "Other" in sa and "other:" not in (row.get("notes") or "").lower():
            err("C14", "solution area 'Other' needs the detail in Notes as 'Other: ...'")

        # C15 notes
        if len((row.get("notes") or "").strip()) < 20:
            err("C15", "notes must describe what was done, in detail")

        # C18 confidence
        if row.get("confidence") not in CONFIDENCE:
            err("C18", f"confidence must be one of {CONFIDENCE}")

        return E, W, H
