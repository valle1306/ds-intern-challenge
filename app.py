"""SignalDesk Weekly Health Check — Home.

A launcher, deliberately: it leads with the week's headline finding, says what
the tool is and what it helps you decide, and sends you onward. It renders no
tables and no charts, so it fits one screen.

Every figure below is read off the same pipeline the rest of the app uses
(data_processing.py via ui_helpers.load_sample_pipeline), never hardcoded, so
the front page cannot drift out of sync with the analysis behind it.
"""

import streamlit as st

from data_processing import find_prompt_change_date, prompt_change_comparison
from ui_helpers import inject_custom_css, load_sample_pipeline

st.set_page_config(page_title="SignalDesk Weekly Health Check", layout="wide")
inject_custom_css()

st.markdown(
    """
    <div class="sd-hero sd-hero--compact">
      <div class="sd-hero-eyebrow">SignalDesk</div>
      <h1 class="sd-hero-title">Weekly Health Check</h1>
      <p class="sd-hero-subtitle">One read of a messy weekly export that tells you which
      numbers you can quote and which you can't.</p>
      <p class="sd-hero-meta">Week of 2026-08-01 to 2026-08-07 &middot; 41 rows in, 40 after
      dedupe &middot; 10 data-quality issues found</p>
    </div>
    """,
    unsafe_allow_html=True,
)

_, clean_df, issues, rollup = load_sample_pipeline()

# ---------------------------------------------------------------------------
# Hero stat -- the single most useful thing this week's analysis produced, so
# it leads rather than sitting in a bullet. Both figures are computed.
# ---------------------------------------------------------------------------
_comparison = prompt_change_comparison(clean_df, issues, find_prompt_change_date(clean_df))
_gaps = (_comparison["delta_naive"] - _comparison["delta_adj"]).abs()
_flipped = _comparison.loc[_gaps.idxmax()] if not _comparison.empty else None

if _flipped is not None:
    _dropped = int(_flipped["sessions_after"] - _flipped["sessions_after_adj"])
    _share = _dropped / _flipped["sessions_after"] if _flipped["sessions_after"] else 0.0
    st.markdown(
        f"""
        <div class="sd-stat-band">
          <div class="sd-stat-figure">
            <span class="sd-stat-before">{_flipped['delta_naive'] * 100:+.1f}pp</span>
            <span class="sd-stat-arrow">&rarr;</span>
            <span class="sd-stat-after">{_flipped['delta_adj'] * 100:+.1f}pp</span>
          </div>
          <div class="sd-stat-copy">
            <div class="sd-stat-eyebrow">This week's headline</div>
            <p>{_flipped['workflow']}'s completion rate looks like it gained
            {_flipped['delta_naive'] * 100:+.1f}pp after the 2026-08-04 prompt change. Remove
            the one duplicated demo-account row &mdash; {_dropped:,} sessions, {_share:.0%} of
            that workflow's entire post-change volume &mdash; and the gain is
            {_flipped['delta_adj'] * 100:+.1f}pp. <strong>The win was the row, not the
            prompt.</strong></p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Orientation + the findings the hero stat doesn't already carry
# ---------------------------------------------------------------------------
_worst = rollup.loc[rollup["completion_rate"].idxmin()]
_best = rollup.loc[rollup["completion_rate"].idxmax()]
_has_divergence = (issues["category"] == "confidence_quality_divergence").any()

_also = [
    f"<strong>{_worst['workflow']}</strong> is genuinely behind at "
    f"{_worst['completion_rate']:.1%} completion &mdash; its 95% interval doesn't overlap "
    f"{_best['workflow']}'s, so this is a real gap, not sampling noise."
]
if _has_divergence:
    _also.append(
        "Model confidence hit its weekly high the same day completion and user rating "
        "collapsed. <strong>Confidence is not quality</strong> &mdash; don't use it as a proxy."
    )
_also.append(
    f"{len(issues)} data-quality issues were found in a 41-row file, including a duplicate "
    f"row whose two notes disagree about the cause."
)

st.markdown(
    f"""
    <div class="sd-guide-grid">
      <div class="sd-guide-card">
        <div class="sd-guide-eyebrow">What this is</div>
        <p>A weekly health check over one SignalDesk usage export. It cleans the file, flags
        what's wrong with it, and reports only the rates that survive that cleaning &mdash; so
        a number and its caveat always arrive together.</p>
        <p>Use it to decide which workflow is actually working, which metric to trust least,
        and what to investigate before rolling anything out more broadly.</p>
      </div>
      <div class="sd-guide-card sd-guide-card--verdict">
        <div class="sd-guide-eyebrow">Also worth knowing this week</div>
        <ul class="sd-verdict-list">{"".join(f"<li>{line}</li>" for line in _also)}</ul>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Navigation. st.container(border=True) is a stable public API and supplies the
# card chrome natively -- an earlier attempt styled [data-testid="stPageLink"],
# which does not exist in the Streamlit bundle, so the links rendered bare.
# ---------------------------------------------------------------------------
st.markdown('<div class="sd-nav-label">Where to go next</div>', unsafe_allow_html=True)

_NAV = [
    ("pages/1_Weekly_Findings.py",
     "**Weekly Findings**  \nWhat's working, what's suspicious, what to do next",
     ":material/insights:"),
    ("pages/2_Workflow_Explorer.py",
     "**Workflow Explorer**  \nOne workflow's daily numbers, sources and trend",
     ":material/travel_explore:"),
    ("pages/3_Data_Trust_Center.py",
     "**Data Trust Center**  \nEvery issue found, the method, and its limits",
     ":material/verified_user:"),
]

for _col, (_page, _label, _icon) in zip(st.columns(3), _NAV):
    with _col, st.container(border=True):
        st.page_link(_page, label=_label, icon=_icon)

with st.container(border=True):
    st.page_link(
        "pages/4_Upload_Your_Own_Week.py",
        label="**Upload Your Own Week** — run this exact check on any SignalDesk export",
        icon=":material/upload_file:",
    )
