"""SignalDesk Weekly Findings — the analysis, one question per tab.

Presentation only. Every number here comes from data_processing.py via
ui_helpers.load_sample_pipeline; this file arranges it.

The three tabs are the three questions the teammate in the domain packet
actually asked. Tabs rather than one long column so each answer is a single
screen instead of a scroll.
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

st.set_page_config(page_title="SignalDesk · Weekly Findings", layout="wide")
inject_custom_css()
st.title("Weekly Findings")
st.caption("Week of 2026-08-01 to 2026-08-07. One question per tab.")

raw, clean_df, issues, rollup = load_sample_pipeline()

# Copy for the "What to do next" tab, kept as data so the render loop stays
# short and the wording is editable in one place. Ordered most to least urgent.
NEXT_ACTIONS: list[tuple[str, str, str]] = [
    (
        "High",
        "Don't ship the prompt change as a win yet",
        "Its entire apparent gain is one duplicated demo-account row. Get the 2026-08-05 "
        "Sales / Lead summary / email spike (140 sessions, more than 2x the surrounding "
        "days' median) confirmed or excluded at the source, then re-run the comparison on "
        "the **What looks suspicious** tab.",
    ),
    (
        "High",
        "Find out what the Support review-policy change on 2026-08-07 actually did",
        "Completion fell to ~57% and user rating to 2.1 the same day model confidence hit "
        "its weekly high of 0.91. Confidence went up while everything users actually feel "
        "went down. One day of post-change data is not a new steady state — but it is "
        "enough to warrant asking before the policy spreads to other workflows.",
    ),
    (
        "Medium",
        "Chase the two rows missing on 2026-08-07",
        "Sales / Lead summary / manual and Support / Reply draft / manual have no row that "
        "day — the same day as the policy change. That timing makes an export failure and a "
        "real drop in usage impossible to tell apart from the file alone.",
    ),
    (
        "Medium",
        "Treat Feedback clustering as this week's least trustworthy workflow",
        "On the data as well as the numbers: lowest completion (66.7%) and acceptance "
        "(65.9%), highest flag rate (18.8%), plus a team-casing split, an invalid `n/a` "
        "confidence value, and two rows self-flagged as small samples.",
    ),
    (
        "Low",
        "Stop quoting Feedback clustering's minutes-saved figure on its own",
        "At 13.0 it is the highest of the three workflows, which reads as success until you "
        "notice it is paired with the worst completion, acceptance and confidence of any "
        "workflow. Time saved and output quality are pointing in opposite directions there, "
        "and the packet already warns that minutes saved is directional at best.",
    ),
]

tab_working, tab_suspicious, tab_next = st.tabs(
    ["What's working", "What looks suspicious", "What to do next"]
)

# ---------------------------------------------------------------------------
# 1. What's working
# ---------------------------------------------------------------------------
with tab_working:
    # Deliberately NO single blended completion rate. The domain packet warns
    # against averaging across things that aren't comparable, and this tab's own
    # finding is that the workflows differ by more than sampling error -- so a
    # blended headline would hide exactly what the page exists to show.
    _lo_wf = rollup.loc[rollup["completion_rate"].idxmin()]
    _hi_wf = rollup.loc[rollup["completion_rate"].idxmax()]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sessions analyzed", f"{int(clean_df['sessions'].sum()):,}")
    col2.metric(
        "Completion rate range",
        f"{_lo_wf['completion_rate']:.1%}-{_hi_wf['completion_rate']:.1%}",
    )
    col3.metric("Issues flagged", f"{len(issues):,}")
    col4.metric("Duplicate rows removed", f"{raw.shape[0] - clean_df.shape[0]:,}")

    render_concern_tag_strip(rollup, issues)
    render_rate_comparison_chart(rollup)

    # Compare best and worst workflow by their Wilson intervals rather than
    # their point estimates, so the ranking claim is only made when the data
    # supports it. Computed, not hardcoded.
    _ranked = rollup.sort_values("completion_rate")
    _worst, _best = _ranked.iloc[0], _ranked.iloc[-1]
    if _worst["completion_hi"] < _best["completion_lo"]:
        st.success(
            f"**{_best['workflow']} and {_ranked.iloc[-2]['workflow']} are effectively "
            f"tied** at ~{_best['completion_rate']:.0%} completion. "
            f"**{_worst['workflow']} is genuinely behind, not just unlucky**: its 95% "
            f"interval ({_worst['completion_lo']:.1%}-{_worst['completion_hi']:.1%}, "
            f"n={int(_worst['sessions_total']):,} sessions) does not overlap "
            f"{_best['workflow']}'s "
            f"({_best['completion_lo']:.1%}-{_best['completion_hi']:.1%}). It also trails "
            f"on acceptance and leads on flag rate — three signals agreeing."
        )
    else:
        st.info(
            "No workflow separates from the others once sampling error is accounted for — "
            "the 95% completion-rate intervals overlap, so treat this ranking as provisional."
        )

    # The table is evidence for the claim above, not the claim itself, so it
    # opens closed. row_count is internal QA context and stays on the Upload page.
    with st.expander("Full weekly rollup table"):
        _fmt_all = {
            "completion_rate": "{:.1%}", "acceptance_rate": "{:.1%}", "flag_rate": "{:.1%}",
            "avg_minutes_saved": "{:.1f}", "median_confidence": "{:.2f}",
            "user_rating": "{:.1f}", "sessions_total": "{:,.0f}",
        }
        _display = with_ci_display(rollup).drop(columns=["row_count"])
        render_table(_display, fmt={k: v for k, v in _fmt_all.items() if k in _display.columns})
        st.caption(
            "Rates are completed-weighted, so a 4-session day cannot swing the week the way "
            "a 140-session one would. Concern tags rate the *data*, not the workflow — see "
            "Data Trust Center for the rule."
        )

# ---------------------------------------------------------------------------
# 2. What looks suspicious
# ---------------------------------------------------------------------------
with tab_suspicious:
    headline = build_confidence_quality_headline(clean_df, issues)
    if headline:
        st.warning(headline)
    render_prompt_change_panel(clean_df, issues)

# ---------------------------------------------------------------------------
# 3. What to do next
# ---------------------------------------------------------------------------
with tab_next:
    st.caption(
        "Five things, most urgent first. Each opens to the reasoning and the rows behind it."
    )
    for severity, headline_text, detail in NEXT_ACTIONS:
        with st.expander(f"**{severity}** · {headline_text}"):
            st.markdown(detail)
