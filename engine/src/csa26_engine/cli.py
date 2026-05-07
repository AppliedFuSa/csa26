"""CLI-Entry der csa26-engine — wird von der GitHub-Action ausgeführt.

Liest Konfiguration aus `CSA26_*`-Environment-Variablen (siehe
`action.yml`-Inputs), läuft `analyze()` über alle `.c`-Dateien im
`src-dir`, schreibt Job Summary, Inline-Annotations und SARIF.

Konsistent mit der Phase-1-Action-Schnittstelle: dieselben Inputs,
dieselben Outputs.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .engine import analyze, filter_by_severity_at_least
from .findings import Finding, Severity
from .outputs import write_annotations, write_job_summary, write_sarif
from .preprocessor import SourceLoader

DEFAULT_WORKSPACE = Path("/github/workspace")
WORKSPACE_ENV = "GITHUB_WORKSPACE"
ACTION_OUTPUT_ENV = "GITHUB_OUTPUT"


@dataclass(frozen=True, slots=True)
class Config:
    workspace: Path
    src_dir: Path
    rule_set: str
    severity_threshold: Severity
    fail_on_findings: bool
    sarif_output: Path
    include_paths: tuple[Path, ...]
    defines: tuple[str, ...]
    undefines: tuple[str, ...]

    @classmethod
    def from_env(cls, env: dict[str, str]) -> Config:
        workspace = Path(_value_or(env, WORKSPACE_ENV, str(DEFAULT_WORKSPACE)))
        return cls(
            workspace=workspace,
            src_dir=workspace / _value_or(env, "CSA26_SRC_DIR", "."),
            rule_set=_value_or(env, "CSA26_RULE_SET", "misra-c-2012"),
            severity_threshold=_severity_from_str(
                _value_or(env, "CSA26_SEVERITY_THRESHOLD", "warning")
            ),
            fail_on_findings=_truthy(_value_or(env, "CSA26_FAIL_ON_FINDINGS", "false")),
            sarif_output=workspace / _value_or(env, "CSA26_SARIF_OUTPUT", "csa26.sarif"),
            include_paths=tuple(
                (workspace / entry).resolve(strict=False)
                for entry in _parse_multiline(env.get("CSA26_INCLUDE_PATHS", ""))
            ),
            defines=_parse_multiline(env.get("CSA26_DEFINES", "")),
            undefines=_parse_multiline(env.get("CSA26_UNDEFINES", "")),
        )


def main(argv: list[str] | None = None) -> int:  # noqa: ARG001
    config = Config.from_env(dict(os.environ))

    if config.rule_set != "misra-c-2012":
        sys.stderr.write(
            f"::error::csa26-engine v0.x supports only rule-set 'misra-c-2012', "
            f"got {config.rule_set!r}.\n"
        )
        return 2

    if not config.src_dir.exists():
        sys.stderr.write(f"::error::src-dir does not exist: {config.src_dir}\n")
        return 2

    sources = list(_collect_c_sources(config.src_dir))
    if not sources:
        sys.stdout.write(f"csa26-engine: no .c files found under {config.src_dir}\n")
        _write_action_outputs(sarif_file=config.sarif_output, finding_count=0)
        return 0

    loader = SourceLoader(include_paths=config.include_paths)
    define_dict = _defines_to_dict(config.defines)

    sys.stdout.write(f"::group::csa26-engine — analysing {len(sources)} source file(s)\n")
    if config.include_paths:
        sys.stdout.write(f"  include paths: {len(config.include_paths)}\n")
        for p in config.include_paths:
            sys.stdout.write(f"    -I {p}\n")
    if config.defines:
        sys.stdout.write(f"  defines: {', '.join(config.defines)}\n")
    sys.stdout.write("::endgroup::\n")

    all_findings: list[Finding] = []
    for src_path in sources:
        rel_file = _relative_to(src_path, config.workspace)
        try:
            findings = analyze(
                src_path.read_text(encoding="utf-8"),
                file=rel_file,
                source_loader=loader,
                defines=define_dict,
                undefines=tuple(config.undefines),
            )
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"::error file={rel_file}::csa26-engine failed on {rel_file}: {exc}\n")
            return 3
        all_findings.extend(findings)

    filtered = filter_by_severity_at_least(all_findings, config.severity_threshold)
    src_relative = _relative_to(config.src_dir, config.workspace)

    write_job_summary(filtered, threshold=config.severity_threshold, src_dir=src_relative)
    write_annotations(filtered)
    write_sarif(filtered, sarif_path=config.sarif_output, src_dir=src_relative)
    _write_action_outputs(sarif_file=config.sarif_output, finding_count=len(filtered))

    sys.stdout.write(
        f"csa26-engine: {len(filtered)} finding(s) at or above severity "
        f"'{config.severity_threshold.value}'.\n"
    )

    if config.fail_on_findings and filtered:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _value_or(env: dict[str, str], key: str, default: str) -> str:
    raw = env.get(key, default) or default
    stripped = raw.strip()
    return stripped or default


def _truthy(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_multiline(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(line.strip() for line in value.splitlines() if line.strip())


def _severity_from_str(value: str) -> Severity:
    normalized = (value or "").strip().lower()
    if normalized in {"error"}:
        return Severity.ERROR
    if normalized in {"warning"}:
        return Severity.WARNING
    return Severity.NOTE  # erlaubt auch "note", "information", "style"


def _defines_to_dict(defines: tuple[str, ...]) -> dict[str, str]:
    """`NAME=value` → dict; `NAME` allein → leerer String (vom Preprocessor
    als Default-`1` interpretiert)."""
    out: dict[str, str] = {}
    for entry in defines:
        if "=" in entry:
            name, _, value = entry.partition("=")
            out[name.strip()] = value
        else:
            out[entry.strip()] = ""
    return out


def _collect_c_sources(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix == ".c":
        yield root
        return
    yield from sorted(root.rglob("*.c"))


def _relative_to(path: Path, workspace: Path) -> str:
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
