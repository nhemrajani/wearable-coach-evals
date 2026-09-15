# Privacy Policy

**wearable-coach-evals** — a personal research project evaluating the quality of
AI coaching advice built on wearable data.

Last updated: 1 September 2026

## What this is

This is a single-user research tool, not a product or a service. It is run
locally by its author on their own computer, using their own WHOOP account. It
has no users other than the author, no servers, and no sign-up.

## What data it accesses

With your explicit authorisation through WHOOP's OAuth flow, and only for the
scopes you approve, it reads:

- Profile and body measurements (height, weight, max heart rate)
- Recovery data (recovery score, heart rate variability, resting heart rate)
- Sleep data (duration, stages, efficiency, performance)
- Cycles and strain
- Workouts

It also reads information you enter yourself in a local log: meals, symptoms,
and training goals. WHOOP does not capture these, and they never leave your
machine except as described below.

## Where it is stored

On your own computer, in files under your home directory. There is no cloud
database, no hosted backend, and nothing is uploaded to the author or to any
analytics service. The project's public code repository explicitly excludes all
data files.

## What leaves your computer

Two things, and only these:

1. **Requests to the WHOOP API**, to fetch your own data, authorised by you.
2. **Text sent to a large language model provider (Anthropic).** Evaluating
   coaching advice requires asking a model to produce that advice. Prompts may
   therefore contain your health metrics and log entries. This is the one way
   your data reaches a third party, and it is inherent to what the tool does. If
   you are not comfortable with that, do not use this tool.

Nothing is sold, shared, or transmitted to anyone else.

## Retention and deletion

Data stays on your machine until you delete it. Deleting the project's data
directory removes everything it holds. There is no copy anywhere else.

## Revoking access

You can revoke this application's access to your WHOOP data at any time from
your WHOOP account settings, without contacting anyone. Revocation immediately
stops any further access to your WHOOP data.

## Health disclaimer

This tool evaluates the quality of automated coaching advice. It is not medical
advice, it is not a medical device, and it is not a substitute for a qualified
clinician. Nothing it produces should be used to diagnose, treat, or make
decisions about a health condition.

## Contact

Questions about this policy: neeharika.hemrajani@yale.edu
