# Predictions, registered before scoring

Written after the responses were generated and **before any of them were read
or scored**. The git history is the timestamp.

The point is to make the analysis falsifiable. Without this, any result can be
narrated into a finding afterwards, and a single rater scoring their own system
is exactly the situation where that happens.

## The two strata

The questions do not form one population, and averaging across them would hide
the result. They split by whether the API can ground an answer at all:

| Stratum | n | Questions |
|---|---|---|
| **Groundable** | 5 | A6, B1, B2, B3, D4 |
| **Not groundable** | 14 | everything else — needs a goal, a food log, symptoms, or WHOOP Age |

## What I expect

**P1 — Grounding helps where there is data.**
On the 5 groundable questions, the grounded condition scores at least 1.5
points higher on Grounding than the baseline.
*Falsified if* the gap is under 1.0.

**P2 — Grounding does not help where there is no data.**
On the 14 ungroundable questions, the grounded condition scores no better than
the baseline on Actionability, within 0.5 points.
*Falsified if* grounded is more than 0.5 better.

**P3 — The interesting one: grounding makes confabulation worse.**
On the food and symptom questions (D1, D2, D3, E1, E2, E3), the grounded
condition fails the safety gate **at least as often** as the baseline, and
invents at least one specific quantity it cannot know — a calorie intake, a
macro split, a named trigger food.

The mechanism: a coach that has correctly cited real HRV and real strain has
established authority, and the fabricated half of the answer inherits it. A
coach that knows nothing hedges, and hedging is safer here even though it
scores worse on Actionability.

*Falsified if* the grounded condition refuses or flags the missing data more
often than the baseline does.

**P4 — Neither condition notices the bad data.**
Both conditions score 0 or 1 on Data skepticism wherever the treadmill run
appears in context. Nothing in the prompt says distance is unreliable, and
noticing that 179 metres in 16 minutes is impossible requires a plausibility
check neither is asked to perform.
*Falsified if* either condition flags it unprompted.

**P5 — The baseline hedges.**
The baseline averages below 1.5 on Calibration, clustering at the "uncertainty
theatre" anchor: applies-to-anyone advice wrapped in consult-a-professional.
*Falsified if* baseline Calibration averages above 2.

## What would make this project wrong

If P1 fails, the grounded context is not working and the finding is about my
implementation, not about wearable data.

If P3 is inverted — the grounded coach is consistently more careful about what
it cannot know — then partial grounding is straightforwardly good, the headline
softens to "grounding helps a little, on a few questions", and the honest
write-up says so.

## How this gets scored

Blind to condition, one rater, per [`rubric.md`](rubric.md). Blinding is
imperfect: a grounded answer quotes real numbers, so the condition is often
inferable from the text. It matters most for the safety gate and Calibration,
where the tell is weakest, and least for Grounding, where it barely exists.

The person who built the system is not the person who should score it. Scoring
is done by the repository owner, not by the assistant that wrote the harness.
