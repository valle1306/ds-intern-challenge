"""SignalDesk — Upload Your Own Week.

Runs the exact same cleaning / issue-detection / rollup pipeline used on the
bundled sample data, but on a user-uploaded CSV. Nothing is persisted --
everything here is recomputed fresh in this session. Presentation only; all
logic lives in data_processing.py.
"""

import streamlit as st

from data_processing import (
    REQUIRED_COLUMNS,
    clean,
    detect_issues,
    load_raw,
    validate_schema,
    weekly_rollup,
)
from ui_helpers import (
    build_confidence_quality_headline,
    inject_custom_css,
    render_concern_tag_strip,
    render_issues_panel,
    render_rate_comparison_chart,
    render_table,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SignalDesk · Upload Your Own Week", layout="wide")
inject_custom_css()
st.title("Upload Your Own Week")
st.markdown(
    "Run this exact same cleaning, issue-detection, and rollup pipeline on your own "
    "SignalDesk export. Nothing is stored — everything is recomputed fresh in this session."
)

uploaded = st.file_uploader("CSV file", type="csv")

if uploaded is None:
    st.info("Expected columns: " + ", ".join(REQUIRED_COLUMNS))
    st.caption("See the Overview page (sidebar) for this week's sample data.")
    st.stop()

# ---------------------------------------------------------------------------
# Load + validate schema
# ---------------------------------------------------------------------------
raw = load_raw(uploaded)
problems = validate_schema(raw)

if problems:
    st.error(
        "This file doesn't look like a SignalDesk export:\n"
        + "\n".join(f"- {p}" for p in problems)
    )
    st.stop()

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
try:
    clean_df = clean(raw)
    issues = detect_issues(raw, clean_df)
    rollup = weekly_rollup(clean_df, issues)
except Exception as e:
    st.error(
        "Couldn't process this file: dates and numeric columns need to be in a plain, "
        f"standard format (e.g. 2026-08-01). Underlying error: {e}"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Headline warning — the confidence-vs-quality trap
# ---------------------------------------------------------------------------
headline = build_confidence_quality_headline(clean_df, issues)
if headline:
    st.warning(headline)
else:
    st.success("No confidence-vs-quality divergence detected in this file.")

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
render_concern_tag_strip(rollup, issues)

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
render_rate_comparison_chart(rollup)

# ---------------------------------------------------------------------------
# Detected issues
# ---------------------------------------------------------------------------
st.subheader("Detected issues")
render_issues_panel(issues)
