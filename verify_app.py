"""End-to-end verification for the SignalDesk Streamlit app.

Exercises every page via streamlit.testing.v1.AppTest (executes each page's
real script and inspects its element tree / exceptions -- no browser
required) plus plain-pandas checks on the new pure helper functions in
ui_helpers.py. Run with: python verify_app.py

This does NOT and cannot verify actual pixel-level appearance (colors,
spacing, whether the injected CSS renders as intended) -- AppTest inspects
structure and data, not rendered CSS. That stays a manual check against the
deployed app.
"""

import re

import pandas as pd
from streamlit.testing.v1 import AppTest

from data_processing import (
    clean,
    detect_issues,
    find_prompt_change_date,
    load_raw,
    prompt_change_comparison,
    weekly_rollup,
)
from ui_helpers import (
    _CUSTOM_CSS,
    _prompt_change_verdict,
    _rate_comparison_data,
    concern_tag,
    source_level_rollup,
    with_ci_display,
)

SAMPLE_CSV = "sample-data/product_usage_events.csv"

PAGES = [
    "app.py",
    "pages/1_Weekly_Findings.py",
    "pages/2_Workflow_Explorer.py",
    "pages/3_Data_Trust_Center.py",
    "pages/4_Upload_Your_Own_Week.py",
]


def _non_css_markdown(at):
    """Markdown elements that are NOT the injected <style> block -- CSS class
    names (e.g. .sd-tag-strip, .sd-callout--annotation) appear as literal
    selector text inside that block, which would otherwise false-positive
    any substring search for those same class names."""
    return [m for m in at.markdown if not m.value.strip().startswith("<style>")]


# ---------------------------------------------------------------------------
# Pure-function checks, real verified numbers -- no Streamlit involved
# ---------------------------------------------------------------------------
assert concern_tag(pd.DataFrame({"severity": ["high", "medium"]})) == ("Elevated concern", "sd-tag--elevated")
assert concern_tag(pd.DataFrame({"severity": ["medium", "low"]})) == ("Watch", "sd-tag--watch")
assert concern_tag(pd.DataFrame({"severity": []})) == ("Low concern", "sd-tag--low")
assert concern_tag(None) == ("Low concern", "sd-tag--low")
assert concern_tag(pd.DataFrame({"severity": pd.Series([], dtype=object)})) == ("Low concern", "sd-tag--low")

_rollup_stub = pd.DataFrame({
    "workflow": ["A"], "completion_rate": [0.8], "acceptance_rate": [0.7], "flag_rate": [0.1],
})
_chart_df = _rate_comparison_data(_rollup_stub)
assert list(_chart_df.columns) == ["Completion rate", "Acceptance rate", "Flag rate"]
assert _chart_df.loc["A", "Completion rate"] == 0.8
assert _rate_comparison_data(pd.DataFrame()).empty

_clean_df = clean(load_raw())
_wf_clean = _clean_df[_clean_df["workflow"] == "Lead summary"]
_src = source_level_rollup(_wf_clean).set_index("source")
assert abs(_src.loc["email", "completion_rate"] - 0.84) < 1e-6, _src.loc["email", "completion_rate"]
assert abs(_src.loc["manual", "completion_rate"] - 0.70) < 1e-6, _src.loc["manual", "completion_rate"]
assert source_level_rollup(pd.DataFrame()).empty

# with_ci_display: one readable interval column, raw bounds gone, order kept.
_issues = detect_issues(load_raw(), _clean_df)
_rollup = weekly_rollup(_clean_df, _issues)
_ci = with_ci_display(_rollup)
assert "completion_ci" in _ci.columns and "completion_lo" not in _ci.columns
assert list(_ci.columns).index("completion_ci") == list(_ci.columns).index("completion_rate") + 1
assert _ci.set_index("workflow").loc["Feedback clustering", "completion_ci"] == "60.0%-72.7%"
assert with_ci_display(pd.DataFrame()).empty

