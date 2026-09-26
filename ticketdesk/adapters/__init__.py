"""Ticket systems. One Protocol, two implementations. TICKET_SOURCE in .env picks one.

  local        data/tickets.json, the demo store the dashboard shows
  freshservice the real thing (FRESHSERVICE_DOMAIN, FRESHSERVICE_API_KEY)

Adding Zendesk, Jira or ServiceNow = one more file with these five methods.
"""
from __future__ import annotations

import os
from typing import Protocol


class TicketSystem(Protocol):
    def new_tickets(self) -> list[dict]: ...                                   # tickets nobody touched yet
    def get(self, ticket_id: str) -> dict: ...
    def reply(self, ticket_id: str, text: str, auto: bool = False) -> None: ... # public reply to the requester
    def escalate(self, ticket_id: str, level: str, note: str) -> None: ...     # assign to L2/L3 with a private note
    def set_stage(self, ticket_id: str, stage: str, **fields) -> None: ...     # progress + agent output, for the UI


def get_system() -> TicketSystem:
    source = os.getenv("TICKET_SOURCE", "local").strip().lower()
    if source == "freshservice":
        from adapters.freshservice import Freshservice
        return Freshservice()
    from adapters.local_store import LocalStore
    return LocalStore()
