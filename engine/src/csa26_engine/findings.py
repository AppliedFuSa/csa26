"""Findings-Datentypen für csa26-engine.

Eine `Finding` ist das Ergebnis einer Rule-Auswertung — Rule-ID,
Severity, Message und Source-Location. Der Output-Layer nimmt die
Liste und produziert daraus Job Summary, Inline-Annotations und SARIF.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .tokens import SourceLocation


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass(frozen=True, slots=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    location: SourceLocation


__all__ = ["Finding", "Severity"]
