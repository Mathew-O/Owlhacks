"""End to end with no model and no network: python -m tests.smoke

Covers: L1 auto reply, L2 escalation with note, L3 escalation, low confidence review with edit then send,
review then skip, rerun safety (a paused ticket is not restarted), reset.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp(prefix="ticketdesk_"))
shutil.copy(ROOT / "data" / "sample_tickets.json", tmp / "sample_tickets.json")
os.environ.update({"TICKETDESK_DATA": str(tmp), "TICKETDESK_DB": str(tmp / "test.db"), "MODEL": "fake:rules",
                   "MODEL_TRIAGE": "fake:rules", "MODEL_DRAFT": "fake:rules", "AUTO_REPLY": "on", "AUTO_ESCALATE": "on",
                   "AUTO_MIN_CONFIDENCE": "0.8"})

import runner  # noqa: E402

store = runner.system()
store.reset()


def ticket(i: str) -> dict:
    return store.get(i)


# 1. L1 password, confident -> auto reply
r = runner.process("INC-1001")
t = ticket("INC-1001")
assert r["status"] == "done" and r["outcome"] == "auto_replied", r
assert t["status"] == "auto_replied" and "password" in t["reply"].lower() and t["triage"]["level"] == "L1", t["status"]
assert t["hits"][0]["path"] == "password-reset.md"
print("1 ok  L1 auto reply:", t["triage"]["category"], t["triage"]["confidence"])

# 2. L2 laptop -> escalated with note
r = runner.process("INC-1019")
t = ticket("INC-1019")
assert r["outcome"] == "escalated_L2" and t["status"] == "escalated_L2" and "Suggested fix" in t["escalation_note"], t
assert "with a specialist now" in t["reply"]
print("2 ok  L2 escalation:", t["assigned"])

# 3. L3 outage -> escalated L3
r = runner.process("INC-1029")
t = ticket("INC-1029")
assert r["outcome"] == "escalated_L3" and t["triage"]["level"] == "L3", t["triage"]
print("3 ok  L3 escalation")

# 4. Low confidence -> review, edit, then send
os.environ["AUTO_MIN_CONFIDENCE"] = "0.99"
r = runner.process("INC-1008")
assert r["status"] == "waiting", r
assert ticket("INC-1008")["stage"] == "waiting"
assert runner.process("INC-1008")["status"] == "waiting", "rerun must not restart a paused ticket"
r = runner.resume("INC-1008", "edit", note="mention the 4th floor printer name")
assert r["status"] == "waiting", r
t = ticket("INC-1008")
assert "4th floor printer name" in t["draft"], t["draft"]
r = runner.resume("INC-1008", "send", text=t["draft"] + "\nEdited by a human.")
t = ticket("INC-1008")
assert r["outcome"] == "replied" and t["status"] == "replied" and t["reply"].endswith("Edited by a human."), t["status"]
print("4 ok  review, edit, send")

# 5. review then skip
r = runner.process("INC-1013")
assert r["status"] == "waiting"
r = runner.resume("INC-1013", "skip")
assert r["outcome"] == "skipped" and ticket("INC-1013")["outcome"] == "skipped" and ticket("INC-1013")["status"] == "skipped"
assert "INC-1013" not in {t["id"] for t in store.new_tickets()}, "a skipped ticket must not be picked up again"
print("5 ok  review, skip")

# 6. review then escalate by hand
r = runner.process("INC-1010")
r = runner.resume("INC-1010", "escalate", level="L2")
assert r["outcome"] == "escalated_L2" and ticket("INC-1010")["status"] == "escalated_L2"
print("6 ok  review, escalate")

# 7. AUTO_REPLY off -> L1 waits
os.environ["AUTO_MIN_CONFIDENCE"] = "0.8"
os.environ["AUTO_REPLY"] = "off"
assert runner.process("INC-1003")["status"] == "waiting"
print("7 ok  kill switch")

# 8. process_new leaves finished ones alone
os.environ["AUTO_REPLY"] = "on"
done = runner.process_new()
assert all(d["status"] in {"done", "waiting"} for d in done) and len(done) >= 20, len(done)
print(f"8 ok  process_new handled {len(done)} tickets")

# 9. add a live ticket like a judge would
t = store.add("Cannot print from the 4th floor", "Printer says offline for me only, New York 4th floor.", "judge@northline.com")
r = runner.process(t["id"])
assert r["outcome"] == "auto_replied", r
print("9 ok  live ticket auto replied:", t["id"])

# 10. odd model answers never crash triage
import models  # noqa: E402
assert models._json('Sure! {"a": {"b": 1}} and then {more}') == {"a": {"b": 1}}
assert models._json("```json\n{\"category\": \"vpn\"}\n```") == {"category": "vpn"}
assert models._json("no json here") is None
calls = []
models._invoke = lambda role, system, user: calls.append(role) or '{"category": ["vpn"], "level": 7}'
t = models.triage({"subject": "VPN broken", "body": "GlobalProtect fails", "requester": "a@b.c"})
assert t["category"] == "vpn" and t["level"] == "L1" and t["model"] == "fake:rules", t
models._invoke = lambda role, system, user: '{"category": "printer", "level": "l2", "urgency": "HIGH", "confidence": 85, "missing_info": "which printer?"}'
t = models.triage({"subject": "x", "body": "y", "requester": "a@b.c"})
assert t["level"] == "L2" and t["urgency"] == "high" and t["confidence"] == 0.85 and t["missing_info"] == ["which printer?"], t
print("10 ok odd model answers")

shutil.rmtree(tmp, ignore_errors=True)
print("\nall smoke tests passed")
