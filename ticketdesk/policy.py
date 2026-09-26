"""The rules a human wrote. The model classifies, this file decides what is allowed.

Levels:  L1 = service desk can fix with a known runbook.
         L2 = needs a specialist, approval, or hands on hardware.
         L3 = many users, a site, or a core service. Incident.
"""
from __future__ import annotations

import os

# category -> (lowest allowed level, what it means). The model can raise a level, never lower it below this.
CATEGORIES: dict[str, tuple[str, str]] = {
    "password":        ("L1", "password reset, account locked, expired password"),
    "mfa":             ("L1", "authenticator app, MFA codes, new phone"),
    "vpn":             ("L1", "VPN (GlobalProtect) will not connect, setup on a new laptop"),
    "printer":         ("L1", "printing or scanning on an office printer"),
    "email":           ("L1", "Outlook, mailbox, calendar, shared mailbox problems"),
    "how_to":          ("L1", "how do I questions about Microsoft 365, Teams, Freshservice"),
    "access_request":  ("L2", "needs an approval: shared drive, app role, new hire, leaver"),
    "software":        ("L2", "install or licence request for an application"),
    "hardware":        ("L2", "laptop, monitor, dock, phone, replacement or repair"),
    "server":          ("L2", "one server, service, disk or job for one team"),
    "security":        ("L2", "phishing, malware, suspicious login, lost device"),
    "firewall_change": ("L2", "firewall rule change, goes through the change process"),
    "network":         ("L3", "an office, a site link, Wi-Fi for a whole floor"),
    "outage":          ("L3", "many users down, core service down"),
    "other":           ("L2", "anything that fits nothing above"),
}

# Only these can be answered with no human click. Everything else waits for a person or is escalated.
AUTO_OK = {"password", "mfa", "vpn", "printer", "email", "how_to"}

LEVEL_ORDER = {"L1": 1, "L2": 2, "L3": 3}

# Keyword rules with weights. Used by the fake model, and as a fallback when a real model answers badly.
# A phrase that can only mean one thing scores 3, a generic word scores 1. Highest total wins, ties go to the first listed.
KEYWORDS: dict[str, dict[str, int]] = {
    "outage":          {"for everyone": 3, "all users": 3, "whole office is affected": 3, "both offices": 3, "nobody can": 2,
                        "no one can": 2, "company wide": 3, "down for all": 3, "is down for": 2, "503": 1},
    "network":         {"wifi": 3, "wi-fi": 3, "no internet": 3, "internet is down": 3, "site link": 3, "whole floor": 3,
                        "floor": 1, "cannot reach": 2, "timeout": 2, "office cannot": 2, "everyone in": 2, "switch": 1},
    "security":        {"phishing": 3, "suspicious": 3, "gift card": 3, "malware": 3, "virus": 3, "clicked a link": 3,
                        "typed my password": 3, "stolen": 3, "lost my laptop": 3, "hacked": 3, "ransom": 3, "strange email": 2},
    "firewall_change": {"firewall": 3, "open port": 3, "inbound": 2, "allow traffic": 3, "traceroute": 3, "ping": 2, "acl": 3, "port ": 1},
    "server":          {"server": 2, "disk is full": 3, "disk full": 3, "disk space": 3, "backup job": 3, "nightly job": 3,
                        "service stopped": 3, "sql": 2, "database": 2, "rpt-": 2},
    "access_request":  {"access to": 3, "add me": 3, "shared drive": 2, "new hire": 3, "starts monday": 3, "permission": 2,
                        "remove access": 3, "leaver": 3, "needs laptop": 2},
    "software":        {"install": 2, "installed": 2, "licence": 3, "license": 3, "visio": 3, "adobe": 3, "acrobat": 3, "software": 1},
    "hardware":        {"will not turn on": 3, "won't turn on": 3, "no light": 3, "monitor": 2, "dock": 3, "docking": 3, "keyboard": 2,
                        "battery": 2, "screen": 1, "replacement": 2, "charger": 2, "laptop": 1},
    "mfa":             {"mfa": 3, "authenticator": 3, "2fa": 3, "verification code": 3, "new phone": 3, "codes": 1},
    "vpn":             {"vpn": 3, "globalprotect": 3, "global protect": 3, "gateway": 2, "remote access": 3, "from home": 2},
    "password":        {"password": 2, "locked out": 3, "locked": 2, "expired": 3, "log in": 1, "login": 1, "reset": 2},
    "printer":         {"printer": 3, "printing": 3, "print": 2, "scan": 2, "scanner": 3, "toner": 3},
    "email":           {"outlook": 3, "mailbox": 3, "inbox": 3, "not receiving": 3, "emails from": 2, "junk": 2, "email": 1},
    "how_to":          {"how do i": 3, "how to": 3, "where do i": 3, "is there a way": 3, "can you show me": 3},
}


