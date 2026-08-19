"""Shared Streamlit rendering helpers used by app.py and every page in
pages/. This is the one place the Streamlit API meets the data layer
(data_processing.py) and the label layer (labels.py); both of those stay
free of streamlit imports by design.
"""
import html

import pandas as pd
import streamlit as st

from data_processing import (
    clean,
    detect_issues,
    find_prompt_change_date,
    load_raw,
    prompt_change_comparison,
    weekly_rollup,
)
from labels import COLUMN_LABELS, CATEGORY_LABELS


_CUSTOM_CSS = """
<style>
:root {
  --sd-indigo-50:  #EEF2FF; --sd-indigo-100: #E0E7FF; --sd-indigo-200: #C7D2FE;
  --sd-indigo-600: #4F46E5; --sd-indigo-700: #4338CA; --sd-indigo-900: #312E81;

  --sd-slate-50:  #F8FAFC; --sd-slate-100: #F1F5F9; --sd-slate-200: #E2E8F0;
  --sd-slate-300: #CBD5E1; --sd-slate-500: #64748B; --sd-slate-600: #475569;
  --sd-slate-900: #0F172A;

  --sd-red-50:    #FEF2F2; --sd-red-200:    #FECACA; --sd-red-700:    #B91C1C;
  --sd-amber-50:  #FFFBEB; --sd-amber-200:  #FDE68A; --sd-amber-700:  #B45309;
  --sd-yellow-50: #FEFCE8; --sd-yellow-200: #FEF08A; --sd-yellow-800: #854D0E;
  --sd-green-50:  #F0FDF4; --sd-green-200:  #BBF7D0; --sd-green-700:  #15803D;

  --sd-radius-sm: 8px; --sd-radius-md: 12px; --sd-radius-lg: 16px; --sd-radius-pill: 999px;
  --sd-shadow-sm: 0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06);
  --sd-shadow-md: 0 2px 4px rgba(15,23,42,.04), 0 4px 12px rgba(15,23,42,.08);

  --sd-space-1: 4px;  --sd-space-2: 8px;  --sd-space-3: 12px; --sd-space-4: 16px;
  --sd-space-5: 24px; --sd-space-6: 32px; --sd-space-7: 48px;
}

[data-testid="stHeading"] h1 {
  font-size: 2.25rem; font-weight: 800; color: var(--sd-slate-900);
  letter-spacing: -0.02em; line-height: 1.15;
}
[data-testid="stHeading"] h2 {
  font-size: 1.5rem; font-weight: 700; color: var(--sd-slate-900); letter-spacing: -0.01em;
}
[data-testid="stHeading"] h3 {
  font-size: 1.125rem; font-weight: 700; color: var(--sd-slate-900);
  padding-bottom: var(--sd-space-2); border-bottom: 1px solid var(--sd-slate-200);
  margin-top: var(--sd-space-6); margin-bottom: var(--sd-space-4);
}
[data-testid="stCaptionContainer"] { color: var(--sd-slate-500); font-size: 0.875rem; }

[data-testid="stMain"] { background-color: var(--sd-slate-50); }
[data-testid="stMainBlockContainer"] { padding-top: var(--sd-space-5); padding-bottom: var(--sd-space-5); }
[data-testid="stHorizontalBlock"] { gap: var(--sd-space-4); }

[data-testid="stMetric"] {
  background: #FFFFFF; border: 1px solid var(--sd-slate-200); border-radius: var(--sd-radius-md);
  padding: var(--sd-space-4) var(--sd-space-5); box-shadow: var(--sd-shadow-sm);
}
[data-testid="stMetricLabel"] {
  font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.04em; color: var(--sd-slate-500);
}
[data-testid="stMetricValue"] { font-size: 1.875rem; font-weight: 700; color: var(--sd-indigo-700); }
[data-testid="stMetricDelta"] { font-size: 0.8125rem; font-weight: 600; }

.sd-issue-row {
  display: flex; align-items: flex-start; gap: var(--sd-space-3);
  padding: var(--sd-space-2) 0; border-bottom: 1px solid var(--sd-slate-100);
  font-size: 0.9rem; color: var(--sd-slate-900);
}
.sd-issue-row:last-child { border-bottom: none; }
.sd-badge {
  display: inline-flex; align-items: center; flex-shrink: 0; margin-top: 0.125rem;
  padding: 0.125rem 0.625rem; border-radius: var(--sd-radius-pill);
  font-size: 0.6875rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.03em; border: 1px solid transparent; line-height: 1.5;
}
.sd-badge--high    { background: var(--sd-red-50);    color: var(--sd-red-700);    border-color: var(--sd-red-200); }
.sd-badge--medium  { background: var(--sd-amber-50);  color: var(--sd-amber-700);  border-color: var(--sd-amber-200); }
.sd-badge--low     { background: var(--sd-yellow-50); color: var(--sd-yellow-800); border-color: var(--sd-yellow-200); }
.sd-badge--default { background: var(--sd-slate-100); color: var(--sd-slate-600); border-color: var(--sd-slate-200); }
.sd-issue-desc { flex: 1; }

.sd-tag {
  display: inline-flex; align-items: center; padding: 0.25rem 0.75rem;
  border-radius: var(--sd-radius-pill); font-size: 0.75rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.03em; border: 1px solid transparent;
}
.sd-tag--elevated { background: var(--sd-red-50);   color: var(--sd-red-700);   border-color: var(--sd-red-200); }
.sd-tag--watch    { background: var(--sd-amber-50); color: var(--sd-amber-700); border-color: var(--sd-amber-200); }
.sd-tag--low      { background: var(--sd-green-50); color: var(--sd-green-700); border-color: var(--sd-green-200); }
.sd-tag-row { display: flex; align-items: center; gap: var(--sd-space-3); margin: var(--sd-space-2) 0 var(--sd-space-4); }
.sd-tag-caption { font-size: 0.875rem; color: var(--sd-slate-500); }
.sd-tag-strip { display: flex; flex-wrap: wrap; gap: var(--sd-space-4); margin-bottom: var(--sd-space-4); }
.sd-tag-chip {
  display: inline-flex; align-items: center; gap: var(--sd-space-2); background: #FFFFFF;
  border: 1px solid var(--sd-slate-200); border-radius: var(--sd-radius-md);
  padding: var(--sd-space-2) var(--sd-space-3); box-shadow: var(--sd-shadow-sm);
}
.sd-tag-chip-name { font-size: 0.875rem; font-weight: 600; color: var(--sd-slate-900); }

.sd-callout {
  background: var(--sd-indigo-50); border: 1px solid var(--sd-indigo-100);
  border-left: 3px solid var(--sd-indigo-600); border-radius: var(--sd-radius-md);
  padding: var(--sd-space-4) var(--sd-space-5); margin: var(--sd-space-4) 0;
  font-size: 0.9rem; color: var(--sd-slate-900); line-height: 1.55;
}
.sd-callout--annotation strong { color: var(--sd-indigo-700); }

.sd-hero {
  background: linear-gradient(135deg, var(--sd-indigo-50) 0%, #FFFFFF 100%);
  border: 1px solid var(--sd-indigo-100); border-left: 4px solid var(--sd-indigo-600);
  border-radius: var(--sd-radius-lg); padding: var(--sd-space-5) var(--sd-space-6);
  margin-bottom: var(--sd-space-6);
}
.sd-hero-eyebrow {
  font-size: 0.75rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--sd-indigo-600); margin-bottom: var(--sd-space-2);
}
.sd-hero-title  { font-size: 2.25rem; font-weight: 800; color: var(--sd-slate-900);
  letter-spacing: -0.02em; margin: 0 0 var(--sd-space-2); line-height: 1.15; }
.sd-hero-subtitle { font-size: 1.0625rem; color: var(--sd-slate-600); margin: 0 0 var(--sd-space-2); max-width: 70ch; }
.sd-hero-meta   { font-size: 0.8125rem; color: var(--sd-slate-500); margin: 0; }

[data-testid="stSidebarNavLink"] {
  border-radius: var(--sd-radius-sm); margin: 2px var(--sd-space-2); font-weight: 500; color: var(--sd-slate-600);
}
[data-testid="stSidebarNavLink"]:hover { background-color: var(--sd-indigo-50); color: var(--sd-indigo-700); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background-color: var(--sd-indigo-50); color: var(--sd-indigo-700); font-weight: 700;
}

[data-testid="stDataFrame"] { border: 1px solid var(--sd-slate-200); border-radius: var(--sd-radius-md); overflow: hidden; }
[data-testid="stExpander"] { border: 1px solid var(--sd-slate-200); border-radius: var(--sd-radius-md); box-shadow: var(--sd-shadow-sm); overflow: hidden; }
[data-testid="stAlertContainer"] { border-radius: var(--sd-radius-md); box-shadow: var(--sd-shadow-sm); }
/* --- Home launcher: compact hero + guidance cards ---------------------- */
.sd-hero--compact { padding: var(--sd-space-4) var(--sd-space-5); margin-bottom: var(--sd-space-4); }
.sd-hero--compact .sd-hero-title { font-size: 1.75rem; }
.sd-hero--compact .sd-hero-subtitle { font-size: 1rem; margin-bottom: var(--sd-space-1); }

.sd-guide-grid {
  display: grid; grid-template-columns: 1fr 2fr;
  gap: var(--sd-space-4); margin-bottom: var(--sd-space-5);
}
@media (max-width: 700px) { .sd-guide-grid { grid-template-columns: 1fr; } }
.sd-guide-card {
  background: #FFFFFF; border: 1px solid var(--sd-slate-200);
  border-radius: var(--sd-radius-md); padding: var(--sd-space-4) var(--sd-space-5);
  box-shadow: var(--sd-shadow-sm);
}
.sd-guide-card p { font-size: 0.9rem; color: var(--sd-slate-600); line-height: 1.55; margin: 0; }
.sd-guide-eyebrow {
  font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--sd-indigo-600); margin-bottom: var(--sd-space-2);
}
.sd-guide-card--verdict { background: var(--sd-indigo-50); border-color: var(--sd-indigo-100); }
.sd-verdict-list { margin: 0; padding-left: 1.1rem; }
.sd-verdict-list li {
  font-size: 0.9rem; color: var(--sd-slate-900); line-height: 1.5;
  margin-bottom: var(--sd-space-2);
}
.sd-verdict-list li:last-child { margin-bottom: 0; }

.sd-nav-label {
  font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--sd-slate-500); margin-bottom: var(--sd-space-2);
}

/* Hero stat -- the front page's focal point. Deliberately the only place in
   the app with type this large, so it reads as the headline and nothing
   competes with it. */
.sd-stat-band {
  display: flex; align-items: center; gap: var(--sd-space-6); flex-wrap: wrap;
  background: #FFFFFF; border: 1px solid var(--sd-indigo-100);
  border-left: 4px solid var(--sd-indigo-600); border-radius: var(--sd-radius-lg);
  padding: var(--sd-space-5) var(--sd-space-6); margin-bottom: var(--sd-space-4);
  box-shadow: var(--sd-shadow-md);
}
.sd-stat-figure {
  display: flex; align-items: baseline; gap: var(--sd-space-3);
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.sd-stat-before {
  font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em;
  color: var(--sd-slate-300); text-decoration: line-through;
}
.sd-stat-arrow { font-size: 1.5rem; color: var(--sd-slate-300); }
.sd-stat-after {
  font-size: 3.25rem; font-weight: 800; letter-spacing: -0.03em;
  color: var(--sd-indigo-700); line-height: 1;
}
.sd-stat-copy { flex: 1; min-width: 320px; }
.sd-stat-eyebrow {
  font-size: 0.6875rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--sd-indigo-600); margin-bottom: var(--sd-space-1);
}
.sd-stat-copy p {
  font-size: 0.9375rem; color: var(--sd-slate-600); line-height: 1.55; margin: 0; max-width: 78ch;
}
.sd-stat-copy strong { color: var(--sd-slate-900); }

/* --- Tab bar ----------------------------------------------------------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: var(--sd-space-4); border-bottom: 1px solid var(--sd-slate-200);
  margin-bottom: var(--sd-space-4);
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  font-size: 0.9375rem; font-weight: 600; color: var(--sd-slate-500); padding: 0 0 var(--sd-space-2);
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { color: var(--sd-indigo-700); }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--sd-indigo-600); }
</style>
"""


