"""Score triage on the sample tickets: python desk.py eval

Prints level accuracy, category accuracy, the mistakes, and seconds per ticket. Writes eval.json.
The number for the presentation: "levels right: N / 30 with <model>".
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

import models  # noqa: E402


def main() -> None:
    rows = json.loads((Path(__file__).with_name("data") / "sample_tickets.json").read_text(encoding="utf-8"))
    results, t0 = [], time.time()
    for t in rows:
        tri = models.triage(t)
        exp = t.get("expected", {})
        results.append({"id": t["id"], "subject": t["subject"], "expected": exp, "got": {"category": tri["category"], "level": tri["level"]},
                        "confidence": tri["confidence"], "model": tri.get("model", "")})
        mark = "ok " if tri["level"] == exp.get("level") else "XX "
        print(f"{mark}{t['id']}  {t['subject'][:44]:44}  {exp.get('level')} {exp.get('category'):16} -> {tri['level']} {tri['category']:16} {tri['confidence']:.2f}")
    n = len(rows)
    lvl = sum(r["got"]["level"] == r["expected"].get("level") for r in results)
    cat = sum(r["got"]["category"] == r["expected"].get("category") for r in results)
    # the two mistakes that matter most: an L2/L3 called L1 (would be auto answered), and an L1 pushed up (wasted specialist time)
    under = sum(r["expected"].get("level") in {"L2", "L3"} and r["got"]["level"] == "L1" for r in results)
    over = sum(r["expected"].get("level") == "L1" and r["got"]["level"] != "L1" for r in results)
    secs = (time.time() - t0) / max(n, 1)
    summary = {"model": models.model_for("triage"), "tickets": n, "levels_right": lvl, "categories_right": cat,
               "l2_l3_called_l1": under, "l1_pushed_up": over, "seconds_per_ticket": round(secs, 1)}
    print(f"\nlevels right: {lvl} / {n}   categories right: {cat} / {n}   L2/L3 called L1: {under}   L1 pushed up: {over}   {secs:.1f}s per ticket   model {summary['model']}")
    Path(__file__).with_name("eval.json").write_text(json.dumps({"summary": summary, "results": results}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
