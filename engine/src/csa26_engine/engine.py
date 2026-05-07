"""Top-Level-API der csa26-engine.

Eine Funktion: `analyze()` führt die ganze Pipeline durch:
roher Quellcode → Lexer → Preprocessor → Parser → Symbol-Resolution
→ Type-Inference → Rules → sortierte Findings-Liste.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .findings import Finding, Severity
from .parser import parse
from .preprocessor import Preprocessor, SourceLoader
from .rules import ALL_RULES, AnalysisContext, Rule
from .symbols import bind
from .types import infer_types


def analyze(
    source: str,
    *,
    file: str = "<input>",
    include_paths: tuple[Path, ...] = (),
    defines: dict[str, str] | None = None,
    undefines: tuple[str, ...] = (),
    source_loader: SourceLoader | None = None,
    rules: Iterable[Rule] | None = None,
) -> list[Finding]:
    """Komplette Pipeline. Liefert eine sortierte Findings-Liste
    (nach Datei, dann Zeile, dann Spalte, dann Rule-ID)."""
    pp = Preprocessor(
        include_paths=include_paths,
        defines=defines or {},
        undefines=undefines,
        source_loader=source_loader,
    )
    tokens = pp.process(source=source, file=file)
    tu = parse(tokens)
    bindings = bind(tu)
    types = infer_types(bindings)
    ctx = AnalysisContext(
        tu=tu,
        bindings=bindings,
        types=types,
        used_macro_names=frozenset(pp.used_macro_names),
        user_macros=dict(pp.user_macros),
    )
    findings: list[Finding] = []
    selected = tuple(rules) if rules is not None else ALL_RULES
    for rule in selected:
        for finding in rule.check(ctx):
            findings.append(finding)
    findings.sort(
        key=lambda f: (
            f.location.file,
            f.location.line,
            f.location.column,
            f.rule_id,
        )
    )
    return findings


def filter_by_severity_at_least(findings: list[Finding], threshold: Severity) -> list[Finding]:
    rank = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.NOTE: 2}
    threshold_rank = rank[threshold]
    return [f for f in findings if rank[f.severity] <= threshold_rank]


__all__ = ["analyze", "filter_by_severity_at_least"]