def inject_custom_css() -> None:
    """Inject the SignalDesk visual design system. Call once per page,
    immediately after st.set_page_config(...), before any other st.* call.
    Font loading and sidebar background/border are handled natively via
    .streamlit/config.toml (theme.font, theme.sidebar, showSidebarBorder) --
    this CSS block only covers what native theming can't reach: KPI cards,
    severity/concern badges, headings, hero, callouts, table/expander framing.
    """
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_sample_pipeline():
    """Run load_raw/clean/detect_issues/weekly_rollup on the bundled sample
    CSV once per server process; returns (raw, clean_df, issues, rollup).
    Every page except the Upload page should call this instead of re-running
    the pipeline itself, so all pages agree exactly and it's computed once.
    """
    raw = load_raw()
    clean_df = clean(raw)
    issues = detect_issues(raw, clean_df)
    rollup = weekly_rollup(clean_df, issues)
    return raw, clean_df, issues, rollup


def render_table(df: pd.DataFrame, fmt: dict | None = None) -> None:
    """Render df as a hide_index st.dataframe with columns renamed via
    COLUMN_LABELS. `fmt`, if given, is keyed by the ORIGINAL (raw) column
    names (e.g. {"completion_rate": "{:.1%}"}) and is translated to the
    renamed columns internally -- callers never have to think about the
    rename/format ordering. Missing keys in COLUMN_LABELS just keep their
    original name (no KeyError).
    """
    display_df = df.rename(columns=COLUMN_LABELS)
    if fmt:
        translated_fmt = {COLUMN_LABELS.get(k, k): v for k, v in fmt.items()}
        st.dataframe(display_df.style.format(translated_fmt), width="stretch", hide_index=True)
    else:
        st.dataframe(display_df, width="stretch", hide_index=True)


