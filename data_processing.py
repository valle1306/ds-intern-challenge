"""Pure data-processing logic for the product usage events dataset.

No Streamlit, no UI-formatted printing here -- this module is imported by a
separate app.py that renders the results. Keep the function names and
signatures below stable since app.py depends on them.
"""

from __future__ import annotations

import pandas as pd

DATA_PATH = "sample-data/product_usage_events.csv"

NUMERIC_COLS = [
    "sessions",
    "completed",
    "accepted_output",
    "flagged_for_review",
    "avg_minutes_saved",
    "median_confidence",
    "user_rating",
]

ISSUE_COLUMNS = ["category", "date", "team", "workflow", "source", "description", "severity"]


def load_raw(path: str = DATA_PATH) -> pd.DataFrame:
    """Read every cell as its literal source string -- no NA coercion yet.

    A blank cell reads as "" and the literal text "n/a" stays "n/a".
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def _pick_spelling(spellings: pd.Series) -> str:
    """Given the original team spellings within one lower-case group, return
    the most common ORIGINAL spelling. Ties are broken in favor of Title Case.
    """
    counts = spellings.value_counts()
    top_count = counts.max()
    candidates = counts[counts == top_count].index.tolist()
    if len(candidates) == 1:
        return candidates[0]
    for candidate in candidates:
        if candidate == candidate.title():
            return candidate
    return candidates[0]


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return a typed, deduped, normalized DataFrame. See module docstring /
    the calling contract for the exact transformation steps.
    """
    df = raw.copy()

    # 1. Coerce numeric columns; "" and "n/a" (and anything else non-numeric)
    #    become NaN.
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 2. Drop exact-duplicate rows on every column except `notes`, keeping
    #    the first occurrence.
    dedup_cols = [c for c in df.columns if c != "notes"]
    df = df.drop_duplicates(subset=dedup_cols, keep="first")
    df = df.reset_index(drop=True)

    # 3. Normalize `team` casing: within each team.str.lower() group, map
    #    every row to that group's most common original spelling.
    lower_team = df["team"].str.lower()
    canonical_by_lower = df.groupby(lower_team)["team"].apply(_pick_spelling)
    df["team"] = lower_team.map(canonical_by_lower)

    # 4. Parse `date` to datetime64.
    df["date"] = pd.to_datetime(df["date"])

    # 5. Add rate columns.
    df["completion_rate"] = df["completed"] / df["sessions"]
    df["acceptance_rate"] = df["accepted_output"] / df["completed"]
    df["flag_rate"] = df["flagged_for_review"] / df["completed"]

    return df


