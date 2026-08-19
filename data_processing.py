"""Pure data-processing logic for the product usage events dataset.

No Streamlit, no UI-formatted printing here -- this module is imported by a
separate app.py that renders the results. Keep the function names and
signatures below stable since app.py depends on them.
"""

from __future__ import annotations

import io
import math

import pandas as pd

DATA_PATH = "sample-data/product_usage_events.csv"

# The `notes` text that marks the day a new prompt version went live. Rows are
# found by substring match on this, never by a hardcoded date, so the
# prompt-change analysis also works on an uploaded week.
PROMPT_CHANGE_NOTE = "new prompt version started"

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

REQUIRED_COLUMNS = [
    "date", "team", "workflow", "source", "sessions", "completed",
    "accepted_output", "flagged_for_review", "avg_minutes_saved",
    "median_confidence", "user_rating", "notes",
]


# Read the CSV with no type coercion so raw values like "" and "n/a" stay literal.
def load_raw(path: str = DATA_PATH) -> pd.DataFrame:
    """Read every cell as its literal source string -- no NA coercion yet.

    A blank cell reads as "" and the literal text "n/a" stays "n/a".

    `path` may be the default sample-data path, another CSV path, or any
    file-like/bytes buffer accepted by pandas.read_csv's filepath_or_buffer
    (e.g. a Streamlit UploadedFile from st.file_uploader, or io.BytesIO).
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


# Check a raw DataFrame has the required columns and at least one data row.
def validate_schema(raw: pd.DataFrame) -> list[str]:
    """Return a list of human-readable schema problems with `raw` (empty
    list = valid). Checks required-column presence and non-emptiness only;
    does not mutate raw. Call before clean()/detect_issues() on any
    non-bundled (e.g. uploaded) CSV.
    """
    problems: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        problems.append("Missing required column(s): " + ", ".join(missing))
    if raw.empty:
        problems.append("The file has no data rows.")
    return problems


# Pick the majority original spelling for a case-insensitive team-name group.
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


# Type-coerce, dedupe, normalize team casing, and add the three rate columns.
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


# Run a per-group boolean flag function and return one index-aligned mask.
def _group_flag_mask(df: pd.DataFrame, keys: list[str], flag_fn) -> pd.Series:
    """Apply `flag_fn` to each (`keys`) group of `df` and stitch the per-group
    boolean Series back into a single mask aligned to df.index.

    Deliberately an explicit loop rather than DataFrameGroupBy.apply():
    apply()'s return shape varies with the number of groups, and a frame that
    collapses to exactly one group raises "ValueError: Buffer dtype mismatch"
    on pandas 3.0.x. A loop is shape-stable for 0, 1, or n groups -- which
    matters because an uploaded CSV covering a single team/workflow/source is
    a perfectly ordinary file.

    `flag_fn` receives the full group (grouping columns included) and must
    return a boolean Series positionally matching that group's rows.
    """
    mask = pd.Series(False, index=df.index)
    if df.empty:
        return mask
    for _, group in df.groupby(keys, sort=False):
        mask.loc[group.index] = flag_fn(group).astype(bool).to_numpy()
    return mask


# Diff raw vs. clean to flag every data-quality issue found in the export.
def detect_issues(raw: pd.DataFrame, clean_df: pd.DataFrame) -> pd.DataFrame:
    """Detect data-quality issues by diffing `raw` against `clean_df`. See
    the calling contract for the exact categories detected.
    """
    issues: list[dict] = []

    # Append one issue row to the running list.
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

    # Map a raw team spelling to clean_df's canonical spelling for that team.
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
    # Flag rows whose sessions exceed 2x their group's median (spike detector).
    def spike_flags(group: pd.DataFrame) -> pd.Series:
        sessions = group["sessions"]
        flags = pd.Series(False, index=group.index)
        for idx in group.index:
            others = sessions.drop(idx)
            med = others.median()
            if pd.notna(med) and med > 0 and pd.notna(sessions.loc[idx]) and sessions.loc[idx] > 2 * med:
                flags.loc[idx] = True
        return flags

    spike_mask = _group_flag_mask(clean_df, ["team", "workflow", "source"], spike_flags)

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
    # Flag the row where confidence peaks but rating bottoms out in its group.
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

    divergence_mask = _group_flag_mask(
        clean_df, ["team", "workflow", "source"], divergence_flags
    )

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


# 95% Wilson score interval for a count-based rate (e.g. completed/sessions).
def wilson_interval(successes: float, trials: float, z: float = 1.96) -> tuple[float, float]:
    """Return the (low, high) Wilson score interval for `successes`/`trials`.

    Wilson rather than the textbook normal approximation for two reasons that
    both bite on this data: it never produces bounds outside [0, 1], and it
    stays sane at small n -- rows here go down to 4 and 5 sessions, where the
    normal approximation is simply wrong. z=1.96 is the two-sided 95% level.

    Returns (nan, nan) when `trials` is 0 or missing, so callers can format it
    the same way they format any other missing value.
    """
    if not trials or pd.isna(trials) or pd.isna(successes) or trials <= 0:
        return (float("nan"), float("nan"))
    n = float(trials)
    p = float(successes) / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    # Clamp: at p=0 or p=1 the algebra lands a hair outside [0, 1] on floating
    # point (e.g. -3e-17), which would render as "-0.0%".
    return (min(max(lo, 0.0), 1.0), min(max(hi, 0.0), 1.0))


# Weighted average of `values` by `weights`, skipping rows where either is NaN.
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


# Roll clean_df up to one completed-weighted summary row per team+workflow.
def weekly_rollup(clean_df: pd.DataFrame, issues: pd.DataFrame) -> pd.DataFrame:
    """One row per (team, workflow) with completed-weighted rates."""
    rows = []
    for (team, workflow), group in clean_df.groupby(["team", "workflow"], sort=False):
        sessions_total = group["sessions"].sum()
        completed_total = group["completed"].sum()
        accepted_total = group["accepted_output"].sum()
        flagged_total = group["flagged_for_review"].sum()

        completion_rate = completed_total / sessions_total if sessions_total else float("nan")
        completion_lo, completion_hi = wilson_interval(completed_total, sessions_total)
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
                "completion_lo": completion_lo,
                "completion_hi": completion_hi,
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



# Find the date a new prompt version went live, from the notes column.
def find_prompt_change_date(clean_df: pd.DataFrame) -> pd.Timestamp | None:
    """Return the earliest date whose `notes` mention PROMPT_CHANGE_NOTE, or
    None if no row does.

    Read out of the data rather than hardcoded so an uploaded week with its own
    change date works, and a week with no prompt change simply gets no
    prompt-change analysis instead of a wrong one.
    """
    if clean_df is None or clean_df.empty or "notes" not in clean_df.columns:
        return None
    hit = clean_df["notes"].str.contains(PROMPT_CHANGE_NOTE, case=False, na=False)
    if not hit.any():
        return None
    return clean_df.loc[hit, "date"].min()


# Rows carrying a high-severity issue, as a mask over clean_df.
def high_severity_row_mask(clean_df: pd.DataFrame, issues: pd.DataFrame) -> pd.Series:
    """Mark every clean_df row that carries a high-severity issue, matched on
    (date, team, workflow, source).

    Deliberately surgical: it drops the individual flagged rows, not the whole
    day and not the whole workflow, so the adjusted comparison keeps as much
    real data as possible.
    """
    mask = pd.Series(False, index=clean_df.index)
    if clean_df.empty or issues is None or issues.empty:
        return mask
    high = issues[issues["severity"].str.lower() == "high"]
    if high.empty:
        return mask
    key_cols = ["date", "team", "workflow", "source"]
    rows = pd.MultiIndex.from_frame(clean_df[key_cols])
    flagged = pd.MultiIndex.from_frame(high[key_cols])
    return pd.Series(rows.isin(flagged), index=clean_df.index)


# Completed-weighted before/after rates around a prompt change, naive and adjusted.
def prompt_change_comparison(
    clean_df: pd.DataFrame, issues: pd.DataFrame, change_date
) -> pd.DataFrame:
    """One row per workflow comparing the days before `change_date` against
    `change_date` onward, computed twice: over every row ("naive"), and again
    with high-severity-flagged rows removed ("adjusted", see
    high_severity_row_mask).

    All rates are built from summed numerators and denominators, never by
    averaging per-row rates -- the same completed-weighted rule weekly_rollup
    uses, so a 4-session day cannot swing the result like a 140-session one.

    The point of showing both columns is that they disagree: a naive before/
    after read attributes contaminated rows to the prompt change. Workflows
    with no rows in one of the two windows are dropped, since there is nothing
    to compare.

    IMPORTANT CAVEAT, which the UI repeats: this bounds a claim, it does not
    prove one. The "after" window is a handful of days that also contains other
    events, there is no control group, and removing flagged rows is itself a
    judgment call. Read it as "the apparent effect is not robust", never as
    "the prompt change caused X".
    """
    cols = [
        "workflow", "completion_before", "completion_after", "delta_naive",
        "completion_before_adj", "completion_after_adj", "delta_adj",
        "sessions_after", "sessions_after_adj", "rows_excluded",
    ]
    if clean_df is None or clean_df.empty or change_date is None:
        return pd.DataFrame(columns=cols)

    change_ts = pd.Timestamp(change_date)
    excluded = high_severity_row_mask(clean_df, issues)

    # Completed-weighted completion rate + session count over a row subset.
    def _rate(df):
        sessions = df["sessions"].sum()
        completed = df["completed"].sum()
        return (completed / sessions if sessions else float("nan"), sessions)

    rows = []
    for workflow, group in clean_df.groupby("workflow", sort=False):
        before = group[group["date"] < change_ts]
        after = group[group["date"] >= change_ts]
        if before.empty or after.empty:
            continue
        keep = ~excluded.loc[group.index]
        before_adj = before[keep.loc[before.index]]
        after_adj = after[keep.loc[after.index]]

        c_before, _ = _rate(before)
        c_after, n_after = _rate(after)
        c_before_adj, _ = _rate(before_adj)
        c_after_adj, n_after_adj = _rate(after_adj)

        rows.append({
            "workflow": workflow,
            "completion_before": c_before,
            "completion_after": c_after,
            "delta_naive": c_after - c_before,
            "completion_before_adj": c_before_adj,
            "completion_after_adj": c_after_adj,
            "delta_adj": c_after_adj - c_before_adj,
            "sessions_after": n_after,
            "sessions_after_adj": n_after_adj,
            "rows_excluded": int(excluded.loc[group.index].sum()),
        })

    return pd.DataFrame(rows, columns=cols)


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
    _buf_raw = load_raw(io.BytesIO(open(DATA_PATH, "rb").read()))
    assert _buf_raw.equals(raw), "load_raw(buffer) must match load_raw(path) on identical bytes"
    assert validate_schema(raw) == [], f"bundled sample data should pass validate_schema, got {validate_schema(raw)}"
    assert validate_schema(raw.drop(columns=["sessions"])) != [], "validate_schema must catch a missing required column"

    # Wilson bounds must bracket the point estimate and stay inside [0, 1].
    for k, n in [(8, 10), (0, 5), (5, 5), (126, 140), (1, 1000)]:
        lo, hi = wilson_interval(k, n)
        assert 0.0 <= lo <= k / n <= hi <= 1.0, f"bad Wilson interval for {k}/{n}: {lo}, {hi}"
    assert all(pd.isna(v) for v in wilson_interval(0, 0)), "0 trials must give (nan, nan)"
    assert {"completion_lo", "completion_hi"} <= set(rollup.columns)

    # A CSV that collapses to ONE (team, workflow, source) group used to raise
    # "Buffer dtype mismatch" from groupby().apply() -- regression guard.
    _one_group_csv = """date,team,workflow,source,sessions,completed,accepted_output,flagged_for_review,avg_minutes_saved,median_confidence,user_rating,notes