_SEVERITY_BADGE = {
    "high":   ("High",   "sd-badge--high"),
    "medium": ("Medium", "sd-badge--medium"),
    "low":    ("Low",    "sd-badge--low"),
}


def render_issues_panel(issues: pd.DataFrame, empty_message: str = "No issues detected.") -> None:
    """One st.expander per issue category present in `issues` (title from
    CATEGORY_LABELS + count), each row rendered as a severity badge + escaped
    description. `description` may originate from user-uploaded data (Upload
    Your Own Week) -- html.escape() every interpolated dynamic string, always.
    """
    if issues is None or issues.empty:
        st.info(empty_message)
        return
    for category in issues["category"].unique():
        cat_issues = issues[issues["category"] == category]
        if cat_issues.empty:
            continue
        title = CATEGORY_LABELS.get(category, str(category).replace("_", " ").title())
        with st.expander(f"{title} ({len(cat_issues)})"):
            for _, row in cat_issues.iterrows():
                sev = str(row.get("severity", "")).lower()
                label, css_class = _SEVERITY_BADGE.get(sev, (sev.title() or "Unknown", "sd-badge--default"))
                desc = html.escape(str(row["description"]))
                st.markdown(
                    f'<div class="sd-issue-row"><span class="sd-badge {css_class}">{label}</span>'
                    f'<span class="sd-issue-desc">{desc}</span></div>',
                    unsafe_allow_html=True,
                )


