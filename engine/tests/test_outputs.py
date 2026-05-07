"""Unit-Tests für die Output-Formate."""

import json
from pathlib import Path

from csa26_engine.findings import Finding, Severity
from csa26_engine.outputs import (
    build_sarif,
    format_annotation,
    render_job_summary,
    write_job_summary,
)
from csa26_engine.tokens import SourceLocation


def _f(rule_id="misra-c2012-8.4", severity=Severity.WARNING, line=10):
    return Finding(
        rule_id=rule_id,
        severity=severity,
        message="reason for the finding",
        location=SourceLocation("src/main.c", line, 5),
    )


# --- Job Summary -------------------------------------------------------------


def test_render_job_summary_zero_findings():
    out = render_job_summary([], threshold=Severity.WARNING, src_dir=".")
    assert "Total findings:** 0" in out
    assert "No findings" in out


def test_render_job_summary_groups_by_severity():
    findings = [
        _f(severity=Severity.ERROR, line=10),
        _f(severity=Severity.WARNING, line=20),
        _f(severity=Severity.WARNING, line=21),
        _f(severity=Severity.NOTE, line=30),
    ]
    out = render_job_summary(findings, threshold=Severity.NOTE, src_dir="src")
    assert "Total findings:** 4" in out
    assert "### Error (1)" in out
    assert "### Warning (2)" in out
    assert "### Note (1)" in out


def test_write_job_summary_appends_to_file(tmp_path: Path):
    summary = tmp_path / "summary.md"
    write_job_summary(
        [_f()],
        threshold=Severity.WARNING,
        src_dir=".",
        summary_path=summary,
    )
    content = summary.read_text(encoding="utf-8")
    assert "csa26 — MISRA-C:2012 pre-audit" in content


# --- Annotations -------------------------------------------------------------


def test_annotation_uses_warning_level_for_warning():
    line = format_annotation(_f(severity=Severity.WARNING))
    assert line.startswith("::warning ")
    assert "file=src/main.c" in line
    assert "line=10" in line


def test_annotation_uses_notice_level_for_note():
    line = format_annotation(_f(severity=Severity.NOTE))
    assert line.startswith("::notice ")


def test_annotation_uses_error_level_for_error():
    line = format_annotation(_f(severity=Severity.ERROR))
    assert line.startswith("::error ")


def test_annotation_includes_rule_id_in_visible_message():
    line = format_annotation(_f())
    body = line.split("::", 2)[2]
    assert body.startswith("[misra-c2012-8.4] ")


# --- SARIF -------------------------------------------------------------------


def test_sarif_minimal_structure():
    sarif = build_sarif([_f()], src_dir=".")
    assert sarif["version"] == "2.1.0"
    runs = sarif["runs"]
    assert len(runs) == 1
    driver = runs[0]["tool"]["driver"]
    assert driver["name"] == "csa26-engine"
    assert any(rule["id"] == "misra-c2012-8.4" for rule in driver["rules"])
    results = runs[0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "misra-c2012-8.4"
    assert results[0]["level"] == "warning"


def test_sarif_serialises_to_json_cleanly():
    sarif = build_sarif([_f()], src_dir=".")
    json.dumps(sarif)


def test_sarif_dedupes_repeated_rule_ids():
    findings = [_f(line=1), _f(line=2), _f(line=3)]
    sarif = build_sarif(findings, src_dir=".")
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1
    assert len(sarif["runs"][0]["results"]) == 3
