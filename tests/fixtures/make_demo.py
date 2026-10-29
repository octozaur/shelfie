"""Build a demo project with a realistic registry (dates relative to now).

The demo is one fictional project — "Nimbus", a small team launching a weather API —
and everything Claude made for it over six months.

Usage: python3 tests/fixtures/make_demo.py <target-dir>   (name the dir "nimbus")
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shelfie import formats, render, store  # noqa: E402

NOW = datetime.now().astimezone().replace(second=0, microsecond=0)


def at(days, hour=10, minute=0):
    return (NOW - timedelta(days=days)).replace(hour=hour, minute=minute).isoformat()


def url(slug):
    return {"url": f"https://claude.ai/artifact/{slug}"}


# type, title, description, location, created (days, h, m), changes [(days, h, m, note)], status
ITEMS = [
    ("artifact", "Launch plan — public beta",
     "Week-by-week plan to public beta: owners, dates, risks and the go / no-go checklist.",
     dict(url("NimbusLaunch7"), path="plans/launch-plan.html", source_type="html"),
     (6, 11, 2), [(3, 16, 20, "Moved Product Hunt launch to week 3"),
                  (0, 14, 10, "Added the support rota and status-page owner")]),
    ("server", "Landing page prototype",
     "Interactive landing page with the live forecast widget, for the design review.",
     {"server": {"command": "npm run dev", "cwd": "web", "port": 5173, "name": "landing"}},
     (2, 9, 40), [(0, 11, 40, "New hero copy and the pricing teaser")]),
    ("sheet", "Pricing model",
     "Three tiers with unit economics per 1,000 API calls and break-even by month.",
     {"path": "finance/pricing-model.xlsx"}, (0, 9, 24), []),
    ("slides", "Seed round deck",
     "14 slides for investor meetings: problem, traction, market, team and the ask.",
     {"path": "pitch/seed-deck.pptx"}, (9, 12, 0),
     [(5, 18, 5, "Traction slide updated with October usage"), (1, 10, 15, "Tightened the ask to $1.2M")]),
    ("pdf", "API reference v1",
     "Print-ready reference for all 12 endpoints with request and response examples.",
     {"path": "docs/api-reference-v1.pdf"}, (3, 16, 40), [(2, 12, 0, "Added rate-limit headers")]),
    ("md", "Launch checklist",
     "Everything that must be true before beta: infra, docs, legal, support.",
     {"path": "plans/launch-checklist.md"}, (12, 15, 0), [(4, 11, 0, "Checked off legal review")]),
    ("artifact", "Competitor landscape",
     "Dashboard comparing six weather APIs on price, coverage, latency and free tier.",
     url("NimbusMarket2"), (24, 10, 15),
     [(19, 9, 0, "Added two European providers"), (13, 9, 30, "Latency benchmarks from the test run")]),
    ("image", "App icon set",
     "App and favicon icons in all store sizes, exported from the final logo.",
     {"path": "brand/icons/", "files": [f"brand/icons/icon-{s}.png" for s in
                                        (16, 32, 48, 64, 128, 180, 192, 256, 512, 1024)]},
     (31, 13, 0), []),
    ("doc", "Privacy policy draft",
     "Plain-language privacy policy covering location data and retention.",
     {"path": "legal/privacy-policy.docx"}, (38, 11, 0), [(33, 17, 0, "Lawyer's edits merged")]),
    ("html", "Status page mockup",
     "Public status page with uptime history and incident timeline.",
     {"path": "web/status.html"}, (45, 10, 0), [(41, 10, 0, "Added the incident subscription form")]),
    ("html", "Onboarding emails",
     "Eight-step onboarding sequence for new API keys, from welcome to upgrade nudge.",
     {"path": "emails/onboarding/", "files": [f"emails/onboarding/step-{i}.html" for i in range(1, 9)]},
     (58, 14, 0), [(52, 12, 0, "Shortened steps 3–5")]),
    ("md", "Customer interviews — synthesis",
     "Patterns from 11 developer interviews: what they pay for and what they'd switch for.",
     {"path": "research/interviews-synthesis.md"}, (80, 12, 0), []),
    ("pdf", "Partner one-pager",
     "One page for hardware partners: coverage map, SLA and integration effort.",
     {"path": "sales/partner-one-pager.pdf"}, (118, 10, 0), [(116, 10, 0, "New coverage map")]),
    ("artifact", "Product brief",
     "What Nimbus is, who it's for, and the three bets for the first year.",
     url("NimbusBrief01"), (150, 10, 0), []),
    ("md", "Scratch notes", None, {"path": "notes/scratch.md"}, (60, 9, 0), [], "ignored"),
]


def main(target):
    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    store.save_config(root, {"version": 1, "formats": list(formats.ALL), "exclude": []})
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
        for f in (e["files"] or ([e["path"]] if e["path"] else [])):
            p = root / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("demo")
    with store.locked_registry(root) as reg:
        reg["entries"] = entries
    print(render.render(root))


if __name__ == "__main__":
    main(sys.argv[1])
