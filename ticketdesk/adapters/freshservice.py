"""Freshservice, API v2. Same five methods as the local store.

.env:  TICKET_SOURCE=freshservice
       FRESHSERVICE_DOMAIN=yourcompany.freshservice.com
       FRESHSERVICE_API_KEY=...            (Profile settings > API key)
       FRESHSERVICE_L2_GROUP_ID=...        (Admin > Groups, the number in the URL)
       FRESHSERVICE_L3_GROUP_ID=...
       FRESHSERVICE_TAG=ticketdesk         (added to every ticket the agent touched)

Endpoints used (docs: api.freshservice.com):
  GET  /api/v2/tickets?filter=new_and_my_open&per_page=30
  GET  /api/v2/tickets/{id}
  POST /api/v2/tickets/{id}/reply      {"body": "<html>"}
  POST /api/v2/tickets/{id}/notes      {"body": "<html>", "private": true}
  PUT  /api/v2/tickets/{id}            {"group_id": ..., "priority": ..., "tags": [...]}  (tags are merged, not replaced)
"""
from __future__ import annotations

import html
import os

import requests

PRIORITY = {"low": 1, "normal": 2, "high": 3}


class Freshservice:
    def __init__(self) -> None:
        self.base = f"https://{os.environ['FRESHSERVICE_DOMAIN']}/api/v2"
        self.auth = (os.environ["FRESHSERVICE_API_KEY"], "X")
        self.tag = os.getenv("FRESHSERVICE_TAG", "ticketdesk")
        self.groups = {"L2": os.getenv("FRESHSERVICE_L2_GROUP_ID"), "L3": os.getenv("FRESHSERVICE_L3_GROUP_ID")}

    def _call(self, method: str, path: str, **kw) -> dict:
        r = requests.request(method, self.base + path, auth=self.auth, timeout=30, **kw)
        r.raise_for_status()
        return r.json() if r.text else {}

    @staticmethod
    def _shape(t: dict) -> dict:
        return {"id": str(t["id"]), "subject": t.get("subject", ""),
                "body": t.get("description_text") or t.get("description", ""),
                "requester": t.get("requester", {}).get("email") if isinstance(t.get("requester"), dict) else str(t.get("requester_id", "")),
                "created": t.get("created_at", ""), "status": "new" if t.get("status") == 2 else "open", "raw_status": t.get("status")}

    def new_tickets(self) -> list[dict]:
        rows = self._call("GET", "/tickets", params={"filter": "new_and_my_open", "per_page": 30, "include": "requester"}).get("tickets", [])
        return [self._shape(t) for t in rows if self.tag not in (t.get("tags") or [])]

    def get(self, ticket_id: str) -> dict:
        return self._shape(self._call("GET", f"/tickets/{ticket_id}", params={"include": "requester"}).get("ticket", {}))

    def _add_tags(self, ticket_id: str, new: list[str], **more) -> None:
        """Freshservice replaces the tag list on PUT, so read the current tags and merge."""
        current = self._call("GET", f"/tickets/{ticket_id}").get("ticket", {}).get("tags") or []
        self._call("PUT", f"/tickets/{ticket_id}", json={"tags": sorted(set(current) | set(new)), **more})

    def reply(self, ticket_id: str, text: str, auto: bool = False) -> None:
        body = "<br>".join(html.escape(ln) for ln in text.splitlines())
        self._call("POST", f"/tickets/{ticket_id}/reply", json={"body": body})
        self._add_tags(ticket_id, [self.tag, "auto" if auto else "reviewed"])

    def escalate(self, ticket_id: str, level: str, note: str) -> None:
        body = "<br>".join(html.escape(ln) for ln in note.splitlines())
        self._call("POST", f"/tickets/{ticket_id}/notes", json={"body": body, "private": True})
        more = {"group_id": int(self.groups[level])} if self.groups.get(level) else {}
        self._add_tags(ticket_id, [self.tag, level.lower()], **more)

    def set_stage(self, ticket_id: str, stage: str, **fields) -> None:
        tri = fields.get("triage")
        if tri and tri.get("urgency") in PRIORITY:      # the graph sends the triage once, right after the triage node
            self._call("PUT", f"/tickets/{ticket_id}", json={"priority": PRIORITY[tri["urgency"]]})
