"""C-Preprocessor für csa26-engine.

Implementiert ISO/IEC 9899:1999 §6.10 als Token-Stream-Transformation:
Lexer → Preprocessor → preprocesster Token-Stream.

Iteration 1 (dieser Modul-Stand):
- `#include "..."` und `#include <...>` mit Include-Path-Auflösung
- `#define NAME` und `#define NAME tokens…` (object-like)
- `#undef NAME`
- `#ifdef NAME` / `#ifndef NAME` / `#else` / `#endif` (verschachtelt)
- `#if defined(NAME)` und `#if 0 / #if 1`
- `#elif defined(NAME)`
- `#error message` / `#warning message`
- `#pragma`, `#line` werden parsed und ignoriert
- Object-like Macro-Expansion mit Hide-Set zur Rekursions-Prävention
- Predefined: `__FILE__`, `__LINE__`

Iteration 2 (folgt in einem zweiten Commit):
- Function-like Macros mit Parametern und `__VA_ARGS__`
- Token-Pasting `##`
- Stringification `#`
- Volle `#if`-Constant-Expression-Auswertung
- Adjacent String-Literal-Concatenation (ISO Phase 6)
- Backslash-Newline-Line-Splicing (ISO Phase 2)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .lexer import tokenize
from .tokens import SourceLocation, Token, TokenKind


class PreprocessorError(ValueError):
    def __init__(self, message: str, location: SourceLocation) -> None:
        super().__init__(f"{location}: {message}")
        self.location = location


# Predefined Macros, deren Wert beim Lookup-Time ausgewertet wird —
# liegen nicht in der `self.macros`-Tabelle, müssen aber separat
# erkannt werden.
_PREDEFINED_MACROS: frozenset[str] = frozenset({"__FILE__", "__LINE__"})


@dataclass(frozen=True, slots=True)
class Macro:
    name: str
    replacement: tuple[Token, ...]
    location: SourceLocation
    is_function_like: bool = False  # Iteration 2


@dataclass(slots=True)
class _CondFrame:
    """Conditional-Frame im `#if`-Stack.

    `taken` ist True, sobald irgendein Branch dieses `#if`-Blocks
    aktiv war — verhindert, dass `#elif` oder `#else` nochmal aktiviert.
    """

    active: bool
    taken: bool
    location: SourceLocation


# ---------------------------------------------------------------------------
# Source-Loading (für Header-Auflösung) — austauschbar für Tests
# ---------------------------------------------------------------------------


class SourceLoader:
    """Liest Header-Dateien anhand des `#include`-Header-Namens."""

    def __init__(self, include_paths: tuple[Path, ...] = ()) -> None:
        self.include_paths = include_paths

    def load(self, header_name: str, *, is_system: bool, requesting_file: str) -> tuple[Path, str]:
        candidates: list[Path] = []
        if not is_system:
            base = Path(requesting_file).parent
            candidates.append(base / header_name)
        candidates.extend(p / header_name for p in self.include_paths)
        for candidate in candidates:
            if candidate.is_file():
                return candidate, candidate.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"header {header_name!r} not found (searched: {[str(c) for c in candidates]})"
        )


class InMemorySourceLoader(SourceLoader):
    """Test-Loader: Header-Inhalte aus einem dict, kein Dateisystem."""

    def __init__(self, files: dict[str, str]) -> None:
        super().__init__(())
        self._files = files

    def load(self, header_name: str, *, is_system: bool, requesting_file: str) -> tuple[Path, str]:
        if header_name not in self._files:
            raise FileNotFoundError(f"header {header_name!r} not in test loader")
        return Path(header_name), self._files[header_name]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def preprocess(
    source: str,
    *,
    file: str = "<input>",
    include_paths: tuple[Path, ...] = (),
    defines: dict[str, str] | None = None,
    undefines: tuple[str, ...] = (),
    source_loader: SourceLoader | None = None,
) -> list[Token]:
    pp = Preprocessor(
        include_paths=include_paths,
        defines=defines or {},
        undefines=undefines,
        source_loader=source_loader,
    )
    return pp.process(source=source, file=file)


# ---------------------------------------------------------------------------
# Preprocessor
# ---------------------------------------------------------------------------


class Preprocessor:
    """Stateful Preprocessor — eine Instanz pro Übersetzungs-Einheit."""

    MAX_INCLUDE_DEPTH = 64

    def __init__(
        self,
        *,
        include_paths: tuple[Path, ...] = (),
        defines: dict[str, str] | None = None,
        undefines: tuple[str, ...] = (),
        source_loader: SourceLoader | None = None,
    ) -> None:
        self.macros: dict[str, Macro] = {}
        self.cond_stack: list[_CondFrame] = []
        self.diagnostics: list[tuple[str, str, SourceLocation]] = []
        self.source_loader = source_loader or SourceLoader(include_paths)
        self._include_depth = 0
        self._init_defines(defines or {}, undefines)

    def process(self, *, source: str, file: str) -> list[Token]:
        tokens = tokenize(source, file=file)
        out = self._run(tokens, file=file)
        if self.cond_stack:
            top = self.cond_stack[-1]
            raise PreprocessorError("unterminated conditional (missing #endif)", top.location)
        return out

    # ---- init -----------------------------------------------------------------

    def _init_defines(self, defines: dict[str, str], undefines: tuple[str, ...]) -> None:
        loc = SourceLocation("<command-line>", 0, 0)
        for name, value in defines.items():
            if value == "":
                replacement = (Token(TokenKind.CONSTANT, "1", loc),)
            else:
                replacement = tuple(
                    t for t in tokenize(value, file="<command-line>") if t.kind is not TokenKind.EOF
                )
            self.macros[name] = Macro(name=name, replacement=replacement, location=loc)
        for name in undefines:
            self.macros.pop(name, None)

    # ---- main loop ------------------------------------------------------------

    def _run(self, tokens: list[Token], *, file: str) -> list[Token]:
        out: list[Token] = []
        i = 0
        at_line_start = True
        n = len(tokens)
        while i < n:
            tok = tokens[i]

            if tok.kind is TokenKind.EOF:
                break

            if tok.kind is TokenKind.NEWLINE:
                at_line_start = True
                i += 1
                continue

            if at_line_start and tok.kind is TokenKind.PUNCTUATOR and tok.text == "#":
                i, included = self._handle_directive(tokens, i, file=file)
                if included:
                    out.extend(included)
                at_line_start = True
                continue

            if not self._is_active():
                at_line_start = False
                i += 1
                continue

            at_line_start = False

            if tok.kind is TokenKind.IDENTIFIER and (
                tok.text in self.macros or tok.text in _PREDEFINED_MACROS
            ):
                out.extend(self._expand_object_like(tok, frozenset()))
                i += 1
                continue

            out.append(tok)
            i += 1
        return out

    def _is_active(self) -> bool:
        return all(frame.active for frame in self.cond_stack)

    # ---- directive dispatch ---------------------------------------------------

    def _handle_directive(
        self, tokens: list[Token], i: int, *, file: str
    ) -> tuple[int, list[Token]]:
        directive_loc = tokens[i].location
        i += 1
        if i >= len(tokens) or tokens[i].kind is TokenKind.NEWLINE:
            return self._consume_to_eol(tokens, i), []

        name_tok = tokens[i]
        # Direktiv-Namen können C-Keywords sein (`if`, `else`) oder
        # Identifier (`define`, `undef`, `include`, `ifdef`, `ifndef`,
        # `elif`, `endif`, `error`, `warning`, `pragma`, `line`).
        if name_tok.kind not in (TokenKind.IDENTIFIER, TokenKind.KEYWORD):
            raise PreprocessorError(
                f"expected directive name, got {name_tok.text!r}", name_tok.location
            )
        name = name_tok.text
        i += 1
        line_tokens, end_idx = self._collect_line(tokens, i)

        if name in {"if", "ifdef", "ifndef", "else", "elif", "endif"}:
            self._dispatch_conditional(name, line_tokens, directive_loc)
            return end_idx, []

        if not self._is_active():
            return end_idx, []

        if name == "define":
            self._handle_define(line_tokens, directive_loc)
            return end_idx, []
        if name == "undef":
            self._handle_undef(line_tokens, directive_loc)
            return end_idx, []
        if name == "include":
            included = self._handle_include(line_tokens, directive_loc, requesting_file=file)
            return end_idx, included
        if name == "error":
            self._handle_error(line_tokens, directive_loc)
            return end_idx, []
        if name == "warning":
            self._handle_warning(line_tokens, directive_loc)
            return end_idx, []
        if name in {"pragma", "line"}:
            return end_idx, []

        raise PreprocessorError(f"unknown directive #{name}", name_tok.location)

    def _collect_line(self, tokens: list[Token], i: int) -> tuple[list[Token], int]:
        line: list[Token] = []
        while i < len(tokens) and tokens[i].kind is not TokenKind.NEWLINE:
            if tokens[i].kind is TokenKind.EOF:
                break
            line.append(tokens[i])
            i += 1
        if i < len(tokens) and tokens[i].kind is TokenKind.NEWLINE:
            i += 1
        return line, i

    def _consume_to_eol(self, tokens: list[Token], i: int) -> int:
        _, end_idx = self._collect_line(tokens, i)
        return end_idx

    # ---- define / undef -------------------------------------------------------

    def _handle_define(self, line: list[Token], loc: SourceLocation) -> None:
        if not line:
            raise PreprocessorError("#define requires an identifier", loc)
        name_tok = line[0]
        if name_tok.kind is not TokenKind.IDENTIFIER:
            raise PreprocessorError(
                f"#define expected identifier, got {name_tok.text!r}", name_tok.location
            )
        if len(line) >= 2 and line[1].kind is TokenKind.PUNCTUATOR and line[1].text == "(":
            # Function-like Macros — Iteration 2.
            raise PreprocessorError(
                "function-like macros are not yet supported (iteration 1 limitation)",
                line[1].location,
            )
        replacement = tuple(line[1:])
        self.macros[name_tok.text] = Macro(
            name=name_tok.text, replacement=replacement, location=name_tok.location
        )

    def _handle_undef(self, line: list[Token], loc: SourceLocation) -> None:
        if not line or line[0].kind is not TokenKind.IDENTIFIER:
            raise PreprocessorError("#undef requires an identifier", loc)
        self.macros.pop(line[0].text, None)

    # ---- include --------------------------------------------------------------

    def _handle_include(
        self, line: list[Token], loc: SourceLocation, *, requesting_file: str
    ) -> list[Token]:
        if self._include_depth >= self.MAX_INCLUDE_DEPTH:
            raise PreprocessorError(f"#include nesting too deep (>{self.MAX_INCLUDE_DEPTH})", loc)
        if not line:
            raise PreprocessorError("#include requires a header name", loc)

        header, is_system = self._parse_header_name(line, loc)

        try:
            path, header_source = self.source_loader.load(
                header, is_system=is_system, requesting_file=requesting_file
            )
        except FileNotFoundError as exc:
            raise PreprocessorError(str(exc), loc) from exc

        self._include_depth += 1
        try:
            sub_tokens = tokenize(header_source, file=str(path))
            return self._run(sub_tokens, file=str(path))
        finally:
            self._include_depth -= 1

    def _parse_header_name(self, line: list[Token], loc: SourceLocation) -> tuple[str, bool]:
        first = line[0]
        if first.kind is TokenKind.STRING_LITERAL:
            return first.text.strip('"'), False
        if first.kind is TokenKind.PUNCTUATOR and first.text == "<":
            parts: list[str] = []
            j = 1
            while j < len(line):
                if line[j].kind is TokenKind.PUNCTUATOR and line[j].text == ">":
                    return "".join(parts), True
                parts.append(line[j].text)
                j += 1
            raise PreprocessorError("unterminated <...> in #include", loc)
        raise PreprocessorError(
            f'#include expected "..." or <...>, got {first.text!r}', first.location
        )

    # ---- error / warning ------------------------------------------------------

    def _handle_error(self, line: list[Token], loc: SourceLocation) -> None:
        message = " ".join(t.text for t in line)
        self.diagnostics.append(("error", message, loc))
        raise PreprocessorError(f"#error: {message}", loc)

    def _handle_warning(self, line: list[Token], loc: SourceLocation) -> None:
        message = " ".join(t.text for t in line)
        self.diagnostics.append(("warning", message, loc))

    # ---- conditionals ---------------------------------------------------------

    def _dispatch_conditional(self, name: str, line: list[Token], loc: SourceLocation) -> None:
        if name == "ifdef":
            self._open_conditional(self._is_defined_in(line, loc), loc)
        elif name == "ifndef":
            self._open_conditional(not self._is_defined_in(line, loc), loc)
        elif name == "if":
            self._open_conditional(self._eval_if(line, loc), loc)
        elif name == "elif":
            if not self.cond_stack:
                raise PreprocessorError("#elif without matching #if", loc)
            frame = self.cond_stack[-1]
            if frame.taken:
                frame.active = False
            else:
                value = self._eval_if(line, loc)
                frame.active = value and self._outer_active(skip_top=True)
                frame.taken = value
        elif name == "else":
            if not self.cond_stack:
                raise PreprocessorError("#else without matching #if", loc)
            frame = self.cond_stack[-1]
            if frame.taken:
                frame.active = False
            else:
                frame.active = self._outer_active(skip_top=True)
                frame.taken = True
        elif name == "endif":
            if not self.cond_stack:
                raise PreprocessorError("#endif without matching #if", loc)
            self.cond_stack.pop()

    def _open_conditional(self, value: bool, loc: SourceLocation) -> None:
        outer_active = self._is_active()
        self.cond_stack.append(
            _CondFrame(
                active=value and outer_active,
                taken=value,
                location=loc,
            )
        )

    def _outer_active(self, *, skip_top: bool) -> bool:
        frames = self.cond_stack[:-1] if skip_top else self.cond_stack
        return all(frame.active for frame in frames)

    def _is_defined_in(self, line: list[Token], loc: SourceLocation) -> bool:
        if not line or line[0].kind is not TokenKind.IDENTIFIER:
            raise PreprocessorError("expected identifier", loc)
        return line[0].text in self.macros

    def _eval_if(self, line: list[Token], loc: SourceLocation) -> bool:
        if not line:
            raise PreprocessorError("#if without expression", loc)

        toks = list(line)
        negate = False
        if toks and toks[0].kind is TokenKind.PUNCTUATOR and toks[0].text == "!":
            negate = True
            toks = toks[1:]

        if toks and toks[0].kind is TokenKind.IDENTIFIER and toks[0].text == "defined":
            rest = toks[1:]
            if rest and rest[0].kind is TokenKind.PUNCTUATOR and rest[0].text == "(":
                if len(rest) < 3 or rest[1].kind is not TokenKind.IDENTIFIER or rest[2].text != ")":
                    raise PreprocessorError("malformed defined(...)", loc)
                value = rest[1].text in self.macros
            elif rest and rest[0].kind is TokenKind.IDENTIFIER:
                value = rest[0].text in self.macros
            else:
                raise PreprocessorError("malformed defined", loc)
            return (not value) if negate else value

        if len(toks) == 1 and toks[0].kind is TokenKind.CONSTANT:
            try:
                value = int(toks[0].text, 0) != 0
            except ValueError as exc:
                raise PreprocessorError(
                    f"cannot evaluate constant in #if: {toks[0].text}", loc
                ) from exc
            return (not value) if negate else value

        raise PreprocessorError(
            "iteration 1 supports only `defined(NAME)`, `!defined(NAME)`, "
            "and bare integer constants in #if/#elif",
            loc,
        )

    # ---- macro expansion ------------------------------------------------------

    def _expand_object_like(self, tok: Token, hide_set: frozenset[str]) -> list[Token]:
        if tok.text in hide_set:
            return [tok]

        # Predefined: context-abhängig
        if tok.text == "__FILE__":
            return [Token(TokenKind.STRING_LITERAL, f'"{tok.location.file}"', tok.location)]
        if tok.text == "__LINE__":
            return [Token(TokenKind.CONSTANT, str(tok.location.line), tok.location)]

        macro = self.macros[tok.text]
        next_hide = hide_set | {macro.name}

        # Replacement-Tokens: Source-Location auf Aufruf-Site legen, damit
        # spätere Findings auf den User-Code zeigen, nicht auf die Macro-
        # Definition.
        rewritten = [Token(t.kind, t.text, tok.location) for t in macro.replacement]
        return self._expand_stream(rewritten, hide_set=next_hide)

    def _expand_stream(self, tokens: list[Token], *, hide_set: frozenset[str]) -> list[Token]:
        out: list[Token] = []
        for t in tokens:
            if (
                t.kind is TokenKind.IDENTIFIER
                and t.text not in hide_set
                and (t.text in self.macros or t.text in _PREDEFINED_MACROS)
            ):
                out.extend(self._expand_object_like(t, hide_set))
            else:
                out.append(t)
        return out
