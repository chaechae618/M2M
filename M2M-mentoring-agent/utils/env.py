"""Environment loading helpers."""

from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


ROOT = Path(__file__).resolve().parent.parent


def load_project_env() -> None:
    """Load project-local env files before modules read os.environ."""
    for path in [ROOT / ".env", ROOT / ".env.local", ROOT.parent / ".env", ROOT.parent / ".env.local"]:
        if load_dotenv is not None:
            load_dotenv(path)
            continue
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
