"""Datentypen für csa26-Findings und Severity-Ordnung."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import total_ordering


@total_ordering
class Severity(Enum):
    """Cppcheck-Severities, sortiert von ernst nach informativ.

    Reihenfolge entspricht der Cppcheck-Konvention:
    error > warning > style > performance > portability > information.
    """

    ERROR = ("error", 0)
    WARNING = ("warning", 1)
    STYLE = ("style", 2)
    PERFORMANCE = ("performance", 3)
    PORTABILITY = ("portability", 4)
    INFORMATION = ("information", 5)

    def __init__(self, label: str, rank: int) -> None:
        self.label = label
        self.rank = rank

    @classmethod
    def from_str(cls, value: str) -> Severity:
        normalized = (value or "").strip().lower()
        for member in cls:
            if member.label == normalized:
                return member
        return cls.INFORMATION

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Severity):
            return NotImplemented
        # "kleiner" = ernster — passt zu „mindestens so ernst wie".
        return self.rank < other.rank

    def at_least_as_severe_as(self, threshold: Severity) -> bool:
        return self.rank <= threshold.rank


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    file: str
    line: int
    column: int

    @property
    def is_misra(self) -> bool:
        return self.rule_id.startswith("misra-")

    @property
    def misra_rule_number(self) -> str | None:
        """„misra-c2012-8.13" → „8.13"."""
        if not self.is_misra:
            return None
        prefix = "misra-c2012-"
        if self.rule_id.startswith(prefix):
            return self.rule_id[len(prefix) :]
        # Fallback: alles nach dem letzten „-".
        return self.rule_id.rsplit("-", 1)[-1]
