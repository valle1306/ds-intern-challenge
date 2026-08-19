# Submission README

**[▶ Live app](https://ds-intern-challenge-833dovxbxed3jsnuf5jgwh.streamlit.app/)** · [![verify](https://github.com/valle1306/ds-intern-challenge/actions/workflows/verify.yml/badge.svg)](https://github.com/valle1306/ds-intern-challenge/actions/workflows/verify.yml)

## Track Chosen

Track A: Fictional Domain Packet (SignalDesk).

## What I Built

**SignalDesk Weekly Health Check** reads one messy usage export and reports only the rates that survive cleaning. Every number arrives with its caveat.

A guided home leads to four tabbed pages: Findings, Explorer, Trust Center, Upload. They share one pipeline, and each view fits a screen.

The tool detects duplicates, invalid literals, missing rows, label drift, suspicious spikes, and confidence/quality divergence. It reports completed-weighted rates with 95% Wilson intervals, and compares before and after a prompt change both naively and with flagged rows removed.

## Who It Is For

A product lead deciding whether to trust this week's numbers.

## Run It

```
pip install -r requirements.txt
streamlit run app.py
python verify_app.py    # end-to-end checks
```

## Data Or Source Used

`sample-data/product_usage_events.csv`. Fictional, shipped with the challenge. 41 rows, 2026-08-01 to 08-07.

## Assumptions I Made

completion_rate = completed/sessions; acceptance_rate = accepted_output/completed; flag_rate = flagged_for_review/completed. Rates are completed-weighted, never averages of daily rates. Duplicates collapsed. Team casing merged to majority spelling. Blank and literal `n/a` are missing, not zero.

## Data Issues Or Caveats I Noticed

Ten flagged: a duplicate 08-05 row whose notes disagree, a 2.6x spike that day, an `n/a` confidence, a blank rating, a `product`/`Product` split, two rows missing on 08-07, two small-sample rows. On 08-07 Support's completion and rating collapsed as confidence peaked. Confidence is not quality. One week, no control group, so nothing here is causal.

## What I Would Do Next With More Time

Confirm the 08-05 spike and 08-07 policy change at the source, then re-run the comparison. Add week-over-week baselines so a spike is measured against history, not asserted.
