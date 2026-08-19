"""SignalDesk Weekly Health Check — Streamlit UI.

Presentation only. All cleaning / issue-detection / rollup logic lives in
data_processing.py; this file just renders it.
"""

import streamlit as st

from ui_helpers import (
    build_confidence_quality_headline,
    load_sample_pipeline,
    render_table,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SignalDesk Weekly Health Check", layout="wide")
st.title("SignalDesk Weekly Health Check")
st.markdown(
    "**The question:** Can this week's SignalDesk numbers be trusted, and what do they actually say?"
)
st.caption(
    "Week of 2026-08-01 to 2026-08-07 · cleaned & deduped · see the Data Trust Center page "
    "(sidebar) before quoting these numbers elsewhere"
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
raw, clean_df, issues, rollup = load_sample_pipeline()

# ---------------------------------------------------------------------------
# Headline warning — the confidence-vs-quality trap
# ---------------------------------------------------------------------------
headline = build_confidence_quality_headline(clean_df, issues)
if headline:
    st.warning(headline)

# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------
_total_sessions = int(clean_df["sessions"].sum())
_sessions_sum = clean_df["sessions"].sum()
_overall_completion_rate = (
    clean_df["completed"].sum() / _sessions_sum if _sessions_sum else 0.0
)
_n_issues = len(issues)
_dupes_removed = raw.shape[0] - clean_df.shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total sessions", f"{_total_sessions:,}")
col2.metric("Overall completion rate", f"{_overall_completion_rate * 100:.1f}%")
col3.metric("Issues flagged", f"{_n_issues:,}")
col4.metric("Duplicate rows removed", f"{_dupes_removed:,}")

# ---------------------------------------------------------------------------
# Weekly rollup by workflow
# ---------------------------------------------------------------------------
st.subheader("Weekly rollup by workflow")

_fmt_all = {
    "completion_rate": "{:.1%}",
    "acceptance_rate": "{:.1%}",
    "flag_rate": "{:.1%}",
    "avg_minutes_saved": "{:.1f}",
    "median_confidence": "{:.2f}",
    "user_rating": "{:.1f}",
    "sessions_total": "{:,.0f}",
}
_fmt = {k: v for k, v in _fmt_all.items() if k in rollup.columns}

render_table(rollup, fmt=_fmt)

# ---------------------------------------------------------------------------
# Bottom line: what to look at next
# ---------------------------------------------------------------------------
st.subheader("Bottom line: what to look at next")
st.markdown(
    """
1. **[High]** Confirm what the Support review-policy change on 2026-08-07 actually did — completion rate crashed to ~57% and rating to 2.1 the same day confidence hit its weekly high (0.91).
2. **[High]** Verify the 2026-08-05 Sales/Lead-summary/email session spike (140, more than 2x the surrounding days' median) against the source system — it coincides with a duplicate row whose two notes disagree on the cause.
3. **[Medium]** Find out why two expected rows are missing on 2026-08-07 (Sales/Lead summary/manual, Support/Reply draft/manual) — the same day as the policy change.
4. **[Medium]** Treat Product/Feedback clustering as this week's least trustworthy workflow — lowest completion rate (66.7%), highest flag rate (18.8%), plus a team-casing inconsistency, an invalid "n/a" confidence value, and two rows marked "small sample."
"""
)

# ---------------------------------------------------------------------------
# Nav pointer
# ---------------------------------------------------------------------------
st.info(
    "Drill into one workflow's daily numbers on **Workflow Explorer**, see every detected "
    "issue and the full methodology on **Data Trust Center**, or run this same check on your "
    "own week's export on **Upload Your Own Week** — all in the sidebar."
)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.caption(
    "Rates are completed-weighted (not a naive average of daily rows) so low-volume days "
    "don't count the same as high-volume days. completion_rate = completed/sessions, "
    "acceptance_rate = accepted_output/completed, flag_rate = flagged_for_review/completed. "
    "Full methodology, term definitions, and every detected issue live on the Data Trust "
    "Center page."
)
