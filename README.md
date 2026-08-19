# Submission README

## Track Chosen

Track A — Fictional Domain Packet (SignalDesk).

## What I Built

A four-page Streamlit tool, "SignalDesk Weekly Health Check," styled with a custom card-based theme instead of a bare default page. Overview shows the headline finding, KPIs, concern tags, the rollup, a rate chart, and a prioritized "Bottom line." Workflow Explorer drills into one workflow's daily data, a source-level rollup, a change-point note, trend, and filtered issues. Data Trust Center lists every detected issue plus the full methodology and term definitions. Upload Your Own Week runs any same-schema CSV through the identical pipeline, with a friendly error on bad columns, so it works on this week's data or a reader's own export.

## Who It Is For

A SignalDesk product lead deciding whether to trust this week's numbers.

## Data Or Source Used

`sample-data/product_usage_events.csv` — fictional, provided with the challenge; 41 rows, 2026-08-01 to 2026-08-07.

## Assumptions I Made

completion_rate = completed/sessions; acceptance_rate = accepted_output/completed; flag_rate = flagged_for_review/completed. Weekly figures are completed-weighted, not a simple mean of daily rows. Exact duplicates collapsed; team-casing variants merged to majority spelling. Blanks and literal "n/a" are both treated as missing, not zero.

## Data Issues Or Caveats I Noticed

Duplicate row (2026-08-05, Sales/Lead summary/email) with conflicting notes. A non-numeric "n/a" confidence value; a blank rating; a "product"/"Product" casing split. A 2.6x spike on 2026-08-05 tied to a demo-account note. 2026-08-07: Support/Reply draft/queue's completion rate and rating crashed the same day confidence hit its weekly high and the review policy changed mid-day — confidence is not quality. Two expected rows missing that day. Two rows marked "small sample."

## What I Would Do Next With More Time

Confirm the 2026-08-05 spike/duplicate and 2026-08-07 policy change/missing rows against the real source; add week-over-week comparison once more weeks exist.
