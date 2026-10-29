"""Project paths, config and registry storage."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import secrets
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def project_root(payload: dict | None = None) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    if payload and payload.get("cwd"):
        return Path(payload["cwd"])
    return Path.cwd()


def shelfie_dir(root: Path) -> Path:
    return Path(root) / ".shelfie"


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def load_config(root: Path) -> dict | None:
    return _read_json(shelfie_dir(root) / "config.json", None)


def save_config(root: Path, cfg: dict) -> None:
    _write_json(shelfie_dir(root) / "config.json", cfg)


def _empty_registry() -> dict:
    return {"version": 1, "entries": []}


def read_registry(root: Path) -> dict:
    return _read_json(shelfie_dir(root) / "registry.json", _empty_registry())


@contextlib.contextmanager
def locked_registry(root: Path):
    """Yield the registry under an exclusive lock; write it back on success."""
    d = shelfie_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            reg = read_registry(root)
            yield reg
            _write_json(d / "registry.json", reg)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def new_id() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log_error(root: Path, exc: BaseException) -> None:
    try:
        d = shelfie_dir(root)
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "errors.log", "a", encoding="utf-8") as f:
            f.write(f"--- {now_iso()}\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass
