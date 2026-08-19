"""SignalDesk — Upload Your Own Week.

Runs the exact same cleaning / issue-detection / rollup pipeline used on the
bundled sample data, but on a user-uploaded CSV. Nothing is persisted --
everything here is recomputed fresh in this session. Presentation only; all
logic lives in data_processing.py.
"""

import streamlit as st

from data_processing import (
    REQUIRED_COLUMNS,
    find_prompt_change_date,
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
    render_prompt_change_panel,
    render_rate_comparison_chart,
    render_table,
    with_ci_display,
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
# KPI strip stays above the tabs as persistent context for the file just loaded
# ---------------------------------------------------------------------------
_sessions_sum = clean_df["sessions"].sum()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Sessions analyzed", f"{int(_sessions_sum):,}")
col2.metric(
    "Overall completion rate",
    f"{(clean_df['completed'].sum() / _sessions_sum if _sessions_sum else 0.0) * 100:.1f}%",
)
col3.metric("Issues flagged", f"{len(issues):,}")
col4.metric("Duplicate rows removed", f"{raw.shape[0] - clean_df.shape[0]:,}")

tab_summary, tab_prompt, tab_issues = st.tabs(["Summary", "Prompt change", "Issues"])

with tab_summary:
    headline = build_confidence_quality_headline(clean_df, issues)
    if headline:
        st.warning(headline)
    else:
        st.success("No confidence-vs-quality divergence detected in this file.")

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
    # row_count is kept here, unlike on Weekly Findings: for an unknown file it
    # is real diagnostic context for how much data backs each row.
    _display_rollup = with_ci_display(rollup)
    render_table(
        _display_rollup,
        fmt={k: v for k, v in _fmt_all.items() if k in _display_rollup.columns},
    )
    render_rate_comparison_chart(rollup)

with tab_prompt:
    # Self-gating: renders nothing when this file has no "new prompt version
    # started" note, so an ordinary week gets an explanation instead of a blank.
    if find_prompt_change_date(clean_df) is None:
        st.info(
            "No prompt-change analysis for this file: no row's `notes` mention a new prompt "
            "version, so there is no before/after boundary to compare across."
        )
    else:
        render_prompt_change_panel(clean_df, issues)

with tab_issues:
    render_issues_panel(issues)
