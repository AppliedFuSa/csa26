"""Entry point der csa26-GitHub-Action.

Ablauf:

1. Konfiguration aus `CSA26_*`-Env-Vars lesen.
2. Cppcheck mit MISRA-Addon auf `src-dir` ausführen.
3. XML-Output parsen, Findings nach Severity-Threshold filtern.
4. Drei Outputs schreiben: Job Summary, Inline-Annotations, SARIF.
5. GitHub-Action-Outputs (`sarif-file`, `finding-count`) schreiben.
6. Exit-Code abhängig von `fail-on-findings`.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .cppcheck import parse_cppcheck_xml, run_cppcheck
from .findings import Finding, Severity
from .outputs import write_annotations, write_job_summary, write_sarif
from .rules import RuleDescription, lookup_rule, resolve_rules_dir

DEFAULT_WORKSPACE = Path("/github/workspace")
WORKSPACE_ENV = "GITHUB_WORKSPACE"
ACTION_OUTPUT_ENV = "GITHUB_OUTPUT"


@dataclass(frozen=True, slots=True)
class Config:
    src_dir: Path
    rule_set: str
    severity_threshold: Severity
    fail_on_findings: bool
    sarif_output: Path
    workspace: Path
    include_paths: tuple[Path, ...]
    defines: tuple[str, ...]
    undefines: tuple[str, ...]

    @classmethod
    def from_env(cls, env: dict[str, str]) -> Config:
        workspace = Path(_value_or(env, WORKSPACE_ENV, str(DEFAULT_WORKSPACE)))
        include_paths = tuple(
            (workspace / entry).resolve(strict=False)
            for entry in parse_multiline(env.get("CSA26_INCLUDE_PATHS", ""))
        )
        return cls(
            src_dir=workspace / _value_or(env, "CSA26_SRC_DIR", "."),
            rule_set=_value_or(env, "CSA26_RULE_SET", "misra-c-2012"),
            severity_threshold=Severity.from_str(
                _value_or(env, "CSA26_SEVERITY_THRESHOLD", "style")
            ),
            fail_on_findings=_truthy(_value_or(env, "CSA26_FAIL_ON_FINDINGS", "false")),
            sarif_output=workspace / _value_or(env, "CSA26_SARIF_OUTPUT", "csa26.sarif"),
            workspace=workspace,
            include_paths=include_paths,
            defines=parse_multiline(env.get("CSA26_DEFINES", "")),
            undefines=parse_multiline(env.get("CSA26_UNDEFINES", "")),
        )


def _value_or(env: dict[str, str], key: str, default: str) -> str:
    """`os.environ.get` mit Default für Blank-Werte. GitHub Actions
    passes leere Strings für Inputs, die einen Default haben — der
    Default greift dort nur, wenn der Key komplett fehlt. Der Wrapper
    will in beiden Fällen denselben Effekt."""
    raw = env.get(key, default) or default
    stripped = raw.strip()
    return stripped or default


def _truthy(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def parse_multiline(value: str) -> tuple[str, ...]:
    """Multiline-Action-Input → Tuple aus nicht-leeren, gestrippten Zeilen."""
    if not value:
        return ()
    return tuple(line.strip() for line in value.splitlines() if line.strip())


def filter_misra_only(findings: list[Finding]) -> tuple[list[Finding], int]:
    """Behält nur MISRA-Findings, zählt Cppcheck-Built-ins als gedroppt.

    csa26 ist ein gezieltes MISRA-C:2012-Pre-Audit. Cppcheck-Built-in-
    Findings (z.B. `nullPointer`, `constParameterPointer`) sind in diesem
    Tool Rauschen, weil wir keine eigene Regel-Beschreibung dafür haben
    und der Reviewer nicht erwartet, sie hier zu sehen.
    """
    misra = [f for f in findings if f.is_misra]
    return misra, len(findings) - len(misra)


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
    config = Config.from_env(dict(os.environ))

    if config.rule_set != "misra-c-2012":
        sys.stderr.write(
            f"::error::csa26 v0.1 supports only rule-set 'misra-c-2012', got '{config.rule_set}'.\n"
        )
        return 2

    if not config.src_dir.exists():
        sys.stderr.write(f"::error::src-dir does not exist: {config.src_dir}\n")
        return 2

    xml_path = config.workspace / ".csa26" / "cppcheck-report.xml"
    sys.stdout.write(f"::group::csa26 — running cppcheck on {config.src_dir}\n")
    if config.include_paths:
        sys.stdout.write(f"  include paths: {len(config.include_paths)}\n")
        for path in config.include_paths:
            sys.stdout.write(f"    -I {path}\n")
    if config.defines:
        sys.stdout.write(f"  defines: {', '.join(config.defines)}\n")
    if config.undefines:
        sys.stdout.write(f"  undefines: {', '.join(config.undefines)}\n")
    run = run_cppcheck(
        config.src_dir,
        xml_path,
        include_paths=config.include_paths,
        defines=config.defines,
        undefines=config.undefines,
    )
    if run.stderr.strip():
        sys.stdout.write(run.stderr)
    sys.stdout.write("::endgroup::\n")

    if run.returncode not in (0, 1):
        # Cppcheck liefert Returncode 1 bei gefundenen Issues — das ist
        # für uns OK. Andere Codes signalisieren Tool-/Konfig-Fehler.
        sys.stderr.write(f"::error::cppcheck failed with exit code {run.returncode}\n")
        return run.returncode or 3

    findings = parse_cppcheck_xml(xml_path)
    misra_findings, dropped_non_misra = filter_misra_only(findings)
    if dropped_non_misra:
        sys.stdout.write(
            f"csa26: dropping {dropped_non_misra} non-MISRA cppcheck "
            "finding(s) (csa26 is a MISRA-C:2012 pre-audit tool).\n"
        )

    filtered = [
        finding
        for finding in misra_findings
        if finding.severity.at_least_as_severe_as(config.severity_threshold)
    ]
    filtered = [_relativize(finding, config.workspace) for finding in filtered]

    rules_dir = resolve_rules_dir()

    def lookup(rule_id: str) -> RuleDescription:
        return lookup_rule(rule_id, rules_dir=rules_dir)

    src_relative = _relative_to_workspace(config.src_dir, config.workspace)
    write_job_summary(filtered, lookup, threshold=config.severity_threshold, src_dir=src_relative)
    write_annotations(filtered, lookup)
    write_sarif(filtered, lookup, sarif_path=config.sarif_output, src_dir=src_relative)

    _write_action_outputs(
        sarif_file=config.sarif_output,
        finding_count=len(filtered),
    )

    sys.stdout.write(
        f"csa26: {len(filtered)} finding(s) at or above severity "
        f"'{config.severity_threshold.label}'.\n"
    )

    if config.fail_on_findings and filtered:
        return 1
    return 0


def _relativize(finding: Finding, workspace: Path) -> Finding:
    """Pfade relativ zum Workspace darstellen, damit GitHub die Annotation
    im PR-Diff korrekt platziert."""
    if not finding.file:
        return finding
    file_path = Path(finding.file)
    try:
        relative = file_path.resolve().relative_to(workspace.resolve())
    except (ValueError, OSError):
        return finding
    return Finding(
        rule_id=finding.rule_id,
        severity=finding.severity,
        message=finding.message,
        file=str(relative),
        line=finding.line,
        column=finding.column,
    )


def _relative_to_workspace(path: Path, workspace: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace.resolve())) or "."
    except (ValueError, OSError):
        return str(path)


def _write_action_outputs(*, sarif_file: Path, finding_count: int) -> None:
    target = os.environ.get(ACTION_OUTPUT_ENV)
    if not target:
        return
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(f"sarif-file={sarif_file}\n")
        fh.write(f"finding-count={finding_count}\n")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
