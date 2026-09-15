"""Read your own WHOOP data.

    python src/whoop_client.py probe     # which endpoints actually exist
    python src/whoop_client.py pull      # fetch recent data into data/

Run src/whoop_auth.py first. Everything written here lands in the gitignored
data directory and never goes near the repository.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config import API_BASE, ensure_data_dir
from whoop_auth import access_token

# WHOOP's own docs are explicit about /v2/cycle, /v2/activity/sleep and
# /v2/activity/workout, and vaguer about the rest — recovery is described as
# reachable "through the Cycle endpoints", and profile and body measurement are
# not spelled out at all. Rather than guess in silence, `probe` asks the API.
ENDPOINTS: dict[str, str] = {
    "cycles": "/v2/cycle",
    "recovery": "/v2/recovery",
    "sleep": "/v2/activity/sleep",
    "workouts": "/v2/activity/workout",
    "profile": "/v2/user/profile/basic",
    "body": "/v2/user/measurement/body",
}

# Tried only if the primary path 404s.
FALLBACKS: dict[str, list[str]] = {
    "recovery": ["/v2/cycle/recovery", "/v1/recovery"],
    "profile": ["/v2/user/profile", "/v1/user/profile/basic"],
    "body": ["/v2/user/measurement", "/v1/user/measurement/body"],
}

PAGED = {"cycles", "recovery", "sleep", "workouts"}


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=API_BASE,
        headers={"Authorization": f"Bearer {access_token()}"},
        timeout=30,
    )


def get(path: str, params: dict | None = None, client: httpx.Client | None = None) -> Any:
    owned = client is None
    client = client or _client()
    try:
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()
    finally:
        if owned:
            client.close()


def probe() -> dict[str, dict]:
    """Ask the API which endpoints exist, instead of assuming.

    Reports the status code for each candidate path so an unavailable metric is
    a documented finding rather than a silent gap.
    """
    found: dict[str, dict] = {}
    with _client() as client:
        for name, path in ENDPOINTS.items():
            candidates = [path] + FALLBACKS.get(name, [])
            for candidate in candidates:
                params = {"limit": 1} if name in PAGED else None
                try:
                    response = client.get(candidate, params=params)
                except httpx.HTTPError as exc:
                    found[name] = {"path": candidate, "status": f"error: {exc}"}
                    break
                found[name] = {"path": candidate, "status": response.status_code}
                if response.status_code == 200:
                    payload = response.json()
                    records = payload.get("records") if isinstance(payload, dict) else None
                    found[name]["fields"] = sorted(
                        (records[0] if records else payload).keys()
                    ) if isinstance(payload, dict) else []
                    break
    return found


def paged(name: str, days: int = 30, limit: int = 25) -> list[dict]:
    """Every record of one type in the last N days, following next_token."""
    path = ENDPOINTS[name]
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    records: list[dict] = []
    token: str | None = None
    with _client() as client:
        while True:
            params: dict[str, Any] = {"limit": limit, "start": start}
            if token:
                params["nextToken"] = token
            payload = get(path, params, client=client)
            records.extend(payload.get("records", []))
            token = payload.get("next_token")
            if not token:
                return records


def pull(days: int = 30) -> dict:
    """Fetch recent data and write it to the gitignored data directory."""
    available = probe()
    data_dir = ensure_data_dir()
    snapshot: dict[str, Any] = {"pulled_at": datetime.now(timezone.utc).isoformat()}

    for name, info in available.items():
        if info.get("status") != 200:
            snapshot[name] = {"unavailable": info}
            continue
        snapshot[name] = paged(name, days=days) if name in PAGED else get(info["path"])

    out = data_dir / "whoop_snapshot.json"
    out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    out.chmod(0o600)
    return {"written": str(out), "summary": summarise(snapshot)}


def summarise(snapshot: dict) -> dict:
    """Counts only — never the data itself, so this is safe to print."""
    out = {}
    for name, value in snapshot.items():
        if name == "pulled_at":
            continue
        if isinstance(value, list):
            out[name] = f"{len(value)} records"
        elif isinstance(value, dict) and "unavailable" in value:
            out[name] = f"unavailable (HTTP {value['unavailable']['status']})"
        else:
            out[name] = "1 record"
    return out


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if command == "probe":
        for name, info in probe().items():
            status = info["status"]
            mark = "ok  " if status == 200 else "MISS"
            print(f"  {mark} {name:9} {info['path']:32} {status}")
            if info.get("fields"):
                print(f"       fields: {', '.join(info['fields'][:8])}")
    elif command == "pull":
        result = pull()
        print(f"written: {result['written']}")
        for name, count in result["summary"].items():
            print(f"  {name:9} {count}")
    else:
        raise SystemExit("usage: python src/whoop_client.py [probe|pull]")
