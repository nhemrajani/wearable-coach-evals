"""Run every question under every condition, then produce a blind scoring sheet.

    python src/runner.py run                 # generate responses
    python src/runner.py sheet               # write the blind scoring sheet

Questions are parsed out of evals/questions.md so that file stays the single
source of truth. Responses and the condition key are written to the gitignored
data directory; only aggregate results are ever published.
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import DATA_DIR, ROOT, ensure_data_dir

QUESTIONS_MD = ROOT / "evals" / "questions.md"
RESPONSES = Path(DATA_DIR) / "responses.json"
SHEET = Path(DATA_DIR) / "scoring_sheet.md"
KEY = Path(DATA_DIR) / "scoring_key.json"

OLLAMA = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:14b"
CONDITIONS = ("baseline", "grounded")

# Table rows look like: | A1 | Question text? | `goal` `whoop` |
_ROW = re.compile(r"^\|\s*([A-Z]\d+)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|\s*$")
_SECTION = re.compile(r"^##\s+([A-Z])\.\s+(.+?)\s*$")


def parse_questions() -> list[dict]:
    """Read the question set out of the markdown, keeping one source of truth."""
    questions: list[dict] = []
    section = ""
    for line in QUESTIONS_MD.read_text(encoding="utf-8").splitlines():
        heading = _SECTION.match(line)
        if heading:
            section = heading.group(2)
            continue
        row = _ROW.match(line)
        if not row:
            continue
        qid, text, needs = row.groups()
        if qid == "#":  # the header row
            continue
        questions.append(
            {
                "id": qid,
                "section": section,
                "question": text,
                "needs": re.findall(r"`([a-z]+)`", needs),
            }
        )
    return questions


def ask(messages: list[dict], model: str = MODEL, temperature: float = 0.7) -> dict:
    """One call to the local model. Nothing leaves the machine."""
    started = time.monotonic()
    response = httpx.post(
        OLLAMA,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=300,
    )
    response.raise_for_status()
    payload = response.json()
    return {
        "text": payload["message"]["content"].strip(),
        "tokens": payload.get("eval_count"),
        "seconds": round(time.monotonic() - started, 1),
    }


def run(model: str = MODEL, samples: int = 1) -> Path:
    import context

    questions = parse_questions()
    if not questions:
        raise SystemExit(f"No questions parsed from {QUESTIONS_MD}")
    snapshot = context.load_snapshot()

    ensure_data_dir()
    results: list[dict] = []
    total = len(questions) * len(CONDITIONS) * samples
    done = 0

    for question in questions:
        for condition in CONDITIONS:
            for sample in range(samples):
                messages = context.build(condition, question["question"], snapshot)
                answer = ask(messages, model=model)
                done += 1
                print(
                    f"  [{done}/{total}] {question['id']:3} {condition:9} "
                    f"{answer['seconds']:5.1f}s  {answer['tokens'] or 0:4} tokens",
                    flush=True,
                )
                results.append(
                    {
                        "response_id": f"r{len(results) + 1:03d}",
                        "question_id": question["id"],
                        "section": question["section"],
                        "question": question["question"],
                        "needs": question["needs"],
                        "condition": condition,
                        "sample": sample,
                        "model": model,
                        "response": answer["text"],
                        "tokens": answer["tokens"],
                        "seconds": answer["seconds"],
                    }
                )

    RESPONSES.write_text(
        json.dumps(
            {
                "run_at": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "samples_per_cell": samples,
                "responses": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    RESPONSES.chmod(0o600)
    return RESPONSES


def sheet(seed: int = 1) -> Path:
    """Write the scoring sheet with conditions stripped and order shuffled.

    Blinding is imperfect and the write-up should say so: a grounded answer
    quotes the member's numbers, so a scorer can often infer the condition from
    the text however it is shuffled. It still helps for calibration,
    actionability and the safety gate, where the tell is much weaker.
    """
    payload = json.loads(RESPONSES.read_text(encoding="utf-8"))
    responses = payload["responses"][:]
    random.Random(seed).shuffle(responses)

    key = {r["response_id"]: {"condition": r["condition"], "question_id": r["question_id"]}
           for r in responses}
    KEY.write_text(json.dumps(key, indent=2), encoding="utf-8")
    KEY.chmod(0o600)

    out = [
        "# Blind scoring sheet",
        "",
        f"Model: `{payload['model']}` · generated {payload['run_at'][:10]} · "
        f"{len(responses)} responses, order shuffled, condition hidden.",
        "",
        "Score each against [`../evals/rubric.md`](../evals/rubric.md). Fill in the",
        "fields under each response. Use `n/a` where a dimension does not apply,",
        "and write one line of justification per score — that is what makes a",
        "disagreement legible later.",
        "",
        "```",
        "grounding:     0-3 | n/a        because ...",
        "skepticism:    0-3 | n/a        because ...",
        "calibration:   0-3 | n/a        because ...",
        "actionability: 0-3 | n/a        because ...",
        "gate:          pass | fail      because ...",
        "```",
        "",
        "---",
        "",
    ]

    for r in responses:
        out += [
            f"## {r['response_id']}",
            "",
            f"**Question ({r['question_id']}):** {r['question']}",
            "",
            "<details><summary>Response</summary>",
            "",
            r["response"],
            "",
            "</details>",
            "",
            "```",
            "grounding:     ",
            "skepticism:    ",
            "calibration:   ",
            "actionability: ",
            "gate:          ",
            "```",
            "",
            "---",
            "",
        ]

    SHEET.write_text("\n".join(out), encoding="utf-8")
    SHEET.chmod(0o600)
    return SHEET


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    if command == "questions":
        for q in parse_questions():
            print(f"  {q['id']:3} [{','.join(q['needs']):16}] {q['question'][:64]}")
        print(f"\n  {len(parse_questions())} questions")
    elif command == "run":
        path = run()
        print(f"\nwritten: {path}")
        print("next: python src/runner.py sheet")
    elif command == "sheet":
        path = sheet()
        payload = json.loads(RESPONSES.read_text(encoding="utf-8"))
        print(f"written: {path}  ({len(payload['responses'])} responses, shuffled)")
        print(f"key:     {KEY}  (do not read this until scoring is done)")
    else:
        raise SystemExit("usage: python src/runner.py [questions|run|sheet]")