_CONCERN_TAGS = {
    "elevated": ("Elevated concern", "sd-tag--elevated"),
    "watch":    ("Watch",             "sd-tag--watch"),
    "low":      ("Low concern",       "sd-tag--low"),
}


def concern_tag(wf_issues: pd.DataFrame) -> tuple[str, str]:
    """One-sentence rule over an already-filtered (single team/workflow)
    issues slice: 'Elevated concern' if it has >=1 high-severity issue, else
    'Watch' if it has >=1 medium-severity issue, else 'Low concern'. Returns
    (label, css_class). Deliberately not a blended numeric score -- e.g.
    3*high+2*medium+1*low ties Support (1h/1m/1l=6) and Product (0h/2m/2l=6)
    despite very different severity profiles; a count-only tag rule doesn't.
    """
    if wf_issues is None or wf_issues.empty:
        key = "low"
    else:
        sev = wf_issues["severity"].str.lower()
        if (sev == "high").any():
            key = "elevated"
        elif (sev == "medium").any():
            key = "watch"
        else:
            key = "low"
    return _CONCERN_TAGS[key]


def render_concern_tag(wf_issues: pd.DataFrame) -> None:
    """Single concern-tag badge + caption for one already-filtered workflow
    (Workflow Explorer)."""
    label, css_class = concern_tag(wf_issues)
    st.markdown(
        f'<div class="sd-tag-row"><span class="sd-tag {css_class}">{html.escape(label)}</span>'
        f'<span class="sd-tag-caption">data-quality signal for this workflow this week -- '
        f'see Data Trust Center for the full issue list</span></div>',
        unsafe_allow_html=True,
    )


