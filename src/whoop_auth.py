"""One-time WHOOP authorisation, then silent refresh forever after.

Run this once:

    python src/whoop_auth.py

It opens your browser, you approve on WHOOP's own consent screen, and the
tokens land in data/whoop_token.json (gitignored, chmod 600). Your client
secret goes straight from .env to WHOOP and is never printed or logged.
"""

from __future__ import annotations

import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from config import (
    AUTH_URL,
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    SCOPES,
    TOKEN_PATH,
    TOKEN_URL,
    ensure_data_dir,
)

# Tokens are refreshed this many seconds before they actually expire, so a
# long-running script never fails mid-request.
EXPIRY_MARGIN = 120

_PAGE = """<!doctype html><meta charset="utf-8">
<title>WHOOP connected</title>
<body style="font-family:-apple-system,sans-serif;text-align:center;padding:4rem">
<h2>{heading}</h2><p>{detail}</p><p>You can close this tab.</p>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    """Catches the single redirect WHOOP sends back after consent."""

    result: dict = {}

    def do_GET(self) -> None:  # noqa: N802 - name fixed by http.server
        params = parse_qs(urlparse(self.path).query)
        _CallbackHandler.result = {k: v[0] for k, v in params.items()}
        ok = "code" in _CallbackHandler.result
        body = _PAGE.format(
            heading="Connected" if ok else "Authorisation failed",
            detail="Head back to your terminal." if ok
            else _CallbackHandler.result.get("error_description", "No code returned."),
        )
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args) -> None:
        """Silence the default stderr logging; it would echo the auth code."""


def save_tokens(payload: dict) -> Path:
    ensure_data_dir()
    payload = dict(payload)
    payload["expires_at"] = time.time() + float(payload.get("expires_in", 3600))
    TOKEN_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    TOKEN_PATH.chmod(0o600)
    return TOKEN_PATH


def load_tokens() -> dict | None:
    if not TOKEN_PATH.is_file():
        return None
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def refresh(tokens: dict) -> dict:
    """Trade a refresh token for a new access token."""
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise SystemExit(
            "No refresh token stored. Run 'python src/whoop_auth.py' again — the "
            "'offline' scope is what makes WHOOP issue one."
        )
    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID(),
            "client_secret": CLIENT_SECRET(),
            "scope": "offline",
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise SystemExit(
            f"Token refresh failed (HTTP {response.status_code}). Re-run "
            "'python src/whoop_auth.py' to authorise again."
        )
    save_tokens(response.json())
    reloaded = load_tokens()
    assert reloaded is not None  # just written
    return reloaded


def access_token() -> str:
    """The current access token, refreshed if it is about to expire."""
    tokens = load_tokens()
    if tokens is None:
        raise SystemExit(
            "Not authorised yet. Run 'python src/whoop_auth.py' once to connect "
            "your WHOOP account."
        )
    if time.time() >= float(tokens.get("expires_at", 0)) - EXPIRY_MARGIN:
        tokens = refresh(tokens)
    return tokens["access_token"]


def authorize() -> Path:
    """Full consent flow. Opens a browser and waits for the single callback."""
    port = urlparse(REDIRECT_URI).port or 80
    state = secrets.token_urlsafe(24)

    url = AUTH_URL + "?" + urlencode(
        {
            "client_id": CLIENT_ID(),
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )

    print("Opening WHOOP's consent screen in your browser...")
    print("If it does not open, paste this in yourself:\n")
    print(url + "\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", port), _CallbackHandler)
    server.timeout = 300
    server.handle_request()  # exactly one request, then stop listening
    server.server_close()

    result = _CallbackHandler.result
    if not result:
        raise SystemExit("Timed out waiting for WHOOP to redirect back.")
    if "code" not in result:
        raise SystemExit(f"WHOOP returned an error: {result.get('error', result)}")
    if result.get("state") != state:
        # Mismatched state means the response did not come from the request we
        # made, so the code is not trustworthy.
        raise SystemExit("State mismatch — discarding this response.")

    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": result["code"],
            "client_id": CLIENT_ID(),
            "client_secret": CLIENT_SECRET(),
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise SystemExit(
            f"Token exchange failed (HTTP {response.status_code}): {response.text[:300]}"
        )

    path = save_tokens(response.json())
    granted = load_tokens().get("scope", "")
    print(f"\nConnected. Tokens saved to {path} (readable only by you).")
    if granted:
        print(f"Scopes granted: {granted}")
    return path


if __name__ == "__main__":
    authorize()
