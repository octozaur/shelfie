"""Build a demo project with a realistic registry (dates relative to now).

Usage: python3 tests/fixtures/make_demo.py <target-dir>
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shelfie import render, store  # noqa: E402

NOW = datetime.now().astimezone().replace(second=0, microsecond=0)


def at(days, hour=10, minute=0):
    return (NOW - timedelta(days=days)).replace(hour=hour, minute=minute).isoformat()


ITEMS = [
    # type, title, desc, location, created(days,h,m), changes[(days,h,m,note)], extra
    ("artifact", "Northwind — onboarding agent brief",
     "Agent design for the client's onboarding flow, with open questions and the deployment choice.",
     {"url": "https://claude.ai/code/artifact/DemoBrief01", "path": "briefs/northwind-agent.html", "source_type": "html"},
     (0, 11, 2), [(0, 12, 35, "Reworded Q7–Q9 after the client call"),
                  (0, 14, 10, "Added the Fargate scheduled-task section and cost estimate")]),
    ("server", "Logo motion lab",
     "Interactive parameter lab for the animated logo; runs as a local dev server.",
     {"server": {"command": "npm run dev", "cwd": "logo-lab", "port": 5173, "name": "lab"}},
     (0, 9, 40), [(0, 11, 40, "Added growth stages slider")]),
    ("html", "Q4 capacity snapshot", "Bench and allocation table for the leadership sync, by team.",
     {"path": "reports/q4-capacity.html"}, (0, 9, 24), []),
    ("pdf", "Lisbon walking guide", "31 places plus food and logistics sections, print-ready.",
     {"path": "guides/lisbon-guide.pdf"}, (2, 16, 40),
     [(2, 18, 5, "Moved beaches into their own section"), (1, 10, 15, "Fixed map pins on page 4")]),
    ("slides", "Pitch deck — location privacy", "12-slide deck explaining the privacy concept for an RFP.",
     {"path": "pitch/privacy.pptx"}, (2, 12, 0), []),
    ("md", "Аналіз витрат H1", "Monthly deficit breakdown with travel as the main driver.",
     {"path": "finance/analiz-H1.md"}, (9, 15, 0), [(8, 11, 0, "Added June numbers")]),
    ("artifact", "Team challenge dashboard", "Strategy for first place and a weekly progress table for the team.",
     {"url": "https://claude.ai/artifact/DemoChallenge1"}, (16, 10, 15),
     [(12, 9, 0, "Week 2 results"), (5, 9, 30, "Week 3 results and new targets")]),
    ("image", "Brand mark — vector export", "CMYK-ready vector of the logo for DTF print.",
     {"path": "print/logo-cmyk.svg"}, (20, 13, 0), []),
    ("doc", "Fleet app product report", "Business-analysis write-up of the app's modules and gaps.",
     {"path": "fleet/product-report.docx"}, (30, 11, 0), [(27, 17, 0, "Added inventory module findings")]),
    ("sheet", "Tool subscriptions", "Seats, owners and monthly cost per team.",
     {"path": "ops/subscriptions.xlsx"}, (41, 10, 0), [(35, 10, 0, "Added October seats")]),
    ("html", "Puzzle game — level library", "74 standalone puzzle levels across three difficulty tiers.",
     {"path": "puzzle/levels/", "files": [f"puzzle/levels/level-{i:02}.html" for i in range(1, 75)]},
     (47, 14, 0), [(44, 12, 0, "Sealed 4 levels behind the finale")]),
    ("artifact", "Workshop playbook", "36 ideas, formats, rules and prizes for the offsite.",
     {"url": "https://claude.ai/artifact/DemoPlaybook"}, (78, 12, 0), []),
    ("pdf", "Porto walking guide", "38 places with a printable map.",
     {"path": "guides/porto-guide.pdf"}, (120, 10, 0), [(118, 10, 0, "Added museum opening hours")]),
    ("html", "Client context brief v1", "One-page dashboard of the client's regulatory context for the team.",
     {"path": "client-brief.html"}, (150, 10, 0), []),
    ("md", "Old meeting notes export", None, {"path": "notes/meeting.md"}, (60, 9, 0), [], "ignored"),
]


def main(target):
    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    store.save_config(root, {"version": 1, "formats": list(json.loads(json.dumps(
        ["artifact", "html", "pdf", "md", "doc", "slides", "sheet", "server", "image"]))), "exclude": []})
    entries = []
    for i, item in enumerate(ITEMS):
        etype, title, desc, loc, created, changes = item[:6]
        status = item[6] if len(item) > 6 else "artifact"
        c_at = at(*created)
        hist = [] if status == "ignored" else [{"at": c_at, "note": "Created"}]
        hist += [{"at": at(d, h, m), "note": n} for d, h, m, n in changes]
        e = {"id": f"demo{i:02}", "type": etype, "status": status, "title": title, "description": desc,
             "path": None, "source_type": None, "url": None, "server": None, "files": None,
             "created_at": c_at, "updated_at": hist[-1]["at"] if hist else c_at, "changes": hist,
             "pending": None, "noted_sessions": ["demo"]}
        e.update(loc)
        entries.append(e)
        for f in (e["files"] or ([e["path"]] if e["path"] and i != 12 else [])):
            p = root / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("demo")
    # one pending item, detected just now
    entries.append({"id": "demo99", "type": "html", "status": "pending", "title": None, "description": None,
                    "path": "drafts/pricing-table.html", "source_type": None, "url": None, "server": None,
                    "files": None, "created_at": at(0, NOW.hour, NOW.minute), "updated_at": at(0, NOW.hour, NOW.minute),
                    "changes": [], "pending": {"kind": "new", "session": "x", "at": at(0)}, "noted_sessions": []})
    (root / "drafts").mkdir(exist_ok=True)
    (root / "drafts" / "pricing-table.html").write_text("demo")
    with store.locked_registry(root) as reg:
        reg["entries"] = entries
    print(render.render(root))


if __name__ == "__main__":
    main(sys.argv[1])
