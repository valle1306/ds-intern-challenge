"""SignalDesk Data Trust Center — Streamlit UI.

Presentation only. All cleaning / issue-detection / rollup logic lives in
data_processing.py (via ui_helpers.load_sample_pipeline); this file just
renders every detected issue and documents exactly how the numbers
elsewhere in this app were computed.
"""

import pandas as pd
import streamlit as st

from ui_helpers import inject_custom_css, load_sample_pipeline, render_concern_tag_strip, render_issues_panel
from labels import CATEGORY_LABELS

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SignalDesk · Data Trust Center", layout="wide")
inject_custom_css()
st.title("Data Trust Center")
st.caption(
    "Everything found wrong with this week's export, and exactly how the numbers "
    "elsewhere in this app were computed."
)

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
raw, clean_df, issues, rollup = load_sample_pipeline()

# ---------------------------------------------------------------------------
# Three tabs: what was found, how it was computed, and where the method stops
# being trustworthy. The last two are long-form documentation -- tabbing them
# keeps the issue list, which is what people come here for, above the fold.
# ---------------------------------------------------------------------------
tab_issues, tab_method, tab_limits = st.tabs(["Issues", "Methodology", "Known limitations"])

with tab_issues:
    if issues is None or issues.empty:
        st.info("No issues detected.")
    else:
        summary = pd.crosstab(
            issues["category"].map(lambda c: CATEGORY_LABELS.get(c, c)),
            issues["severity"].str.title(),
        )
        st.dataframe(summary)

    render_concern_tag_strip(rollup, issues)
    st.caption("See the Methodology tab for exactly how each concern tag is decided.")

    _severity_options = sorted(issues["severity"].dropna().unique())
    _issue_type_options = sorted(
        CATEGORY_LABELS.get(c, c) for c in issues["category"].dropna().unique()
    )

    col1, col2 = st.columns(2)
    with col1:
        selected_severities = st.multiselect(
            "Severity", options=_severity_options, default=_severity_options
        )
    with col2:
        selected_issue_types = st.multiselect(
            "Issue type", options=_issue_type_options, default=_issue_type_options
        )

    _issue_labels = issues["category"].map(lambda c: CATEGORY_LABELS.get(c, c))
    filtered_issues = issues[
        issues["severity"].isin(selected_severities) & _issue_labels.isin(selected_issue_types)
    ]
    render_issues_panel(filtered_issues)

with tab_method:
    st.caption(
        "How every number in this app was computed. Rate formulas are open by default; "
        "the rest expand on demand."
    )
    # Generated from one source of truth so a topic cannot document a formula
    # the code no longer uses. Order is reading order, not importance.
    _METHODOLOGY: dict[str, str] = {
    'Rate formulas': """
- `completion_rate = completed / sessions`
- `acceptance_rate = accepted_output / completed`
- `flag_rate = flagged_for_review / completed`

Rates are completed-weighted (not a naive average of daily rows) so low-volume days don't
count the same as high-volume days.
""",
    'Cleaning rules': """
- Exact-duplicate rows (identical on every column except `notes`) are collapsed, keeping the
  first occurrence, with conflicting notes surfaced as a `Duplicate row` issue rather than
  silently dropped.
- Team names are case-normalized to each case-insensitive group's majority original spelling.
- Blank cells and the literal text `"n/a"` are both treated as missing, never as zero.
""",
    'Data-quality concern tag': """
Each workflow gets a one-sentence concern tag, not a blended score: **Elevated concern** if
it has at least one high-severity issue this week, else **Watch** if it has at least one
medium-severity issue, else **Low concern**. A raw issue count alone ranks workflows
unfairly -- Product has more total issues than Sales this week but zero high-severity ones,
while Sales has two.
""",
    'Confidence intervals': """
Completion rates carry a 95% **Wilson score interval**, not a bare point estimate. Wilson
rather than the textbook normal approximation because it never produces bounds outside
0-100% and it stays sane at small n -- rows in this export go down to 4 and 5 sessions, where
the normal approximation is simply wrong. This is what lets the Overview say Feedback
clustering is behind rather than merely lower: its interval doesn't overlap Lead
summary's.
""",
    'Prompt-change comparison': """
The days before the `new prompt version started` note vs that day onward, completed-weighted,
computed twice: over every row, and again with the individual rows carrying a **high-severity**
issue removed. Only those rows are dropped -- not whole days, not whole workflows. The change
date is read from the `notes` column, never hardcoded, so an uploaded week with its own change
date works too. The two columns disagree, and that disagreement is the finding: a naive
before/after read credits the prompt with a contaminated row's numbers.
""",
    'Source-level rollup': """
The Workflow Explorer page's "By source" table uses these exact same rate formulas, grouped
one level deeper by `source` instead of just `team`/`workflow` -- a workflow's blended
weekly number can hide real differences in how its sessions come in.
""",
    'Term definitions': """
- `sessions` means workflow runs, not unique users.
- `completed` means the workflow reached a final output, not that the output was good.
- `accepted_output` means a user accepted the output with no major rework. It is a rough
  signal, not a perfect quality label.
- `flagged_for_review` means a user or policy marked the output for human review. More flags
  can mean worse output, stricter review, or more careful users.
- `avg_minutes_saved` is an estimate. Treat it as directional, not ground truth.
- `median_confidence` is model-reported confidence. It is not the same as correctness.
- `notes` may change how a row should be interpreted.
""",
    }
    for _i, (_topic, _body) in enumerate(_METHODOLOGY.items()):
        with st.expander(_topic, expanded=(_i == 0)):
            st.markdown(_body)

with tab_limits:
    st.markdown(
        """
    These are worth knowing before anyone treats a flag here as a finding.

    - **The confidence-vs-quality detector is a screen, not a test.** It fires when one row is
      simultaneously its group's highest model confidence and its lowest user rating. In a 7-row
      group those can coincide by chance roughly one time in seven, so across this week's 8 groups
      you would expect about one false positive even in clean data. It earns attention here because
      the flagged row also has an independent explanation in its own `notes` (a mid-day policy
      change) and a collapse in completion rate. Read the flag as *go look*, never as *this is real*.
    - **The spike threshold is chosen, not derived.** "More than 2x the group's median sessions
      among its other rows" is a reasonable screen, not a significance test. A genuine 2.1x growth
      day would be flagged; a suspicious 1.9x day would not.
    - **Missing rows assume a dense grid.** Every date x team x workflow x source combination seen
      anywhere in the file is expected on every date. A workflow that legitimately ran on only some
      days would be reported as having missing rows.
    - **One week, no control group.** There is no week-over-week baseline and no holdout, so
      nothing here separates a prompt effect from a day-of-week effect or ordinary drift. The
      prompt-change table bounds a claim; it cannot establish causation.
    - **`accepted_output` and `avg_minutes_saved` are proxies.** Both come from the packet marked as
      rough or directional. Every rate built on them inherits that.
    """
    )
