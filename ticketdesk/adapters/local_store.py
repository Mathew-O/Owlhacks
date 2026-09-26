"""The demo ticket system: a JSON file. Same five methods as the real one.

data/tickets.json is the live queue. data/sample_tickets.json is the reset point.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import threading
from pathlib import Path

DATA_DIR = Path(os.getenv("TICKETDESK_DATA", Path(__file__).resolve().parent.parent / "data"))
LIVE = DATA_DIR / "tickets.json"
SAMPLE = DATA_DIR / "sample_tickets.json"
_lock = threading.RLock()


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


class LocalStore:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not LIVE.exists():
            self.reset()

    # ----- file -----
    def _read(self) -> list[dict]:
        with _lock:
            return json.loads(LIVE.read_text(encoding="utf-8")) if LIVE.exists() else []

    def _write(self, rows: list[dict]) -> None:
        with _lock:
            tmp = LIVE.with_suffix(".tmp")
            tmp.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
            tmp.replace(LIVE)

    def reset(self) -> None:
        with _lock:
            if SAMPLE.exists():
                shutil.copy(SAMPLE, LIVE)
            else:
                self._write([])

    # ----- Protocol -----
    def all(self) -> list[dict]:
        return self._read()

    def new_tickets(self) -> list[dict]:
        return [t for t in self._read() if t.get("status") == "new"]

    def get(self, ticket_id: str) -> dict:
        for t in self._read():
            if t["id"] == ticket_id:
                return t
        raise KeyError(ticket_id)

    def add(self, subject: str, body: str, requester: str) -> dict:
        with _lock:
            rows = self._read()
            n = max((int(t["id"].split("-")[-1]) for t in rows if t["id"].split("-")[-1].isdigit()), default=1000) + 1
            t = {"id": f"INC-{n}", "subject": subject, "body": body, "requester": requester, "created": now(),
                 "status": "new", "stage": "new", "history": [{"at": now(), "event": "created"}]}
            rows.append(t)
            self._write(rows)
            return t

    def reply(self, ticket_id: str, text: str, auto: bool = False) -> None:
        self._update(ticket_id, status="auto_replied" if auto else "replied", stage="done",
                     event=("auto reply sent" if auto else "reply sent"), reply=text)

    def escalate(self, ticket_id: str, level: str, note: str) -> None:
        self._update(ticket_id, status=f"escalated_{level}", stage="done", assigned=f"{level} queue",
                     event=f"escalated to {level}", escalation_note=note)

    def set_stage(self, ticket_id: str, stage: str, **fields) -> None:
        self._update(ticket_id, stage=stage, event=f"stage: {stage}", **fields)

    def _update(self, ticket_id: str, event: str = "", **fields) -> None:
        with _lock:
            rows = self._read()
            for t in rows:
                if t["id"] == ticket_id:
                    t.update(fields)
                    if event:
                        t.setdefault("history", []).append({"at": now(), "event": event})
                    break
            self._write(rows)
