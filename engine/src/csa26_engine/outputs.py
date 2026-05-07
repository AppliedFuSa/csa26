"""Output-Formate für csa26-engine.

Drei parallele Repräsentationen einer `list[Finding]`:

1. Job-Summary-Markdown (für `$GITHUB_STEP_SUMMARY`).
2. GitHub-Workflow-Annotations (`::warning file=…`-Format).
3. SARIF 2.1.0 (für den Security-Tab).

Entspricht funktional den Phase-1-Outputs aus `src/csa26/outputs.py`,
ist aber direkt auf das `Finding`-Format der Engine zugeschnitten
und nutzt die Rule-Titles aus `rules.ALL_RULES` als Beschreibung.
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
from .rules import ALL_RULES, Rule

JOB_SUMMARY_ENV = "GITHUB_STEP_SUMMARY"

_SEVERITY_LABEL = {
    Severity.ERROR: "Error",
    Severity.WARNING: "Warning",
    Severity.NOTE: "Note",
}

_SEVERITY_ORDER: tuple[Severity, ...] = (Severity.ERROR, Severity.WARNING, Severity.NOTE)


def _rule_index() -> dict[str, Rule]:
    return {rule.rule_id: rule for rule in ALL_RULES}


# ---------------------------------------------------------------------------
# Job Summary
# ---------------------------------------------------------------------------


def render_job_summary(findings: list[Finding], *, threshold: Severity, src_dir: str) -> str:
    rules_by_id = _rule_index()
    by_severity: dict[Severity, list[Finding]] = defaultdict(list)
    for f in findings:
        by_severity[f.severity].append(f)

    lines: list[str] = []
    lines.append("## csa26 — MISRA-C:2012 pre-audit")
    lines.append("")
    lines.append(
        f"**Total findings:** {len(findings)}  •  "
        f"**Severity threshold:** `{threshold.value}`  •  "
        f"**Scanned:** `{src_dir}`"
    )
    lines.append("")

    if not findings:
        lines.append("No findings at or above the configured severity threshold. ✅")
        lines.append("")
        lines.append("---")
        lines.append(
            f"_csa26-engine v{__version__} — pre-audit tool. "
            "Does not replace formal MISRA-C:2012 compliance assessment._"
        )
        return "\n".join(lines)

    lines.append("| Severity | Count |")
    lines.append("|---|---:|")
    for sev in _SEVERITY_ORDER:
        count = len(by_severity.get(sev, []))
        if count:
            lines.append(f"| {_SEVERITY_LABEL[sev]} | {count} |")
    lines.append("")

    for sev in _SEVERITY_ORDER:
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"### {_SEVERITY_LABEL[sev]} ({len(items)})")
        lines.append("")
        lines.append("| Rule | File | Line | Description |")
        lines.append("|---|---|---:|---|")
        for f in items:
            rule = rules_by_id.get(f.rule_id)
            title = rule.title if rule is not None else f.rule_id
            description = _shorten(f.message or title, 140)
            row = (
                f"| `{_md_escape(f.rule_id)}` | "
                f"`{_md_escape(f.location.file)}` | "
                f"{f.location.line} | "
                f"{_md_escape(description)} |"
            )
            lines.append(row)
        lines.append("")

    lines.append("---")
    lines.append(
        f"_csa26-engine v{__version__} — pre-audit tool. "
        "Findings produced by the in-tree engine (no third-party static analyser). "
        "Rule descriptions are csa26-original paraphrases; "
        "csa26 does not redistribute verbatim MISRA rule text._"
    )
    return "\n".join(lines)


def write_job_summary(
    findings: list[Finding],
    *,
    threshold: Severity,
    src_dir: str,
    summary_path: Path | None = None,
) -> None:
    target = summary_path or _job_summary_target_from_env()
    if target is None:
        return
    rendered = render_job_summary(findings, threshold=threshold, src_dir=src_dir)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(rendered)
        fh.write("\n")


def _job_summary_target_from_env() -> Path | None:
    raw = os.environ.get(JOB_SUMMARY_ENV)
    return Path(raw) if raw else None


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _shorten(value: str, limit: int) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Inline-Annotations
# ---------------------------------------------------------------------------


def write_annotations(findings: Iterable[Finding], *, stream: TextIO | None = None) -> None:
    out = stream or sys.stdout
    for f in findings:
        out.write(format_annotation(f))
        out.write("\n")


def format_annotation(f: Finding) -> str:
    rule = _rule_index().get(f.rule_id)
    title = rule.title if rule is not None else f.rule_id
    annotation_title = f"{title} [{f.rule_id}]"
    body = f"[{f.rule_id}] {f.message or title}"
    parts = [f"file={_escape_property(f.location.file)}"]
    if f.location.line > 0:
        parts.append(f"line={f.location.line}")
    if f.location.column > 0:
        parts.append(f"col={f.location.column}")
    parts.append(f"title={_escape_property(annotation_title)}")
    level = _annotation_level(f.severity)
    return f"::{level} {','.join(parts)}::{_escape_data(body)}"


def _annotation_level(severity: Severity) -> str:
    if severity is Severity.ERROR:
        return "error"
    if severity is Severity.WARNING:
        return "warning"
    return "notice"


def _escape_property(value: str) -> str:
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


def write_sarif(findings: list[Finding], *, sarif_path: Path, src_dir: str) -> None:
    sarif = build_sarif(findings, src_dir=src_dir)
    sarif_path.parent.mkdir(parents=True, exist_ok=True)
    sarif_path.write_text(json.dumps(sarif, indent=2), encoding="utf-8")


def build_sarif(findings: list[Finding], *, src_dir: str) -> dict:
    rules_by_id = _rule_index()
    rule_descriptors: dict[str, dict] = {}
    results: list[dict] = []
    for f in findings:
        rule = rules_by_id.get(f.rule_id)
        title = rule.title if rule is not None else f.rule_id
        if f.rule_id not in rule_descriptors:
            rule_descriptors[f.rule_id] = {
                "id": f.rule_id,
                "name": title,
                "shortDescription": {"text": title},
                "fullDescription": {"text": title},
                "defaultConfiguration": {"level": _sarif_level(f.severity)},
                "properties": {
                    "category": "MISRA-C:2012",
                    "rule_set": "misra-c-2012",
                },
            }
        results.append(
            {
                "ruleId": f.rule_id,
                "level": _sarif_level(f.severity),
                "message": {"text": f.message or title},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f.location.file,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": _sarif_region(f),
                        }
                    }
                ],
                "properties": {"severity": f.severity.value},
            }
        )

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "csa26-engine",
                        "version": __version__,
                        "informationUri": "https://github.com/AppliedFuSa/csa26",
                        "rules": list(rule_descriptors.values()),
                    }
                },
                "originalUriBaseIds": {"%SRCROOT%": {"uri": f"file://{src_dir}/"}},
                "results": results,
            }
        ],
    }


def _sarif_level(sev: Severity) -> str:
    if sev is Severity.ERROR:
        return "error"
    if sev is Severity.WARNING:
        return "warning"
    return "note"


def _sarif_region(f: Finding) -> dict:
    region: dict[str, int] = {}
    if f.location.line > 0:
        region["startLine"] = f.location.line
    if f.location.column > 0:
        region["startColumn"] = f.location.column
    if not region:
        region["startLine"] = 1
    return region


__all__ = [
    "render_job_summary",
    "write_job_summary",
    "write_annotations",
    "format_annotation",
    "write_sarif",
    "build_sarif",
]
