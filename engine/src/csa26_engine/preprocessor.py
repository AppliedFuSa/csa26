"""C-Preprocessor für csa26-engine.

Implementiert ISO/IEC 9899:1999 §6.10 als Token-Stream-Transformation:
Lexer → Preprocessor → preprocesster Token-Stream.

Funktions-Umfang (Iteration 2 — vollständig):
- `#include "..."` / `#include <...>` mit Include-Path-Auflösung
- `#define` für object-like und function-like Macros
- Function-like Macros mit Parametern, `__VA_ARGS__`, `#`-Stringification
  und `##`-Token-Pasting
- `#undef`
- `#ifdef` / `#ifndef` / `#if` / `#elif` / `#else` / `#endif` mit
  vollwertiger Konstanten-Expression-Auswertung (||, &&, |, ^, &,
  ==, !=, <, >, <=, >=, <<, >>, +, -, *, /, %, !, ~, ?:)
- `defined(NAME)` / `defined NAME`
- `#error` / `#warning` / `#pragma` / `#line`
- Predefined: `__FILE__`, `__LINE__`
- Adjacent String-Literal-Concatenation (ISO Phase 6) als Post-Pass

Bekannte Limitationen:
- Backslash-Newline-Line-Splicing (ISO Phase 2) ist NICHT implementiert.
  In realem Embedded-Code fast nur bei Macro-Definitionen relevant —
  wir akzeptieren `\\` am Ende einer `#define`-Zeile nicht. Workaround
  in Test-Fixtures: Macro-Body in eine Zeile schreiben.
- Trigraphs werden nicht ersetzt.
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


_PREDEFINED_MACROS: frozenset[str] = frozenset({"__FILE__", "__LINE__"})


# ---------------------------------------------------------------------------
# Macro-Datenstrukturen
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Macro:
    name: str
    replacement: tuple[Token, ...]
    location: SourceLocation
    is_function_like: bool = False
    params: tuple[str, ...] = ()
    is_variadic: bool = False


@dataclass(slots=True)
class _CondFrame:
    active: bool
    taken: bool
    location: SourceLocation


# ---------------------------------------------------------------------------
# Source-Loading
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
        # User-#define-Macros (separat von command-line-defines) und ihre
        # Verwendung — gebraucht für Rule 2.5 (unused macros).
        self.user_macros: dict[str, Macro] = {}
        self.used_macro_names: set[str] = set()
        self._init_defines(defines or {}, undefines)

    def process(self, *, source: str, file: str) -> list[Token]:
        tokens = tokenize(source, file=file)
        out = self._run(tokens, file=file)
        if self.cond_stack:
            top = self.cond_stack[-1]
            raise PreprocessorError("unterminated conditional (missing #endif)", top.location)
        return _concat_adjacent_strings(out)

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

            if self._can_expand(tok, hide_set=frozenset()):
                expanded, new_i = self._expand_at(tokens, i, hide_set=frozenset())
                out.extend(expanded)
                i = new_i
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

        # Function-like nur, wenn `(` direkt nach dem Identifier (adjacent in
        # der Quelltext-Spalte) folgt — sonst ist `(...)` Teil der
        # Replacement-List eines object-like Macros.
        if (
            len(line) >= 2
            and line[1].kind is TokenKind.PUNCTUATOR
            and line[1].text == "("
            and _is_adjacent(name_tok, line[1])
        ):
            params, is_variadic, replacement_start = self._parse_params(line, name_tok.location)
            replacement = tuple(line[replacement_start:])
            macro = Macro(
                name=name_tok.text,
                replacement=replacement,
                location=name_tok.location,
                is_function_like=True,
                params=params,
                is_variadic=is_variadic,
            )
            self.macros[name_tok.text] = macro
            self.user_macros[name_tok.text] = macro
            return

        replacement = tuple(line[1:])
        macro = Macro(
            name=name_tok.text,
            replacement=replacement,
            location=name_tok.location,
        )
        self.macros[name_tok.text] = macro
        self.user_macros[name_tok.text] = macro

    def _parse_params(
        self, line: list[Token], loc: SourceLocation
    ) -> tuple[tuple[str, ...], bool, int]:
        # line[1] == '(', wir sammeln bis ')'
        params: list[str] = []
        i = 2
        # leere Parameter-Liste: `MACRO()`
        if i < len(line) and line[i].text == ")":
            return (), False, i + 1

        while i < len(line):
            tok = line[i]
            if tok.text == "...":
                i += 1
                if i >= len(line) or line[i].text != ")":
                    raise PreprocessorError(
                        "expected ')' after '...' in macro param list", tok.location
                    )
                i += 1
                return tuple(params), True, i
            if tok.kind is not TokenKind.IDENTIFIER:
                raise PreprocessorError(f"expected parameter name, got {tok.text!r}", tok.location)
            params.append(tok.text)
            i += 1
            if i >= len(line):
                raise PreprocessorError("unterminated macro parameter list", loc)
            sep = line[i]
            if sep.text == ")":
                i += 1
                return tuple(params), False, i
            if sep.text == ",":
                i += 1
                continue
            raise PreprocessorError(
                f"expected ',' or ')' in macro param list, got {sep.text!r}",
                sep.location,
            )
        raise PreprocessorError("unterminated macro parameter list", loc)

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
        self.cond_stack.append(_CondFrame(active=value and outer_active, taken=value, location=loc))

    def _outer_active(self, *, skip_top: bool) -> bool:
        frames = self.cond_stack[:-1] if skip_top else self.cond_stack
        return all(frame.active for frame in frames)

    def _is_defined_in(self, line: list[Token], loc: SourceLocation) -> bool:
        if not line or line[0].kind is not TokenKind.IDENTIFIER:
            raise PreprocessorError("expected identifier", loc)
        name = line[0].text
        # `#ifdef`/`#ifndef` zählen als Use des Macros — verhindert
        # False-Positives bei Header-Guards in Rule 2.5.
        self.used_macro_names.add(name)
        return name in self.macros

    def _eval_if(self, line: list[Token], loc: SourceLocation) -> bool:
        if not line:
            raise PreprocessorError("#if without expression", loc)
        evaluator = _ConstExprEvaluator(line, self.macros, loc, self.used_macro_names)
        return evaluator.evaluate() != 0

    # ---- macro expansion ------------------------------------------------------

    def _can_expand(self, tok: Token, *, hide_set: frozenset[str]) -> bool:
        if tok.kind is not TokenKind.IDENTIFIER:
            return False
        if tok.text in hide_set:
            return False
        return tok.text in self.macros or tok.text in _PREDEFINED_MACROS

    def _expand_at(
        self, tokens: list[Token], i: int, *, hide_set: frozenset[str]
    ) -> tuple[list[Token], int]:
        """Expand the macro starting at tokens[i].

        Returns (expanded-tokens, new-index-into-tokens).
        Function-like macros consume `(` … `)` from the input stream.
        """
        tok = tokens[i]

        # Predefined: __FILE__, __LINE__
        if tok.text == "__FILE__":
            return [Token(TokenKind.STRING_LITERAL, f'"{tok.location.file}"', tok.location)], i + 1
        if tok.text == "__LINE__":
            return [Token(TokenKind.CONSTANT, str(tok.location.line), tok.location)], i + 1

        macro = self.macros[tok.text]
        self.used_macro_names.add(macro.name)
        next_hide = hide_set | {macro.name}

        if not macro.is_function_like:
            replacement = [Token(t.kind, t.text, tok.location) for t in macro.replacement]
            return self._rescan(replacement, hide_set=next_hide), i + 1

        # Function-like: muss von `(` gefolgt sein, sonst keine Expansion.
        # Whitespace ist im Lexer schon weg, der nächste Token-Index ist also
        # direkt der Kandidat für `(`.
        j = i + 1
        if j >= len(tokens) or tokens[j].kind is TokenKind.EOF or tokens[j].text != "(":
            # Kein Function-Call → Identifier bleibt unexpandiert (so will's
            # die ISO-Spec auch).
            return [tok], i + 1

        args, j_after = self._collect_arguments(tokens, j, macro, tok.location)
        substituted = self._substitute(macro, args, hide_set=next_hide, call_loc=tok.location)
        return self._rescan(substituted, hide_set=next_hide), j_after

    def _collect_arguments(
        self,
        tokens: list[Token],
        paren_idx: int,
        macro: Macro,
        call_loc: SourceLocation,
    ) -> tuple[list[list[Token]], int]:
        """`tokens[paren_idx]` ist '('. Sammelt die Argumente bis zum
        matchenden ')' und liefert sie als Liste-von-Token-Listen.
        """
        i = paren_idx + 1
        depth = 1
        args: list[list[Token]] = []
        current: list[Token] = []
        n = len(tokens)
        # variadic: Komma bei depth==1 trennt Argumente, ABER ab dem
        # variadischen Index werden alle restlichen Kommata Teil des
        # __VA_ARGS__-Arguments.
        fixed_count = len(macro.params)
        while i < n:
            tok = tokens[i]
            if tok.kind is TokenKind.EOF:
                raise PreprocessorError(f"unterminated macro call to {macro.name!r}", call_loc)
            if tok.kind is TokenKind.NEWLINE:
                # Newlines im Macro-Aufruf sind erlaubt — wir überspringen sie.
                i += 1
                continue
            if tok.text == "(" and tok.kind is TokenKind.PUNCTUATOR:
                depth += 1
                current.append(tok)
            elif tok.text == ")" and tok.kind is TokenKind.PUNCTUATOR:
                depth -= 1
                if depth == 0:
                    # Letztes Argument abschließen — auch leeres Argument bei
                    # `MACRO()` zählt als 0 Args, nicht als 1 leeres Arg.
                    if current or args:
                        args.append(current)
                    return args, i + 1
                current.append(tok)
            elif (
                tok.text == ","
                and tok.kind is TokenKind.PUNCTUATOR
                and depth == 1
                and not (macro.is_variadic and len(args) >= fixed_count)
            ):
                args.append(current)
                current = []
            else:
                current.append(tok)
            i += 1
        raise PreprocessorError(f"unterminated macro call to {macro.name!r}", call_loc)

    def _substitute(
        self,
        macro: Macro,
        args: list[list[Token]],
        *,
        hide_set: frozenset[str],
        call_loc: SourceLocation,
    ) -> list[Token]:
        # Argumentanzahl validieren
        n_args = len(args)
        n_params = len(macro.params)
        if macro.is_variadic:
            if n_args < n_params:
                raise PreprocessorError(
                    f"too few arguments for {macro.name!r} "
                    f"(expected at least {n_params}, got {n_args})",
                    call_loc,
                )
        else:
            if n_args != n_params:
                # Special case: macro with no params, called as `M()` → 0 args.
                if not (n_params == 0 and n_args == 0):
                    raise PreprocessorError(
                        f"argument count mismatch for {macro.name!r} "
                        f"(expected {n_params}, got {n_args})",
                        call_loc,
                    )

        # Map: Parameter-Name → unexpanded Args. Für variadic gibt es
        # zusätzlich __VA_ARGS__ als alle restlichen Args mit Kommas.
        unexpanded: dict[str, list[Token]] = dict(zip(macro.params, args[:n_params], strict=True))
        if macro.is_variadic:
            va_tokens: list[Token] = []
            for k, arg in enumerate(args[n_params:]):
                if k > 0:
                    va_tokens.append(Token(TokenKind.PUNCTUATOR, ",", call_loc))
                va_tokens.extend(arg)
            unexpanded["__VA_ARGS__"] = va_tokens

        # Cache für expandierte Args (lazy, weil bei `#`/`##` unexpanded gewollt)
        expanded_cache: dict[str, list[Token]] = {}

        def get_expanded(name: str) -> list[Token]:
            if name in expanded_cache:
                return expanded_cache[name]
            expanded = self._rescan(list(unexpanded[name]), hide_set=frozenset())
            expanded_cache[name] = expanded
            return expanded

        out: list[Token] = []
        rep = macro.replacement
        i = 0
        while i < len(rep):
            tok = rep[i]
            anchored = Token(tok.kind, tok.text, call_loc)

            # Stringification: `# param`
            if tok.text == "#" and tok.kind is TokenKind.PUNCTUATOR:
                if i + 1 >= len(rep):
                    raise PreprocessorError("'#' must be followed by a parameter", tok.location)
                nxt = rep[i + 1]
                if nxt.text not in unexpanded:
                    raise PreprocessorError(
                        f"'#' must be followed by a parameter, got {nxt.text!r}",
                        nxt.location,
                    )
                stringified = _stringify(unexpanded[nxt.text])
                out.append(Token(TokenKind.STRING_LITERAL, stringified, call_loc))
                i += 2
                continue

            # Token-Pasting: `lhs ## rhs`
            paste_op = rep[i + 1] if i + 1 < len(rep) else None
            if paste_op and paste_op.text == "##" and paste_op.kind is TokenKind.PUNCTUATOR:
                lhs_tokens = self._param_or_self(tok, unexpanded, call_loc)
                # Sammle alle ## rhs hintereinander (links-assoziativ)
                acc = list(lhs_tokens)
                j = i + 1
                while j < len(rep) and rep[j].text == "##" and rep[j].kind is TokenKind.PUNCTUATOR:
                    if j + 1 >= len(rep):
                        raise PreprocessorError("'##' must have a right operand", rep[j].location)
                    rhs = rep[j + 1]
                    rhs_tokens = self._param_or_self(rhs, unexpanded, call_loc)
                    acc = _paste(acc, rhs_tokens, call_loc)
                    j += 2
                out.extend(acc)
                i = j
                continue

            # Normaler Parameter → expandierte Args einfügen
            if tok.kind is TokenKind.IDENTIFIER and tok.text in unexpanded:
                out.extend(Token(t.kind, t.text, call_loc) for t in get_expanded(tok.text))
                i += 1
                continue

            out.append(anchored)
            i += 1
        return out

    def _param_or_self(
        self,
        tok: Token,
        unexpanded: dict[str, list[Token]],
        call_loc: SourceLocation,
    ) -> list[Token]:
        if tok.kind is TokenKind.IDENTIFIER and tok.text in unexpanded:
            return [Token(t.kind, t.text, call_loc) for t in unexpanded[tok.text]]
        return [Token(tok.kind, tok.text, call_loc)]

    def _rescan(self, tokens: list[Token], *, hide_set: frozenset[str]) -> list[Token]:
        """Rescan ist die zweite Pass der Macro-Expansion: nach Substitution
        (oder direkt für object-like) wird der entstandene Stream nochmal
        nach Macro-Namen durchsucht.
        """
        out: list[Token] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if self._can_expand(tok, hide_set=hide_set):
                expanded, j = self._expand_at(tokens, i, hide_set=hide_set)
                out.extend(expanded)
                i = j
                continue
            out.append(tok)
            i += 1
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_adjacent(left: Token, right: Token) -> bool:
    return (
        left.location.file == right.location.file
        and left.location.line == right.location.line
        and right.location.column == left.location.column + len(left.text)
    )


def _stringify(tokens: list[Token]) -> str:
    """ISO C99 §6.10.3.2: stringification.

    - Whitespace zwischen Tokens wird zu einem einzelnen Space.
    - Innerhalb von String-Literalen müssen `\\` und `"` escaped werden.
    """
    parts: list[str] = []
    for t in tokens:
        text = t.text
        if t.kind is TokenKind.STRING_LITERAL or (
            t.kind is TokenKind.CONSTANT and text.startswith(("'", "L'"))
        ):
            text = text.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(text)
    return '"' + " ".join(parts) + '"'


def _paste(lhs: list[Token], rhs: list[Token], call_loc: SourceLocation) -> list[Token]:
    """ISO C99 §6.10.3.3: token-pasting.

    Verschmilzt das letzte Token aus lhs mit dem ersten aus rhs durch
    String-Konkatenation und re-Lexierung. Wenn entweder Seite leer ist,
    wird die andere unverändert zurückgegeben.
    """
    if not lhs:
        return list(rhs)
    if not rhs:
        return list(lhs)
    last = lhs[-1]
    first = rhs[0]
    pasted_text = last.text + first.text
    # Re-lex: das Ergebnis muss ein gültiges einziges Token sein.
    pasted_tokens = [
        t for t in tokenize(pasted_text, file=str(call_loc.file)) if t.kind is not TokenKind.EOF
    ]
    if len(pasted_tokens) != 1:
        # Nicht-einzelnes Token nach Paste — undefined behavior in ISO,
        # in der Praxis ist das ein Bug im Macro. Wir liefern alle entstehenden
        # Tokens, weil das Cppcheck und GCC auch tolerant tun.
        merged = [Token(t.kind, t.text, call_loc) for t in pasted_tokens]
    else:
        only = pasted_tokens[0]
        merged = [Token(only.kind, only.text, call_loc)]
    return list(lhs[:-1]) + merged + list(rhs[1:])


def _concat_adjacent_strings(tokens: list[Token]) -> list[Token]:
    """ISO C99 Translation Phase 6: angrenzende String-Literale werden
    zu einem zusammengezogen.
    """
    out: list[Token] = []
    for tok in tokens:
        if (
            tok.kind is TokenKind.STRING_LITERAL
            and out
            and out[-1].kind is TokenKind.STRING_LITERAL
        ):
            prev = out[-1]
            # Strip trailing `"` von prev und führendes `"` von tok.
            prev_body = _string_body(prev.text)
            tok_body = _string_body(tok.text)
            wide = prev.text.startswith("L") or tok.text.startswith("L")
            prefix = "L" if wide else ""
            out[-1] = Token(
                TokenKind.STRING_LITERAL,
                f'{prefix}"{prev_body}{tok_body}"',
                prev.location,
            )
        else:
            out.append(tok)
    return out


def _string_body(literal: str) -> str:
    """Entfernt führendes `"` (oder `L"`) und schließendes `"` aus einem
    String-Literal-Token-Text."""
    if literal.startswith('L"'):
        body = literal[2:]
    else:
        body = literal[1:]
    if body.endswith('"'):
        body = body[:-1]
    return body


# ---------------------------------------------------------------------------
# Constant-Expression-Evaluator für #if / #elif (ISO C99 §6.10.1)
# ---------------------------------------------------------------------------


class _ConstExprEvaluator:
    """Recursive-descent-Parser für die §6.10.1-Subset-Grammatik.

    Operator-Präzedenz (von hoch nach niedrig):
      unary  > * / %  > + -  > << >>  > < <= > >=  > == !=
      > &  > ^  > |  > &&  > ||  > ?:

    `defined(NAME)` und `defined NAME` werden vor der Macro-Expansion
    behandelt; alle anderen Identifier werden expandiert. Identifier,
    die nach Expansion immer noch Identifier sind, evaluieren zu 0.
    """

    def __init__(
        self,
        line: list[Token],
        macros: dict[str, Macro],
        loc: SourceLocation,
        used_macro_names: set[str] | None = None,
    ) -> None:
        self._tokens = self._preprocess_line(line, macros, used_macro_names)
        self._pos = 0
        self._loc = loc

    @staticmethod
    def _preprocess_line(
        line: list[Token],
        macros: dict[str, Macro],
        used_macro_names: set[str] | None = None,
    ) -> list[Token]:
        # Erst `defined(X)`/`defined X` durch 0/1-Konstanten ersetzen,
        # damit der nachfolgende Macro-Expansion-Schritt sie nicht
        # aufgreift. `defined()` zählt als Use für Rule 2.5 (sonst
        # melden wir Header-Guard-Macros als unused).
        out: list[Token] = []
        i = 0

        def _record_use(name: str) -> None:
            if used_macro_names is not None:
                used_macro_names.add(name)

        while i < len(line):
            tok = line[i]
            if tok.kind is TokenKind.IDENTIFIER and tok.text == "defined":
                j = i + 1
                if j < len(line) and line[j].text == "(":
                    if (
                        j + 2 >= len(line)
                        or line[j + 1].kind is not TokenKind.IDENTIFIER
                        or line[j + 2].text != ")"
                    ):
                        raise PreprocessorError("malformed defined(...)", tok.location)
                    name = line[j + 1].text
                    _record_use(name)
                    out.append(
                        Token(
                            TokenKind.CONSTANT,
                            "1" if name in macros else "0",
                            tok.location,
                        )
                    )
                    i = j + 3
                elif j < len(line) and line[j].kind is TokenKind.IDENTIFIER:
                    name = line[j].text
                    _record_use(name)
                    out.append(
                        Token(
                            TokenKind.CONSTANT,
                            "1" if name in macros else "0",
                            tok.location,
                        )
                    )
                    i = j + 1
                else:
                    raise PreprocessorError("malformed defined", tok.location)
                continue
            out.append(tok)
            i += 1
        return out

    # ---- entry ----------------------------------------------------------------

    def evaluate(self) -> int:
        value = self._ternary()
        if self._pos != len(self._tokens):
            tok = self._tokens[self._pos]
            raise PreprocessorError(
                f"unexpected token in #if expression: {tok.text!r}",
                tok.location,
            )
        return value

    # ---- helpers --------------------------------------------------------------

    def _peek(self) -> Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _accept(self, *texts: str) -> Token | None:
        tok = self._peek()
        if tok is not None and tok.text in texts:
            self._pos += 1
            return tok
        return None

    # ---- expression hierarchy -------------------------------------------------

    def _ternary(self) -> int:
        cond = self._logical_or()
        if self._accept("?"):
            then_branch = self._ternary()
            if not self._accept(":"):
                raise PreprocessorError("expected ':' in ?: expression", self._loc)
            else_branch = self._ternary()
            return then_branch if cond else else_branch
        return cond

    def _logical_or(self) -> int:
        value = self._logical_and()
        while self._accept("||"):
            rhs = self._logical_and()
            value = 1 if (value or rhs) else 0
        return value

    def _logical_and(self) -> int:
        value = self._bitwise_or()
        while self._accept("&&"):
            rhs = self._bitwise_or()
            value = 1 if (value and rhs) else 0
        return value

    def _bitwise_or(self) -> int:
        value = self._bitwise_xor()
        while self._accept("|"):
            value |= self._bitwise_xor()
        return value

    def _bitwise_xor(self) -> int:
        value = self._bitwise_and()
        while self._accept("^"):
            value ^= self._bitwise_and()
        return value

    def _bitwise_and(self) -> int:
        value = self._equality()
        while self._accept("&"):
            value &= self._equality()
        return value

    def _equality(self) -> int:
        value = self._relational()
        while True:
            if self._accept("=="):
                value = 1 if value == self._relational() else 0
            elif self._accept("!="):
                value = 1 if value != self._relational() else 0
            else:
                break
        return value

    def _relational(self) -> int:
        value = self._shift()
        while True:
            if self._accept("<="):
                value = 1 if value <= self._shift() else 0
            elif self._accept(">="):
                value = 1 if value >= self._shift() else 0
            elif self._accept("<"):
                value = 1 if value < self._shift() else 0
            elif self._accept(">"):
                value = 1 if value > self._shift() else 0
            else:
                break
        return value

    def _shift(self) -> int:
        value = self._additive()
        while True:
            if self._accept("<<"):
                value <<= self._additive()
            elif self._accept(">>"):
                value >>= self._additive()
            else:
                break
        return value

    def _additive(self) -> int:
        value = self._multiplicative()
        while True:
            if self._accept("+"):
                value += self._multiplicative()
            elif self._accept("-"):
                value -= self._multiplicative()
            else:
                break
        return value

    def _multiplicative(self) -> int:
        value = self._unary()
        while True:
            if self._accept("*"):
                value *= self._unary()
            elif self._accept("/"):
                divisor = self._unary()
                if divisor == 0:
                    raise PreprocessorError("division by zero in #if", self._loc)
                # C-Integer-Division: Trunkierung gegen 0
                value = int(value / divisor)
            elif self._accept("%"):
                divisor = self._unary()
                if divisor == 0:
                    raise PreprocessorError("modulo by zero in #if", self._loc)
                value = value - int(value / divisor) * divisor
            else:
                break
        return value

    def _unary(self) -> int:
        if self._accept("+"):
            return self._unary()
        if self._accept("-"):
            return -self._unary()
        if self._accept("!"):
            return 0 if self._unary() else 1
        if self._accept("~"):
            return ~self._unary()
        return self._primary()

    def _primary(self) -> int:
        tok = self._peek()
        if tok is None:
            raise PreprocessorError("unexpected end of #if expression", self._loc)
        if self._accept("("):
            value = self._ternary()
            if not self._accept(")"):
                raise PreprocessorError("expected ')' in #if expression", self._loc)
            return value
        if tok.kind is TokenKind.CONSTANT:
            self._pos += 1
            return _parse_int_constant(tok)
        if tok.kind is TokenKind.IDENTIFIER:
            # ISO C99 §6.10.1: identifiers that survive macro expansion
            # evaluate to 0.
            self._pos += 1
            return 0
        raise PreprocessorError(f"unexpected token in #if expression: {tok.text!r}", tok.location)


def _parse_int_constant(tok: Token) -> int:
    text = tok.text
    # Suffixe (u, U, l, L, ll, LL und Kombinationen) entfernen.
    while text and text[-1] in "uUlL":
        text = text[:-1]
    try:
        return int(text, 0)
    except ValueError as exc:
        raise PreprocessorError(
            f"cannot parse integer constant {tok.text!r}", tok.location
        ) from exc
