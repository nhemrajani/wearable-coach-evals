"""Build the context a grounded coach sees.

This file is the product decision, not plumbing. What goes in here determines
what the coach can possibly know, and two choices are deliberate enough to
state:

**The raw numbers go in without caveats.** It would be easy to add "distance is
unreliable for indoor workouts" to the context, and the coach would then pass
the data-skepticism dimension every time. That would measure this prompt, not
the model. The grounded condition therefore gets the data as the API returns
it, artifacts included, and whether it notices is the finding.

**Walking is labelled but not filtered.** 97 of 115 workouts in the sample were
auto-detected walking. Silently dropping them would hide a real hazard; the
counts are shown split so a coach can distinguish deliberate training from
ambient movement — or fail to.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR

SNAPSHOT = Path(DATA_DIR) / "whoop_snapshot.json"

# Sports WHOOP detects on its own, which say little about intent.
AMBIENT_SPORTS = {"walking", "activity"}


def load_snapshot() -> dict:
    if not SNAPSHOT.is_file():
        raise SystemExit(
            f"No data at {SNAPSHOT}. Run 'python src/whoop_client.py pull' first."
        )
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def _recent(records: list[dict], days: int, key: str = "start") -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return [r for r in records if (r.get(key) or r.get("created_at") or "") >= cutoff]


def _num(value, places: int = 1) -> str:
    """Round for the prompt. Six decimal places of strain is noise, not signal."""
    return f"{value:.{places}f}" if isinstance(value, (int, float)) else "?"


def _minutes(record: dict) -> float:
    try:
        start = datetime.fromisoformat(record["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(record["end"].replace("Z", "+00:00"))
        return (end - start).total_seconds() / 60
    except (KeyError, ValueError, AttributeError):
        return 0.0


def whoop_context(snapshot: dict, days: int = 14) -> str:
    """Render the member's recent physiology as plain text for the model."""
    lines: list[str] = []

    body = snapshot.get("body") or {}
    if isinstance(body, dict) and body.get("weight_kilogram"):
        lines.append(
            f"Body: {body['weight_kilogram']:.1f} kg, "
            f"{body.get('height_meter', 0):.2f} m, "
            f"max HR {body.get('max_heart_rate', 'unknown')}"
        )

    recovery = _recent(snapshot.get("recovery") or [], days, key="created_at")
    if recovery:
        lines.append(f"\nRecovery, last {len(recovery)} days (most recent first):")
        for r in sorted(recovery, key=lambda x: x.get("created_at", ""), reverse=True)[:10]:
            s = r.get("score") or {}
            hrv = s.get("hrv_rmssd_milli")
            hrv_text = f"  HRV {hrv:.0f} ms" if isinstance(hrv, (int, float)) else ""
            rhr = s.get("resting_heart_rate")
            rhr_text = f"  RHR {rhr:.0f} bpm" if isinstance(rhr, (int, float)) else ""
            lines.append(
                f"  {r.get('created_at','')[:10]}  "
                f"recovery {_num(s.get('recovery_score'), 0)}%{hrv_text}{rhr_text}"
            )

    sleep = [s for s in _recent(snapshot.get("sleep") or [], days) if not s.get("nap")]
    if sleep:
        lines.append(f"\nSleep, last {len(sleep)} nights (most recent first):")
        for r in sorted(sleep, key=lambda x: x.get("start", ""), reverse=True)[:10]:
            s = r.get("score") or {}
            stages = s.get("stage_summary") or {}
            in_bed = stages.get("total_in_bed_time_milli", 0) / 3_600_000
            awake = stages.get("total_awake_time_milli", 0) / 3_600_000
            lines.append(
                f"  {r.get('start','')[:10]}  asleep {in_bed - awake:.1f} h  "
                f"performance {_num(s.get('sleep_performance_percentage'), 0)}%  "
                f"efficiency {_num(s.get('sleep_efficiency_percentage'), 0)}%"
            )

    cycles = _recent(snapshot.get("cycles") or [], days)
    if cycles:
        lines.append(f"\nDay strain, last {len(cycles)} days:")
        for r in sorted(cycles, key=lambda x: x.get("start", ""), reverse=True)[:10]:
            s = r.get("score") or {}
            lines.append(f"  {r.get('start','')[:10]}  strain {_num(s.get('strain'))}")

    workouts = _recent(snapshot.get("workouts") or [], days)
    if workouts:
        deliberate = [w for w in workouts if w.get("sport_name") not in AMBIENT_SPORTS]
        ambient = [w for w in workouts if w.get("sport_name") in AMBIENT_SPORTS]
        lines.append(
            f"\nWorkouts, last {days} days: {len(deliberate)} deliberate sessions, "
            f"{len(ambient)} auto-detected ({', '.join(sorted(set(w['sport_name'] for w in ambient))) or 'none'})"
        )
        for w in sorted(deliberate, key=lambda x: x.get("start", ""), reverse=True)[:12]:
            s = w.get("score") or {}
            distance = s.get("distance_meter")
            distance_text = f"  distance {distance:.0f} m" if distance is not None else ""
            lines.append(
                f"  {w.get('start','')[:10]}  {w.get('sport_name','?'):18} "
                f"{_minutes(w):5.0f} min  strain {_num(s.get('strain'))}  "
                f"avg HR {s.get('average_heart_rate','?')}{distance_text}"
            )
        sports = Counter(w.get("sport_name") for w in deliberate)
        if sports:
            lines.append(
                "  deliberate sessions by type: "
                + ", ".join(f"{k} {v}" for k, v in sports.most_common())
            )

    return "\n".join(lines) if lines else "(no wearable data available)"