def flag(key: str, default: str = "on") -> bool:
    return os.getenv(key, default).strip().lower() in {"on", "1", "true", "yes"}


def floor_level(category: str) -> str:
    return CATEGORIES.get(category, CATEGORIES["other"])[0]


def final_level(category: str, model_level: str) -> str:
    """The model may raise the level (a password ticket that is really a breach), never lower it."""
    floor = floor_level(category)
    model_level = str(model_level).strip().upper()
    model_level = model_level if model_level in LEVEL_ORDER else floor
    return model_level if LEVEL_ORDER[model_level] > LEVEL_ORDER[floor] else floor


def decide(triage: dict) -> str:
    """auto = reply with no click. escalate = hand to L2/L3 with a note, no click. review = a person decides."""
    level, category = triage["level"], triage["category"]
    conf = float(triage.get("confidence", 0))
    threshold = float(os.getenv("AUTO_MIN_CONFIDENCE", "0.8"))
    if triage.get("missing_info"):
        return "review"
    if level == "L1":
        if flag("AUTO_REPLY") and category in AUTO_OK and conf >= threshold:
            return "auto"
        return "review"
    if flag("AUTO_ESCALATE") and conf >= threshold:
        return "escalate"
    return "review"


def explain(triage: dict) -> str:
    """One line a judge can read: why this ticket went where it went."""
    level, cat, conf = triage["level"], triage["category"], float(triage.get("confidence", 0))
    threshold = float(os.getenv("AUTO_MIN_CONFIDENCE", "0.8"))
    if triage.get("missing_info"):
        return f"{level} {cat}, but the model needs info from the requester, so a person decides"
    if level == "L1":
        if not flag("AUTO_REPLY"):
            return f"{level} {cat}, auto reply is switched off, so a person decides"
        if cat not in AUTO_OK:
            return f"{level} {cat} is not on the auto reply list, so a person decides"
        if conf < threshold:
            return f"{level} {cat}, confidence {conf:.2f} is under {threshold:.2f}, so a person decides"
        return f"{level} {cat}, confidence {conf:.2f} over {threshold:.2f}, safe category, auto reply"
    if not flag("AUTO_ESCALATE"):
        return f"{level} {cat}, auto escalate is off, so a person decides"
    if conf < threshold:
        return f"{level} {cat}, confidence {conf:.2f} is under {threshold:.2f}, so a person decides"
    return f"{level} {cat}, confidence {conf:.2f}, escalated to {level} with a note and a suggested fix"


def guess_category(text: str) -> tuple[str, float]:
    """Keyword rules. Returns (category, confidence). Highest weighted score wins, ties go to the first listed (big problems first)."""
    t = text.lower()
    best, best_score, runner_up = "other", 0, 0
    for cat, words in KEYWORDS.items():
        score = sum(w_ for w, w_ in words.items() if w in t)
        if score > best_score:
            best, best_score, runner_up = cat, score, best_score
        elif score > runner_up:
            runner_up = score
    if best_score == 0:
        return "other", 0.4
    margin = best_score - runner_up
    return best, min(0.95, 0.6 + 0.1 * min(margin, 3) + 0.02 * min(best_score, 5))