# The prompt-change verdict must name the workflow whose apparent effect
# collapses, and must stay silent when there is nothing to contradict.
_pc = prompt_change_comparison(_clean_df, _issues, find_prompt_change_date(_clean_df))
_verdict = _prompt_change_verdict(_pc)
assert _verdict and "Lead summary" in _verdict and "+0.0pp" in _verdict, _verdict
assert _prompt_change_verdict(pd.DataFrame()) is None
_flat = _pc.copy()
_flat["delta_adj"] = _flat["delta_naive"]
assert _prompt_change_verdict(_flat) is None, "no gap between naive and adjusted -> no verdict"

print("OK: pure-function checks passed (concern_tag, _rate_comparison_data, "
      "source_level_rollup, with_ci_display, _prompt_change_verdict)")

# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
at = AppTest.from_file("app.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
# Home is a launcher: it must stay free of tables and charts, or it will scroll.
assert len(at.dataframe) == 0, "Home must render no tables"
assert len(at.metric) == 0, "Home must render no KPI cards"
_md = _non_css_markdown(at)
assert any("sd-hero--compact" in m.value for m in _md), "compact hero not found"
assert any("sd-guide-card" in m.value for m in _md), "guidance cards not found"
# The verdict lines are computed from the pipeline, not written down.
_verdict = chr(10).join(m.value for m in _md)
assert "sd-stat-band" in _verdict, "hero stat band missing"
# Both hero figures are computed: the naive gain and the adjusted one it collapses to.
assert "+4.4pp" in _verdict and "+0.0pp" in _verdict, "hero stat figures wrong"
assert "The win was the row, not the" in _verdict, "hero stat conclusion missing"
assert "Feedback clustering" in _verdict, "worst-workflow finding missing"
assert "Confidence is not quality" in _verdict, "confidence finding missing"
# Navigation must actually render. An earlier version styled a testid that does
# not exist in the Streamlit bundle, so the links shipped bare and unnoticed.
_nav = at.get("page_link")
assert len(_nav) == 4, f"expected 4 nav page links, got {len(_nav)}"
_targets = {pl.page for pl in _nav}
assert _targets == {
    "Weekly_Findings", "Workflow_Explorer", "Data_Trust_Center", "Upload_Your_Own_Week"
}, _targets
print("OK: app.py (launcher: no tables/charts, computed hero stat, 4 nav links)")

# ---------------------------------------------------------------------------
# pages/1_Weekly_Findings.py -- the analysis, three tabs
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/1_Weekly_Findings.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.metric) == 4, len(at.metric)
_md = _non_css_markdown(at)
assert any("sd-tag-strip" in m.value for m in _md), "concern-tag strip not found"
assert any("not robust" in m.value for m in _md), "prompt-change verdict not rendered"
# The CI-backed ranking claim must take the computed non-overlap branch.
assert any("does not overlap" in s_.value for s_ in at.success), "CI ranking claim not rendered"
# All five next-actions render, collapsed, most urgent first.
_labels = [e.label for e in at.expander]
assert sum(1 for lbl in _labels if lbl.startswith("**High**")) == 2, _labels
assert any("Full weekly rollup table" in lbl for lbl in _labels), _labels
assert len([lbl for lbl in _labels if lbl.startswith("**")]) == 5, _labels
print("OK: pages/1_Weekly_Findings.py (3 tabs, CI claim, verdict, 5 collapsed actions)")

# ---------------------------------------------------------------------------
# pages/1_Workflow_Explorer.py -- drive the selectbox through all 3 options
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/2_Workflow_Explorer.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.selectbox) == 1
assert len(at.tabs) == 4, f"expected 4 detail tabs, got {len(at.tabs)}"

for option in ["Lead summary", "Reply draft", "Feedback clustering"]:
    at.selectbox[0].select(option).run(timeout=30)
    assert not at.exception, f"{option}: {[str(e) for e in at.exception]}"
    _md = _non_css_markdown(at)
    has_annotation = any("sd-callout--annotation" in m.value for m in _md)
    if option == "Reply draft":
        assert has_annotation, "change-point annotation missing for Reply draft"
        assert any("56.7%" in m.value for m in _md if "sd-callout--annotation" in m.value)
    else:
        assert not has_annotation, f"change-point annotation should not appear for {option}"
print("OK: pages/2_Workflow_Explorer.py (all 3 workflows, change-point annotation correctly gated)")

