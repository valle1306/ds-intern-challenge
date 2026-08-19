"""Shared Streamlit rendering helpers used by app.py and every page in
pages/. This is the one place the Streamlit API meets the data layer
(data_processing.py) and the label layer (labels.py); both of those stay
free of streamlit imports by design.
"""
import pandas as pd
import streamlit as st

from data_processing import load_raw, clean, detect_issues, weekly_rollup
from labels import COLUMN_LABELS, CATEGORY_LABELS, SEVERITY_ICONS


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


def render_issues_panel(issues: pd.DataFrame, empty_message: str = "No issues detected.") -> None:
    """One st.expander per issue category present in `issues` (title from
    CATEGORY_LABELS + count), each row prefixed with its SEVERITY_ICONS icon.
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
                icon = SEVERITY_ICONS.get(str(row.get("severity", "")).lower(), "⚪")
                st.markdown(f"{icon} {row['description']}")


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
