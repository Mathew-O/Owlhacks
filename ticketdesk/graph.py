"""ticketdesk: the graph. One ticket in, one of three things out: auto reply, escalation, or a human decision.

  intake -> triage -> retrieve -> solve -> draft -> gate
  gate:   auto      -> auto_send -> log            (L1, safe category, confident, AUTO_REPLY=on)
          escalate  -> escalate  -> log            (L2/L3, confident, AUTO_ESCALATE=on)
          review    -> human_review (pause)        (everything else)
  human_review:  send | edit (back to draft) | escalate | skip

Every ticket is one thread. The pause is saved in ticketdesk.db, so the dashboard can answer it minutes later.
"""
from __future__ import annotations

import operator
import sqlite3
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

import kb
import models
import policy
from adapters import TicketSystem


class State(TypedDict):
    ticket: dict            # id, subject, body, requester
    triage: dict            # category, level, urgency, confidence, summary, missing_info, model
    hits: list[dict]        # matching runbooks
    solution: str           # engineer view: numbered steps
    draft: str              # requester view: the reply
    decision: str           # auto | escalate | review
    edit_note: str          # what the reviewer asked to change
    outcome: str            # auto_replied | replied | escalated_L2 | escalated_L3 | skipped
    notes: Annotated[list[str], operator.add]


def make_nodes(system: TicketSystem):
    """Nodes close over the ticket system so the graph itself has no idea which one it is."""

    def intake(state: State) -> dict:
        t = state["ticket"]
        system.set_stage(t["id"], "triage")
        return {"notes": [f"intake {t['id']}"]}

    def triage(state: State) -> dict:
        tri = models.triage(state["ticket"])
        system.set_stage(state["ticket"]["id"], "retrieve", triage=tri)
        return {"triage": tri, "notes": [f"triage {tri['category']} {tri['level']} {tri['confidence']:.2f}"]}

    def retrieve(state: State) -> dict:
        t, tri = state["ticket"], state["triage"]
        hits = kb.search(f"{t['subject']} {t['body']}", k=3, category=tri["category"])
        system.set_stage(t["id"], "solve", hits=[{"title": h["title"], "path": h["path"], "score": h["score"]} for h in hits])
        return {"hits": hits, "notes": [f"kb {[h['path'] for h in hits]}"]}

    def solve(state: State) -> dict:
        sol = models.solve(state["ticket"], state["triage"], state["hits"])
        system.set_stage(state["ticket"]["id"], "draft", solution=sol)
        return {"solution": sol}

    def draft(state: State) -> dict:
        text = models.draft(state["ticket"], state["triage"], state["solution"], state["hits"], state.get("edit_note", ""))
        system.set_stage(state["ticket"]["id"], "gate", draft=text)
        return {"draft": text}

    def gate(state: State) -> Command[Literal["auto_send", "escalate", "human_review"]]:
        d = policy.decide(state["triage"]) if not state.get("edit_note") else "review"   # an edited draft always goes back to the person
        system.set_stage(state["ticket"]["id"], {"auto": "auto_send", "escalate": "escalate", "review": "waiting"}[d], decision=d)
        return Command(goto={"auto": "auto_send", "escalate": "escalate", "review": "human_review"}[d], update={"decision": d})

    def human_review(state: State) -> Command[Literal["send", "draft", "escalate", "log"]]:
        answer = interrupt({"ticket": state["ticket"], "triage": state["triage"], "solution": state["solution"], "draft": state["draft"]})
        action = answer.get("action", "skip")
        if action == "send":
            return Command(goto="send", update={"draft": answer.get("text") or state["draft"], "notes": ["human: send"]})
        if action == "edit":
            return Command(goto="draft", update={"edit_note": answer.get("note", ""), "notes": [f"human: edit {answer.get('note', '')}"]})
        if action == "escalate":
            tri = {**state["triage"], "level": answer.get("level") or ("L2" if state["triage"]["level"] == "L1" else state["triage"]["level"])}
            return Command(goto="escalate", update={"triage": tri, "notes": ["human: escalate"]})
        return Command(goto="log", update={"outcome": "skipped", "notes": ["human: skip"]})

    def auto_send(state: State) -> dict:
        system.reply(state["ticket"]["id"], state["draft"] + "\n\n[sent automatically, L1 runbook answer]", auto=True)
        return {"outcome": "auto_replied"}

    def send(state: State) -> dict:
        system.reply(state["ticket"]["id"], state["draft"], auto=False)
        return {"outcome": "replied"}

    def escalate(state: State) -> dict:
        t, tri = state["ticket"], state["triage"]
        level = tri["level"] if tri["level"] in {"L2", "L3"} else "L2"
        by = "a reviewer via ticketdesk" if any(n.startswith("human: escalate") for n in state["notes"]) else "ticketdesk"
        system.reply(t["id"], models.ack_text(t, {**tri, "level": level}), auto=True)
        system.escalate(t["id"], level, models.escalation_note(t, {**tri, "level": level}, state["solution"], state["hits"], by=by))
        return {"outcome": f"escalated_{level}"}

    def log(state: State) -> dict:
        extra = {"status": "skipped"} if state.get("outcome") == "skipped" else {}
        system.set_stage(state["ticket"]["id"], "done", outcome=state.get("outcome", ""), agent_notes=state["notes"], **extra)
        return {}

    return {"intake": intake, "triage": triage, "retrieve": retrieve, "solve": solve, "draft": draft, "gate": gate,
            "human_review": human_review, "auto_send": auto_send, "send": send, "escalate": escalate, "log": log}


def builder(system: TicketSystem) -> StateGraph:
    b = StateGraph(State)
    for name, fn in make_nodes(system).items():
        b.add_node(name, fn)
    b.add_edge(START, "intake")
    b.add_edge("intake", "triage")
    b.add_edge("triage", "retrieve")
    b.add_edge("retrieve", "solve")
    b.add_edge("solve", "draft")
    b.add_edge("draft", "gate")
    # gate and human_review route themselves with Command(goto=...)
    b.add_edge("auto_send", "log")
    b.add_edge("send", "log")
    b.add_edge("escalate", "log")
    b.add_edge("log", END)
    return b


def build_graph(system: TicketSystem, db: str | Path | None = None):
    path = Path(db) if db else Path(__file__).with_name("ticketdesk.db")
    conn = sqlite3.connect(path, check_same_thread=False)
    return builder(system).compile(checkpointer=SqliteSaver(conn))


def make_graph():
    """For LangGraph Studio (langgraph dev), which brings its own memory."""
    from adapters import get_system
    return builder(get_system()).compile()


def mermaid() -> str:
    from adapters.local_store import LocalStore
    return builder(LocalStore()).compile().get_graph().draw_mermaid()