def detect_issues(raw: pd.DataFrame, clean_df: pd.DataFrame) -> pd.DataFrame:
    """Detect data-quality issues by diffing `raw` against `clean_df`. See
    the calling contract for the exact categories detected.
    """
    issues: list[dict] = []

    def add_issue(category, date, team, workflow, source, description, severity):
        issues.append(
            {
                "category": category,
                "date": pd.to_datetime(date) if pd.notna(date) and date != "" else pd.NaT,
                "team": team,
                "workflow": workflow,
                "source": source,
                "description": description,
                "severity": severity,
            }
        )

    # Map each team's lowercase spelling to its canonical (majority) spelling
    # so every issue's `team` field matches clean_df's normalization -- a
    # raw-sourced issue built from a minority-spelling row (e.g. "product")
    # would otherwise fail to match its group when weekly_rollup counts
    # issues per (team, workflow).
    canonical_by_lower = {}
    for team in clean_df["team"].unique():
        canonical_by_lower[team.lower()] = team

    def canonical_team(raw_team):
        return canonical_by_lower.get(str(raw_team).lower(), raw_team)

    # --- duplicate_row -----------------------------------------------
    dedup_cols = [c for c in raw.columns if c != "notes"]
    dup_mask = raw.duplicated(subset=dedup_cols, keep=False)
    dup_rows = raw[dup_mask]
    if len(dup_rows):
        for _, group in dup_rows.groupby(dedup_cols, sort=False):
            first = group.iloc[0]
            notes_text = " vs ".join(repr(n) for n in group["notes"].tolist())
            add_issue(
                "duplicate_row",
                first["date"],
                canonical_team(first["team"]),
                first["workflow"],
                first["source"],
                (
                    f"Exact duplicate rows for {first['date']} / {first['team']} / "
                    f"{first['workflow']} / {first['source']} (all columns match except "
                    f"notes, which conflict: {notes_text})"
                ),
                "high",
            )

    # --- invalid_numeric_literal & missing_value ----------------------
    for col in NUMERIC_COLS:
        raw_col = raw[col]
        coerced = pd.to_numeric(raw_col, errors="coerce")
        empty_mask = raw_col == ""
        invalid_mask = (~empty_mask) & coerced.isna()
        missing_mask = empty_mask

        for idx in raw.index[invalid_mask]:
            r = raw.loc[idx]
            add_issue(
                "invalid_numeric_literal",
                r["date"],
                canonical_team(r["team"]),
                r["workflow"],
                r["source"],
                f"Column '{col}' has a non-numeric literal value: {r[col]!r}",
                "medium",
            )

        for idx in raw.index[missing_mask]:
            r = raw.loc[idx]
            add_issue(
                "missing_value",
                r["date"],
                canonical_team(r["team"]),
                r["workflow"],
                r["source"],
                f"Column '{col}' is blank (empty string) for this row",
                "low",
            )

    # --- label_inconsistency ------------------------------------------
    # clean_df already carries the canonical (majority) spelling per
    # team.str.lower() group (canonical_by_lower, built above). Any raw row
    # whose original spelling differs from that canonical spelling is a
    # minority-spelling row.
    raw_lower_team = raw["team"].str.lower()
    canonical_series = raw_lower_team.map(canonical_by_lower)
    mismatch_mask = canonical_series.notna() & (canonical_series != raw["team"])
    for idx in raw.index[mismatch_mask]:
        r = raw.loc[idx]
        canonical = canonical_series.loc[idx]
        add_issue(
            "label_inconsistency",
            r["date"],
            canonical,
            r["workflow"],
            r["source"],
            (
                f"Team spelling '{r['team']}' is a minority spelling within its "
                f"case-insensitive group; the group's canonical spelling is '{canonical}'"
            ),
            "medium",
        )

    # --- missing_expected_row ------------------------------------------
    combos = clean_df[["team", "workflow", "source"]].drop_duplicates().reset_index(drop=True)
    dates = pd.Series(clean_df["date"].unique(), name="date")
    combos["_key"] = 1
    dates_df = dates.to_frame()
    dates_df["_key"] = 1
    expected = combos.merge(dates_df, on="_key").drop(columns="_key")

    actual_keys = set(
        zip(clean_df["date"], clean_df["team"], clean_df["workflow"], clean_df["source"])
    )
    for row in expected.itertuples(index=False):
        key = (row.date, row.team, row.workflow, row.source)
        if key not in actual_keys:
            add_issue(
                "missing_expected_row",
                row.date,
                row.team,
                row.workflow,
                row.source,
                (
                    f"no row for this date/team/workflow/source: "
                    f"{row.date.date()} / {row.team} / {row.workflow} / {row.source}"
                ),
                "medium",
            )

    # --- suspicious_spike ------------------------------------------------
    def spike_flags(group: pd.DataFrame) -> pd.Series:
        sessions = group["sessions"]
        flags = pd.Series(False, index=group.index)
        for idx in group.index:
            others = sessions.drop(idx)
            med = others.median()
            if pd.notna(med) and med > 0 and pd.notna(sessions.loc[idx]) and sessions.loc[idx] > 2 * med:
                flags.loc[idx] = True
        return flags

    if len(clean_df):
        spike_mask = clean_df.groupby(["team", "workflow", "source"], group_keys=False).apply(
            spike_flags, include_groups=False
        )
        spike_mask = spike_mask.reindex(clean_df.index, fill_value=False)
    else:
        spike_mask = pd.Series(dtype=bool)

    for idx in clean_df.index[spike_mask]:
        r = clean_df.loc[idx]
        add_issue(
            "suspicious_spike",
            r["date"],
            r["team"],
            r["workflow"],
            r["source"],
            (
                f"sessions={r['sessions']:g} is more than 2x the group's median "
                f"sessions among its other rows for {r['team']} / {r['workflow']} / {r['source']}"
            ),
            "high",
        )

    # --- confidence_quality_divergence -----------------------------------
    def divergence_flags(group: pd.DataFrame) -> pd.Series:
        flags = pd.Series(False, index=group.index)
        if len(group) <= 1:
            return flags
        max_conf = group["median_confidence"].max()
        min_rating = group["user_rating"].min()
        if pd.isna(max_conf) or pd.isna(min_rating):
            return flags
        mask = (group["median_confidence"] == max_conf) & (group["user_rating"] == min_rating)
        flags[mask] = True
        return flags

    if len(clean_df):
        divergence_mask = clean_df.groupby(["team", "workflow", "source"], group_keys=False).apply(
            divergence_flags, include_groups=False
        )
        divergence_mask = divergence_mask.reindex(clean_df.index, fill_value=False)
    else:
        divergence_mask = pd.Series(dtype=bool)

    for idx in clean_df.index[divergence_mask]:
        r = clean_df.loc[idx]
        add_issue(
            "confidence_quality_divergence",
            r["date"],
            r["team"],
            r["workflow"],
            r["source"],
            (
                f"median_confidence={r['median_confidence']:g} is this group's weekly max "
                f"while user_rating={r['user_rating']:g} is this group's weekly min for "
                f"{r['team']} / {r['workflow']} / {r['source']}"
            ),
            "high",
        )

    # --- small_sample -------------------------------------------------
    small_mask = clean_df["notes"].str.contains("small sample", case=False, na=False)
    for idx in clean_df.index[small_mask]:
        r = clean_df.loc[idx]
        add_issue(
            "small_sample",
            r["date"],
            r["team"],
            r["workflow"],
            r["source"],
            f"notes flag a small sample: {r['notes']!r}",
            "low",
        )

    if issues:
        return pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    return pd.DataFrame(columns=ISSUE_COLUMNS)


