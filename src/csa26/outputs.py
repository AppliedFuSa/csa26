"""Drei parallele Outputs für einen csa26-Lauf:

1. Job Summary — Markdown an `$GITHUB_STEP_SUMMARY` angehängt.
2. Inline-Annotations — `::warning file=...`-Zeilen auf stdout.
3. SARIF 2.1.0 — JSON-Datei im Workspace, vom Nutzer per
   `actions/upload-sarif` in den Security-Tab geladen.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from . import __version__
from .findings import Finding, Severity
from .rules import RuleDescription

JOB_SUMMARY_ENV = "GITHUB_STEP_SUMMARY"

_SEVERITY_LABEL_DE = {
    Severity.ERROR: "Error",
    Severity.WARNING: "Warning",
    Severity.STYLE: "Style",
    Severity.PERFORMANCE: "Performance",
    Severity.PORTABILITY: "Portability",
    Severity.INFORMATION: "Information",
}


# ---------------------------------------------------------------------------
# Job Summary (Markdown)
# ---------------------------------------------------------------------------


def write_job_summary(
    findings: Iterable[Finding],
    rule_lookup,
    *,
    threshold: Severity,
    src_dir: str,
    summary_path: Path | None = None,
) -> None:
    target = summary_path or _job_summary_target()
    if target is None:
        return
    rendered = render_job_summary(list(findings), rule_lookup, threshold=threshold, src_dir=src_dir)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(rendered)
        fh.write("\n")


def render_job_summary(
    findings: list[Finding],
    rule_lookup,
    *,
    threshold: Severity,
    src_dir: str,
) -> str:
    by_severity: dict[Severity, list[Finding]] = defaultdict(list)
    for finding in findings:
        by_severity[finding.severity].append(finding)

    total = len(findings)
    lines: list[str] = []
    lines.append("## csa26 — MISRA-C:2012 pre-audit")
    lines.append("")
    lines.append(
        f"**Total findings:** {total}  •  "
        f"**Severity threshold:** `{threshold.label}`  •  "
        f"**Scanned:** `{src_dir}`"
    )
    lines.append("")
    if total == 0:
        lines.append("No findings at or above the configured severity threshold. ✅")
        lines.append("")
        lines.append("---")
        lines.append(
            f"_csa26 v{__version__} — pre-audit tool. "
            "Does not replace formal MISRA-C:2012 compliance assessment._"
        )
        return "\n".join(lines)

    # Counts pro Severity
    lines.append("| Severity | Count |")
    lines.append("|---|---:|")
    for severity in Severity:
        count = len(by_severity.get(severity, []))
        if count == 0:
            continue
        lines.append(f"| {_SEVERITY_LABEL_DE[severity]} | {count} |")
    lines.append("")

    # Detail-Tabelle pro Severity
    for severity in Severity:
        items = by_severity.get(severity, [])
        if not items:
            continue
        lines.append(f"### {_SEVERITY_LABEL_DE[severity]} ({len(items)})")
        lines.append("")
        lines.append("| Rule | File | Line | Description |")
        lines.append("|---|---|---:|---|")
        for finding in items:
            rule = rule_lookup(finding.rule_id)
            description = _shorten(rule.description or finding.message, 140)
            rule_id = _md_escape(finding.rule_id)
            file = _md_escape(finding.file)
            desc = _md_escape(description)
            lines.append(f"| `{rule_id}` | `{file}` | {finding.line} | {desc} |")
        lines.append("")

    lines.append("---")
    lines.append(
        f"_csa26 v{__version__} — pre-audit tool. "
        "Findings are based on Cppcheck + MISRA addon. "
        "Rule descriptions are csa26-original paraphrases; "
        "csa26 does not redistribute verbatim MISRA rule text._"
    )
    return "\n".join(lines)


def _job_summary_target() -> Path | None:
    raw = os.environ.get(JOB_SUMMARY_ENV)
    if not raw:
        return None
    return Path(raw)


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _shorten(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Inline-Annotations (GitHub workflow commands)
# ---------------------------------------------------------------------------


def write_annotations(
    findings: Iterable[Finding],
    rule_lookup,
    *,
    stream: TextIO | None = None,
) -> None:
    out = stream or sys.stdout
    for finding in findings:
        rule = rule_lookup(finding.rule_id)
        line = format_annotation(finding, rule)
        out.write(line)
        out.write("\n")


def format_annotation(finding: Finding, rule: RuleDescription) -> str:
    level = _annotation_level(finding.severity)
    title = f"{rule.title} [{finding.rule_id}]"
    message = rule.description or finding.message or rule.title
    parts = [f"file={_escape_property(finding.file)}"]
    if finding.line > 0:
        parts.append(f"line={finding.line}")
    if finding.column > 0:
        parts.append(f"col={finding.column}")
    parts.append(f"title={_escape_property(title)}")
    return f"::{level} {','.join(parts)}::{_escape_data(message)}"


def _annotation_level(severity: Severity) -> str:
    if severity == Severity.ERROR:
        return "error"
    if severity == Severity.WARNING:
        return "warning"
    return "notice"


def _escape_property(value: str) -> str:
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


# ---------------------------------------------------------------------------
# SARIF 2.1.0
# ---------------------------------------------------------------------------

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)


def write_sarif(
    findings: list[Finding],
    rule_lookup,
    *,
    sarif_path: Path,
    src_dir: str,
) -> None:
    sarif = build_sarif(findings, rule_lookup, src_dir=src_dir)
    sarif_path.parent.mkdir(parents=True, exist_ok=True)
    sarif_path.write_text(json.dumps(sarif, indent=2), encoding="utf-8")


def build_sarif(findings: list[Finding], rule_lookup, *, src_dir: str) -> dict:
    rules_by_id: dict[str, dict] = {}
    results: list[dict] = []

    for finding in findings:
        rule = rule_lookup(finding.rule_id)
        if finding.rule_id not in rules_by_id:
            rules_by_id[finding.rule_id] = {
                "id": finding.rule_id,
                "name": rule.title,
                "shortDescription": {"text": rule.title},
                "fullDescription": {"text": rule.description or rule.title},
                "defaultConfiguration": {
                    "level": _sarif_level(finding.severity),
                },
                "properties": {
                    "category": "MISRA-C:2012",
                    "rule_set": "misra-c-2012",
                    "csa26_paraphrase": not rule.is_placeholder,
                },
            }
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": _sarif_level(finding.severity),
                "message": {
                    "text": rule.description or finding.message or rule.title,
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding.file,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": _sarif_region(finding),
                        }
                    }
                ],
                "properties": {
                    "severity": finding.severity.label,
                },
            }
        )

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "csa26",
                        "version": __version__,
                        "informationUri": "https://github.com/AppliedFuSa/csa26",
                        "rules": list(rules_by_id.values()),
                    }
                },
                "originalUriBaseIds": {"%SRCROOT%": {"uri": f"file://{src_dir}/"}},
                "results": results,
            }
        ],
    }


def _sarif_level(severity: Severity) -> str:
    if severity == Severity.ERROR:
        return "error"
    if severity == Severity.WARNING:
        return "warning"
    return "note"


def _sarif_region(finding: Finding) -> dict:
    region: dict[str, int] = {}
    if finding.line > 0:
        region["startLine"] = finding.line
    if finding.column > 0:
        region["startColumn"] = finding.column
    if not region:
        # SARIF benötigt mindestens ein Region-Feld; Default Zeile 1.
        region["startLine"] = 1
    return region
