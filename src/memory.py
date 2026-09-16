"""What the coach remembers between conversations.

Wearable APIs describe what happened to a body. They hold nothing about what
was advised, whether it was followed, what it changed, or what the member ate
and felt. That absence is the thing this project is trying to measure, so the
memory layer is deliberately shaped around the four gaps:

    observations  claims the coach made about the member's patterns
    advice        what it told them to do, and whether they did it
    outcomes      what the metrics did afterwards
    member_log    meals, symptoms and goals — the data no wrist sensor has

The observations table is the interesting one. "Your recovery drops after
back-to-back strain days" is a falsifiable claim about a person, and a coach
that is confidently wrong about someone's patterns fails differently from one
that misreads today's number. Storing claims with the window they were drawn
from means they can be checked later against what actually happened.

Everything lives in the gitignored data directory. Nothing here is published.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

from config import DATA_DIR, ensure_data_dir

DB_PATH = Path(DATA_DIR) / "memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    made_on       TEXT NOT NULL,
    claim         TEXT NOT NULL,
    basis         TEXT,
    window_start  TEXT,
    window_end    TEXT,
    confidence    TEXT,
    verdict       TEXT NOT NULL DEFAULT 'untested',
    verdict_note  TEXT,
    verified_on   TEXT
);

CREATE TABLE IF NOT EXISTS advice (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    given_on       TEXT NOT NULL,
    question_id    TEXT,
    condition      TEXT,
    advice         TEXT NOT NULL,
    timeframe      TEXT,
    observable     TEXT,
    adherence      TEXT NOT NULL DEFAULT 'unknown',
    adherence_note TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    advice_id   INTEGER NOT NULL REFERENCES advice (id) ON DELETE CASCADE,
    observed_on TEXT NOT NULL,
    metric      TEXT,
    before      REAL,
    after       REAL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS member_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_on  TEXT NOT NULL,
    kind       TEXT NOT NULL,
    content    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_log_date ON member_log (logged_on);
CREATE INDEX IF NOT EXISTS idx_obs_verdict ON observations (verdict);
"""

# A claim is one of these, and nothing else counts as an observation. Vague
# statements cannot be checked later, so they are not worth storing.
VERDICTS = ("untested", "held", "contradicted", "unfalsifiable")

# What the member records that the wearable cannot.
LOG_KINDS = ("meal", "symptom", "goal", "note")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    try:
        yield conn
    finally:
        conn.close()
    DB_PATH.chmod(0o600)


def _rows(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


# --------------------------------------------------------------------------
# Observations — claims the coach made about the member
# --------------------------------------------------------------------------


def record_observation(
    claim: str,
    basis: str | None = None,
    window: tuple[str, str] | None = None,
    confidence: str | None = None,
    made_on: str | None = None,
) -> int:
    """Store a pattern claim so it can be checked against reality later."""
    with connect() as conn:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO observations
                    (made_on, claim, basis, window_start, window_end, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    made_on or date.today().isoformat(),
                    claim.strip(),
                    basis,
                    window[0] if window else None,
                    window[1] if window else None,
                    confidence,
                ),
            )
        return int(cursor.lastrowid)


def settle_observation(observation_id: int, verdict: str, note: str | None = None) -> None:
    """Record whether a claim held up. This is how the coach is held to account."""
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    with connect() as conn:
        with conn:
            conn.execute(
                """
                UPDATE observations
                   SET verdict = ?, verdict_note = ?, verified_on = ?
                 WHERE id = ?
                """,
                (verdict, note, date.today().isoformat(), observation_id),
            )


def observations(verdict: str | None = None) -> list[dict]:
    with connect() as conn:
        if verdict:
            return _rows(conn.execute(
                "SELECT * FROM observations WHERE verdict = ? ORDER BY made_on DESC", (verdict,)
            ))
        return _rows(conn.execute("SELECT * FROM observations ORDER BY made_on DESC"))


