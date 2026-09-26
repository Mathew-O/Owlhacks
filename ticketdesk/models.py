"""The three model calls: triage, solve, draft. One door for any brain.

MODEL_TRIAGE and MODEL_DRAFT in .env pick the brain per job (MODEL sets both).
  anthropic:claude-sonnet-5     Claude through the API (ANTHROPIC_API_KEY)
  ollama:gemma3:4b              local, free, needs Ollama running
  fake:rules                    no model at all, keyword rules and runbook text; always works

Any failed call falls back to fake:rules and is written to CALLS, so a demo never dies.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import kb
import policy

CALLS: list[dict] = []          # last calls, shown in the dashboard
_llms: dict[str, Any] = {}


def model_for(role: str) -> str:
    return os.getenv(f"MODEL_{role.upper()}") or os.getenv("MODEL") or "fake:rules"


def _llm(model: str):
    if model not in _llms:
        from langchain.chat_models import init_chat_model
        provider = model.partition(":")[0]
        extra: dict[str, Any] = {}
        if provider == "anthropic" and os.getenv("ANTHROPIC_WORKSPACE_ID"):
            extra["default_headers"] = {"anthropic-workspace-id": os.getenv("ANTHROPIC_WORKSPACE_ID")}
        if provider == "ollama":
            extra["num_ctx"] = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
        _llms[model] = init_chat_model(model, temperature=0.2, **extra)
    return _llms[model]


def _invoke(role: str, system: str, user: str) -> str | None:
    """Text from the model for this role, or None when there is no model or it failed."""
    model = model_for(role)
    if model.startswith("fake"):
        CALLS.append({"role": role, "model": model, "seconds": 0, "ok": True})
        return None
    t0 = time.time()
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        out = _llm(model).invoke([SystemMessage(system), HumanMessage(user)]).content
        text = out if isinstance(out, str) else "".join(p.get("text", "") for p in out if isinstance(p, dict))
        CALLS.append({"role": role, "model": model, "seconds": round(time.time() - t0, 1), "ok": True})
        return text
    except Exception as e:  # noqa: BLE001  (no key, no credits, Ollama down, package missing)
        CALLS.append({"role": role, "model": model, "seconds": round(time.time() - t0, 1), "ok": False,
                      "error": f"{type(e).__name__}: {str(e)[:160]}"})
        print(f"[{role}] {model} failed ({type(e).__name__}), using fake rules for this step")
        return None


def _json(text: str) -> dict | None:
    """The first complete {...} object in the text. Models wrap JSON in prose or fences; prose after it may have braces."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def ticket_text(ticket: dict) -> str:
    return f"Subject: {ticket.get('subject', '')}\nFrom: {ticket.get('requester', '')}\n\n{ticket.get('body', '')}"


# ---------- 1. triage ----------
TRIAGE_SYSTEM = """You triage IT service desk tickets. Answer with JSON only, no prose.

Categories and their normal level:
{cats}

Levels: L1 = service desk fixes it with a known runbook. L2 = specialist, approval or hands on hardware.
L3 = many users, a whole office, or a core service. You may raise a level (a password ticket that is really a
breach is security L2), never lower it below the category's normal level.

Return:
{{"category": "<one of the categories>", "level": "L1|L2|L3", "urgency": "low|normal|high",
  "confidence": 0.0 to 1.0, "summary": "<one line, what is wrong>", "missing_info": ["<question to ask the requester, only if you truly cannot proceed>"]}}"""


