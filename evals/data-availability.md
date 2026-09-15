# What the WHOOP API actually exposes

Measured against a live account on 15 September 2026, 30-day window, API v2,
with all six read scopes granted. This documents the API's shape, not anyone's
health data.

## Endpoints that work

All six resolve, including `/v2/recovery` — WHOOP's own docs describe recovery
as reachable "through the Cycle endpoints" and do not name a standalone path.
It exists.

| Endpoint | Returns |
|---|---|
| `/v2/cycle` | strain, kilojoules, average and max heart rate |
| `/v2/recovery` | recovery score, resting HR, HRV (rmssd), SpO2, skin temperature |
| `/v2/activity/sleep` | stage breakdown, sleep need, respiratory rate, performance, consistency, efficiency |
| `/v2/activity/workout` | strain, HR, HR-zone durations, kilojoules, sport name, sometimes distance |
| `/v2/user/profile/basic` | name, email, user id |
| `/v2/user/measurement/body` | height, weight, max heart rate |

## What is not there

**WHOOP Age is not exposed anywhere.** Not as an endpoint, not as a field on
profile or body measurement. A member sees this number in the app and can
reasonably ask what drives it, and no application built on the official API can
ground a single sentence of the answer.

**Nothing about intake.** No food, no calories consumed, no hydration. Energy
*expenditure* is estimated and returned; energy *intake* does not exist in the
model. Any question about deficit, surplus or diet is unanswerable from this
API alone.

**Nothing subjective.** No symptoms, soreness, mood, stress or illness. A
question like "I get painful bloating after certain meals" has no purchase on
any field here.

**No goals.** There is nowhere to say "I have a 10k in eight weeks." The API
describes what happened, never what the member is training for.

## What is there but unreliable

These matter more than the flat absences, because a naive consumer treats them
as trustworthy.

**Distance is sparse.** Populated in 7 of 115 workouts (6%) in the sample, and
`None` in the rest. `altitude_gain_meter` and `altitude_change_meter` follow
the same pattern.

**Distance can be wrong.** One 16-minute running workout reported 179 metres.
That is not a slow run, it is an artifact. A coach that reasons from it will
confidently tell a member something false about their fitness.

**Workout counts overstate training.** 115 workouts in 30 days sounds like an
athlete in heavy training. 97 of them were auto-detected walking. Distinguishing
intentional training from ambient movement is left entirely to the consumer, and
getting it wrong inverts the advice.

**`score_state` is an enum, not a guarantee.** Every record in this sample was
`SCORED`, but the field also carries `PENDING_SCORE` and `UNSCORABLE`. Code that
assumes a score is present will break on a night the strap was charging.

## Why this matters for the evaluation

Of the 18 questions in [`questions.md`](questions.md), this API can fully ground
7. The rest fail for one of three reasons, none of which a better model fixes:

1. The data does not exist in the API (intake, symptoms, goals, WHOOP Age).
2. The data exists but is sparse, so an answer is available some days and not
   others.
3. The data exists but is wrong, and nothing marks it as wrong.

The third is the dangerous one, and it produces a rubric dimension that a
generic coach cannot even be tested on: **does the answer notice implausible
data instead of reasoning from it?**