def accuracy() -> dict:
    """How often the coach's claims about this member turned out to be true.

    Untested and unfalsifiable claims are reported separately rather than
    counted as successes — a coach that only makes uncheckable claims should
    not score well.
    """
    with connect() as conn:
        counts = {
            row["verdict"]: row["n"]
            for row in conn.execute(
                "SELECT verdict, COUNT(*) AS n FROM observations GROUP BY verdict"
            )
        }
    settled = counts.get("held", 0) + counts.get("contradicted", 0)
    return {
        **{v: counts.get(v, 0) for v in VERDICTS},
        "settled": settled,
        "held_rate": (counts.get("held", 0) / settled) if settled else None,
    }


# --------------------------------------------------------------------------
# Advice and what came of it
# --------------------------------------------------------------------------


def record_advice(
    advice: str,
    timeframe: str | None = None,
    observable: str | None = None,
    question_id: str | None = None,
    condition: str | None = None,
    given_on: str | None = None,
) -> int:
    with connect() as conn:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO advice
                    (given_on, question_id, condition, advice, timeframe, observable)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    given_on or date.today().isoformat(),
                    question_id,
                    condition,
                    advice.strip(),
                    timeframe,
                    observable,
                ),
            )
        return int(cursor.lastrowid)


def record_adherence(advice_id: int, adherence: str, note: str | None = None) -> None:
    with connect() as conn:
        with conn:
            conn.execute(
                "UPDATE advice SET adherence = ?, adherence_note = ? WHERE id = ?",
                (adherence, note, advice_id),
            )


def record_outcome(
    advice_id: int,
    metric: str | None = None,
    before: float | None = None,
    after: float | None = None,
    note: str | None = None,
    observed_on: str | None = None,
) -> int:
    with connect() as conn:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO outcomes (advice_id, observed_on, metric, before, after, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (advice_id, observed_on or date.today().isoformat(), metric, before, after, note),
            )
        return int(cursor.lastrowid)


def advice_history(limit: int = 20) -> list[dict]:
    """Past advice with its outcome, which is what the grounded coach reads."""
    with connect() as conn:
        return _rows(conn.execute(
            """
            SELECT a.*,
                   o.metric, o.before, o.after, o.note AS outcome_note
              FROM advice a
              LEFT JOIN outcomes o ON o.advice_id = a.id
             ORDER BY a.given_on DESC
             LIMIT ?
            """,
            (limit,),
        ))


# --------------------------------------------------------------------------
# The member's own log — the data the wearable does not have
# --------------------------------------------------------------------------


def log(kind: str, content: str, logged_on: str | None = None) -> int:
    """Record a meal, symptom, goal or note.

    This exists to test the thesis rather than to work around it: if adding
    intake and symptom data is what makes the unanswerable questions
    answerable, that is the finding.
    """
    if kind not in LOG_KINDS:
        raise ValueError(f"kind must be one of {LOG_KINDS}")
    with connect() as conn:
        with conn:
            cursor = conn.execute(
                "INSERT INTO member_log (logged_on, kind, content) VALUES (?, ?, ?)",
                (logged_on or date.today().isoformat(), kind, content.strip()),
            )
        return int(cursor.lastrowid)


def entries(kind: str | None = None, since: str | None = None) -> list[dict]:
    query = "SELECT * FROM member_log WHERE 1=1"
    params: list = []
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    if since:
        query += " AND logged_on >= ?"
        params.append(since)
    query += " ORDER BY logged_on DESC, id DESC"
    with connect() as conn:
        return _rows(conn.execute(query, params))


def summary() -> dict:
    """Counts only — safe to print and safe to publish."""
    with connect() as conn:
        return {
            "observations": conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
            "advice": conn.execute("SELECT COUNT(*) FROM advice").fetchone()[0],
            "outcomes": conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0],
            "log_entries": conn.execute("SELECT COUNT(*) FROM member_log").fetchone()[0],
            "claim_accuracy": accuracy(),
        }


if __name__ == "__main__":
    import json

    print(json.dumps(summary(), indent=2))