def render_concern_tag_strip(rollup: pd.DataFrame, issues: pd.DataFrame) -> None:
    """One concern-tag chip per (team, workflow) row in `rollup`, in rollup's
    row order (Overview, Upload Your Own Week, Data Trust Center)."""
    if rollup is None or rollup.empty:
        return
    chips = []
    for _, r in rollup.iterrows():
        if issues is not None and not issues.empty:
            wf_issues = issues[(issues["team"] == r["team"]) & (issues["workflow"] == r["workflow"])]
        else:
            wf_issues = issues
        label, css_class = concern_tag(wf_issues)
        chips.append(
            f'<span class="sd-tag-chip"><span class="sd-tag {css_class}">{html.escape(label)}</span>'
            f'<span class="sd-tag-chip-name">{html.escape(str(r["workflow"]))}</span></span>'
        )
    st.markdown(f'<div class="sd-tag-strip">{"".join(chips)}</div>', unsafe_allow_html=True)


def _rate_comparison_data(rollup: pd.DataFrame) -> pd.DataFrame:
    """Pure data prep for the workflow rate-comparison chart: rollup's three
    rate columns, indexed by workflow, columns renamed via COLUMN_LABELS. No
    Streamlit calls -- unit-testable with plain pandas assertions."""
    cols = ["completion_rate", "acceptance_rate", "flag_rate"]
    if rollup is None or rollup.empty:
        return pd.DataFrame(columns=[COLUMN_LABELS.get(c, c) for c in cols])
    return rollup.set_index("workflow")[cols].rename(columns=COLUMN_LABELS)


# Categorical slots (blue / orange / aqua), NOT three steps of one indigo.
# The three series are identities, not magnitudes, so a sequential ramp would
# imply an ordering that isn't there. The previous indigo ramp also failed
# validation outright: its lightest step sat outside the lightness band, read as
# gray (chroma 0.06), and hit only 1.45:1 against the surface -- flag rate was
# effectively invisible. These three pass every check including all-pairs CVD
# separation. Aqua lands at 2.74:1, under the 3:1 bar, which the relief rule
# permits because the full rollup table renders directly above this chart.
_RATE_SERIES_COLORS = ["#2A78D6", "#EB6834", "#1BAF7A"]


