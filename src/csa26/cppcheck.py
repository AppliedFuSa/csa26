"""Cppcheck-Aufruf und XML-Output-Parsing.

Wir rufen Cppcheck mit dem MISRA-Addon (`misra.py`) im klassischen
„use --rule-texts=<file>"-Modus auf und ignorieren das Hint-Geplänkel
in den Messages — die fachliche Beschreibung liefert csa26 aus dem
eigenen `rules/`-Asset (siehe `rules.py`).
"""

from __future__ import annotations

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .findings import Finding, Severity

CPPCHECK_BIN = "cppcheck"
DEFAULT_ADDONS_DIR = Path("/usr/share/cppcheck/addons")
ADDONS_DIR_ENV = "CSA26_CPPCHECK_ADDONS_DIR"

_RULE_TEXTS_HINT = re.compile(
    r"\s*\(use --rule-texts=<file> to get proper output\)\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CppcheckRun:
    returncode: int
    xml_path: Path
    stderr: str


def resolve_addons_dir() -> Path:
    raw = os.environ.get(ADDONS_DIR_ENV)
    return Path(raw) if raw else DEFAULT_ADDONS_DIR


def resolve_misra_addon() -> Path:
    addons_dir = resolve_addons_dir()
    candidate = addons_dir / "misra.py"
    if not candidate.is_file():
        raise FileNotFoundError(
            f"misra.py addon not found at {candidate}. "
            f"Set {ADDONS_DIR_ENV} or install cppcheck with addons."
        )
    return candidate


def run_cppcheck(src_dir: Path, output_xml: Path) -> CppcheckRun:
    """Führt Cppcheck mit MISRA-Addon aus und schreibt XML-Output."""
    misra_py = resolve_misra_addon()
    output_xml.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        CPPCHECK_BIN,
        "--enable=warning,style,performance,portability,information",
        "--inline-suppr",
        "--quiet",
        f"--addon={misra_py}",
        "--xml",
        "--xml-version=2",
        f"--output-file={output_xml}",
        str(src_dir),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return CppcheckRun(
        returncode=completed.returncode,
        xml_path=output_xml,
        stderr=completed.stderr,
    )


def parse_cppcheck_xml(xml_path: Path) -> list[Finding]:
    """Parst Cppcheck-XML und liefert eine flache Finding-Liste.

    Bei mehreren `<location>` pro `<error>` wird die erste verwendet
    (Cppcheck stellt in der Regel den primären Fundort an die erste
    Position; weitere Locations sind Stack-Trace-artig und für eine
    einzelne Annotation weniger nützlich).
    """
    if not xml_path.is_file() or xml_path.stat().st_size == 0:
        return []

    tree = ET.parse(xml_path)
    root = tree.getroot()
    findings: list[Finding] = []
    for error in root.iter("error"):
        rule_id = error.attrib.get("id", "").strip()
        if not rule_id:
            continue
        severity = Severity.from_str(error.attrib.get("severity", ""))
        message = _clean_message(error.attrib.get("msg", ""))
        location = error.find("location")
        if location is None:
            # Cppcheck-Findings ohne Location (z.B. Tool-Konfig-Probleme)
            # werden in v0.1 unterdrückt — sie haben im PR-Diff keinen
            # sinnvollen Anker.
            continue
        file_path = location.attrib.get("file", "")
        try:
            line = int(location.attrib.get("line", "0") or 0)
        except ValueError:
            line = 0
        try:
            column = int(location.attrib.get("column", "0") or 0)
        except ValueError:
            column = 0
        findings.append(
            Finding(
                rule_id=rule_id,
                severity=severity,
                message=message,
                file=file_path,
                line=line,
                column=column,
            )
        )
    return findings


def _clean_message(raw: str) -> str:
    """Entfernt den `--rule-texts`-Hint, den misra.py per Default mit
    in jede Meldung schreibt, wenn keine Volltext-Datei mitgegeben wird.
    Wir wollen diesen Volltext bewusst nicht — siehe NOTICE / MISRA-
    Lizenzhinweis. Der Hint ist nur Rauschen für csa26-Nutzer."""
    return _RULE_TEXTS_HINT.sub(" ", raw).strip()
