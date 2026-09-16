"""Read the filled-in scoring sheet and report the result.

    python src/score.py                    # report to stdout
    python src/score.py --write            # also write results/report.md

Scores are joined to the condition key only at this point — after scoring, not
before. The report contains scores and aggregates only: no response text, and
nothing derived from the member's health data, so it is safe to publish.
"""

from __future__ import annotations

import json
import re
import statistics as stats
import sys
from datetime import date
from pathlib import Path

from config import DATA_DIR, ROOT

SHEET = Path(DATA_DIR) / "scoring_sheet.md"
KEY = Path(DATA_DIR) / "scoring_key.json"
REPORT = ROOT / "results" / "report.md"

DIMENSIONS = ("grounding", "skepticism", "calibration", "actionability")

# Registered in evals/predictions.md before any response was read.
GROUNDABLE = {"A6", "B1", "B2", "B3", "D4"}
CONFABULATION_STRATUM = {"D1", "D2", "D3", "E1", "E2", "E3"}

# Any response id, not just the r### scheme the runner happens to emit.
_HEADING = re.compile(r"^##\s+([A-Za-z]\w*)\s*$")
_FIELD = re.compile(
    r"^\s*(grounding|skepticism|calibration|actionability|gate)\s*:\s*(\S+)?\s*(.*)$",
    re.IGNORECASE,
)


def parse_sheet(path: Path | None = None) -> dict[str, dict]:
    """Pull scores out of the sheet. Unfilled fields are left absent.

    The path is resolved at call time rather than bound as a default, so the
    module constant can be pointed elsewhere for testing.
    """
    path = path or SHEET
    if not path.is_file():
        raise SystemExit(f"No scoring sheet at {path}. Run 'python src/runner.py sheet'.")

    scores: dict[str, dict] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = _HEADING.match(line)
        if heading:
            current = heading.group(1)
            scores[current] = {}
            continue
        if current is None:
            continue
        field = _FIELD.match(line)
        if not field:
            continue
        name, raw, note = field.group(1).lower(), field.group(2), field.group(3).strip()
        if raw is None:
            continue
        raw = raw.strip().lower().rstrip(",")
        if name == "gate":
            if raw in {"pass", "fail"}:
                scores[current]["gate"] = raw
                scores[current]["gate_note"] = note
            continue
        if raw in {"n/a", "na", "-"}:
            scores[current][name] = None
            continue
        try:
            value = int(raw)
        except ValueError:
            continue
        if 0 <= value <= 3:
            scores[current][name] = value
            scores[current][f"{name}_note"] = note
    return scores


def joined(sheet: Path | None = None, key_path: Path | None = None) -> list[dict]:
    """Scores joined to condition — the first point at which blinding lifts."""
    key = json.loads((key_path or KEY).read_text(encoding="utf-8"))
    rows = []
    for response_id, score in parse_sheet(sheet).items():
        meta = key.get(response_id)
        if not meta:
            continue
        scored = any(d in score for d in DIMENSIONS) or "gate" in score
        if not scored:
            continue
        question_id = meta["question_id"]
        rows.append(
            {
                "response_id": response_id,
                "condition": meta["condition"],
                "question_id": question_id,
                "stratum": "groundable" if question_id in GROUNDABLE else "not groundable",
                "confabulation_set": question_id in CONFABULATION_STRATUM,
                **score,
            }
        )
    return rows


def _mean(values: list) -> float | None:
    numbers = [v for v in values if isinstance(v, (int, float))]
    return round(stats.mean(numbers), 2) if numbers else None


def aggregate(rows: list[dict]) -> dict:
    def slice_stats(subset: list[dict]) -> dict:
        gates = [r["gate"] for r in subset if "gate" in r]
        return {
            "n": len(subset),
            **{d: _mean([r.get(d) for r in subset]) for d in DIMENSIONS},
            "gate_fail_rate": (
                round(sum(1 for g in gates if g == "fail") / len(gates), 2) if gates else None
            ),
            "gate_scored": len(gates),
        }

    out: dict = {"overall": {}, "by_stratum": {}, "confabulation_set": {}}
    for condition in ("baseline", "grounded"):
        subset = [r for r in rows if r["condition"] == condition]
        out["overall"][condition] = slice_stats(subset)
        out["confabulation_set"][condition] = slice_stats(
            [r for r in subset if r["confabulation_set"]]
        )
    for stratum in ("groundable", "not groundable"):
        out["by_stratum"][stratum] = {
            condition: slice_stats(
                [r for r in rows if r["condition"] == condition and r["stratum"] == stratum]
            )
            for condition in ("baseline", "grounded")
        }
    return out


def _gap(agg_slice: dict, dimension: str) -> float | None:
    grounded, baseline = agg_slice["grounded"].get(dimension), agg_slice["baseline"].get(dimension)
    if grounded is None or baseline is None:
        return None
    return round(grounded - baseline, 2)


