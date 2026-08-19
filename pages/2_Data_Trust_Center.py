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
# Summary
# ---------------------------------------------------------------------------
st.subheader("Summary")
if issues is None or issues.empty:
    st.info("No issues detected.")
else:
    summary = pd.crosstab(
        issues["category"].map(lambda c: CATEGORY_LABELS.get(c, c)),
        issues["severity"].str.title(),
    )
    st.dataframe(summary)

render_concern_tag_strip(rollup, issues)
st.caption("See Methodology below for exactly how each concern tag is decided.")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
_severity_options = sorted(issues["severity"].dropna().unique())
_issue_type_options = sorted(CATEGORY_LABELS.get(c, c) for c in issues["category"].dropna().unique())

col1, col2 = st.columns(2)
with col1:
    selected_severities = st.multiselect(
        "Severity",
        options=_severity_options,
        default=_severity_options,
    )
with col2:
    selected_issue_types = st.multiselect(
        "Issue type",
        options=_issue_type_options,
        default=_issue_type_options,
    )

_issue_labels = issues["category"].map(lambda c: CATEGORY_LABELS.get(c, c))
filtered_issues = issues[
    issues["severity"].isin(selected_severities) & _issue_labels.isin(selected_issue_types)
]

# ---------------------------------------------------------------------------
# Full issue list
# ---------------------------------------------------------------------------
st.subheader("Full issue list")
render_issues_panel(filtered_issues)

# ---------------------------------------------------------------------------
# Methodology
# ---------------------------------------------------------------------------
st.subheader("Methodology")
st.markdown(
    """
**Rate formulas**

- `completion_rate = completed / sessions`
- `acceptance_rate = accepted_output / completed`
- `flag_rate = flagged_for_review / completed`

Rates are completed-weighted (not a naive average of daily rows) so low-volume days don't
count the same as high-volume days.

**Cleaning rules**

- Exact-duplicate rows (identical on every column except `notes`) are collapsed, keeping the
  first occurrence, with conflicting notes surfaced as a `Duplicate row` issue rather than
  silently dropped.
- Team names are case-normalized to each case-insensitive group's majority original spelling.
- Blank cells and the literal text `"n/a"` are both treated as missing, never as zero.

**Data-quality concern tag**

Each workflow gets a one-sentence concern tag, not a blended score: **Elevated concern** if
it has at least one high-severity issue this week, else **Watch** if it has at least one
medium-severity issue, else **Low concern**. A raw issue count alone ranks workflows
unfairly -- Product has more total issues than Sales this week but zero high-severity ones,
while Sales has two.

**Source-level rollup**

The Workflow Explorer page's "By source" table uses these exact same rate formulas, grouped
one level deeper by `source` instead of just `team`/`workflow` -- a workflow's blended
weekly number can hide real differences in how its sessions come in.

**Term definitions**

- `sessions` means workflow runs, not unique users.
- `completed` means the workflow reached a final output, not that the output was good.
- `accepted_output` means a user accepted the output with no major rework. It is a rough
  signal, not a perfect quality label.
- `flagged_for_review` means a user or policy marked the output for human review. More flags
  can mean worse output, stricter review, or more careful users.
- `avg_minutes_saved` is an estimate. Treat it as directional, not ground truth.
- `median_confidence` is model-reported confidence. It is not the same as correctness.
- `notes` may change how a row should be interpreted.
"""
)
