"""C-Lexer für csa26-engine.

Handgeschriebener Character-by-Character-Lexer. Bewusst ohne
Regex-Engine, damit jede Erkennungs-Entscheidung in Code sichtbar
ist und im Audit nachvollziehbar bleibt.

Sprach-Scope (ISO/IEC 9899:1999 §6.4):
- Whitespace und Kommentare (`/* */`, `//`) werden verschluckt.
- NEWLINE-Tokens werden produziert — der Preprocessor braucht sie.
- Identifier + 37 C99-Keywords + 16 GCC-Extension-Keywords.
- Integer-Konstanten dezimal/hex/oktal mit Suffixen u/U/l/L/ll/LL.
- Float-Konstanten dezimal und hex (`0x1.fp10`-Form), Suffixe f/F/l/L.
- Char-Konstanten und String-Literale, mit Escape-Sequenzen
  (`\\n`, `\\t`, `\\xHH`, `\\NNN`-oktal, …) und L-Präfix.
- ISO-C99-Punctuators (longest-match-first: 3-Zeichen vor 2-Zeichen
  vor 1-Zeichen).

Bekannte Phase-1-Limitationen:
- Backslash-Newline-Line-Splicing (ISO C99 Translation Phase 2)
  passiert hier nicht. Der Preprocessor muss das vor dem Lexer
  übernehmen, sonst sind Multi-Line-Identifier kaputt.
- Digraphen (`<:`, `:>`, `<%`, `%>`, `%:`, `%:%:`) werden noch nicht
  erkannt — sehr selten in modernem Embedded-Code.
- Trigraphs (ISO Phase 1) werden nicht ersetzt.
"""

from __future__ import annotations

from .tokens import ALL_KEYWORDS, SourceLocation, Token, TokenKind


class LexerError(ValueError):
    def __init__(self, message: str, location: SourceLocation) -> None:
        super().__init__(f"{location}: {message}")
        self.location = location


# ISO-C99-Punctuators, sortiert nach Länge absteigend (longest-match-first).
_PUNCTUATORS_3 = ("...", "<<=", ">>=")
_PUNCTUATORS_2 = (
    "->",
    "++",
    "--",
    "<<",
    ">>",
    "<=",
    ">=",
    "==",
    "!=",
    "&&",
    "||",
    "*=",
    "/=",
    "%=",
    "+=",
    "-=",
    "&=",
    "|=",
    "^=",
    "##",
)
_PUNCTUATORS_1 = tuple("[](){}.&*+-~!/%<>^|?:;=,#")


def tokenize(source: str, *, file: str = "<input>") -> list[Token]:
    """Zerlegt `source` in eine Token-Liste.

    Returnt eine flache Liste in Reihenfolge des Auftretens, mit
    `EOF`-Sentinel-Token am Ende.
    """
    return _Lexer(source, file).run()