def render_rate_comparison_chart(rollup: pd.DataFrame) -> None:
    """Grouped (not stacked) bar chart of completion/acceptance/flag rate per
    workflow, straight off weekly_rollup's own columns -- no new math."""
    chart_df = _rate_comparison_data(rollup)
    if chart_df.empty:
        st.info("No rollup data to chart.")
        return
    st.bar_chart(chart_df, stack=False, color=_RATE_SERIES_COLORS, height=320)
    st.caption(
        "Read flag rate in the opposite direction from the other two: taller is worse, and "
        "per the domain packet it is ambiguous even then -- more flags can mean worse output, "
        "stricter review, or simply more careful users."
    )


def source_level_rollup(wf_clean: pd.DataFrame) -> pd.DataFrame:
    """Same completed-weighted rate formulas as data_processing.weekly_rollup
    (completion_rate=completed/sessions, acceptance_rate=accepted/completed,
    flag_rate=flagged/completed), one level deeper: grouped by (team,
    workflow, source) instead of just (team, workflow). Takes an
    already-workflow-filtered clean_df slice (e.g. Workflow Explorer's
    wf_clean). Ratios are built from summed numerators/denominators, never
    averaging a per-row rate directly."""
    cols = ["team", "workflow", "source", "completion_rate", "acceptance_rate",
            "flag_rate", "sessions_total", "row_count"]
    if wf_clean is None or wf_clean.empty:
        return pd.DataFrame(columns=cols)
    rows = []
    for (team, workflow, source), group in wf_clean.groupby(["team", "workflow", "source"], sort=False):
        sessions_total = group["sessions"].sum()
        completed_total = group["completed"].sum()
        accepted_total = group["accepted_output"].sum()
        flagged_total = group["flagged_for_review"].sum()
        rows.append({
            "team": team, "workflow": workflow, "source": source,
            "completion_rate": completed_total / sessions_total if sessions_total else float("nan"),
            "acceptance_rate": accepted_total / completed_total if completed_total else float("nan"),
            "flag_rate": flagged_total / completed_total if completed_total else float("nan"),
            "sessions_total": sessions_total,
            "row_count": len(group),
        })
    return pd.DataFrame(rows, columns=cols)


def render_change_point_note(wf_clean: pd.DataFrame, source: str, change_date: str) -> None:
    """Single-day-outlier note for one `source` within an already
    workflow-filtered `wf_clean` slice. Compares the tight daily
    completion-rate range before `change_date` against that day's own numbers
    and notes text, with two required caveats: (1) only one day of
    post-change data exists; (2) if the change_date row's own notes describe
    a mid-period change, that single day's numbers are themselves a blend,
    not a clean 'after' measurement. Never frames this as before-avg vs
    after-avg since after n=1. No-op if there's no data both before and on
    `change_date` for `source` -- safe to call speculatively."""
    change_ts = pd.Timestamp(change_date)
    sub = wf_clean[wf_clean["source"] == source]
    pre = sub[sub["date"] < change_ts]
    on_day = sub[sub["date"] == change_ts]
    if pre.empty or on_day.empty:
        return
    daily = pre.groupby("date")[["completed", "sessions"]].sum()
    daily["completion_rate"] = daily["completed"] / daily["sessions"]
    lo, hi = daily["completion_rate"].min(), daily["completion_rate"].max()
    row = on_day.iloc[0]
    notes_txt = html.escape(str(row.get("notes", "")).strip())
    change_date_str = html.escape(change_date)
    source_str = html.escape(str(source))
    st.markdown(
        f'<div class="sd-callout sd-callout--annotation">'
        f'<strong>{change_date_str} looks like a change point, not noise.</strong> '
        f'{source_str} completion rate held in a tight {lo:.1%}&ndash;{hi:.1%} range across the '
        f'{len(daily)} days before {change_date_str}, then fell to {row["completion_rate"]:.1%} '
        f'that day (flag rate {row["flag_rate"]:.1%}, acceptance {row["acceptance_rate"]:.1%}, '
        f'rating {row["user_rating"]:.1f}) &mdash; the same day model confidence hit its weekly '
        f'high ({row["median_confidence"]:.2f}). That row\'s own notes: &ldquo;{notes_txt}&rdquo;.'
        f'<br><em>Caveats:</em> only one day of post-change data exists here, so this isn\'t yet '
        f'a confirmed new steady state; and because the change happened mid-day, this single '
        f'day\'s numbers are themselves a blend of pre- and post-change sessions, not a clean '
        f'"after" measurement.</div>',
        unsafe_allow_html=True,
    )


