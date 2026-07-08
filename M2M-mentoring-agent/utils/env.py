"""Environment loading helpers."""

from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent


def load_project_env() -> None:
    """Load project-local env files before modules read os.environ."""
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local")
    load_dotenv(ROOT.parent / ".env")
    load_dotenv(ROOT.parent / ".env.local")
