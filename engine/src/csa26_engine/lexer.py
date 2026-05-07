"""C-Lexer für csa26-engine.

Skelett — wird in den nächsten Iterationen ausgebaut. Aktueller
Stand: Token-Klassifikation steht (`tokens.py`), aber die
Tokenizer-Logik ist nur als Stub angelegt, damit das Skelett
import- und testbar ist.

Reihenfolge der Implementierungs-Schritte (Plan):

1. Whitespace + Kommentare verschlucken
2. Identifier + Keywords
3. Integer-Constants (dezimal, hex, oktal, mit Suffixen)
4. Float-Constants
5. Char-Constants und String-Literals (mit Escape-Sequenzen)
6. Punctuators (alle 49 ISO-C99-Punctuators)
7. Header-Namen im Preprocessor-Kontext (`<…>` / `"…"` nach `#include`)
"""

from __future__ import annotations

from .tokens import SourceLocation, Token, TokenKind


class LexerError(ValueError):
    def __init__(self, message: str, location: SourceLocation) -> None:
        super().__init__(f"{location}: {message}")
        self.location = location


def tokenize(source: str, *, file: str = "<input>") -> list[Token]:
    """Zerlegt `source` in eine Token-Liste.

    Stub — wirft `NotImplementedError`. Die echte Implementation kommt
    in der nächsten Iteration; hier nur die Signatur, damit der Rest
    der Engine sich darauf beziehen kann.
    """
    raise NotImplementedError(
        "Lexer noch nicht implementiert — Skelett-Stand. "
        "Siehe engine/README.md für die Implementations-Reihenfolge."
    )


__all__ = ["tokenize", "LexerError", "Token", "TokenKind", "SourceLocation"]
