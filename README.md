# Submission README

## Track Chosen

Track A — Fictional Domain Packet (SignalDesk).

## What I Built

A Streamlit view, "SignalDesk Weekly Health Check": a cleaned/deduped weekly rollup per workflow (completion rate, acceptance rate, flag rate, avg minutes saved, confidence, rating) beside a "Don't trust this blindly" panel listing the raw export's data-quality issues, so a reader can judge whether this week's numbers are safe to quote.

## Who It Is For

A SignalDesk product lead deciding whether to trust this week's usage numbers.

## Data Or Source Used

`sample-data/product_usage_events.csv` — fictional, provided with the challenge; 41 rows, 2026-08-01 to 2026-08-07.

## Assumptions I Made

- completion_rate = completed/sessions; acceptance_rate = accepted_output/completed; flag_rate = flagged_for_review/completed.
- Weekly figures are completed-weighted, not a simple mean of daily rows.
- Exact-duplicate rows collapsed; "product"/"Product" casing merged into one team.
- Blank cells and literal "n/a" both treated as missing, not zero.

## Data Issues Or Caveats I Noticed

- Duplicate row (2026-08-05, Sales/Lead summary/email) with conflicting notes ("traffic spike from demo account" vs "duplicate export row").
- Literal "n/a" in a numeric confidence column; one blank rating; a team-casing split ("product" vs "Product").
- ~2.6x session spike on 2026-08-05 for Sales/Lead summary/email tied to a "demo account" note, unexplained after removing the duplicate.
- 2026-08-07: Support/Reply draft/queue's completion rate, acceptance rate, and rating crashed the day confidence hit its weekly high (0.91) and the review policy changed mid-day — confidence is not quality.
- Two rows missing on 2026-08-07 (Sales/Lead summary/manual, Support/Reply draft/manual), present other days.
- Two rows marked "small sample" by the source.

## What I Would Do Next With More Time

Confirm the 2026-08-05 spike/duplicate against the real source; ask Support about the 2026-08-07 policy change and missing rows; add a week-over-week trend once more data exists.
