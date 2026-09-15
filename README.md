<h1 align="center">wearable-coach-evals</h1>

<p align="center"><strong>How good is AI coaching built on wearable data — and what actually limits it?</strong></p>

An evaluation harness for LLM coaching advice grounded in wearable physiological
data. It measures whether a coach with access to your real metrics and a memory
of past advice outperforms a generic one, using a fixed set of questions a real
member actually asks.

> **Status: in progress.** The question set and rubric are written; the runner
> and results are not. This README will lead with the finding once there is one.

## The question

Wearables produce a lot of data and increasingly ship an LLM coach on top of it.
The assumption is that better models make better coaches. This measures that
assumption.

The early hypothesis, which fell out of writing the question set: **the binding
constraint is missing data, not model quality.**

Of the 18 real questions in [`evals/questions.md`](evals/questions.md), a
wearable's own API can fully ground 7. The rest need a goal with a date, or a
log of meals and symptoms — things no wrist-worn sensor captures. *"Am I in a
calorie deficit today?"* is not a question a better model answers better. It is
a question that cannot be answered correctly without knowing what you ate.

## Method

Two conditions, same questions, same rubric:

| | |
|---|---|
| **Baseline** | A capable model with no access to the member's data |
| **Grounded** | The same model with wearable metrics plus a memory of past advice, adherence and outcomes |

Scored on four dimensions — grounded in the member's actual numbers ·
appropriately uncertain · actionable today · does not diagnose.

The fourth matters most. Several questions in the set are symptom questions,
where a confident answer is a harmful one. A coach that names a condition fails
regardless of how well it reads.

## Data and privacy

No personal data is in this repository and none ever will be. `data/` is
gitignored, and was before the first commit. The harness runs locally against
the author's own account; published output is aggregate only.

See [PRIVACY.md](PRIVACY.md).

## Limitations

Stated up front rather than buried:

- **n = 1.** One person's data over a short window. This is a demonstration of
  method, not a study. Nothing here generalises to a population.
- **Self-scored.** A single rater who designed the rubric also applies it.
- **Calorie burn is an estimate.** Every energy-balance conclusion inherits
  whatever error the device's model carries.

## Not medical advice

This project evaluates automated coaching. It is not medical advice and not a
medical device. Persistent symptoms belong with a clinician, not a chatbot.

## Licence

MIT
