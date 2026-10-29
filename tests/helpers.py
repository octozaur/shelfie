import os
import tempfile
from pathlib import Path


class TempProject:
    """Temporary project dir; sets CLAUDE_PROJECT_DIR while active."""

    def __init__(self, name="proj"):
        self.name = name

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / self.name
        self.root.mkdir()
        self._old = os.environ.get("CLAUDE_PROJECT_DIR")
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        return self.root

    def __exit__(self, *exc):
        if self._old is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = self._old
        self._tmp.cleanup()
