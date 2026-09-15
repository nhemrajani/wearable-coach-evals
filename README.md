<h1 align="center">wearable-coach-evals</h1>

<p align="center"><strong>How good is AI coaching built on wearable data — and what actually limits it?</strong></p>

An evaluation harness for LLM coaching advice grounded in wearable physiological
data. It measures whether a coach with access to your real metrics and a memory
of past advice outperforms a generic one, using a fixed set of questions a real
member actually asks.

> **Status: in progress.** Question set written, API surveyed, first finding
> below. Rubric and runner next.

## The question

Wearables produce a lot of data and increasingly ship an LLM coach on top of it.
The assumption is that better models make better coaches. This measures that
assumption.

The hypothesis, which fell out of writing the question set: **the binding
constraint is missing data, not model quality.**

Of the 18 real questions in [`evals/questions.md`](evals/questions.md), the
official API can fully ground 7. *"Am I in a calorie deficit today?"* is not a
question a better model answers better. It cannot be answered correctly without
knowing what you ate, and no wrist-worn sensor knows that.

### First finding: the gaps are not where you would guess

Surveying the live API ([`evals/data-availability.md`](evals/data-availability.md))
turned up three kinds of gap, and the third is the one that can hurt someone:

1. **Absent.** No intake, no symptoms, no goals — and **WHOOP Age is not
   exposed at all**, despite being a headline number members see daily and ask
   about.
2. **Sparse.** Workout distance is populated in 6% of workouts. An answer is
   available some days and not others, with nothing signalling which.
3. **Present but wrong.** One 16-minute running workout reported a distance of
   179 metres. That is a GPS artifact, and nothing in the payload marks it as
   one. A coach reasoning from it will state something false about the member's
   fitness with complete confidence.

The third gap produces a rubric dimension a generic coach cannot even be tested
on, because it has no data to misread: **does the answer notice implausible
data rather than reasoning from it?**

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
