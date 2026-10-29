"""Turn capture candidates into registry entries."""
from __future__ import annotations

from pathlib import PurePosixPath

from . import formats, store


def _in_group(entry: dict, path: str) -> bool:
    files = entry.get("files")
    if not files:
        return False
    if path in files:
        return True
    gpath = entry["path"]
    if gpath == "./":
        return False
    parent = str(PurePosixPath(path).parent) + "/"
    return parent == gpath and formats.type_for_path(path) == _type_of_group(entry)


def _type_of_group(entry: dict) -> str:
    return entry.get("source_type") or entry["type"]


def find_entry(reg: dict, *, path: str | None = None, url: str | None = None,
               server_key: tuple | None = None) -> dict | None:
    for e in reg["entries"]:
        if url is not None and e.get("url") == url:
            return e
        if path is not None and (e.get("path") == path or _in_group(e, path)):
            return e
        if server_key is not None and e.get("server") and \
                (e["server"].get("cwd"), e["server"].get("command")) == server_key:
            return e
    return None


def _new_entry(reg: dict, etype: str, session: str, **fields) -> dict:
    now = store.now_iso()
    e = {"id": store.new_id(), "type": etype, "status": "pending",
         "title": None, "description": None,
         "path": None, "source_type": None, "url": None, "server": None, "files": None,
         "created_at": now, "updated_at": now, "changes": [],
         "pending": {"kind": "new", "session": session, "at": now},
         "noted_sessions": []}
    e.update(fields)
    reg["entries"].append(e)
    return e


def _touch(e: dict, session: str) -> dict:
    now = store.now_iso()
    e["updated_at"] = now
    if e["status"] == "ignored" or session in e.get("noted_sessions", []):
        return e
    if e.get("pending") and e["pending"]["kind"] == "new":
        return e
    e["pending"] = {"kind": "changed", "session": session, "at": now}
    return e


def record_file(reg: dict, cand: dict, session: str) -> dict:
    e = find_entry(reg, path=cand["path"])
    if e is None:
        return _new_entry(reg, cand["type"], session, path=cand["path"], files=cand.get("files"))
    if e.get("files") is not None:
        for f in cand.get("files") or [cand["path"]]:
            if f != e["path"] and f not in e["files"]:
                e["files"].append(f)
    return _touch(e, session)


def record_published(reg: dict, url: str, source_path: str | None, title: str | None,
                     session: str) -> dict:
    e = find_entry(reg, url=url)
    if e is None and source_path:
        e = find_entry(reg, path=source_path)
    if e is None:
        return _new_entry(reg, "artifact", session, url=url, path=source_path,
                          title=title if title else None)
    if e["type"] != "artifact":
        e["source_type"] = e["type"]
        e["type"] = "artifact"
    e["url"] = url
    if source_path and not e.get("path"):
        e["path"] = source_path
    return _touch(e, session)


def record_server(reg: dict, server: dict, session: str) -> dict:
    key = (server.get("cwd"), server.get("command"))
    e = find_entry(reg, server_key=key)
    if e is None:
        return _new_entry(reg, "server", session, server=dict(server))
    if server.get("port") is not None:
        e["server"]["port"] = server["port"]
    return _touch(e, session)
