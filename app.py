"""SignalDesk Weekly Health Check — Streamlit UI (Overview page).

Presentation only. All cleaning / issue-detection / rollup / statistics logic
lives in data_processing.py; this file just renders it.

The page is deliberately ordered around the three questions the teammate in
the domain packet actually asked -- what's working, what looks suspicious,
what should we look at next -- rather than around the shape of the data.
"""

import streamlit as st

from ui_helpers import (
    build_confidence_quality_headline,
    inject_custom_css,
    load_sample_pipeline,
    render_concern_tag_strip,
    render_prompt_change_panel,
    render_rate_comparison_chart,
    render_table,
    with_ci_display,
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
      <p class="sd-hero-subtitle"><strong>The short answer:</strong> two of the three
      workflows are performing about equally well and the third is measurably behind &mdash;
      but this week's two most quotable numbers, the prompt change &ldquo;working&rdquo; and
      Support's record model confidence, are both artifacts. Neither should leave this page
      uncaveated.</p>
      <p class="sd-hero-meta">Week of 2026-08-01 to 2026-08-07 &middot; 41 rows in, 40 after
      dedupe &middot; 10 data-quality issues found &middot; every number below is traceable on
      the Data Trust Center page</p>
    </div>
    """,
    unsafe_allow_html=True,
)

raw, clean_df, issues, rollup = load_sample_pipeline()

# ---------------------------------------------------------------------------
# 1. What's working
# ---------------------------------------------------------------------------
st.subheader("1. What's working")

_total_sessions = int(clean_df["sessions"].sum())
_sessions_sum = clean_df["sessions"].sum()
_overall_completion_rate = (
    clean_df["completed"].sum() / _sessions_sum if _sessions_sum else 0.0
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total sessions", f"{_total_sessions:,}")
col2.metric("Overall completion rate", f"{_overall_completion_rate * 100:.1f}%")
col3.metric("Issues flagged", f"{len(issues):,}")
col4.metric("Duplicate rows removed", f"{raw.shape[0] - clean_df.shape[0]:,}")

render_concern_tag_strip(rollup, issues)
st.caption(
    "Elevated concern = at least one high-severity issue this week; Watch = medium but no "
    "high; Low concern = neither. The tag rates the *data*, not the workflow."
)

_fmt_all = {
    "completion_rate": "{:.1%}", "acceptance_rate": "{:.1%}", "flag_rate": "{:.1%}",
    "avg_minutes_saved": "{:.1f}", "median_confidence": "{:.2f}",
    "user_rating": "{:.1f}", "sessions_total": "{:,.0f}",
}
_display_rollup = with_ci_display(rollup)
render_table(_display_rollup, fmt={k: v for k, v in _fmt_all.items() if k in _display_rollup.columns})
render_rate_comparison_chart(rollup)

# Compare the best and worst workflow by completion rate using their Wilson
# intervals rather than their point estimates, so the ranking claim below is
# only made when the data actually supports it. Computed, not hardcoded.
_ranked = rollup.sort_values("completion_rate")
_worst, _best = _ranked.iloc[0], _ranked.iloc[-1]
if _worst["completion_hi"] < _best["completion_lo"]:
    st.caption(
        f"**{_best['workflow']} and {_ranked.iloc[-2]['workflow']} are effectively tied** at "
        f"~{_best['completion_rate']:.0%} completion. **{_worst['workflow']} is genuinely "
        f"behind, not just unlucky**: its 95% interval "
        f"({_worst['completion_lo']:.1%}-{_worst['completion_hi']:.1%}, "
        f"n={int(_worst['sessions_total']):,} sessions) does not overlap "
        f"{_best['workflow']}'s ({_best['completion_lo']:.1%}-{_best['completion_hi']:.1%}). "
        f"It also trails on acceptance and leads on flag rate — three signals agreeing, which "
        f"is why this is the one ranking claim on the page worth acting on."
    )
else:
    st.caption(
        "No workflow separates from the others once sampling error is accounted for — the "
        "95% completion-rate intervals overlap, so treat this week's ranking as provisional."
    )

# ---------------------------------------------------------------------------
# 2. What looks suspicious
# ---------------------------------------------------------------------------
st.subheader("2. What looks suspicious")

headline = build_confidence_quality_headline(clean_df, issues)
if headline:
    st.warning(headline)

render_prompt_change_panel(clean_df, issues)

# ---------------------------------------------------------------------------
# 3. What to look at next
# ---------------------------------------------------------------------------
st.subheader("3. What to look at next")
st.markdown("""
1. **[High]** **Don't ship the prompt change as a win yet.** Its entire apparent gain is one
   duplicated demo-account row. Get the 2026-08-05 Sales/Lead-summary/email spike (140 sessions,
   >2x the surrounding days) confirmed or excluded at the source, then re-run this comparison.
2. **[High]** **Find out what the Support review-policy change on 2026-08-07 actually did.**
   Completion fell to ~57% and rating to 2.1 the same day model confidence hit its weekly high
   (0.91). Confidence went up while everything users feel went down.
3. **[Medium]** **Chase the two rows missing on 2026-08-07** (Sales/Lead summary/manual,
   Support/Reply draft/manual) — same day as the policy change, which makes an export failure
   and a real usage drop hard to tell apart.
4. **[Medium]** **Treat Feedback clustering as this week's least trustworthy workflow**, on the
   data as well as the numbers: lowest completion (66.7%) and acceptance (65.9%), highest flag
   rate (18.8%), plus a team-casing split, an invalid `n/a` confidence value, and two rows
   self-flagged as small samples.
5. **[Low]** **Stop quoting Feedback clustering's `avg_minutes_saved` (13.0, the highest of the
   three) on its own.** It's paired with the worst completion, acceptance, and confidence of any
   workflow. Time saved and output quality are pointing in opposite directions there.
""")

st.info(
    "Drill into one workflow's daily numbers on **Workflow Explorer**, see every detected "
    "issue and the full methodology on **Data Trust Center**, or run this same check on your "
    "own export on **Upload Your Own Week** — all in the sidebar."
)
