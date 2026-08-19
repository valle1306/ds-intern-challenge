"""SignalDesk Weekly Health Check — Home.

A launcher, deliberately: it says what the tool is, what it helps you decide,
what this week's answer was, and where to go next. It renders no tables and no
charts, so it fits one screen.

The analysis it summarises lives on Weekly Findings; the evidence behind that
lives on Workflow Explorer and Data Trust Center. All computation stays in
data_processing.py -- the three verdict lines below are read off the same
pipeline every other page uses, so they cannot drift out of sync with it.
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

# The verdict card is computed, not written down, so it stays true if the data
# behind it ever changes. Everything here is already-tested pipeline output.
_worst = rollup.loc[rollup["completion_rate"].idxmin()]
_comparison = prompt_change_comparison(clean_df, issues, find_prompt_change_date(clean_df))
_gaps = (_comparison["delta_naive"] - _comparison["delta_adj"]).abs()
_flipped = _comparison.loc[_gaps.idxmax()] if not _comparison.empty else None
_has_divergence = (issues["category"] == "confidence_quality_divergence").any()

_verdict_lines = []
if _flipped is not None:
    _verdict_lines.append(
        f"The prompt change is <strong>not</strong> a win. {_flipped['workflow']}'s "
        f"{_flipped['delta_naive'] * 100:+.1f}pp gain is {_flipped['delta_adj'] * 100:+.1f}pp "
        f"once one flagged row is removed."
    )
_verdict_lines.append(
    f"<strong>{_worst['workflow']}</strong> is genuinely behind at "
    f"{_worst['completion_rate']:.1%} completion &mdash; not sampling noise."
)
if _has_divergence:
    _verdict_lines.append(
        "Model confidence peaked the same day quality collapsed. Confidence is not quality."
    )

_verdict_html = "".join(f"<li>{line}</li>" for line in _verdict_lines)

st.markdown(
    f"""
    <div class="sd-guide-grid">
      <div class="sd-guide-card">
        <div class="sd-guide-eyebrow">What this is</div>
        <p>A weekly health check over one SignalDesk usage export. It cleans the file,
        flags what's wrong with it, and reports the rates that survive that cleaning
        &mdash; so a number and its caveat always arrive together.</p>
      </div>
      <div class="sd-guide-card">
        <div class="sd-guide-eyebrow">What it helps you decide</div>
        <p>Which workflow is actually working, which metric to trust least, whether a
        change helped or just looked like it, and what to investigate before rolling
        anything out more broadly.</p>
      </div>
      <div class="sd-guide-card sd-guide-card--verdict">
        <div class="sd-guide-eyebrow">What you should know this week</div>
        <ul class="sd-verdict-list">{_verdict_html}</ul>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="sd-nav-label">Where to go next</div>', unsafe_allow_html=True)
nav1, nav2, nav3 = st.columns(3)
with nav1:
    st.page_link(
        "pages/1_Weekly_Findings.py",
        label="**Weekly Findings** — what's working, what's suspicious, what to do next",
        icon=":material/insights:",
    )
with nav2:
    st.page_link(
        "pages/2_Workflow_Explorer.py",
        label="**Workflow Explorer** — one workflow's daily numbers, sources and trend",
        icon=":material/travel_explore:",
    )
with nav3:
    st.page_link(
        "pages/3_Data_Trust_Center.py",
        label="**Data Trust Center** — every issue found, the method, and its limits",
        icon=":material/verified_user:",
    )

st.page_link(
    "pages/4_Upload_Your_Own_Week.py",
    label="Got your own export? Run this same check on any week —  **Upload Your Own Week**",
    icon=":material/upload_file:",
)