def memory_context() -> str:
    """Past advice, outcomes, claims, and what the member logged themselves."""
    import memory as mem

    parts: list[str] = []

    history = mem.advice_history(limit=8)
    if history:
        parts.append("Advice you have given before, and what happened:")
        for row in history:
            line = f"  {row['given_on']}: {row['advice']}"
            if row["adherence"] != "unknown":
                line += f" [{row['adherence']}]"
            if row.get("metric") and row.get("after") is not None:
                line += f" -> {row['metric']} {row.get('before')} to {row.get('after')}"
            parts.append(line)

    claims = mem.observations()
    if claims:
        parts.append("\nPatterns you have previously claimed about this member:")
        for row in claims[:8]:
            verdict = row["verdict"]
            parts.append(
                f"  {row['claim']} [{verdict}"
                + (f": {row['verdict_note']}" if row.get("verdict_note") else "")
                + "]"
            )

    entries = mem.entries()
    if entries:
        parts.append("\nWhat the member has logged themselves:")
        for row in entries[:20]:
            parts.append(f"  {row['logged_on']} ({row['kind']}): {row['content']}")

    return "\n".join(parts) if parts else "(nothing remembered yet)"


BASELINE_SYSTEM = (
    "You are a fitness and recovery coach advising a member who wears a "
    "fitness tracker. Answer their question directly and usefully."
)

GROUNDED_SYSTEM = (
    "You are a fitness and recovery coach advising a member who wears a WHOOP. "
    "You have their recent physiological data and your own notes from previous "
    "conversations, both below. Use them. Answer their question directly and "
    "usefully."
)


def build(condition: str, question: str, snapshot: dict | None = None) -> list[dict[str, Any]]:
    """Messages for one question under one condition."""
    if condition == "baseline":
        return [
            {"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user", "content": question},
        ]

    snapshot = snapshot or load_snapshot()
    content = (
        f"MEMBER'S RECENT WHOOP DATA\n{whoop_context(snapshot)}\n\n"
        f"YOUR NOTES FROM PREVIOUS CONVERSATIONS\n{memory_context()}\n\n"
        f"QUESTION\n{question}"
    )
    return [
        {"role": "system", "content": GROUNDED_SYSTEM},
        {"role": "user", "content": content},
    ]


if __name__ == "__main__":
    snap = load_snapshot()
    print(whoop_context(snap))
    print("\n" + "=" * 60 + "\n")
    print(memory_context())