# ---------------------------------------------------------------------------
# pages/2_Data_Trust_Center.py -- drive both multiselects
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/3_Data_Trust_Center.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.multiselect) == 2
assert len(at.tabs) == 3, f"expected 3 tabs, got {len(at.tabs)}"
assert any("sd-tag-strip" in m.value for m in _non_css_markdown(at))

at.multiselect[0].unselect(at.multiselect[0].value[0]).run(timeout=30)
assert not at.exception

at.multiselect[1].set_value([]).run(timeout=30)
assert not at.exception
print("OK: pages/3_Data_Trust_Center.py (multiselect combinations, including empty)")

# ---------------------------------------------------------------------------
# pages/3_Upload_Your_Own_Week.py -- no file, valid sample, malicious CSV
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/4_Upload_Your_Own_Week.py")
at.run(timeout=30)
assert not at.exception
assert len(at.info) >= 1
print("OK: pages/4_Upload_Your_Own_Week.py (no file uploaded)")

at = AppTest.from_file("pages/4_Upload_Your_Own_Week.py")
at.run(timeout=30)
with open(SAMPLE_CSV, "rb") as f:
    content = f.read()
at.file_uploader[0].set_value(("product_usage_events.csv", content, "text/csv")).run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.metric) == 4
assert any("sd-tag-strip" in m.value for m in _non_css_markdown(at))
print("OK: pages/4_Upload_Your_Own_Week.py (real sample CSV)")

# Malicious/messy notes text must render HTML-escaped, not raw. The notes text
# must contain the literal substring "small sample" (case-insensitive) to
# actually reach an issue description -- detect_issues' small_sample detector is
# the only path that embeds raw notes text verbatim (repr'd) into a description.
#
# This fixture is deliberately a SINGLE (team, workflow, source) group, which
# also covers the pandas 3.0.x "Buffer dtype mismatch" crash that
# groupby().apply() used to raise on single-group frames -- now fixed by
# data_processing._group_flag_mask.
_malicious_csv = """date,team,workflow,source,sessions,completed,accepted_output,flagged_for_review,avg_minutes_saved,median_confidence,user_rating,notes
2026-08-01,Sales,Lead summary,email,10,8,7,1,5,0.8,4,"<script>alert(1)</script> & <b>bold</b> small sample"
2026-08-02,Sales,Lead summary,email,10,8,7,1,5,0.8,4,ok
"""

at = AppTest.from_file("pages/4_Upload_Your_Own_Week.py")
at.run(timeout=30)
at.file_uploader[0].set_value(("malicious.csv", _malicious_csv.encode(), "text/csv")).run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
_rendered = "\n".join(m.value for m in at.markdown)
assert "&lt;script&gt;" in _rendered, "expected HTML-escaped script tag not found"
assert "<script>" not in _rendered, "raw unescaped script tag leaked into rendered output"
print("OK: pages/4_Upload_Your_Own_Week.py (malicious CSV renders HTML-escaped, no injection)")


# ---------------------------------------------------------------------------
# Every CSS class the app emits must exist in the stylesheet.
#
# This exists because a real bug shipped: Home styled
# [data-testid="stPageLink"], a testid Streamlit does not emit, so the nav
# links rendered bare and nothing failed. Structural tests can't see styling,
# so the closest cheap guard is proving no element references a class that was
# never defined. The reverse direction is only reported, not asserted --
# sd-badge--default and sd-tag--low are legitimate fallbacks the sample week
# happens not to reach.
# ---------------------------------------------------------------------------
_defined = set(re.findall(r"\.(sd-[A-Za-z0-9_-]+)", _CUSTOM_CSS))
_used = set()
for _f in PAGES:
    _at = AppTest.from_file(_f)
    _at.run(timeout=30)
    for _m in _non_css_markdown(_at):
        for _attr in re.findall(r'class="([^"]+)"', _m.value):
            _used.update(t for t in _attr.split() if t.startswith("sd-"))

_undefined = sorted(_used - _defined)
assert not _undefined, f"CSS classes used but never defined (render unstyled): {_undefined}"
print(f"OK: all {len(_used)} emitted sd-* classes are defined "
      f"(unused fallbacks: {sorted(_defined - _used)})")

print()
print("ALL CHECKS PASSED")