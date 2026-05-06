"""Lookup eigener Regel-Paraphrasen aus dem `rules/`-Asset.

Pro MISRA-C:2012-Regel pflegen wir eine Markdown-Datei
`rules/c2012/<rule-number>.md` mit einer 1–2-Satz-Paraphrase und
einem eigenen Mini-Code-Beispiel. csa26 redistribuiert keinen
wortgetreuen MISRA-Rule-Text — siehe NOTICE.

Format der Markdown-Datei:

    ---
    rule_id: c2012-8.13
    title: Kurzer eigener Titel der Regel
    ---

    Kurze eigene Beschreibung in 1–2 Sätzen.

    ```c
    /* Eigenes Code-Beispiel */
    ```

Frontmatter ist optional — fehlt sie, wird der erste Markdown-Absatz
als Beschreibung genommen und der Titel aus der Rule-Nummer gebaut.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RULES_DIR = Path("/opt/csa26/rules")
RULES_DIR_ENV = "CSA26_RULES_DIR"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass(frozen=True, slots=True)
class RuleDescription:
    rule_id: str  # csa26-interner Schlüssel, z.B. „c2012-8.13"
    title: str  # eigene Kurzfassung (für Annotations-Title)
    description: str  # eigene Paraphrase (für SARIF + Job Summary)
    is_placeholder: bool


def resolve_rules_dir() -> Path:
    raw = os.environ.get(RULES_DIR_ENV)
    return Path(raw) if raw else DEFAULT_RULES_DIR


def lookup_rule(rule_id: str, rules_dir: Path | None = None) -> RuleDescription:
    """Lookup über csa26-Rule-Schlüssel (z.B. „c2012-8.13").

    Falls Cppcheck eine ID wie „misra-c2012-8.13" liefert, vorher mit
    `normalize_rule_id` umwandeln.
    """
    base = rules_dir or resolve_rules_dir()
    canonical = normalize_rule_id(rule_id)
    candidate = base / "c2012" / f"{_rule_number(canonical)}.md"
    if not candidate.is_file():
        return _placeholder(canonical)
    return _parse_rule_file(canonical, candidate)


def normalize_rule_id(rule_id: str) -> str:
    """Cppcheck schreibt „misra-c2012-X.Y", csa26 intern „c2012-X.Y"."""
    rid = (rule_id or "").strip().lower()
    if rid.startswith("misra-"):
        rid = rid[len("misra-") :]
    return rid


def _rule_number(canonical_id: str) -> str:
    # „c2012-8.13" → „8.13"
    if canonical_id.startswith("c2012-"):
        return canonical_id[len("c2012-") :]
    return canonical_id


def _placeholder(canonical_id: str) -> RuleDescription:
    return RuleDescription(
        rule_id=canonical_id,
        title=f"MISRA C:2012 Rule {_rule_number(canonical_id)}",
        description=(
            "Eigene Regel-Beschreibung folgt — csa26 redistribuiert keinen "
            "wortgetreuen MISRA-Text. Siehe rules/c2012/ im Repo."
        ),
        is_placeholder=True,
    )


def _parse_rule_file(canonical_id: str, path: Path) -> RuleDescription:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    title = f"MISRA C:2012 Rule {_rule_number(canonical_id)}"
    body = raw

    if match:
        frontmatter = match.group(1)
        body = match.group(2)
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            if key.strip().lower() == "title":
                value = value.strip()
                if value:
                    title = value

    description = _first_paragraph(body)
    return RuleDescription(
        rule_id=canonical_id,
        title=title,
        description=description,
        is_placeholder=False,
    )


def _first_paragraph(body: str) -> str:
    paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    return paragraphs[0]
