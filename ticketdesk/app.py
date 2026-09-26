"""The dashboard: what the human sees. FastAPI + one HTML file. python desk.py ui  (or run_ui.bat)

Every call returns fast; model work runs on one background worker so the page never freezes.
"""
from __future__ import annotations

import os
import queue
import threading
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import models
import policy
import runner

app = FastAPI(title="ticketdesk")
UI = Path(__file__).with_name("ui") / "index.html"
_jobs: "queue.Queue[tuple]" = queue.Queue()
_busy: dict = {"current": None, "errors": [], "gen": 0}


def _enqueue(fn, *args) -> None:
    _jobs.put((_busy["gen"], fn, args))


def _worker() -> None:
    while True:
        gen, fn, args = _jobs.get()
        if gen != _busy["gen"]:                 # queued before a reset: drop it
            _jobs.task_done()
            continue
        _busy["current"] = args[0] if args else fn.__name__
        try:
            fn(*args)
        except Exception as e:  # noqa: BLE001
            _busy["errors"].append(f"{args}: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            _busy["current"] = None
            _jobs.task_done()


threading.Thread(target=_worker, daemon=True).start()


class NewTicket(BaseModel):
    subject: str
    body: str
    requester: str = "someone@northline.com"


class Decision(BaseModel):
    action: str            # send | edit | escalate | skip
    text: str = ""
    note: str = ""
    level: str = ""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return UI.read_text(encoding="utf-8")


def _rank(t: dict) -> int:
    """Waiting for a person first, then in flight, then new, then finished."""
    if t.get("stage") == "waiting":
        return 3
    if t.get("status") == "new" and t.get("stage") not in {"new", "done"}:
        return 2
    return 1 if t.get("status") == "new" else 0


@app.get("/api/state")
def state() -> JSONResponse:
    store = runner.system()
    tickets = store.all() if hasattr(store, "all") else store.new_tickets()
    for t in tickets:
        t.pop("expected", None)                 # the answer key stays in the file, not on the screen
        if t.get("triage"):
            t["why"] = policy.explain(t["triage"])
    counts: dict[str, int] = {}
    for t in tickets:
        counts[t.get("status", "new")] = counts.get(t.get("status", "new"), 0) + 1
    return JSONResponse({
        "tickets": sorted(tickets, key=lambda t: (_rank(t), t.get("created", "")), reverse=True),
        "config": {"triage_model": models.model_for("triage"), "draft_model": models.model_for("draft"),
                   "auto_reply": policy.flag("AUTO_REPLY"), "auto_escalate": policy.flag("AUTO_ESCALATE"),
                   "threshold": float(os.getenv("AUTO_MIN_CONFIDENCE", "0.8")), "source": os.getenv("TICKET_SOURCE", "local"),
                   "auto_ok": sorted(policy.AUTO_OK)},
        "calls": models.CALLS[-12:], "busy": _busy["current"], "queued": _jobs.qsize(), "errors": _busy["errors"][-5:],
        "counts": counts,
    })


@app.post("/api/tickets")
def add_ticket(t: NewTicket) -> dict:
    store = runner.system()
    if not hasattr(store, "add"):
        raise HTTPException(400, "adding tickets is only for the local demo store")
    row = store.add(t.subject.strip(), t.body.strip(), t.requester.strip())
    _enqueue(runner.process, row["id"])
    return {"id": row["id"], "queued": True}


@app.post("/api/run")
def run_all() -> dict:
    ids = [t["id"] for t in runner.system().new_tickets()]
    for i in ids:
        _enqueue(runner.process, i)
    return {"queued": ids}


@app.post("/api/run/{ticket_id}")
def run_one(ticket_id: str) -> dict:
    try:
        runner.system().get(ticket_id)
    except KeyError:
        raise HTTPException(404, f"no ticket {ticket_id}")
    _enqueue(runner.process, ticket_id)
    return {"queued": [ticket_id]}


@app.post("/api/tickets/{ticket_id}/decision")
def decide(ticket_id: str, d: Decision) -> dict:
    if d.action not in {"send", "edit", "escalate", "skip"}:
        raise HTTPException(400, "action must be send, edit, escalate or skip")
    if not runner.paused(ticket_id):
        raise HTTPException(409, f"{ticket_id} is not waiting for a decision")
    _enqueue(runner.resume, ticket_id, d.action, d.text, d.note, d.level)
    return {"queued": [ticket_id], "action": d.action}


@app.post("/api/reset")
def reset() -> dict:
    _busy["gen"] += 1                           # anything still queued is dropped by the worker
    runner.reset()                              # waits for the running job: same lock as process()
    models.CALLS.clear()
    _busy["errors"].clear()
    return {"ok": True}


@app.get("/api/chart")
def chart() -> dict:
    import graph
    return {"mermaid": graph.mermaid()}