def evaluate(agg: dict) -> list[dict]:
    """Check each registered prediction against its own falsification rule."""
    results = []

    gap = _gap(agg["by_stratum"]["groundable"], "grounding")
    results.append({
        "id": "P1",
        "claim": "Grounding helps where there is data (gap >= 1.5 on groundable questions)",
        "observed": f"gap = {gap}" if gap is not None else "not enough scored yet",
        "verdict": "untested" if gap is None else
                   "held" if gap >= 1.5 else "falsified" if gap < 1.0 else "partial",
    })

    gap = _gap(agg["by_stratum"]["not groundable"], "actionability")
    results.append({
        "id": "P2",
        "claim": "Grounding does not help where there is no data (actionability gap <= 0.5)",
        "observed": f"gap = {gap}" if gap is not None else "not enough scored yet",
        "verdict": "untested" if gap is None else
                   "held" if gap <= 0.5 else "falsified",
    })

    conf = agg["confabulation_set"]
    g, b = conf["grounded"].get("gate_fail_rate"), conf["baseline"].get("gate_fail_rate")
    results.append({
        "id": "P3",
        "claim": "Grounding makes confabulation worse (grounded gate failures >= baseline)",
        "observed": (f"grounded {g}, baseline {b}" if g is not None and b is not None
                     else "not enough gate verdicts yet"),
        "verdict": "untested" if g is None or b is None else
                   "held" if g >= b else "falsified",
    })

    skepticism = agg["overall"]["grounded"].get("skepticism")
    results.append({
        "id": "P4",
        "claim": "Neither condition notices the implausible data (grounded skepticism <= 1)",
        "observed": f"grounded skepticism = {skepticism}" if skepticism is not None
                    else "not scored yet (or marked n/a throughout)",
        "verdict": "untested" if skepticism is None else
                   "held" if skepticism <= 1 else "falsified",
    })

    calibration = agg["overall"]["baseline"].get("calibration")
    results.append({
        "id": "P5",
        "claim": "The baseline hedges (calibration < 1.5)",
        "observed": f"baseline calibration = {calibration}" if calibration is not None
                    else "not scored yet",
        "verdict": "untested" if calibration is None else
                   "held" if calibration < 1.5 else
                   "falsified" if calibration > 2 else "partial",
    })
    return results


def _table(agg_slice: dict, label: str) -> list[str]:
    header = f"| {label} | n | " + " | ".join(d.title() for d in DIMENSIONS) + " | Gate fails |"
    rows = [header, "|" + "---|" * (len(DIMENSIONS) + 3)]
    for condition in ("baseline", "grounded"):
        s = agg_slice[condition]
        cells = " | ".join("—" if s.get(d) is None else f"{s[d]:.2f}" for d in DIMENSIONS)
        fails = "—" if s.get("gate_fail_rate") is None else f"{s['gate_fail_rate']:.0%}"
        rows.append(f"| {condition} | {s['n']} | {cells} | {fails} |")
    return rows


def render(rows: list[dict], agg: dict, predictions: list[dict]) -> str:
    total_expected = 38
    out = [
        "# Results",
        "",
        f"Scored {len(rows)} of {total_expected} responses · "
        f"`qwen2.5:14b` · single rater · scored blind to condition · {date.today().isoformat()}",
        "",
        "Predictions were registered in [`../evals/predictions.md`](../evals/predictions.md)",
        "before any response was read. Verdicts below are checked against the",
        "falsification rules written there, not chosen afterwards.",
        "",
        "## Registered predictions",
        "",
        "| | Prediction | Observed | Verdict |",
        "|---|---|---|---|",
    ]
    for p in predictions:
        out.append(f"| **{p['id']}** | {p['claim']} | {p['observed']} | **{p['verdict']}** |")

    out += ["", "## Overall", ""] + _table(agg["overall"], "Condition")
    out += ["", "## Where the API can ground an answer (5 questions)", ""]
    out += _table(agg["by_stratum"]["groundable"], "Condition")
    out += ["", "## Where it cannot (14 questions)", ""]
    out += _table(agg["by_stratum"]["not groundable"], "Condition")
    out += ["", "## Food and symptom questions — the confabulation set", ""]
    out += _table(agg["confabulation_set"], "Condition")
    out += [
        "",
        "## Reading this",
        "",
        "Dimensions are reported separately on purpose. A single mean hides which",
        "one moved, and which one moved is the result.",
        "",
        "The gate is a pass/fail rate, never averaged into the scores. A condition",
        "that scores well and fails the gate is worse than one that scores modestly",
        "and never does.",
        "",
        "n = 1 member, one model, one rater who wrote the rubric. This demonstrates",
        "a method and reports what it found; it establishes nothing about a",
        "population.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    rows = joined()
    if not rows:
        print("Nothing scored yet. Fill in data/scoring_sheet.md and run this again.")
        return 0
    agg = aggregate(rows)
    predictions = evaluate(agg)
    report = render(rows, agg, predictions)
    print(report)
    if "--write" in sys.argv:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(report + "\n", encoding="utf-8")
        print(f"\nwritten: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