def build_confidence_quality_headline(clean_df: pd.DataFrame, issues: pd.DataFrame) -> str | None:
    """Return a headline sentence for the most severe confidence_quality_divergence
    issue in `issues` (there is at most one per team/workflow/source group by
    construction), or None if there are none. Deliberately generic -- does NOT
    hardcode any specific date/team/workflow -- so it produces a correct
    sentence on the bundled sample data AND on any uploaded file.
    """
    if issues is None or issues.empty:
        return None
    div = issues[issues["category"] == "confidence_quality_divergence"]
    if div.empty:
        return None
    d = div.iloc[0]
    match = clean_df[
        (clean_df["team"] == d["team"])
        & (clean_df["workflow"] == d["workflow"])
        & (clean_df["source"] == d["source"])
        & (clean_df["date"] == d["date"])
    ]
    if match.empty:
        return (
            f"**Confidence isn't quality.** {d['description']} "
            f"High model confidence does not always mean the output was good "
            f"-- don't use confidence as a quality proxy."
        )
    r = match.iloc[0]
    date_str = pd.Timestamp(d["date"]).strftime("%Y-%m-%d") if pd.notna(d["date"]) else "that day"
    completion_pct = f"{r['completion_rate'] * 100:.0f}%" if pd.notna(r["completion_rate"]) else "an unusually low rate"
    rating = f"{r['user_rating']:.1f}" if pd.notna(r["user_rating"]) else "an unusually low rating"
    confidence = f"{r['median_confidence']:.2f}" if pd.notna(r["median_confidence"]) else "its weekly high"
    return (
        f"**Confidence isn't quality.** On {date_str}, the {d['team']} / {d['workflow']} / "
        f"{d['source']} workflow's completion rate fell to ~{completion_pct} and user rating "
        f"dropped to {rating} -- the **same day** model confidence hit {confidence} for that "
        f"workflow. High model confidence does not mean the output was good that day -- don't "
        f"use confidence as a quality proxy."
    )


def render_daily_trend(clean_df: pd.DataFrame, groupby_col: str, empty_message: str) -> None:
    """Completed-weighted daily completion-rate line chart, summed by date and
    `groupby_col` (completed/sessions summed first, then divided -- never
    averaging completion_rate directly, so a low-volume day doesn't count the
    same as a high-volume day). One line per distinct `groupby_col` value.
    Renders `empty_message` via st.info on any failure or empty result,
    instead of a generic "unavailable" stub.
    """
    try:
        daily = clean_df.groupby(["date", groupby_col], as_index=False)[["completed", "sessions"]].sum()
        daily["completion_rate"] = daily["completed"] / daily["sessions"]
        pivoted = daily.pivot(index="date", columns=groupby_col, values="completion_rate")
        if pivoted.empty:
            st.info(empty_message)
        else:
            st.line_chart(pivoted)
    except Exception:
        st.info(empty_message)


def with_ci_display(rollup: pd.DataFrame) -> pd.DataFrame:
    """Collapse weekly_rollup's numeric `completion_lo`/`completion_hi` into a
    single human-readable `completion_ci` string column ("77.3-83.7%"), placed
    right after `completion_rate`, and drop the raw bounds.

    The interval MATH lives in data_processing.wilson_interval; only its
    FORMATTING lives here, matching this app's data/UI split. Returns the frame
    unchanged if the bounds aren't present (e.g. an older cached rollup).
    """
    if rollup is None or rollup.empty or "completion_lo" not in rollup.columns:
        return rollup
    out = rollup.copy()
    out["completion_ci"] = [
        "-" if pd.isna(lo) or pd.isna(hi) else f"{lo:.1%}-{hi:.1%}"
        for lo, hi in zip(out["completion_lo"], out["completion_hi"])
    ]
    out = out.drop(columns=["completion_lo", "completion_hi"])
    cols = list(out.columns)
    cols.insert(cols.index("completion_rate") + 1, cols.pop(cols.index("completion_ci")))
    return out[cols]


