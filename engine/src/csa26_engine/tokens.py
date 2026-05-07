"""Token-Typen und Source-Locations für den csa26-Engine-Lexer.

Die Token-Klassifikation orientiert sich an ISO/IEC 9899:1999 §6.4.
GCC-Extensions, die wir akzeptieren (z.B. `__attribute__`, statement-
expressions), bekommen Standard-Tokens — die Spezial-Behandlung
erfolgt im Parser, nicht im Lexer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    # Klassen aus ISO C99 §6.4
    KEYWORD = auto()
    IDENTIFIER = auto()
    CONSTANT = auto()  # Integer, Float, Char-Konstante
    STRING_LITERAL = auto()
    PUNCTUATOR = auto()

    # Hilfs-Token, kein C-Original
    NEWLINE = auto()  # für den Preprocessor relevant
    WHITESPACE = auto()  # wird vom Lexer normalerweise verschluckt
    COMMENT = auto()  # wird vom Lexer normalerweise verschluckt

    # Preprocessing-spezifische Tokens (vor PP), §6.4.7 / §6.10
    PP_HEADER_NAME = auto()  # <stdio.h> / "local.h"
    PP_HASH = auto()  # # am Zeilenanfang im PP-Modus
    PP_HASH_HASH = auto()  # ##

    # Sentinel
    EOF = auto()


# Alle 37 C99-Keywords plus die GCC-Extensions, die wir als Keyword
# behandeln (statt als Identifier weiterleiten).
C99_KEYWORDS: frozenset[str] = frozenset(
    {
        "auto",
        "break",
        "case",
        "char",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extern",
        "float",
        "for",
        "goto",
        "if",
        "inline",
        "int",
        "long",
        "register",
        "restrict",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "struct",
        "switch",
        "typedef",
        "union",
        "unsigned",
        "void",
        "volatile",
        "while",
        "_Bool",
        "_Complex",
        "_Imaginary",
    }
)

# GCC-Extension-Keywords, die wir als eigenes Keyword durchreichen.
# Der Parser darf sie ignorieren oder gezielt konsumieren; der Lexer
# gibt nicht den Identifier-Namespace dafür her.
GCC_EXTENSION_KEYWORDS: frozenset[str] = frozenset(
    {
        "__attribute__",
        "__asm__",
        "__inline__",
        "__inline",
        "__restrict__",
        "__restrict",
        "__signed__",
        "__signed",
        "__volatile__",
        "__volatile",
        "__const__",
        "__const",
        "__typeof__",
        "__typeof",
        "__extension__",
        "asm",  # GCC-Konvention; ohne -std=c99-strict ist `asm` ein Keyword
    }
)

ALL_KEYWORDS: frozenset[str] = C99_KEYWORDS | GCC_EXTENSION_KEYWORDS


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Position im Quelltext — 1-basiert für `file:line:col` zur
    Konsistenz mit Compiler- und IDE-Konventionen."""

    file: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    text: str
    location: SourceLocation

    def is_keyword(self, *names: str) -> bool:
        return self.kind is TokenKind.KEYWORD and self.text in names

    def is_punctuator(self, *symbols: str) -> bool:
        return self.kind is TokenKind.PUNCTUATOR and self.text in symbols

    def is_identifier(self, *names: str) -> bool:
        if self.kind is not TokenKind.IDENTIFIER:
            return False
        return not names or self.text in names
