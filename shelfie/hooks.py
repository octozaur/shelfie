"""Hook event handlers. Each returns a dict to print as JSON, or None."""
from __future__ import annotations

import os
import time
from pathlib import Path

from . import ingest, notes, render, scan, servers, setup, store


def _rel(root: Path, path: str, cwd: str | None) -> str | None:
    """Project-relative POSIX path, or None when outside the project."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(cwd or root) / p
    try:
        return Path(os.path.normpath(p)).relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        try:
            return Path(os.path.normpath(p)).relative_to(Path(root)).as_posix()
        except ValueError:
            return None


def session_start(root: Path, payload: dict, cfg: dict | None):
    if cfg is None:
        return {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                       "additionalContext": setup.setup_context()}}
    setup.refresh_launcher(root)
    return None


def prompt_submit(root: Path, payload: dict, cfg: dict):
    session = payload.get("session_id") or "default"
    # an existing turn file means the previous turn never reached Stop (interrupted): keep its start
    if scan.turn_start(root, session) is None:
        scan.mark_turn_start(root, session)
    return None


def _servers_from_tool(root: Path, payload: dict) -> list:
    name, ti = payload.get("tool_name"), payload.get("tool_input") or {}
    cwd = payload.get("cwd")
    if name == "Bash" and ti.get("command"):
        cwd_rel = _rel(root, cwd, None) if cwd else "."
        s = servers.detect_bash(ti["command"], cwd_rel if cwd_rel not in (None, "") else ".")
        return [s] if s else []
    if name in ("Write", "Edit", "MultiEdit") and ti.get("file_path"):
        if _rel(root, ti["file_path"], cwd) == ".claude/launch.json":
            return servers.from_launch_json(root)
        return []
    if name == "mcp__Claude_Browser__preview_start":
        s = servers.from_preview_start(ti, root)
        return [s] if s else []
    return []


def post_tool(root: Path, payload: dict, cfg: dict):
    on, session = cfg["formats"], payload.get("session_id") or "default"
    ti = payload.get("tool_input") or {}
    changed = False
    if payload.get("tool_name") == "Artifact":
        if "artifact" in on:
            url, src, title = servers.publish_info(ti, payload.get("tool_response"))
            if url:
                src_rel = _rel(root, src, payload.get("cwd")) if src else None
                with store.locked_registry(root) as reg:
                    ingest.record_published(reg, url, src_rel, title, session)
                changed = True
    elif "server" in on:
        found = _servers_from_tool(root, payload)
        if found:
            with store.locked_registry(root) as reg:
                for s in found:
                    ingest.record_server(reg, s, session)
            changed = True
    if changed:
        render.render(root)
    return None


def stop(root: Path, payload: dict, cfg: dict):
    session = payload.get("session_id") or "default"
    since = scan.turn_start(root, session)
    with store.locked_registry(root) as reg:
        if since is not None:
            paths = scan.changed_files(root, since, cfg["formats"], cfg.get("exclude", []))
            known = {p for p in paths if ingest.find_entry(reg, path=p)}
            for cand in scan.group_new(paths, known):
                ingest.record_file(reg, cand, session)
        pending = notes.pending_entries(reg)
    render.render(root)
    if pending and not payload.get("stop_hook_active"):
        # the forced continuation is still part of this turn: keep scanning from now
        scan.mark_turn_start(root, session, time.time())
        return {"decision": "block", "reason": notes.stop_reason(pending, setup.launcher_command(root))}
    scan.clear_turn(root, session)
    return None


HANDLERS = {"session_start": session_start, "prompt_submit": prompt_submit,
            "post_tool": post_tool, "stop": stop}


def handle(event: str, payload: dict):
    root = store.project_root(payload)
    cfg = store.load_config(root)
    fn = HANDLERS.get(event)
    if fn is None or (cfg is None and event != "session_start"):
        return None
    return fn(root, payload, cfg)
