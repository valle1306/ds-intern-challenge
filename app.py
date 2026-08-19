"""SignalDesk Weekly Health Check — Home.

A launcher: it says what the tool does, offers this sample week's findings on
demand, and sends you onward. It renders no tables and no charts, so it fits
one screen.

Built from native Streamlit containers rather than custom HTML cards. An
earlier version styled its own markup and shipped unstyled without failing any
test, so the front page now uses components whose rendering is guaranteed.

Figures come from the same pipeline the rest of the app uses
(data_processing.py via ui_helpers.load_sample_pipeline), never hardcoded.
"""

import streamlit as st

from ui_helpers import inject_custom_css, load_sample_pipeline

st.set_page_config(page_title="SignalDesk Weekly Health Check", layout="wide")
inject_custom_css()

st.markdown(
    """
    <div class="sd-hero sd-hero--compact">
      <div class="sd-hero-eyebrow">SignalDesk</div>
      <h1 class="sd-hero-title">Weekly Health Check</h1>
      <p class="sd-hero-subtitle">Know which numbers you can quote. And which you can't.</p>
      <p class="sd-hero-meta">Sample week 2026-08-01 to 2026-08-07 &middot; 41 rows in, 40 after
      dedupe &middot; 10 data-quality issues found</p>
    </div>
    """,
    unsafe_allow_html=True,
)

_, clean_df, issues, rollup = load_sample_pipeline()

# ---------------------------------------------------------------------------
# The pitch. Native container + :primary[] colouring, so it renders in the app
# theme colour without depending on a custom stylesheet.
# ---------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### :primary[One export in. Numbers you can defend out.]")
    st.markdown(
        "SignalDesk ships a weekly usage export that is duplicated, mislabelled and "
        "incomplete. This tool reads it, flags every problem it finds, and reports only the "
        "rates that survive that cleaning. Every number arrives with its caveat attached."
    )
    st.markdown(
        "Use it to pick the workflow that is working, find the metric to trust least, and "
        "decide which claims need checking before a wider rollout."
    )

# ---------------------------------------------------------------------------
# Sample-week findings, collapsed. These describe the bundled synthetic export
# and would be wrong for any other file, so they open on request rather than
# greeting every visitor as if they were permanent product facts.
# ---------------------------------------------------------------------------
_worst = rollup.loc[rollup["completion_rate"].idxmin()]
_best = rollup.loc[rollup["completion_rate"].idxmax()]
_has_divergence = (issues["category"] == "confidence_quality_divergence").any()

with st.expander("Findings from the bundled sample week"):
    st.markdown(
        f"- **{_worst['workflow']}** sits at {_worst['completion_rate']:.1%} completion. "
        f"Its 95% interval clears {_best['workflow']}'s, so the gap is real, not noise."
    )
    if _has_divergence:
        st.markdown(
            "- Model confidence peaked the day completion and user rating collapsed. "
            "**Confidence is not quality.** Never use it as a proxy."
        )
    st.markdown(
        f"- {len(issues)} data-quality issues in a 41-row file, including a duplicate row "
        f"whose two notes disagree on the cause."
    )
    st.caption(
        "These describe the synthetic export bundled with this repo. Upload your own week to "
        "run the identical pipeline on real data."
    )

# ---------------------------------------------------------------------------
# Navigation. st.container(border=True) is a stable public API and supplies the
# card chrome natively -- an earlier attempt styled [data-testid="stPageLink"],
# which Streamlit does not emit, so the links rendered bare.
# ---------------------------------------------------------------------------
st.markdown('<div class="sd-nav-label">Explore</div>', unsafe_allow_html=True)

_NAV = [
    ("pages/1_Weekly_Findings.py",
     "**Weekly Findings**  \nPerformance, red flags, next steps",
     ":material/insights:"),
    ("pages/2_Workflow_Explorer.py",
     "**Workflow Explorer**  \nOne workflow, day by day and by source",
     ":material/travel_explore:"),
    ("pages/3_Data_Trust_Center.py",
     "**Data Trust Center**  \nEvery issue found, the method, its limits",
     ":material/verified_user:"),
]

for _col, (_page, _label, _icon) in zip(st.columns(3), _NAV):
    with _col, st.container(border=True):
        st.page_link(_page, label=_label, icon=_icon)

with st.container(border=True):
    st.page_link(
        "pages/4_Upload_Your_Own_Week.py",
        label="**Upload Your Own Week** · run this exact check on any SignalDesk export",
        icon=":material/upload_file:",
    )
