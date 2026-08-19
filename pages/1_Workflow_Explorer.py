"""SignalDesk Workflow Explorer — Streamlit UI.

Presentation only. All cleaning / issue-detection / rollup logic lives in
data_processing.py (via ui_helpers.load_sample_pipeline); this file just
renders one workflow's slice of that pipeline.
"""

import streamlit as st

from ui_helpers import (
    inject_custom_css,
    load_sample_pipeline,
    render_change_point_note,
    render_concern_tag,
    render_daily_trend,
    render_issues_panel,
    render_table,
    source_level_rollup,
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SignalDesk · Workflow Explorer", layout="wide")
inject_custom_css()
st.title("Workflow Explorer")
st.caption("Drill into one workflow's daily numbers, trend, and issues.")

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
raw, clean_df, issues, rollup = load_sample_pipeline()

# ---------------------------------------------------------------------------
# Workflow picker
# ---------------------------------------------------------------------------
selected = st.selectbox("Workflow", ["Lead summary", "Reply draft", "Feedback clustering"])

_WORKFLOW_INFO = {
    "Lead summary": (
        "Sales",
        "Helps Sales summarize inbound lead context before follow-up.",
    ),
    "Reply draft": (
        "Support",
        "Helps Support draft responses that a human can edit or approve.",
    ),
    "Feedback clustering": (
        "Product",
        "Helps Product group user feedback into rough themes.",
    ),
}
_team, _description = _WORKFLOW_INFO[selected]
st.caption(f"{_team} · {_description}")

# ---------------------------------------------------------------------------
# Filter to the selected workflow
# ---------------------------------------------------------------------------
wf_clean = clean_df[clean_df["workflow"] == selected]
wf_rollup = rollup[rollup["workflow"] == selected]
wf_issues = issues[issues["workflow"] == selected]

render_concern_tag(wf_issues)

# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
if not wf_rollup.empty:
    _r = wf_rollup.iloc[0]
    col1.metric("Completion rate", f"{_r['completion_rate'] * 100:.1f}%")
    col2.metric("Acceptance rate", f"{_r['acceptance_rate'] * 100:.1f}%")
    col3.metric("Flag rate", f"{_r['flag_rate'] * 100:.1f}%")
    col4.metric("Total sessions", f"{int(_r['sessions_total']):,}")
else:
    col1.metric("Completion rate", "—")
    col2.metric("Acceptance rate", "—")
    col3.metric("Flag rate", "—")
    col4.metric("Total sessions", "—")

# ---------------------------------------------------------------------------
# Daily detail
# ---------------------------------------------------------------------------
st.subheader("Daily detail")
render_table(
    wf_clean.sort_values("date"),
    fmt={
        "completion_rate": "{:.1%}",
        "acceptance_rate": "{:.1%}",
        "flag_rate": "{:.1%}",
    },
)

# ---------------------------------------------------------------------------
# By source
# ---------------------------------------------------------------------------
st.subheader("By source")
_src = source_level_rollup(wf_clean).drop(columns=["team", "workflow"])
render_table(
    _src,
    fmt={
        "completion_rate": "{:.1%}",
        "acceptance_rate": "{:.1%}",
        "flag_rate": "{:.1%}",
        "sessions_total": "{:,.0f}",
    },
)
st.caption(
    "Same completed-weighted formulas as the workflow-level rollup, one level deeper by "
    "source -- a workflow's blended number can hide real differences in how its sessions "
    "come in."
)

# ---------------------------------------------------------------------------
# Daily trend
# ---------------------------------------------------------------------------
st.subheader("Daily trend")
render_daily_trend(
    wf_clean,
    groupby_col="source",
    empty_message=(
        "No daily trend to show for this workflow — there's no "
        "completed/sessions data to compute a completion rate from."
    ),
)
if selected == "Reply draft":
    render_change_point_note(wf_clean, source="queue", change_date="2026-08-07")

# ---------------------------------------------------------------------------
# Issues for this workflow
# ---------------------------------------------------------------------------
st.subheader("Issues for this workflow")
render_issues_panel(
    wf_issues,
    empty_message="No issues detected for this workflow this week.",
)
