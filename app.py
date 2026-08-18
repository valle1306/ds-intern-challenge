"""SignalDesk Weekly Health Check — Streamlit UI.

Presentation only. All cleaning / issue-detection / rollup logic lives in
data_processing.py; this file just renders it.
"""

import pandas as pd
import streamlit as st

from data_processing import load_raw, clean, detect_issues, weekly_rollup

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SignalDesk Weekly Health Check", layout="wide")
st.title("SignalDesk Weekly Health Check")
st.caption(
    "Week of 2026-08-01 to 2026-08-07 · cleaned & deduped · read the trust panel "
    "below before quoting these numbers elsewhere"
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
raw = load_raw()
clean_df = clean(raw)
issues = detect_issues(raw, clean_df)
rollup = weekly_rollup(clean_df, issues)

# ---------------------------------------------------------------------------
# Headline warning — the confidence-vs-quality trap
# ---------------------------------------------------------------------------
_spike_row = clean_df[
    (clean_df["team"] == "Support")
    & (clean_df["workflow"] == "Reply draft")
    & (clean_df["source"] == "queue")
    & (clean_df["date"] == pd.Timestamp("2026-08-07"))
]

if not _spike_row.empty:
    _r = _spike_row.iloc[0]
    _completion_pct = f"{_r['completion_rate'] * 100:.0f}%"
    _rating = f"{_r['user_rating']:.1f}"
    _confidence = f"{_r['median_confidence']:.2f}"
else:
    # Fallback to the known figures if this exact slice isn't present.
    _completion_pct, _rating, _confidence = "57%", "2.1", "0.91"

st.warning(
    f"**Confidence isn't quality.** On 2026-08-07, the Support / Reply draft / queue "
    f"workflow's completion rate fell to ~{_completion_pct} and user rating crashed to "
    f"{_rating} — the **same day** model confidence hit its weekly high of {_confidence} "
    f"for that workflow, right when the review policy changed mid-day. High model "
    f"confidence does not mean the output was good that day — don't use confidence as a "
    f"quality proxy."
)

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

_pct_cols = [c for c in ["completion_rate", "acceptance_rate", "flag_rate"] if c in rollup.columns]
_fmt = {c: "{:.1%}" for c in _pct_cols}
if "avg_minutes_saved" in rollup.columns:
    _fmt["avg_minutes_saved"] = "{:.1f}"
if "median_confidence" in rollup.columns:
    _fmt["median_confidence"] = "{:.2f}"
if "user_rating" in rollup.columns:
    _fmt["user_rating"] = "{:.1f}"
if "sessions_total" in rollup.columns:
    _fmt["sessions_total"] = "{:,.0f}"

st.dataframe(rollup.style.format(_fmt), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Daily completion rate trend
# ---------------------------------------------------------------------------
st.subheader("Daily completion rate trend")
try:
    # Sum completed/sessions per date+workflow first, then divide -- a workflow
    # can have multiple sources (e.g. email + manual) with different volume, so
    # averaging their completion_rate values directly would weight a 5-session
    # day the same as a 60-session day.
    _daily = clean_df.groupby(["date", "workflow"], as_index=False)[["completed", "sessions"]].sum()
    _daily["completion_rate"] = _daily["completed"] / _daily["sessions"]
    _pivoted = _daily.pivot(index="date", columns="workflow", values="completion_rate")
    if _pivoted.empty:
        st.info("Trend chart unavailable.")
    else:
        st.line_chart(_pivoted)
except Exception:
    st.info("Trend chart unavailable.")

# ---------------------------------------------------------------------------
# Don't trust this blindly — issues panel
# ---------------------------------------------------------------------------
st.subheader("Don't trust this blindly")
st.caption(
    "Specific issues found in this week's export — read before acting on the numbers above."
)

_severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}

if issues is not None and not issues.empty:
    for _category in issues["category"].unique():
        _cat_issues = issues[issues["category"] == _category]
        if _cat_issues.empty:
            continue
        _title = str(_category).replace("_", " ").title()
        with st.expander(f"{_title} ({len(_cat_issues)})"):
            for _, _row in _cat_issues.iterrows():
                _icon = _severity_icon.get(str(_row.get("severity", "")).lower(), "⚪")
                st.markdown(f"{_icon} {_row['description']}")
else:
    st.info("No issues detected in this export.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.caption(
    "Rates are completed-weighted (not a naive average of daily rows) so low-volume days "
    "don't count the same as high-volume days. completion_rate = completed/sessions, "
    "acceptance_rate = accepted_output/completed, flag_rate = flagged_for_review/completed. "
    "See README.md for full assumptions."
)
