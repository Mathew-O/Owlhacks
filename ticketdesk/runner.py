"""Runs the graph for one ticket, and resumes it when a person answers. Used by the dashboard and the CLI."""
from __future__ import annotations

import os
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from langgraph.types import Command   # noqa: E402

import graph as g                      # noqa: E402
from adapters import get_system        # noqa: E402

_system = None
_graph = None
_lock = threading.Lock()


def system():
    global _system
    if _system is None:
        _system = get_system()
    return _system


def graph():
    global _graph
    if _graph is None:
        _graph = g.build_graph(system(), os.getenv("TICKETDESK_DB"))
    return _graph


def _cfg(ticket_id: str) -> dict:
    return {"configurable": {"thread_id": ticket_id}}


def paused(ticket_id: str) -> dict | None:
    """The interrupt payload if this ticket is waiting on a person, else None."""
    snap = graph().get_state(_cfg(ticket_id))
    if snap.next and snap.tasks and snap.tasks[0].interrupts:
        return snap.tasks[0].interrupts[0].value
    return None


def process(ticket_id: str) -> dict:
    """Run one ticket to its end or to the pause. Safe to call twice: a paused ticket is left alone."""
    with _lock:
        if paused(ticket_id):
            return {"status": "waiting", "id": ticket_id}
        t = system().get(ticket_id)
        out = graph().invoke({"ticket": t, "notes": [], "edit_note": "", "hits": []}, _cfg(ticket_id))
        if "__interrupt__" in out:
            return {"status": "waiting", "id": ticket_id}
        return {"status": "done", "id": ticket_id, "outcome": out.get("outcome", "")}


def resume(ticket_id: str, action: str, text: str = "", note: str = "", level: str = "") -> dict:
    """Answer the pause. action: send | edit | escalate | skip."""
    with _lock:
        if not paused(ticket_id):
            return {"status": "not_waiting", "id": ticket_id}
        out = graph().invoke(Command(resume={"action": action, "text": text, "note": note, "level": level}), _cfg(ticket_id))
        if "__interrupt__" in out:
            return {"status": "waiting", "id": ticket_id}
        return {"status": "done", "id": ticket_id, "outcome": out.get("outcome", "")}


def process_new() -> list[dict]:
    return [process(t["id"]) for t in system().new_tickets()]


def reset() -> None:
    """Back to the sample set, and forget every saved thread. Local store only."""
    with _lock:
        if hasattr(system(), "reset"):
            system().reset()
        conn = getattr(graph().checkpointer, "conn", None)
        if conn is not None:
            try:
                conn.execute("DELETE FROM checkpoints")
                conn.execute("DELETE FROM writes")
                conn.commit()
            except Exception:  # noqa: BLE001  (tables not created yet)
                pass
