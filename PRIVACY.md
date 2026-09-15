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

**Always:** requests to the WHOOP API, to fetch your own data, authorised by
you. Nothing else is sent anywhere by default.

**Only if you configure a hosted model:** evaluating coaching advice requires
asking a model to produce that advice, and that model can run in one of two
places.

- **Locally** (the default — an open-weights model on your own machine): no
  health data leaves your computer at any point. The WHOOP API call is the only
  outbound request the tool makes.
- **Through a hosted provider**, if you choose to configure one: prompts sent to
  that provider may contain your health metrics and log entries. That is a real
  transfer of health data to a third party, governed by their privacy terms
  rather than this one. It happens only if you supply an API key for such a
  provider; with no key configured, it cannot happen.

Nothing is sold, shared, or transmitted to anyone else under either setup.

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
