# Submission README

[![verify](https://github.com/valle1306/ds-intern-challenge/actions/workflows/verify.yml/badge.svg)](https://github.com/valle1306/ds-intern-challenge/actions/workflows/verify.yml)

## Track Chosen

Track A — Fictional Domain Packet (SignalDesk).

## What I Built

**SignalDesk Weekly Health Check** — one Streamlit tool answering a product lead's three questions: what's working, what looks suspicious, what to look at next. Drill-down, methodology, and upload pages share that pipeline.

The finding: the 2026-08-04 prompt change *looks* like a +4.4pp completion win for Lead summary. Drop the one duplicated demo-account row — 140 sessions, 36% of its post-change volume — and it's **+0.0pp**. Reply draft's apparent −5.6pp is −3.1pp without the policy-change row. Only Feedback clustering's decline survives — the one workflow measurably behind (95% CI 60.0–72.7% vs Lead summary's 77.3–83.7%, non-overlapping).

## Who It Is For

A product lead deciding whether to trust this week's numbers.

## Run It

```
pip install -r requirements.txt
streamlit run app.py
python verify_app.py    # end-to-end checks
```

## Data Or Source Used

`sample-data/product_usage_events.csv` — fictional, shipped with the challenge; 41 rows, 2026-08-01 to 08-07.

## Assumptions I Made

completion_rate = completed/sessions; acceptance_rate = accepted_output/completed; flag_rate = flagged_for_review/completed. Rates are completed-weighted, never an average of daily rates. Duplicates collapsed; team casing merged to majority spelling. Blank and literal `n/a` are missing, not zero.

## Data Issues Or Caveats I Noticed

Ten flagged: a duplicate 08-05 row whose notes disagree, a 2.6x spike the same day, an `n/a` confidence, a blank rating, a `product`/`Product` split, two rows missing on 08-07, two small-sample rows. On 08-07 Support's completion and rating collapsed as confidence peaked — confidence is not quality. One week, no control group: nothing here is causal.

## What I Would Do Next With More Time

Confirm the 08-05 spike and 08-07 policy change at the source, then re-run the prompt comparison. Add week-over-week baselines so "unusual" is measured, not asserted.
