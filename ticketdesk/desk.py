"""ticketdesk command line.

  python desk.py ui          start the dashboard on http://localhost:8000 (opens the browser)
  python desk.py run         process every new ticket once, then exit (for a scheduled task or cron)
  python desk.py eval        score triage against the 30 sample tickets, prints accuracy
  python desk.py chart       draw the graph to chart.html and open it
  python desk.py reset       back to the sample tickets
"""
from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def ui() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    if not os.getenv("NO_BROWSER"):
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run("app:app", host="127.0.0.1", port=port, log_level="warning")


def run() -> None:
    import runner
    for r in runner.process_new():
        print(r)


def chart() -> None:
    import graph
    m = graph.mermaid()
    html = ("<!doctype html><html><head><meta charset='utf-8'><title>ticketdesk graph</title></head>"
            "<body style='font-family:sans-serif;margin:24px'><h2>ticketdesk graph</h2>"
            "<p>Solid arrow: always. Dashed arrow: gate and human_review decide.</p>"
            f"<pre class='mermaid'>\n{m}\n</pre>"
            "<script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';"
            "mermaid.initialize({startOnLoad:true});</script></body></html>")
    path = Path(__file__).with_name("chart.html")
    path.write_text(html, encoding="utf-8")
    print(m)
    print(f"\nwritten {path}")
    if not os.getenv("NO_BROWSER"):
        webbrowser.open(path.as_uri())


def reset() -> None:
    import runner
    runner.reset()
    print("reset to the sample tickets")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ui"
    if cmd == "eval":
        import eval as ev
        ev.main()
    else:
        {"ui": ui, "run": run, "chart": chart, "reset": reset}.get(cmd, ui)()