2026-08-01,Sales,Lead summary,email,10,8,7,1,5,0.8,4,ok
2026-08-02,Sales,Lead summary,email,12,9,7,1,5,0.8,4,ok
"""
    _one_group = load_raw(io.StringIO(_one_group_csv))
    _one_clean = clean(_one_group)
    _one_issues = detect_issues(_one_group, _one_clean)
    assert weekly_rollup(_one_clean, _one_issues).shape[0] == 1

    # The prompt-change date is read from notes, and the adjusted comparison
    # must contradict the naive one on the sample week.
    change_date = find_prompt_change_date(clean_df)
    assert change_date == pd.Timestamp("2026-08-04"), change_date
    assert find_prompt_change_date(_one_clean) is None, "no note -> no change date"
    pc = prompt_change_comparison(clean_df, issues, change_date).set_index("workflow")
    assert pc.shape[0] == 3, pc.shape
    # Lead summary: +4.4pp naive, exactly flat once the flagged spike row goes.
    assert abs(pc.loc["Lead summary", "delta_naive"] - 0.0435) < 0.002, pc.loc["Lead summary", "delta_naive"]
    assert abs(pc.loc["Lead summary", "delta_adj"]) < 0.005, pc.loc["Lead summary", "delta_adj"]
    # Reply draft: about half the apparent damage was the policy-change row.
    assert abs(pc.loc["Reply draft", "delta_adj"] + 0.031) < 0.005, pc.loc["Reply draft", "delta_adj"]
    # Feedback clustering carries no high-severity rows, so adjusting is a no-op.
    assert pc.loc["Feedback clustering", "rows_excluded"] == 0
    assert abs(pc.loc["Feedback clustering", "delta_naive"] - pc.loc["Feedback clustering", "delta_adj"]) < 1e-9
    assert prompt_change_comparison(clean_df, issues, None).empty

    print(
        f"OK: {clean_df.shape[0]} clean rows, "
        f"team set is exactly {set(clean_df['team'].unique())}, "
        f"median_confidence NaN count={clean_df['median_confidence'].isna().sum()}, "
        f"user_rating NaN count={clean_df['user_rating'].isna().sum()}, "
        f"{len(issues)} issues detected, {rollup.shape[0]} rollup rows"
        f"; Wilson intervals, single-group CSV, and prompt-change comparison OK"
    )
