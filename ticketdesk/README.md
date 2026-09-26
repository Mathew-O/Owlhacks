# ticketdesk

A ticket comes in. The agent triages it, finds the runbook, writes the fix and the reply.
L1 and confident: it answers by itself. L2 or L3: it hands over to the right team with a note.
Not sure: a person clicks. Runs on your PC, on Claude or on a free local model, or both.

```
intake -> triage -> retrieve (runbooks) -> solve -> draft -> gate
   gate: auto reply (L1, safe, confident)  |  escalate L2/L3 with a note  |  human review (send, redraft, escalate, skip)
```

## Start
| Want | Windows | Mac |
|---|---|---|
| First time (installs, runs the tests) | `setup.bat` | `bash setup.sh` |
| Dashboard on http://localhost:8000 | `run_ui.bat` | `bash run_ui.sh` |
| Free local brain (about 4 GB) | `install_ollama.bat` | `brew install ollama && ollama pull gemma3:4b` |
| Score the triage on 30 tickets | `eval.bat` | `bash run_agent.sh eval` |
| Draw the graph | `chart.bat` | `bash run_agent.sh chart` |
| Back to the sample tickets | `reset_demo.bat` or the button | `bash run_agent.sh reset` |

Dashboard: press **Run agent on new tickets**, watch the queue sort itself, open one that says **needs a person**, click.
**+ New ticket** lets a judge type one; it is triaged on the spot.

## Brains (.env)
| Setting | Meaning |
|---|---|
| `MODEL_TRIAGE=ollama:gemma3:4b` | cheap local model reads and classifies |
| `MODEL_DRAFT=anthropic:claude-sonnet-5` | Claude writes the fix and the reply (needs `ANTHROPIC_API_KEY` + credits) |
| `MODEL=...` | sets both at once |
| `fake:rules` | no model at all: keyword rules and runbook text. The safety net. Any failed call falls back to it |

Both, all local, or all Claude: change two lines, restart `run_ui`.

## Policy (.env, no code)
| Setting | Default | Meaning |
|---|---|---|
| `AUTO_REPLY` | on | L1 + safe category + confidence over the gate = reply with no click. off = every reply waits |
| `AUTO_ESCALATE` | on | L2/L3 + confident = hand over with a note and no click |
| `AUTO_MIN_CONFIDENCE` | 0.8 | the gate |
| safe categories | password, mfa, vpn, printer, email, how_to | `policy.py`, `AUTO_OK` |

The model can raise a level (a password ticket that is really a breach), never lower it below the category floor in `policy.py`.

## What the human sees
- Queue: level chip (L1 green, L2 amber, L3 red), status (auto replied, replied, escalated, needs a person), stage bar while it works.
- Ticket: triage with confidence and a one line "why it went where it went", runbooks matched, engineer view of the fix, the draft.
- Needs a person: edit the text and send, or type a note and redraft, or escalate, or skip.
- History and the last model calls with seconds, so you can show Claude vs Ollama speed live.

## Files
| File | What |
|---|---|
| `desk.py` | the command line: `ui`, `run`, `eval`, `chart`, `reset` |
| `graph.py` | the LangGraph graph: State, 11 nodes, `gate` and `human_review` route with `Command`, `interrupt()` is the pause, SQLite memory per ticket |
| `models.py` | triage, solve, draft. One door for any brain, JSON parsing, fallback |
| `policy.py` | categories, level floors, safe list, the gate, the keyword rules |
| `kb.py` + `kb/*.md` | runbooks, BM25 search, the category's runbook always first |
| `adapters/` | `local_store.py` (demo JSON), `freshservice.py` (real API v2). Five methods, add Zendesk or ServiceNow the same way |
| `runner.py` | process one ticket, resume after a click, reset |
| `app.py` + `ui/index.html` | dashboard, one worker thread so the page never freezes |
| `eval.py` | levels right / 30, the number for the pitch |
| `data/sample_tickets.json` | 30 tickets with the level a human gave (14 L1, 12 L2, 4 L3) |
| `tests/smoke.py` | end to end with no model: auto, escalate, review, edit, skip, kill switch, odd model answers |
| `requirements.txt`, `.env.example`, `*.bat`, `*.sh` | install, config template, the buttons |

## Plug in a real ticket system
`TICKET_SOURCE=freshservice` plus domain, API key and the L2/L3 group ids in `.env`. Same graph, same dashboard.
Freshservice endpoints used are listed at the top of `adapters/freshservice.py`.

## Stop
Close the dashboard window. Nothing else runs. Ollama sits in the tray and unloads the model after 5 minutes.

## If something fails
- A chip in "Last model calls" says failed: read the error under it. Ollama not running, no key, no credits, wrong model name.
- The run still finishes: the failed step used `fake:rules`. That is on purpose.
- `python -m tests.smoke` proves the graph with no network at all.