class _Lexer:
    __slots__ = ("source", "file", "pos", "line", "column", "tokens")

    def __init__(self, source: str, file: str) -> None:
        self.source = source
        self.file = file
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    # ------------------------------------------------------------------ utils

    def _here(self) -> SourceLocation:
        return SourceLocation(self.file, self.line, self.column)

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else ""

    def _starts_with(self, needle: str) -> bool:
        return self.source.startswith(needle, self.pos)

    def _advance(self, n: int = 1) -> str:
        consumed = self.source[self.pos : self.pos + n]
        for ch in consumed:
            if ch == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        self.pos += n
        return consumed

    def _emit(self, kind: TokenKind, text: str, location: SourceLocation) -> None:
        self.tokens.append(Token(kind, text, location))

    # ------------------------------------------------------------------ main

    def run(self) -> list[Token]:
        while self.pos < len(self.source):
            ch = self._peek()

            if ch == "\n":
                loc = self._here()
                self._advance()
                self._emit(TokenKind.NEWLINE, "\n", loc)
                continue

            if ch in " \t\r\v\f":
                self._advance()
                continue

            if ch == "/" and self._peek(1) == "*":
                self._skip_block_comment()
                continue

            if ch == "/" and self._peek(1) == "/":
                self._skip_line_comment()
                continue

            # Wide-Char- bzw. Wide-String-Literal: L'…' oder L"…" — muss
            # vor dem Identifier-Branch geprüft werden, weil 'L' sonst
            # als Identifier gelext wird.
            if ch == "L" and self._peek(1) in ("'", '"'):
                self._advance()  # konsumiere 'L'
                next_ch = self._peek()
                if next_ch == "'":
                    self._lex_char_constant(prefix="L")
                else:
                    self._lex_string_literal(prefix="L")
                continue

            if ch == "_" or ch.isalpha():
                self._lex_identifier_or_keyword()
                continue

            if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                self._lex_number()
                continue

            if ch == "'":
                self._lex_char_constant(prefix="")
                continue

            if ch == '"':
                self._lex_string_literal(prefix="")
                continue

            if self._lex_punctuator():
                continue

            raise LexerError(f"unexpected character {ch!r}", self._here())

        self._emit(TokenKind.EOF, "", self._here())
        return self.tokens

    # ------------------------------------------------------------------ comments

    def _skip_block_comment(self) -> None:
        start = self._here()
        self._advance(2)  # konsumiere '/*'
        while self.pos < len(self.source):
            if self._starts_with("*/"):
                self._advance(2)
                return
            self._advance()
        raise LexerError("unterminated block comment", start)

    def _skip_line_comment(self) -> None:
        self._advance(2)  # konsumiere '//'
        while self.pos < len(self.source) and self._peek() != "\n":
            self._advance()

    # ------------------------------------------------------------------ identifiers

    def _lex_identifier_or_keyword(self) -> None:
        start_loc = self._here()
        start_pos = self.pos
        while self.pos < len(self.source) and self._is_ident_continuation(self._peek()):
            self._advance()
        text = self.source[start_pos : self.pos]
        kind = TokenKind.KEYWORD if text in ALL_KEYWORDS else TokenKind.IDENTIFIER
        self._emit(kind, text, start_loc)

    @staticmethod
    def _is_ident_continuation(ch: str) -> bool:
        return ch == "_" or ch.isalnum()

    # ------------------------------------------------------------------ numbers

    def _lex_number(self) -> None:
        start_loc = self._here()
        start_pos = self.pos
        is_hex = False

        if self._peek() == "0" and self._peek(1) in ("x", "X"):
            self._advance(2)
            is_hex = True
            while self.pos < len(self.source) and (
                self._peek().isdigit() or self._peek().lower() in "abcdef"
            ):
                self._advance()
        else:
            while self.pos < len(self.source) and self._peek().isdigit():
                self._advance()

        # Float-Anteil: '.', dann optional weitere Ziffern, dann optional Exponent.
        is_float = False
        if self._peek() == ".":
            is_float = True
            self._advance()
            while self.pos < len(self.source) and (
                self._peek().isdigit() or (is_hex and self._peek().lower() in "abcdef")
            ):
                self._advance()

        # Exponent: 'e' / 'E' für dezimal, 'p' / 'P' für hex-float.
        # Achtung: `"" in "eE"` ist in Python True, daher explizit auf
        # nicht-leeres Zeichen prüfen.
        exp_chars = "pP" if is_hex else "eE"
        exp_ch = self._peek()
        if exp_ch and exp_ch in exp_chars:
            is_float = True
            self._advance()
            sign_ch = self._peek()
            if sign_ch and sign_ch in "+-":
                self._advance()
            if not self._peek().isdigit():
                raise LexerError("expected digit after exponent", self._here())
            while self.pos < len(self.source) and self._peek().isdigit():
                self._advance()

        # Suffixe für Integer (u/U/l/L/ll/LL/ul/UL/...) bzw. Float (f/F/l/L)
        self._consume_number_suffix(is_float=is_float)

        text = self.source[start_pos : self.pos]
        self._emit(TokenKind.CONSTANT, text, start_loc)

    def _consume_number_suffix(self, *, is_float: bool) -> None:
        if is_float:
            ch = self._peek()
            if ch and ch in "fFlL":
                self._advance()
            return

        # Integer: u/U und l/L/ll/LL können in beliebiger Reihenfolge stehen.
        # `"" in "uU"` ist True in Python — daher explizit auf nicht-leeres
        # Zeichen prüfen.
        seen_unsigned = False
        seen_long = 0
        while True:
            ch = self._peek()
            if not ch:
                break
            if ch in "uU" and not seen_unsigned:
                seen_unsigned = True
                self._advance()
                continue
            if ch in "lL" and seen_long < 2:
                # ll/LL nur in gleicher Schreibweise zulassen.
                if seen_long == 1 and self._peek(-1) != ch:
                    raise LexerError("mixed long suffix (Ll/lL not allowed)", self._here())
                seen_long += 1
                self._advance()
                continue
            break

    # ------------------------------------------------------------------ char and string

    def _lex_char_constant(self, *, prefix: str) -> None:
        start_loc = self._here()
        start_pos = self.pos - len(prefix)  # Prefix wurde bereits konsumiert
        self._advance()  # konsumiere "'"
        while self.pos < len(self.source) and self._peek() != "'":
            if self._peek() == "\n":
                raise LexerError("unterminated char constant", start_loc)
            if self._peek() == "\\":
                self._advance()
                if self.pos >= len(self.source):
                    raise LexerError("unterminated escape in char constant", start_loc)
            self._advance()
        if self._peek() != "'":
            raise LexerError("unterminated char constant", start_loc)
        self._advance()  # closing "'"
        text = self.source[start_pos : self.pos]
        self._emit(TokenKind.CONSTANT, text, start_loc)

    def _lex_string_literal(self, *, prefix: str) -> None:
        start_loc = self._here()
        start_pos = self.pos - len(prefix)
        self._advance()  # konsumiere '"'
        while self.pos < len(self.source) and self._peek() != '"':
            if self._peek() == "\n":
                raise LexerError("unterminated string literal", start_loc)
            if self._peek() == "\\":
                self._advance()
                if self.pos >= len(self.source):
                    raise LexerError("unterminated escape in string literal", start_loc)
            self._advance()
        if self._peek() != '"':
            raise LexerError("unterminated string literal", start_loc)
        self._advance()  # closing '"'
        text = self.source[start_pos : self.pos]
        self._emit(TokenKind.STRING_LITERAL, text, start_loc)

    # ------------------------------------------------------------------ punctuators

    def _lex_punctuator(self) -> bool:
        for punct in _PUNCTUATORS_3:
            if self._starts_with(punct):
                loc = self._here()
                text = self._advance(3)
                kind = TokenKind.PUNCTUATOR
                self._emit(kind, text, loc)
                return True
        for punct in _PUNCTUATORS_2:
            if self._starts_with(punct):
                loc = self._here()
                text = self._advance(2)
                # ## ist nur im Preprocessor-Kontext relevant — aber der
                # Parser sieht eh nur die Post-Preprocessor-Tokens, hier
                # markieren wir alles als PUNCTUATOR und differenzieren erst
                # im Preprocessor.
                self._emit(TokenKind.PUNCTUATOR, text, loc)
                return True
        ch = self._peek()
        if ch in _PUNCTUATORS_1:
            loc = self._here()
            self._advance()
            self._emit(TokenKind.PUNCTUATOR, ch, loc)
            return True
        return False


__all__ = ["tokenize", "LexerError", "Token", "TokenKind", "SourceLocation"]