def _completed_weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """Completed-weighted average, skipping NaN rows in both the value and
    the weight sum.
    """
    valid = values.notna() & weights.notna()
    values = values[valid]
    weights = weights[valid]
    total_weight = weights.sum()
    if not len(values) or total_weight == 0:
        return float("nan")
    return (values * weights).sum() / total_weight


def weekly_rollup(clean_df: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """One row per (team, workflow) with completed-weighted rates."""
    rows = []
    for (team, workflow), group in clean_df.groupby(["team", "workflow"], sort=False):
        sessions_total = group["sessions"].sum()
        completed_total = group["completed"].sum()
        accepted_total = group["accepted_output"].sum()
        flagged_total = group["flagged_for_review"].sum()

        completion_rate = completed_total / sessions_total if sessions_total else float("nan")
        acceptance_rate = accepted_total / completed_total if completed_total else float("nan")
        flag_rate = flagged_total / completed_total if completed_total else float("nan")

        avg_minutes_saved = _completed_weighted_mean(group["avg_minutes_saved"], group["completed"])
        median_confidence = _completed_weighted_mean(group["median_confidence"], group["completed"])
        user_rating = _completed_weighted_mean(group["user_rating"], group["completed"])

        if len(issues):
            n_issues = int(((issues["team"] == team) & (issues["workflow"] == workflow)).sum())
        else:
            n_issues = 0

        rows.append(
            {
                "team": team,
                "workflow": workflow,
                "completion_rate": completion_rate,
                "acceptance_rate": acceptance_rate,
                "flag_rate": flag_rate,
                "sessions_total": sessions_total,
                "avg_minutes_saved": avg_minutes_saved,
                "median_confidence": median_confidence,
                "user_rating": user_rating,
                "n_issues": n_issues,
                "row_count": len(group),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    raw = load_raw()
    clean_df = clean(raw)
    issues = detect_issues(raw, clean_df)
    rollup = weekly_rollup(clean_df, issues)
    assert clean_df.shape[0] == raw.shape[0] - 1, f"expected exactly 1 duplicate removed, got {raw.shape[0] - clean_df.shape[0]}"
    assert set(clean_df['team'].unique()) == {"Sales", "Support", "Product"}, f"unexpected team values: {clean_df['team'].unique()}"
    assert clean_df['median_confidence'].isna().sum() >= 1
    assert clean_df['user_rating'].isna().sum() >= 1
    assert len(issues) >= 8, f"expected >=8 issues, got {len(issues)}"
    assert rollup.shape[0] == 3, f"expected 3 rollup rows, got {rollup.shape[0]}"
    print(
        f"OK: {clean_df.shape[0]} clean rows, "
        f"team set is exactly {set(clean_df['team'].unique())}, "
        f"median_confidence NaN count={clean_df['median_confidence'].isna().sum()}, "
        f"user_rating NaN count={clean_df['user_rating'].isna().sum()}, "
        f"{len(issues)} issues detected, {rollup.shape[0]} rollup rows"
    )
