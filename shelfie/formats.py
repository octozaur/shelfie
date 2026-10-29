"""Artifact types: labels, badges, colours and file extensions."""
from __future__ import annotations

TYPES: dict = {
    "artifact": {"label": "Claude artifact", "badge": "ARTIFACT", "color": "#d97757", "exts": ()},
    "html": {"label": "HTML", "badge": "HTML", "color": "#f76b15", "exts": (".html", ".htm")},
    "pdf": {"label": "PDF", "badge": "PDF", "color": "#e5484d", "exts": (".pdf",)},
    "md": {"label": "Markdown", "badge": "MD", "color": "#6e6d68", "exts": (".md", ".markdown")},
    "doc": {"label": "Doc", "badge": "DOCX", "color": "#3e63dd", "exts": (".docx", ".doc", ".odt", ".rtf")},
    "slides": {"label": "Slides", "badge": "PPTX", "color": "#e2a336", "exts": (".pptx", ".key", ".odp")},
    "sheet": {"label": "Sheet", "badge": "XLSX", "color": "#30a46c", "exts": (".xlsx", ".xls", ".csv", ".tsv", ".ods")},
    "server": {"label": "Local server", "badge": "SERVER", "color": "#8e4ec6", "exts": ()},
    "image": {"label": "Image", "badge": "IMG", "color": "#12a594", "exts": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")},
}

ALL: list = list(TYPES)

_EXT_TO_TYPE = {ext: key for key, t in TYPES.items() for ext in t["exts"]}


def type_for_path(path: str) -> str | None:
    """File type key for a path, by extension (case-insensitive)."""
    dot = path.rfind(".")
    if dot == -1 or "/" in path[dot:]:
        return None
    return _EXT_TO_TYPE.get(path[dot:].lower())
