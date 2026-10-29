"""Command-line entry point: hooks plus user/Claude-facing commands."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys

from . import formats, hooks, notes, render, setup, store


def _hook(event: str) -> int:
    root = None
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            return 0
        root = store.project_root(payload)
        out = hooks.handle(event, payload)
        if out:
            sys.stdout.write(json.dumps(out, ensure_ascii=False))
    except Exception as exc:  # hooks must never break Claude
        try:
            if root is not None and store.shelfie_dir(root).is_dir():
                store.log_error(root, exc)
        except Exception:
            pass
    return 0


def _csv(value: str | None) -> list:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _label(e: dict) -> str:
    return e.get("title") or e.get("url") or e.get("path") or (e.get("server") or {}).get("command") or "?"


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(prog="shelfie", description="Automatic artifact log for Claude Code.")
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hook")
    h.add_argument("event")
    n = sub.add_parser("note", help="record Claude's note on a pending item")
    n.add_argument("id")
    n.add_argument("--artifact", choices=["yes", "no"], required=True)
    n.add_argument("--title")
    n.add_argument("--desc")
    n.add_argument("--change")
    for name in ("ignore", "restore"):
        sub.add_parser(name).add_argument("id")
    s = sub.add_parser("setup")
    s.add_argument("--formats", default="all")
    s.add_argument("--allow-permission", choices=["yes", "no"], default="no")
    f = sub.add_parser("formats")
    f.add_argument("--enable")
    f.add_argument("--disable")
    ls = sub.add_parser("list")
    ls.add_argument("--ignored", action="store_true")
    sub.add_parser("render")
    sub.add_parser("open")
    a = p.parse_args(argv)

    if a.cmd == "hook":
        return _hook(a.event)

    root = store.project_root()
    try:
        if a.cmd == "setup":
            chosen = formats.ALL if a.formats.strip() == "all" else _csv(a.formats)
            setup.run_setup(root, chosen, a.allow_permission == "yes")
            print(f"Shelfie is set up. Tracking: {', '.join(chosen)}. "
                  f"Dashboard: {store.shelfie_dir(root) / 'shelfie.html'}")
            return 0
        if store.load_config(root) is None:
            print("Shelfie is not set up in this project yet. Run: shelfie setup", file=sys.stderr)
            return 1
        if a.cmd in ("note", "ignore", "restore"):
            with store.locked_registry(root) as reg:
                if a.cmd == "note":
                    e = notes.apply_note(reg, a.id, a.artifact == "yes", a.title, a.desc, a.change)
                else:
                    e = notes.set_status(reg, a.id, "ignored" if a.cmd == "ignore" else "artifact")
            render.render(root)
            print(f"{a.cmd}: {e['id']} → {e['status']} · {_label(e)}")
            return 0
        if a.cmd == "formats":
            on = store.load_config(root)["formats"]
            if a.enable or a.disable:
                on = setup.set_formats(root, _csv(a.enable), _csv(a.disable))
            for k, t in formats.TYPES.items():
                print(f"{'✓' if k in on else '·'} {k:9} {t['label']}")
            return 0
        if a.cmd == "list":
            for e in store.read_registry(root)["entries"]:
                if (e["status"] == "ignored") == a.ignored:
                    print(f"{e['id']}  {e['status']:8} {e['type']:9} {e['updated_at'][:16]}  {_label(e)}")
            return 0
        if a.cmd in ("render", "open"):
            out = render.render(root)
            if a.cmd == "open":
                opener = "open" if platform.system() == "Darwin" else "xdg-open"
                subprocess.run([opener, str(out)], check=False)
            print(out)
            return 0
    except KeyError as exc:
        print(f"No item with id {exc.args[0]}", file=sys.stderr)
        return 1
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
