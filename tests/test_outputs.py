import json
from pathlib import Path

from csa26.findings import Finding, Severity
from csa26.outputs import (
    build_sarif,
    format_annotation,
    render_job_summary,
    write_job_summary,
)
from csa26.rules import RuleDescription


def _rule(rule_id: str = "misra-c2012-8.13") -> RuleDescription:
    return RuleDescription(
        rule_id=rule_id.replace("misra-", ""),
        title="Const-Korrektheit für Lese-Pointer",
        description="Pointer auf nicht-modifizierte Ziele sollen const-qualifiziert sein.",
        is_placeholder=False,
    )


def _placeholder_lookup(rule_id: str) -> RuleDescription:
    return _rule(rule_id)


def _finding(
    rule_id: str = "misra-c2012-8.13",
    severity: Severity = Severity.STYLE,
    file: str = "src/main.c",
    line: int = 42,
    column: int = 5,
) -> Finding:
    return Finding(rule_id, severity, "raw msg", file, line, column)


# --- Job Summary ----------------------------------------------------------


def test_render_job_summary_with_no_findings():
    out = render_job_summary([], _placeholder_lookup, threshold=Severity.STYLE, src_dir=".")
    assert "No findings" in out
    assert "Total findings:** 0" in out


def test_render_job_summary_groups_by_severity():
    findings = [
        _finding(severity=Severity.ERROR, line=10),
        _finding(severity=Severity.STYLE, line=20),
        _finding(severity=Severity.STYLE, line=30),
    ]
    out = render_job_summary(findings, _placeholder_lookup, threshold=Severity.STYLE, src_dir="src")
    assert "Total findings:** 3" in out
    assert "### Error (1)" in out
    assert "### Style (2)" in out
    # Severity-Counts-Tabelle
    assert "| Error | 1 |" in out
    assert "| Style | 2 |" in out


def test_write_job_summary_appends_to_file(tmp_path: Path):
    summary = tmp_path / "summary.md"
    write_job_summary(
        [_finding()],
        _placeholder_lookup,
        threshold=Severity.STYLE,
        src_dir=".",
        summary_path=summary,
    )
    content = summary.read_text(encoding="utf-8")
    assert "csa26 — MISRA-C:2012 pre-audit" in content


# --- Annotations ----------------------------------------------------------


def test_format_annotation_uses_warning_for_style():
    line = format_annotation(_finding(severity=Severity.STYLE), _rule())
    assert line.startswith("::notice ")
    assert "file=src/main.c" in line
    assert "line=42" in line
    assert "col=5" in line


def test_format_annotation_uses_error_level_for_error():
    line = format_annotation(_finding(severity=Severity.ERROR), _rule())
    assert line.startswith("::error ")


def test_format_annotation_prefixes_message_with_rule_id():
    """Reviewer im PR muss am Annotation-Text direkt erkennen, welche
    Regel das war — `title=`-Property wird in vielen UI-Stellen nicht
    angezeigt, der sichtbare Text dahinter dagegen immer."""
    line = format_annotation(_finding(), _rule())
    body = line.split("::", 2)[2]
    assert body.startswith("[misra-c2012-8.13] ")


def test_format_annotation_escapes_commas_in_path():
    finding = _finding(file="src/odd,name.c")
    line = format_annotation(finding, _rule())
    assert "file=src/odd%2Cname.c" in line


# --- SARIF ----------------------------------------------------------------


def test_build_sarif_minimal_structure():
    sarif = build_sarif(
        [_finding(severity=Severity.STYLE)],
        _placeholder_lookup,
        src_dir=".",
    )
    assert sarif["version"] == "2.1.0"
    runs = sarif["runs"]
    assert len(runs) == 1

    driver = runs[0]["tool"]["driver"]
    assert driver["name"] == "csa26"
    assert any(rule["id"] == "misra-c2012-8.13" for rule in driver["rules"])

    results = runs[0]["results"]
    assert len(results) == 1
    result = results[0]
    assert result["ruleId"] == "misra-c2012-8.13"
    assert result["level"] == "note"  # style → note
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "src/main.c"
    assert location["region"]["startLine"] == 42


def test_build_sarif_serializable_to_json():
    sarif = build_sarif([_finding()], _placeholder_lookup, src_dir=".")
    # Wirft, falls etwas nicht JSON-serialisierbar ist
    json.dumps(sarif)


def test_build_sarif_dedupes_rule_definitions():
    findings = [
        _finding(line=1),
        _finding(line=2),
        _finding(line=3),
    ]
    sarif = build_sarif(findings, _placeholder_lookup, src_dir=".")
    rules = sarif["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1
    assert len(sarif["runs"][0]["results"]) == 3
