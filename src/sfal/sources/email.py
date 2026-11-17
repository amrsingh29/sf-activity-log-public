"""Email source - macOS Mail.app via AppleScript automation (read-only).

Reads only the mailboxes the user lists. Messages are grouped into one evidence item per
thread per day. Noise (no-reply senders, auto-replies, mass mail) is dropped before the AI
sees anything. "Accepted:/Declined:/Tentative:" replies are kept as RSVP signals that
confirm calendar attendance; they are never activities themselves.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from ..evidence import item, make_id

US, RS = "\x1f", "\x1e"  # unit / record separators in the AppleScript output
PREVIEW_CHARS = 300
MASS_RECIPIENTS = 25
NOREPLY = re.compile(r"no-?reply|do-?not-?reply|notification|mailer-daemon|postmaster|alerts?@", re.I)
AUTO_REPLY = re.compile(r"^(automatic reply|auto(matic)?[- ]?reply|out of (the )?office|ooo\b|undeliverable|delivery status)", re.I)
RSVP = re.compile(r"^(accepted|declined|tentative|tentatively accepted|canceled|cancelled)\s*:\s*(.+)$", re.I)
INLINE_IMAGE = re.compile(r"^(image\d*|outlook-[\w-]+)\.(png|jpe?g|gif|bmp)$", re.I)
REPLY_PREFIX = re.compile(r"^\s*((re|fw|fwd|aw|wg|sv|antw)\s*(\[\d+\])?\s*:\s*)+", re.I)

APPLESCRIPT = r'''
on run argv
  set acctName to item 1 of argv
  set mbName to item 2 of argv
  set d0 to my isoToDate(item 3 of argv)
  set d1 to my isoToDate(item 4 of argv)
  set previewChars to (item 5 of argv) as integer
  set US to character id 31
  set RS to character id 30
  set out to ""
  tell application "Mail"
    set mb to mailbox mbName of account acctName
    set useSent to (mbName contains "Sent")
    if useSent then
      set msgs to (messages of mb whose date sent ≥ d0 and date sent < d1)
    else
      set msgs to (messages of mb whose date received ≥ d0 and date received < d1)
    end if
    set oldest to ""
    try
      set lastMsg to last message of mb
      set oldest to my dateToIso(date received of lastMsg)
    end try
    set out to "OLDEST" & US & oldest & RS
    repeat with m in msgs
      set toList to ""
      repeat with r in (to recipients of m)
        set toList to toList & (address of r) & ","
      end repeat
      set ccList to ""
      repeat with r in (cc recipients of m)
        set ccList to ccList & (address of r) & ","
      end repeat
      set attList to ""
      try
        repeat with a in (mail attachments of m)
          set attList to attList & (name of a) & "|"
        end repeat
      end try
      set pv to ""
      if previewChars > 0 then
        try
          set c to content of m
          if (length of c) > previewChars then set c to text 1 thru previewChars of c
          set pv to c
        end try
      end if
      if useSent then
        set dt to date sent of m
      else
        set dt to date received of m
      end if
      set out to out & (message id of m) & US & my dateToIso(dt) & US & (subject of m) & US & (sender of m) & US & toList & US & ccList & US & attList & US & pv & RS
    end repeat
  end tell
  return out
end run

on isoToDate(s)
  set d to current date
  set day of d to 1
  set year of d to (text 1 thru 4 of s) as integer
  set month of d to (text 6 thru 7 of s) as integer
  set day of d to (text 9 thru 10 of s) as integer
  set time of d to 0
  return d
end isoToDate

on dateToIso(d)
  set y to year of d as integer
  set mo to month of d as integer
  set dd to day of d as integer
  set t to time of d
  return (y as string) & "-" & my pad(mo) & "-" & my pad(dd) & "T" & my pad(t div 3600) & ":" & my pad((t mod 3600) div 60) & ":" & my pad(t mod 60)
end dateToIso

on pad(n)
  if n < 10 then return "0" & (n as string)
  return n as string
end pad
'''


class EmailError(Exception):
    pass


def fetch_mailbox(account: str, mailbox: str, d0: date, d1: date, preview: int = PREVIEW_CHARS) -> dict:
    end = d1 + timedelta(days=1)
    r = subprocess.run(["osascript", "-", account, mailbox, d0.isoformat(), end.isoformat(), str(preview)],
                       input=APPLESCRIPT, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        msg = r.stderr.strip()
        if "-1743" in msg or "not allowed" in msg.lower():
            msg = ("Mail automation not allowed. System Settings > Privacy & Security > Automation > "
                   "allow the app running this tool to control Mail.")
        elif "-1728" in msg or "Can’t get mailbox" in msg or "Can't get mailbox" in msg:
            msg = f"mailbox '{mailbox}' not found in Mail account '{account}'"
        raise EmailError(msg[-500:])
    return parse_output(r.stdout)


def parse_output(text: str) -> dict:
    oldest, messages = None, []
    for rec in text.rstrip("\n").split(RS):
        if not rec.strip():
            continue
        f = rec.split(US)
        if f[0] == "OLDEST":
            oldest = f[1] or None
            continue
        f += [""] * (8 - len(f))
        messages.append({
            "message_id": f[0], "date": f[1], "subject": f[2], "sender": f[3],
            "to": [a for a in f[4].split(",") if a], "cc": [a for a in f[5].split(",") if a],
            "attachments": [a for a in f[6].split("|") if a], "preview": f[7].strip(),
        })
    return {"oldest": oldest, "messages": messages}


def _addr(s: str) -> str:
    m = re.search(r"<([^>]+)>", s or "")
    return (m.group(1) if m else (s or "")).strip().lower()


def _domain(a: str) -> str:
    return a.rsplit("@", 1)[-1].lower() if "@" in a else ""


def thread_subject(subject: str) -> str:
    return re.sub(r"\s+", " ", REPLY_PREFIX.sub("", subject or "")).strip()


def normalize(per_mailbox: dict[str, dict], profile) -> list[dict]:
    """per_mailbox: {mailbox_name: parse_output(...)} -> evidence items."""
    import fnmatch
    ignore = [p.lower() for p in profile.source("email").get("ignore_subjects") or []]
    internal = set(profile.internal_domains)
    mine = profile.my_emails
    groups: dict[tuple, list] = defaultdict(list)
    items = []

    for mbox, data in per_mailbox.items():
        for m in data["messages"]:
            subj = m["subject"] or ""
            sender = _addr(m["sender"])
            recips = [_addr(a) for a in m["to"] + m["cc"]]
            day = m["date"][:10]
            rsvp = RSVP.match(subj.strip())
            excluded = None
            if NOREPLY.search(sender):
                excluded = "automated_sender"
            elif AUTO_REPLY.match(subj.strip()):
                excluded = "auto_reply"
            elif len(recips) > MASS_RECIPIENTS:
                excluded = "mass_mail"
            elif any(fnmatch.fnmatch(thread_subject(subj).lower(), p) for p in ignore):
                excluded = "ignored_subject"
            if rsvp:
                items.append(item(
                    id=make_id("mail", "rsvp", m["message_id"]), source="email", kind="rsvp",
                    date=day, title=subj, excluded="rsvp_signal",
                    rsvp=rsvp.group(1).lower(), rsvp_subject=thread_subject(rsvp.group(2)),
                    raw_ref=f"email/{mbox}#{m['message_id']}"))
                continue
            if excluded:
                items.append(item(id=make_id("mail", m["message_id"]), source="email", kind="email",
                                  date=day, title=subj, excluded=excluded,
                                  raw_ref=f"email/{mbox}#{m['message_id']}"))
                continue
            groups[(thread_subject(subj).lower(), day)].append((mbox, m, sender, recips))

    for (tkey, day), msgs in groups.items():
        msgs.sort(key=lambda t: t[1]["date"])
        people = sorted({a for _, m, s, r in msgs for a in [s] + r if a and a not in mine})
        domains = sorted({_domain(a) for a in people if _domain(a) and _domain(a) not in internal})
        sent_by_me = any(s in mine or "sent" in mb.lower() for mb, m, s, r in msgs)
        attachments = sorted({a for _, m, _, _ in msgs for a in m["attachments"] if not INLINE_IMAGE.match(a)})
        flags = []
        if sent_by_me:
            flags.append("sent_by_me")
        if attachments:
            flags.append("attachments")
        if people and not domains:
            flags.append("internal_only")
        first = msgs[0][1]
        items.append(item(
            id=make_id("mail", tkey, day), source="email", kind="email", date=day,
            start=None, end=None, hours=None,
            title=thread_subject(first["subject"]) or "(no subject)",
            people=[p.split("@")[0] for p in people][:12], domains=domains, flags=flags,
            message_count=len(msgs), attachments=attachments[:10],
            preview=(msgs[-1][1]["preview"] or "")[:PREVIEW_CHARS],
            mailboxes=sorted({mb for mb, *_ in msgs}),
            raw_ref=f"email#{'|'.join(m['message_id'] for _, m, _, _ in msgs)[:300]}"))
    return items


def collect(profile, rules, d0: date, d1: date, raw_dir: Path):
    cfg = profile.source("email")
    account = cfg.get("account") or "Exchange"
    per, warnings = {}, []
    for mb in cfg.get("mailboxes") or ["Sent Items"]:
        data = fetch_mailbox(account, mb, d0, d1)
        per[mb] = data
        if data["oldest"] and data["oldest"][:10] > d0.isoformat():
            warnings.append(f"mailbox '{mb}': oldest synced message is {data['oldest'][:10]}, "
                            f"after the period start {d0} - older mail may be missing from Mail.app")
    (raw_dir / "email.json").write_text(json.dumps(per, indent=1, ensure_ascii=False), encoding="utf-8")
    items = normalize(per, profile)
    threads = [x for x in items if x["kind"] == "email" and not x["excluded"]]
    report = {"source": "email", "method": "mailapp", "mailboxes": list(per),
              "messages": sum(len(v["messages"]) for v in per.values()),
              "threads_kept": len(threads),
              "rsvp_signals": sum(1 for x in items if x["kind"] == "rsvp"),
              "excluded": sum(1 for x in items if x["excluded"] and x["kind"] != "rsvp"),
              "completeness": "complete" if not warnings else "partial",
              "warnings": warnings}
    return items, report
