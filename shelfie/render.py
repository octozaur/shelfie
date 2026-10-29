"""Render the static dashboard into .shelfie/shelfie.html."""
from __future__ import annotations

import html
import os
import re
import json
from pathlib import Path

from . import formats, store

_TEMPLATE = Path(__file__).with_name("dashboard.html")


_SAFE_URL = re.compile(r"^https://claude\.ai/[\w\-/]+$")


def _entry_view(root: Path, e: dict) -> dict:
    v = dict(e)
    # registry text is untrusted (it may be shared via git): only claude.ai links and integer ports
    if v.get("url") and not _SAFE_URL.match(str(v["url"])):
        v["url"] = None
    if v.get("server"):
        port = v["server"].get("port")
        v["server"] = dict(v["server"], port=port if isinstance(port, int) and not isinstance(port, bool) else None)
    if e.get("path"):
        abs_path = (root / e["path"]).resolve() if e["path"] != "./" else root.resolve()
        v["abs_path"] = str(abs_path)
        if e.get("files"):
            v["exists"] = any((root / f).exists() for f in e["files"])
        else:
            v["exists"] = abs_path.exists()
    else:
        v["abs_path"] = None
        v["exists"] = None
    return v


def build_data(root: Path) -> dict:
    cfg = store.load_config(root) or {"formats": formats.ALL}
    enabled = [t for t in formats.ALL if t in cfg.get("formats", formats.ALL)]
    reg = store.read_registry(root)
    entries = [_entry_view(root, e) for e in reg["entries"] if e["type"] in enabled]
    types = {k: {f: formats.TYPES[k][f] for f in ("label", "badge", "color")} for k in enabled}
    return {"project": Path(root).name, "generated_at": store.now_iso(),
            "types": types, "entries": entries}


def render(root: Path) -> Path:
    root = Path(root)
    data = json.dumps(build_data(root), ensure_ascii=False).replace("<", "\\u003c")
    page = _TEMPLATE.read_text("utf-8")
    page = page.replace("__SHELFIE_TITLE__", html.escape(f"Artifacts · {root.name}"), 1)
    page = page.replace("__SHELFIE_DATA__", data, 1)
    out = store.shelfie_dir(root) / "shelfie.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".shelfie.{os.getpid()}.tmp")
    tmp.write_text(page, "utf-8")
    tmp.replace(out)
    return out