def triage(ticket: dict) -> dict:
    cats = "\n".join(f"- {c}: {desc} (normal level {lvl})" for c, (lvl, desc) in policy.CATEGORIES.items())
    text = _invoke("triage", TRIAGE_SYSTEM.format(cats=cats), ticket_text(ticket))
    data = _json(text) if text else None
    if data and not isinstance(data.get("category"), str):
        data = None                                          # a list or a number where a name should be: use the rules
    used = model_for("triage") if data and data.get("category") in policy.CATEGORIES else "fake:rules"
    if not data or data.get("category") not in policy.CATEGORIES:
        cat, conf = policy.guess_category(ticket_text(ticket))
        data = {"category": cat, "level": policy.floor_level(cat), "urgency": "normal", "confidence": conf,
                "summary": ticket.get("subject", "")[:120], "missing_info": [],
                "note": "rules" if not text else "rules (model answer was not valid JSON)"}
    data["level"] = policy.final_level(data["category"], str(data.get("level", "")))
    urg = data.get("urgency")
    data["urgency"] = urg.lower() if isinstance(urg, str) and urg.lower() in {"low", "normal", "high"} else "normal"
    try:
        conf = float(data.get("confidence", 0.5))
        if conf != conf:                                     # NaN
            conf = 0.5
        if 1.0 < conf <= 100.0:                              # a percent
            conf = conf / 100.0
        data["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        data["confidence"] = 0.5
    mi = data.get("missing_info") or []
    mi = [mi] if isinstance(mi, str) else (mi if isinstance(mi, list) else [])
    data["missing_info"] = [str(q) for q in mi if str(q).strip()][:3]
    data["summary"] = str(data.get("summary") or ticket.get("subject", ""))[:200]
    data["model"] = used
    return data


# ---------- 2. solve ----------
SOLVE_SYSTEM = """You are a senior IT service desk engineer. Given a ticket and the matching runbooks,
write the fix as short numbered steps the desk can follow. Use only the runbooks given. If the runbooks do
not cover it, say what to check first and who should own it. End with one line: "Escalate if: ..."."""


def solve(ticket: dict, tri: dict, hits: list[dict]) -> str:
    runbooks = "\n\n".join(f"### {h['title']} ({h['path']})\n{h['text'][:2500]}" for h in hits) or "(no runbook matched)"
    user = f"{ticket_text(ticket)}\n\nTriage: {json.dumps({k: tri[k] for k in ('category', 'level', 'summary')})}\n\nRunbooks:\n{runbooks}"
    text = _invoke("draft", SOLVE_SYSTEM, user)
    if text:
        return text.strip()
    if hits:
        lines = kb.steps(hits[0])[:8] or ["Follow the runbook."]
        return (f"From runbook: {hits[0]['title']}\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(lines))
                + f"\n\nEscalate if: the steps above do not fix it, or it matches the escalate line in {hits[0]['path']}.")
    return ("No runbook matched.\n1. Ask the requester for a screenshot and when it started.\n"
            "2. Check if anyone else reports the same.\n3. Hand to the owning team with those answers.\n\nEscalate if: more than one user is affected.")


# ---------- 3. draft ----------
DRAFT_SYSTEM = """You write the reply an IT service desk tech sends to the requester. Voice: a real desk tech. Direct, plain, short.
Rules:
- No empathy filler. Never write "I understand", "I'm sorry to hear", "Thanks for reaching out", "I apologize", "don't worry", "I hope".
- First line after the greeting states the problem as a fact in under 10 words. Example: "Account locked after too many wrong passwords."
- Then "Do this:" and numbered steps, only steps the requester can do themselves (their laptop, the self service portal, their phone).
  Desk only steps (admin console, unlock, reset by staff, group changes) are stated as done, "Unlocked on our side.", or left out.
- One closing line: what to reply if it did not work. Sign "IT Service Desk".
- Under 120 words. No markdown headings, no bold, no exclamation marks, no em dashes."""


def draft(ticket: dict, tri: dict, solution: str, hits: list[dict], edit_note: str = "") -> str:
    first = str(ticket.get("requester", "there")).split("@")[0].split(".")[0].split(" ")[0].title() or "there"
    user = (f"{ticket_text(ticket)}\n\nSolution from the engineer:\n{solution}\n\n"
            + (f"The reviewer asked for this change, apply it: {edit_note}\n" if edit_note else ""))
    text = _invoke("draft", DRAFT_SYSTEM, user)
    if text:
        return text.strip()
    steps = [ln for ln in solution.splitlines() if re.match(r"^\s*\d+[.)]", ln)][:8]
    body = "\n".join(steps) if steps else "1. " + solution.splitlines()[0]
    extra = f"\n\n(Reviewer note applied: {edit_note})" if edit_note else ""
    return (f"Hi {first},\n\n{tri.get('summary', ticket.get('subject', ''))}.\n\n"
            f"Do this:\n{body}\n\nIf that does not fix it, reply here with what you see.{extra}\n\n"
            f"IT Service Desk")


# ---------- 4. escalation note ----------
def escalation_note(ticket: dict, tri: dict, solution: str, hits: list[dict], by: str = "ticketdesk") -> str:
    refs = ", ".join(h["path"] for h in hits) or "none"
    return (f"Escalated to {tri['level']} by {by}. Category: {tri['category']}. Urgency: {tri['urgency']}. "
            f"Confidence {tri['confidence']:.2f} ({tri.get('model', 'model')}).\n\nSummary: {tri['summary']}\n\n"
            f"Suggested fix:\n{solution}\n\nRunbooks: {refs}\n"
            + (f"Open questions for the requester: {'; '.join(tri['missing_info'])}\n" if tri.get("missing_info") else ""))


def ack_text(ticket: dict, tri: dict) -> str:
    first = str(ticket.get("requester", "there")).split("@")[0].split(".")[0].split(" ")[0].title() or "there"
    who = {"L2": "a specialist", "L3": "the incident team"}.get(tri["level"], "the right team")
    return (f"Hi {first},\n\n{tri['summary']}.\n"
            f"This is with {who} now, with the details attached. Updates come on this ticket.\n\nIT Service Desk")