def _prompt_change_verdict(comparison: pd.DataFrame) -> str | None:
    """Build the one-sentence verdict for the prompt-change panel: name the
    workflow whose apparent change shrinks most once flagged rows are removed,
    and quote both numbers in percentage points.

    Computed from the frame, never hardcoded, so it stays true on an uploaded
    week. Returns None when nothing was excluded and there is no gap to report.
    """
    if comparison is None or comparison.empty:
        return None
    gaps = (comparison["delta_naive"] - comparison["delta_adj"]).abs()
    if not gaps.notna().any() or gaps.max() < 0.005:
        return None
    row = comparison.loc[gaps.idxmax()]
    dropped = int(row["sessions_after"] - row["sessions_after_adj"])
    share = dropped / row["sessions_after"] if row["sessions_after"] else 0.0
    n_rows = int(row["rows_excluded"])
    return (
        f"**The apparent effect is not robust.** {row['workflow']}'s completion rate looks "
        f"like it moved {row['delta_naive'] * 100:+.1f}pp after the prompt change. Remove the "
        f"{n_rows} row{'' if n_rows == 1 else 's'} carrying a high-severity data-quality "
        f"issue -- "
        f"{dropped:,} sessions, {share:.0%} of that workflow's post-change volume -- and the "
        f"move is {row['delta_adj'] * 100:+.1f}pp. The headline number is mostly that one row, "
        f"not the new prompt."
    )


def render_prompt_change_panel(clean_df: pd.DataFrame, issues: pd.DataFrame) -> None:
    """Before/after completion rates around the prompt-version change, shown
    naively and with high-severity-flagged rows removed, plus a computed
    verdict and the caveats that make the table honest.

    Self-gating: renders nothing when the data has no prompt-change note, so
    both the sample Overview and the Upload page can call it unconditionally.
    """
    change_date = find_prompt_change_date(clean_df)
    if change_date is None:
        return
    comparison = prompt_change_comparison(clean_df, issues, change_date)
    if comparison.empty:
        return

    change_str = pd.Timestamp(change_date).strftime("%Y-%m-%d")
    st.markdown(f"**Did the {change_str} prompt change help?**")

    display = comparison[[
        "workflow", "completion_before", "completion_after", "delta_naive",
        "completion_after_adj", "delta_adj", "rows_excluded",
    ]]
    # Only surface the adjusted "before" when exclusions actually moved it --
    # otherwise it is a column of duplicated numbers.
    if not comparison["completion_before"].round(6).equals(
        comparison["completion_before_adj"].round(6)
    ):
        display = comparison.drop(columns=["sessions_after", "sessions_after_adj"])
    render_table(display, fmt={
        "completion_before": "{:.1%}", "completion_after": "{:.1%}", "delta_naive": "{:+.1%}",
        "completion_before_adj": "{:.1%}", "completion_after_adj": "{:.1%}",
        "delta_adj": "{:+.1%}", "rows_excluded": "{:,.0f}",
    })

    verdict = _prompt_change_verdict(comparison)
    if verdict:
        st.markdown(
            f'<div class="sd-callout sd-callout--annotation">{verdict}</div>',
            unsafe_allow_html=True,
        )
    st.caption(
        f"Days before {change_str} vs {change_str} onward, completed-weighted. "
        "\"Excl. flagged\" drops only the individual rows carrying a high-severity issue "
        "(the duplicated demo-account spike, the confidence/quality divergence), not whole "
        "days. This bounds a claim rather than proving one: the after-window is a few days, "
        "it contains other events, there is no control group, and choosing to drop those rows "
        "is itself a judgment call. Read it as \"the apparent effect is not robust.\""
    )
