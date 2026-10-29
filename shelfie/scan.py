"""Find artifact files changed during the current turn."""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import time
from collections import defaultdict
from pathlib import Path, PurePosixPath

from . import formats, store

EXCLUDED_DIRS = {".git", ".shelfie", ".claude", "node_modules", ".venv", "venv",
                 "__pycache__", ".superpowers", "dist", "build", ".next", ".dart_tool"}
MAX_FILES = 20000      # candidate files (right type, not excluded) checked per scan
MAX_WALK = 200000      # raw files visited when walking a non-git project
GROUP_THRESHOLD = 5


def _turn_file(root: Path, session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "default"
    return store.shelfie_dir(root) / "state" / f"turn-{safe}.json"


def mark_turn_start(root: Path, session_id: str, at: float | None = None) -> None:
    f = _turn_file(root, session_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"started_at": time.time() if at is None else at}))


def turn_start(root: Path, session_id: str) -> float | None:
    try:
        return json.loads(_turn_file(root, session_id).read_text())["started_at"]
    except (FileNotFoundError, ValueError, KeyError):
        return None


def clear_turn(root: Path, session_id: str) -> None:
    try:
        _turn_file(root, session_id).unlink()
    except FileNotFoundError:
        pass


def _git_files(root: Path) -> list | None:
    if not (root / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, capture_output=True, timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def _walk_files(root: Path) -> list:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        for name in filenames:
            found.append(name if rel_dir == "." else f"{rel_dir}/{name}".replace(os.sep, "/"))
            if len(found) >= MAX_WALK:
                return found
    return found


def changed_files(root: Path, since: float, formats_on: list, exclude: list) -> list:
    """Project-relative paths of enabled-type files with mtime >= since - 1s."""
    root = Path(root)
    candidates = _git_files(root)
    if candidates is None:
        candidates = _walk_files(root)
    wanted = []
    for rel in candidates:
        t = formats.type_for_path(rel)
        if t is None or t not in formats_on:
            continue
        if EXCLUDED_DIRS.intersection(PurePosixPath(rel).parts[:-1]):
            continue
        if any(fnmatch.fnmatch(rel, pat) for pat in exclude):
            continue
        wanted.append(rel)
    result = []
    for rel in wanted[:MAX_FILES]:
        try:
            if os.stat(root / rel).st_mtime >= since - 1.0:
                result.append(rel)
        except OSError:
            continue
    return sorted(result)


def group_new(paths: list, known: set) -> list:
    """Turn changed paths into candidates; collapse bursts of new same-type files per dir."""
    singles, buckets = [], defaultdict(list)
    for rel in paths:
        t = formats.type_for_path(rel)
        if rel in known:
            singles.append({"path": rel, "type": t, "files": None})
        else:
            parent = str(PurePosixPath(rel).parent)
            buckets[(parent, t)].append(rel)
    out = list(singles)
    for (parent, t), files in buckets.items():
        if len(files) >= GROUP_THRESHOLD:
            out.append({"path": ("./" if parent == "." else parent + "/"), "type": t,
                        "files": sorted(files)})
        else:
            out.extend({"path": f, "type": t, "files": None} for f in files)
    return out
