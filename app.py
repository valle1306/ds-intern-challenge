"""SignalDesk Weekly Health Check — Streamlit UI.

Presentation only. All cleaning / issue-detection / rollup logic lives in
data_processing.py; this file just renders it.
"""

import streamlit as st

from ui_helpers import (
    build_confidence_quality_headline,
    inject_custom_css,
    load_sample_pipeline,
    render_concern_tag_strip,
    render_rate_comparison_chart,
    render_table,
)

st.set_page_config(page_title="SignalDesk Weekly Health Check", layout="wide")
inject_custom_css()

# ---------------------------------------------------------------------------
# Hero header -- one self-contained st.markdown call (HTML can't span
# multiple st.* calls)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="sd-hero">
      <div class="sd-hero-eyebrow">SignalDesk</div>
      <h1 class="sd-hero-title">Weekly Health Check</h1>
      <p class="sd-hero-subtitle"><strong>The question:</strong> Can this week's SignalDesk
      numbers be trusted, and what do they actually say?</p>
      <p class="sd-hero-meta">Week of 2026-08-01 to 2026-08-07 &middot; cleaned &amp; deduped
      &middot; see the Data Trust Center page (sidebar) before quoting these numbers elsewhere</p>
    </div>
    """,
    unsafe_allow_html=True,
)

raw, clean_df, issues, rollup = load_sample_pipeline()

headline = build_confidence_quality_headline(clean_df, issues)
if headline:
    st.warning(headline)

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

st.subheader("Weekly rollup by workflow")
render_concern_tag_strip(rollup, issues)
st.caption(
    "Elevated concern = at least one high-severity issue this week; Watch = medium but no "
    "high; Low concern = neither. Full methodology on the Data Trust Center page."
)
_fmt_all = {
    "completion_rate": "{:.1%}", "acceptance_rate": "{:.1%}", "flag_rate": "{:.1%}",
    "avg_minutes_saved": "{:.1f}", "median_confidence": "{:.2f}",
    "user_rating": "{:.1f}", "sessions_total": "{:,.0f}",
}
_fmt = {k: v for k, v in _fmt_all.items() if k in rollup.columns}
render_table(rollup, fmt=_fmt)
render_rate_comparison_chart(rollup)
st.caption("Product/Feedback clustering trails both other workflows on all three rates at once.")

st.subheader("Bottom line: what to look at next")
st.markdown("""
1. **[High]** Confirm what the Support review-policy change on 2026-08-07 actually did — completion rate crashed to ~57% and rating to 2.1 the same day confidence hit its weekly high (0.91).
2. **[High]** Verify the 2026-08-05 Sales/Lead-summary/email session spike (140, more than 2x the surrounding days' median) against the source system — it coincides with a duplicate row whose two notes disagree on the cause.
3. **[Medium]** Find out why two expected rows are missing on 2026-08-07 (Sales/Lead summary/manual, Support/Reply draft/manual) — the same day as the policy change.
4. **[Medium]** Treat Product/Feedback clustering as this week's least trustworthy workflow — lowest completion rate (66.7%), highest flag rate (18.8%), plus a team-casing inconsistency, an invalid "n/a" confidence value, and two rows marked "small sample."
5. **[Low]** Don't cite Product/Feedback clustering's avg_minutes_saved (12.99, the highest of the three workflows) as evidence of success on its own — it's paired with the lowest completion rate (66.7%), lowest acceptance rate (65.9%), and lowest confidence (0.61) of the three. Time saved and output quality are diverging for this workflow this week.
""")

st.info(
    "Drill into one workflow's daily numbers on **Workflow Explorer**, see every detected "
    "issue and the full methodology on **Data Trust Center**, or run this same check on your "
    "own week's export on **Upload Your Own Week** — all in the sidebar."
)

st.caption(
    "Rates are completed-weighted (not a naive average of daily rows) so low-volume days "
    "don't count the same as high-volume days. completion_rate = completed/sessions, "
    "acceptance_rate = accepted_output/completed, flag_rate = flagged_for_review/completed. "
    "Full methodology, term definitions, and every detected issue live on the Data Trust "
    "Center page."
)
