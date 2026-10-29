"""Claude's notes on pending items, ignore/restore, and the Stop-hook request."""
from __future__ import annotations

from . import store

MAX_LISTED = 10
CMD = ".shelfie/bin/shelfie"


def pending_entries(reg: dict) -> list:
    return [e for e in reg["entries"] if e.get("pending")]


def _get(reg: dict, entry_id: str) -> dict:
    for e in reg["entries"]:
        if e["id"] == entry_id:
            return e
    raise KeyError(entry_id)


def _location(e: dict) -> str:
    if e.get("server"):
        s = e["server"]
        return s.get("command") or (f"localhost:{s['port']}" if s.get("port") else "server")
    if e.get("files"):
        return f"{e['path']} ({len(e['files'])} files)"
    return e.get("url") or e.get("path") or "?"


def stop_reason(entries: list, cmd: str = CMD) -> str:
    lines = ["Shelfie: new or changed items need a note before you finish."]
    for e in entries[:MAX_LISTED]:
        kind = "NEW" if e["pending"]["kind"] == "new" else "CHANGED"
        lines.append(f"- {e['id']} · {kind} · {e['type']} · {_location(e)}"[:160])
    if len(entries) > MAX_LISTED:
        lines.append(f"- +{len(entries) - MAX_LISTED} more (they'll come up next time)")
    lines += [
        "",
        f'Record each item with one call: {cmd} note <id> --artifact yes|no '
        '[--title "…"] [--desc "…"] [--change "…"]',
        "NEW: from this conversation decide if it's a real deliverable (no for READMEs, specs, "
        "scratch notes, throwaway servers); if yes give a short English title and a 1–2 sentence "
        "description of what it is and who it's for.",
        "CHANGED: give one short --change line saying what changed. Then end your reply as you would have; no need to mention Shelfie.",
    ]
    return "\n".join(lines)


def apply_note(reg: dict, entry_id: str, artifact: bool, title, desc, change) -> dict:
    e = _get(reg, entry_id)
    pending = e.get("pending")
    if title:
        e["title"] = title
    if desc:
        e["description"] = desc
    if not artifact:
        e["status"] = "ignored"
    elif pending:
        e["status"] = "artifact"
    if pending and artifact:
        if pending["kind"] == "new":
            e["changes"].append({"at": pending["at"], "note": "Created"})
            if change:
                e["changes"].append({"at": pending["at"], "note": change})
        else:
            e["changes"].append({"at": pending["at"], "note": change or "Updated"})
    if pending:
        if pending["session"] not in e["noted_sessions"]:
            e["noted_sessions"].append(pending["session"])
        e["pending"] = None
    return e


def set_status(reg: dict, entry_id: str, status: str) -> dict:
    e = _get(reg, entry_id)
    if status == "ignored":
        e["status"] = "ignored"
        e["pending"] = None
    elif e.get("title"):
        e["status"] = "artifact"
    else:
        e["status"] = "pending"
        e["pending"] = {"kind": "new", "session": "restore", "at": store.now_iso()}
    return e
