"""Detect local servers and claude.ai publishes from tool calls."""
from __future__ import annotations

import json
import re
from pathlib import Path

_SERVER_PATTERNS = [
    r"(npm|pnpm|yarn|bun)( run)? (dev|start|serve|preview)\b",
    r"(npx |pnpm exec |pnpm dlx |yarn dlx |bunx )?(vite|astro dev|nuxt dev|remix dev|"
    r"next (dev|start)|webpack serve|webpack-dev-server|http-server|live-server|serve)\b",
    r"python3? -m http\.server\b",
    r"flutter run\b.*-d web-server\b",
    r"(uvicorn|gunicorn|streamlit run|flask run|rails s(erver)?|php -S|hugo server|"
    r"jekyll serve|mkdocs serve|deno task dev)\b",
    r"node \S*(server|serve|app|index)\S*\.(c|m)?js\b",
]
_SERVER_RE = re.compile(r"^(?:%s)" % "|".join(_SERVER_PATTERNS))
_ENV_RE = re.compile(r"^(?:[A-Z_][A-Z0-9_]*=\S*\s+)+")
_PORT_RES = [
    re.compile(r"--(?:web-)?port[= ](\d{2,5})\b"),
    re.compile(r"(?:^|\s)-p (\d{2,5})\b"),
    re.compile(r"\bPORT=(\d{2,5})\b"),
    re.compile(r"http\.server (\d{2,5})\b"),
    re.compile(r"php -S [\w.]*:(\d{2,5})\b"),
]
_CLAUDE_URL_RE = re.compile(r"https://claude\.ai/(?:code/)?artifact/[\w-]+")
_LOCAL_URL_RE = re.compile(r"^https?://(?:localhost|127\.0\.0\.1|\[::1\]|[\w.-]+\.localhost)(?::(\d+))?")


def _port(command: str) -> int | None:
    for rx in _PORT_RES:
        m = rx.search(command)
        if m:
            return int(m.group(1))
    return None


def detect_bash(command: str, cwd_rel: str) -> dict | None:
    """A dev-server start in a Bash command → {"command", "cwd", "port"}, else None."""
    for segment in re.split(r"&&|\|\||;|\|", command):
        seg = segment.strip()
        env = _ENV_RE.match(seg)
        has_port_env = bool(env and "PORT=" in env.group(0))
        body = seg[env.end():] if env else seg
        if _SERVER_RE.match(body) or (has_port_env and re.match(r"(node|python3?|deno|bun) ", body)):
            return {"command": command.strip(), "cwd": cwd_rel, "port": _port(command)}
    return None


def _launch_configs(root: Path) -> list:
    try:
        data = json.loads((Path(root) / ".claude" / "launch.json").read_text("utf-8"))
        return [c for c in data.get("configurations", []) if isinstance(c, dict)]
    except (OSError, ValueError, AttributeError):
        return []


def _config_to_server(c: dict) -> dict:
    parts = [c.get("runtimeExecutable") or ""] + [str(a) for a in c.get("runtimeArgs") or []]
    port = c.get("port")
    return {"command": " ".join(p for p in parts if p) or None, "cwd": c.get("cwd") or ".",
            "port": port if isinstance(port, int) else None, "name": c.get("name")}


def from_launch_json(root: Path) -> list:
    return [_config_to_server(c) for c in _launch_configs(root)]


def from_preview_start(tool_input: dict, root: Path) -> dict | None:
    name = tool_input.get("name")
    if name:
        for c in _launch_configs(root):
            if c.get("name") == name:
                return _config_to_server(c)
        return None
    m = _LOCAL_URL_RE.match(tool_input.get("url") or "")
    if m:
        return {"command": None, "cwd": ".", "port": int(m.group(1)) if m.group(1) else None}
    return None


def publish_info(tool_input: dict, tool_response) -> tuple:
    """(url, source_path, title) of a claude.ai page publish; all None otherwise."""
    none = (None, None, None)
    if tool_input.get("action", "publish") != "publish" or tool_input.get("asset"):
        return none
    type_url = tool_input.get("type_url")
    if not tool_input.get("file_path") and not type_url:
        return none
    m = _CLAUDE_URL_RE.search(tool_input.get("url") or "")
    if not m:
        if type_url:
            tool_response = (tool_response if isinstance(tool_response, str)
                             else json.dumps(tool_response)).replace(type_url, "")
        text = tool_response if isinstance(tool_response, str) else json.dumps(tool_response)
        m = _CLAUDE_URL_RE.search(text)
    if not m:
        return none
    return m.group(0), tool_input.get("file_path"), tool_input.get("title") or None
