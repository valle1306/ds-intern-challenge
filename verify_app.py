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

import pandas as pd
from streamlit.testing.v1 import AppTest

from data_processing import load_raw, clean
from ui_helpers import concern_tag, source_level_rollup, _rate_comparison_data

SAMPLE_CSV = "sample-data/product_usage_events.csv"


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

print("OK: pure-function checks passed (concern_tag, _rate_comparison_data, source_level_rollup)")

# ---------------------------------------------------------------------------
# app.py
# ---------------------------------------------------------------------------
at = AppTest.from_file("app.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.metric) == 4, len(at.metric)
assert len(at.dataframe) >= 1
_md = _non_css_markdown(at)
assert any("sd-hero" in m.value for m in _md), "hero header not found"
assert any("sd-tag-strip" in m.value for m in _md), "concern-tag strip not found"
print("OK: app.py")

# ---------------------------------------------------------------------------
# pages/1_Workflow_Explorer.py -- drive the selectbox through all 3 options
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/1_Workflow_Explorer.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.selectbox) == 1

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
print("OK: pages/1_Workflow_Explorer.py (all 3 workflows, change-point annotation correctly gated)")

# ---------------------------------------------------------------------------
# pages/2_Data_Trust_Center.py -- drive both multiselects
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/2_Data_Trust_Center.py")
at.run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.multiselect) == 2
assert any("sd-tag-strip" in m.value for m in _non_css_markdown(at))

at.multiselect[0].unselect(at.multiselect[0].value[0]).run(timeout=30)
assert not at.exception

at.multiselect[1].set_value([]).run(timeout=30)
assert not at.exception
print("OK: pages/2_Data_Trust_Center.py (multiselect combinations, including empty)")

# ---------------------------------------------------------------------------
# pages/3_Upload_Your_Own_Week.py -- no file, valid sample, malicious CSV
# ---------------------------------------------------------------------------
at = AppTest.from_file("pages/3_Upload_Your_Own_Week.py")
at.run(timeout=30)
assert not at.exception
assert len(at.info) >= 1
print("OK: pages/3_Upload_Your_Own_Week.py (no file uploaded)")

at = AppTest.from_file("pages/3_Upload_Your_Own_Week.py")
at.run(timeout=30)
with open(SAMPLE_CSV, "rb") as f:
    content = f.read()
at.file_uploader[0].set_value(("product_usage_events.csv", content, "text/csv")).run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
assert len(at.metric) == 4
assert any("sd-tag-strip" in m.value for m in _non_css_markdown(at))
print("OK: pages/3_Upload_Your_Own_Week.py (real sample CSV)")

# Malicious/messy notes text must render HTML-escaped, not raw. The notes
# text must contain the literal substring "small sample" (case-insensitive)
# to actually reach an issue description -- detect_issues' small_sample
# detector is the only path that embeds raw notes text verbatim (repr'd) into
# a description; other categories don't quote notes text directly. Spread
# across 2 distinct (team, workflow, source) groups (not 1) to avoid a
# pre-existing, out-of-scope bug in data_processing.detect_issues on pandas
# 3.0.2 where a groupby().apply(include_groups=False) reindex step raises a
# ValueError when a CSV's rows collapse to exactly one (team, workflow,
# source) group -- not introduced by this change, not fixed here, tracked as
# a known limitation.
_malicious_csv = (
    "date,team,workflow,source,sessions,completed,accepted_output,flagged_for_review,"
    "avg_minutes_saved,median_confidence,user_rating,notes\n"
    "2026-08-01,Sales,Lead summary,email,10,8,7,1,5,0.8,4,"
    '"<script>alert(1)</script> & <b>bold</b> small sample"\n'
    "2026-08-02,Sales,Lead summary,manual,10,8,7,1,5,0.8,4,ok\n"
)
at = AppTest.from_file("pages/3_Upload_Your_Own_Week.py")
at.run(timeout=30)
at.file_uploader[0].set_value(("malicious.csv", _malicious_csv.encode(), "text/csv")).run(timeout=30)
assert not at.exception, [str(e) for e in at.exception]
_rendered = "\n".join(m.value for m in at.markdown)
assert "&lt;script&gt;" in _rendered, "expected HTML-escaped script tag not found"
assert "<script>" not in _rendered, "raw unescaped script tag leaked into rendered output"
print("OK: pages/3_Upload_Your_Own_Week.py (malicious CSV renders HTML-escaped, no injection)")

print()
print("ALL CHECKS PASSED")
