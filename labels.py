"""Presentation-only display-name metadata shared by app.py and every page
in pages/. No pandas or streamlit imports -- pure lookup tables so any file
can import this cheaply and stay consistent.
"""

COLUMN_LABELS: dict[str, str] = {
    "category": "Issue type",
    "date": "Date",
    "team": "Team",
    "workflow": "Workflow",
    "source": "Source",
    "description": "Description",
    "severity": "Severity",
    "sessions": "Sessions",
    "completed": "Completed",
    "accepted_output": "Accepted output",
    "flagged_for_review": "Flagged for review",
    "avg_minutes_saved": "Avg. minutes saved",
    "median_confidence": "Median confidence",
    "user_rating": "User rating",
    "notes": "Notes",
    "completion_rate": "Completion rate",
    "acceptance_rate": "Acceptance rate",
    "flag_rate": "Flag rate",
    "sessions_total": "Total sessions",
    "n_issues": "Issues flagged",
    "row_count": "Row count",
    # Wilson interval bounds are numeric; the UI collapses them into the single
    # display string `completion_ci` via ui_helpers.with_ci_display.
    "completion_lo": "Completion rate low",
    "completion_hi": "Completion rate high",
    "completion_ci": "Completion rate 95% CI",
    # Prompt-change comparison (data_processing.prompt_change_comparison).
    "completion_before": "Before",
    "completion_after": "After (all rows)",
    "delta_naive": "Change (all rows)",
    "completion_before_adj": "Before (excl. flagged)",
    "completion_after_adj": "After (excl. flagged)",
    "delta_adj": "Change (excl. flagged)",
    "sessions_after": "Sessions after",
    "sessions_after_adj": "Sessions after (excl. flagged)",
    "rows_excluded": "Rows excluded",
}

CATEGORY_LABELS: dict[str, str] = {
    "duplicate_row": "Duplicate row",
    "invalid_numeric_literal": "Invalid numeric value",
    "missing_value": "Missing value",
    "label_inconsistency": "Team-name inconsistency",
    "missing_expected_row": "Missing expected row",
    "suspicious_spike": "Suspicious spike",
    "confidence_quality_divergence": "Confidence vs. quality divergence",
    "small_sample": "Small sample",
}
