# Backend Process: Portfolio Operations

The day-to-day partner workflow engines, so the Guide can explain health
scores, the LP digest, the sim queue, and slicing tools.

## Health score
A composite 0–100 per deal with a trend sparkline, blended from the deal's
signals (variance to plan, covenant posture, alert load, data freshness).
Read it as a triage signal, not a valuation.

## Simulation queue
An in-memory, single-worker queue runs Monte Carlo / analysis jobs. Jobs are
lost on restart — fine for partner-driven reruns (just click rerun), but
critical/cron runs should go via the CLI.

## LP digest
Assembles a partner-ready portfolio update (performance, holdings,
distributions) from portfolio/fund data.

## Slicing & workflow
Cohorts, watchlists, owners, deadlines, notes (searchable/taggable), tags —
all over the live store — let a partner organize and monitor the book.

## How to read it
- These run on whatever is in the store; figures are as current as the latest
  snapshots / entered data, not real-time market values.
