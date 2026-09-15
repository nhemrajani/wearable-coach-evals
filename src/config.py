"""Configuration. Every secret comes from .env, which is gitignored.

Nothing in this file holds a credential; it only says where to find one.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# WHOOP OAuth 2.0 and REST endpoints.
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
API_BASE = "https://api.prod.whoop.com/developer"

# "offline" is what makes WHOOP return a refresh token; without it you would
# re-authorise in the browser every couple of hours.
SCOPES = [
    "offline",
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
    "read:body_measurement",
]


def _load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader — avoids a dependency for eight lines of parsing."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        # Real environment variables win, so you can override per-run.
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"{name} is not set. Copy .env.example to .env and fill it in — "
            "see the README."
        )
    return value


CLIENT_ID = lambda: require("WHOOP_CLIENT_ID")  # noqa: E731 - deferred so imports stay cheap
CLIENT_SECRET = lambda: require("WHOOP_CLIENT_SECRET")  # noqa: E731
REDIRECT_URI = os.environ.get("WHOOP_REDIRECT_URI", "http://localhost:8080/callback")

def _data_dir() -> Path:
    """Resolve relative to the project root, not the current directory.

    Otherwise './data' in .env would scatter token files wherever the script
    happened to be run from — including places that are not gitignored.
    """
    raw = Path(os.environ.get("COACH_EVAL_DATA_DIR", "data")).expanduser()
    return raw if raw.is_absolute() else (ROOT / raw).resolve()


DATA_DIR = _data_dir()
TOKEN_PATH = DATA_DIR / "whoop_token.json"


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
