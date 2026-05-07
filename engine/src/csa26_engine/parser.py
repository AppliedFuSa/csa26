"""C99-Subset-Parser für csa26-engine.

Recursive-descent-Parser über die Token-Liste vom Preprocessor.
Erzeugt einen AST aus den Knoten-Typen in `ast_nodes.py`.

Sprach-Scope (C99-Subset):
- Top-Level: Function-Definitionen, Variablen-Deklarationen,
  Struct-/Union-/Enum-/Typedef-Deklarationen.
- Storage-Class: `static`, `extern`, `typedef`, `register`, `auto`.
- Function-Specifier: `inline`.
- Type-Specifiers: `void`, `char`, `short`, `int`, `long`, `signed`,
  `unsigned`, `float`, `double`, `_Bool`, `struct`, `union`, `enum`,
  Typedef-Namen.
- Type-Qualifiers: `const`, `volatile`, `restrict`.
- Pointer-, Array-, Funktions-Declarators in beliebiger Schachtelung
  (Spiral-Rule).
- Statements: Compound, Expression, If, Switch+Case+Default, While,
  Do, For, Return, Break, Continue, Goto+Labeled, Null.
- Expressions: vollständige Precedence-Hierarchie inkl. Assignment,
  Ternary, Cast, sizeof, Postfix (++/--/[]/./->/Call), Unary
  (+/-/!/~/*/&/++/--/sizeof).
- GCC-Extensions: `__attribute__((...))`, `__asm__(…)`,
  `__inline__`, `__restrict__`, `__volatile__` werden erkannt und
  weggeworfen — keine semantische Auswertung.

Bewusste Limitationen für Iteration 1:
- Keine Designated-Initializers (`{.x = 1, [3] = 5}`).
- Keine Compound-Literals (`(int[]){1, 2, 3}`).
- Keine VLAs (variable-length arrays).
- Keine K&R-Function-Definitions.
- Kein `_Generic`, `_Alignof`, `_Atomic`.
- Bit-Fields werden geparst, aber nur als „normaler" Member geführt.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import (
    ArrayType,
    Assignment,
    BasicType,
    BinaryOp,
    BreakStmt,
    CaseStmt,
    CastExpr,
    CharLiteral,
    CompoundStmt,
    ContinueStmt,
    Declaration,
    DefaultStmt,
    DoStmt,
    EnumType,
    Expression,
    ExpressionStmt,
    FloatLiteral,
    ForStmt,
    FunctionCall,
    FunctionDefinition,
    FunctionType,
    GotoStmt,
    Identifier,
    IfStmt,
    InitializerList,
    IntLiteral,
    LabeledStmt,
    MemberAccess,
    NullStmt,
    Param,
    ParenExpr,
    PointerType,
    ReturnStmt,
    Statement,
    StringLiteral,
    StructType,
    Subscript,
    SwitchStmt,
    TernaryOp,
    TranslationUnit,
    Type,
    TypedefName,
    UnaryOp,
    UnionType,
    WhileStmt,
)
from .tokens import SourceLocation, Token, TokenKind

_STORAGE_CLASSES: frozenset[str] = frozenset({"typedef", "extern", "static", "auto", "register"})
_TYPE_QUALIFIERS: frozenset[str] = frozenset({"const", "volatile", "restrict"})
_TYPE_SPECIFIER_KEYWORDS: frozenset[str] = frozenset(
    {
        "void",
        "char",
        "short",
        "int",
        "long",
        "signed",
        "unsigned",
        "float",
        "double",
        "_Bool",
    }
)
_FUNCTION_SPECIFIERS: frozenset[str] = frozenset({"inline"})
_GCC_KEYWORD_QUALIFIERS: dict[str, str] = {
    "__const": "const",
    "__const__": "const",
    "__volatile": "volatile",
    "__volatile__": "volatile",
    "__restrict": "restrict",
    "__restrict__": "restrict",
}
_ASSIGNMENT_OPS: frozenset[str] = frozenset(
    {"=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="}
)


class ParserError(ValueError):
    def __init__(self, message: str, location: SourceLocation) -> None:
        super().__init__(f"{location}: {message}")
        self.location = location


def parse(tokens: list[Token]) -> TranslationUnit:
    return Parser(tokens).parse_translation_unit()


@dataclass(slots=True)
class _DeclSpecs:
    storage_class: str | None
    is_inline: bool
    base_type: Type
    qualifiers: frozenset[str]


class Parser:
    __slots__ = ("tokens", "pos", "_typedef_names")

    def __init__(self, tokens: list[Token]) -> None:
        stripped = [t for t in tokens if t.kind is not TokenKind.NEWLINE]
        if not stripped or stripped[-1].kind is not TokenKind.EOF:
            tail_loc = stripped[-1].location if stripped else _origin()
            stripped.append(Token(TokenKind.EOF, "", tail_loc))
        self.tokens = stripped
        self.pos = 0
        self._typedef_names: set[str] = set()

    # ------------------------------------------------------------------ helpers

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1] if self.tokens else _eof_token()
        return self.tokens[idx]

    def _at_end(self) -> bool:
        return self._peek().kind is TokenKind.EOF

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.kind is not TokenKind.EOF:
            self.pos += 1
        return tok

    def _accept(self, kind: TokenKind, *texts: str) -> Token | None:
        tok = self._peek()
        if tok.kind is not kind:
            return None
        if texts and tok.text not in texts:
            return None
        self._advance()
        return tok

    def _accept_punct(self, *symbols: str) -> Token | None:
        return self._accept(TokenKind.PUNCTUATOR, *symbols)

    def _accept_keyword(self, *names: str) -> Token | None:
        return self._accept(TokenKind.KEYWORD, *names)

    def _expect(self, kind: TokenKind, *texts: str) -> Token:
        tok = self._accept(kind, *texts)
        if tok is None:
            actual = self._peek()
            wanted = "/".join(texts) if texts else kind.name
            raise ParserError(f"expected {wanted}, got {actual.text!r}", actual.location)
        return tok

    def _expect_punct(self, *symbols: str) -> Token:
        return self._expect(TokenKind.PUNCTUATOR, *symbols)

    def _expect_keyword(self, *names: str) -> Token:
        return self._expect(TokenKind.KEYWORD, *names)

    def _check_punct(self, *symbols: str) -> bool:
        tok = self._peek()
        return tok.kind is TokenKind.PUNCTUATOR and tok.text in symbols

    def _check_keyword(self, *names: str) -> bool:
        tok = self._peek()
        return tok.kind is TokenKind.KEYWORD and tok.text in names

    # ------------------------------------------------------------------ GCC ext

    def _skip_gcc_attribute(self) -> None:
        """`__attribute__((…))` — geparst, semantisch verworfen."""
        if not self._accept_keyword("__attribute__"):
            return
        self._expect_punct("(")
        self._expect_punct("(")
        depth = 2
        while depth > 0:
            if self._at_end():
                raise ParserError("unterminated __attribute__", self._peek().location)
            tok = self._advance()
            if tok.kind is TokenKind.PUNCTUATOR:
                if tok.text == "(":
                    depth += 1
                elif tok.text == ")":
                    depth -= 1

    def _skip_gcc_attributes(self) -> None:
        while self._check_keyword("__attribute__"):
            self._skip_gcc_attribute()

    def _skip_gcc_asm_block(self) -> None:
        """`__asm__(...)` und `asm(...)` — geparst, verworfen."""
        if not (self._check_keyword("__asm__") or self._check_keyword("asm")):
            return
        self._advance()
        if not self._accept_punct("("):
            return
        depth = 1
        while depth > 0:
            if self._at_end():
                raise ParserError("unterminated asm", self._peek().location)
            tok = self._advance()
            if tok.kind is TokenKind.PUNCTUATOR:
                if tok.text == "(":
                    depth += 1
                elif tok.text == ")":
                    depth -= 1

    # ------------------------------------------------------------------ types

    def _is_type_start(self, tok: Token | None = None) -> bool:
        tok = tok if tok is not None else self._peek()
        if tok.kind is TokenKind.KEYWORD:
            if tok.text in _STORAGE_CLASSES:
                return True
            if tok.text in _TYPE_QUALIFIERS:
                return True
            if tok.text in _TYPE_SPECIFIER_KEYWORDS:
                return True
            if tok.text in _FUNCTION_SPECIFIERS:
                return True
            if tok.text in {"struct", "union", "enum"}:
                return True
            if tok.text in _GCC_KEYWORD_QUALIFIERS:
                return True
            if tok.text == "__attribute__":
                return True
        if tok.kind is TokenKind.IDENTIFIER and tok.text in self._typedef_names:
            return True
        return False

    # ------------------------------------------------------------------ entry

    def parse_translation_unit(self) -> TranslationUnit:
        loc = self._peek().location if self.tokens else _origin()
        decls: list[FunctionDefinition | Declaration] = []
        while not self._at_end():
            decl = self._parse_external_declaration()
            decls.extend(decl)
        return TranslationUnit(location=loc, declarations=tuple(decls))

    def _parse_external_declaration(
        self,
    ) -> list[FunctionDefinition | Declaration]:
        # GCC-Extension: `__extension__` markiert die folgende Decl als
        # GCC-Extension — wir konsumieren es und parsen weiter.
        if self._accept_keyword("__extension__"):
            return self._parse_external_declaration()

        loc = self._peek().location
        specs = self._parse_declaration_specifiers()

        # Standalone-Type-Specifier-Declaration (z.B. `struct Foo {…};`)
        if self._accept_punct(";"):
            decl = Declaration(
                location=loc,
                name=None,
                type=specs.base_type,
                storage_class=specs.storage_class,
                is_inline=specs.is_inline,
            )
            return [decl]

        first_decl = self._parse_init_declarator(specs)
        # Function-Definition: nach erstem Declarator kommt `{`
        if (
            specs.storage_class != "typedef"
            and isinstance(first_decl.type, FunctionType)
            and self._check_punct("{")
        ):
            body = self._parse_compound_statement()
            return [
                FunctionDefinition(
                    location=loc,
                    name=first_decl.name or "<anonymous>",
                    return_type=first_decl.type.return_type,
                    params=first_decl.type.params,
                    is_variadic=first_decl.type.is_variadic,
                    storage_class=specs.storage_class,
                    is_inline=specs.is_inline,
                    body=body,
                )
            ]

        decls: list[Declaration] = [first_decl]
        if specs.storage_class == "typedef" and first_decl.name:
            self._typedef_names.add(first_decl.name)

        while self._accept_punct(","):
            d = self._parse_init_declarator(specs)
            decls.append(d)
            if specs.storage_class == "typedef" and d.name:
                self._typedef_names.add(d.name)

        self._expect_punct(";")
        return decls

    # ------------------------------------------------------------------ specifiers

    def _parse_declaration_specifiers(self) -> _DeclSpecs:
        storage_class: str | None = None
        is_inline = False
        type_specifier_words: list[str] = []
        qualifiers: set[str] = set()
        struct_or_enum: Type | None = None
        typedef_type: TypedefName | None = None

        while True:
            self._skip_gcc_attributes()
            tok = self._peek()
            if tok.kind is TokenKind.KEYWORD:
                if tok.text in _STORAGE_CLASSES:
                    if storage_class is not None:
                        raise ParserError("multiple storage-class specifiers", tok.location)
                    storage_class = self._advance().text
                    continue
                if tok.text in _FUNCTION_SPECIFIERS or tok.text in {
                    "__inline",
                    "__inline__",
                }:
                    self._advance()
                    is_inline = True
                    continue
                if tok.text in _TYPE_QUALIFIERS:
                    qualifiers.add(self._advance().text)
                    continue
                if tok.text in _GCC_KEYWORD_QUALIFIERS:
                    qualifiers.add(_GCC_KEYWORD_QUALIFIERS[tok.text])
                    self._advance()
                    continue
                if tok.text in _TYPE_SPECIFIER_KEYWORDS:
                    type_specifier_words.append(self._advance().text)
                    continue
                if tok.text in {"__signed", "__signed__"}:
                    self._advance()
                    type_specifier_words.append("signed")
                    continue
                if tok.text == "struct":
                    struct_or_enum = self._parse_struct_or_union(is_union=False)
                    continue
                if tok.text == "union":
                    struct_or_enum = self._parse_struct_or_union(is_union=True)
                    continue
                if tok.text == "enum":
                    struct_or_enum = self._parse_enum()
                    continue
            if (
                tok.kind is TokenKind.IDENTIFIER
                and tok.text in self._typedef_names
                and not type_specifier_words
                and struct_or_enum is None
                and typedef_type is None
            ):
                typedef_type = TypedefName(location=tok.location, name=self._advance().text)
                continue
            break

        base_type: Type
        if struct_or_enum is not None:
            base_type = struct_or_enum
        elif typedef_type is not None:
            base_type = typedef_type
        elif type_specifier_words:
            specs = tuple(sorted(type_specifier_words))
            base_type = BasicType(
                location=self._peek(-1).location if self.pos > 0 else _origin(),
                specifiers=specs,
                qualifiers=frozenset(qualifiers),
            )
            qualifiers = set()  # in BasicType verbraucht
        else:
            # Implicit int (pre-C99) — wir machen es trotzdem mit, weil
            # ältere Embedded-Codebases das nutzen.
            base_type = BasicType(
                location=self._peek().location,
                specifiers=("int",),
                qualifiers=frozenset(),
            )

        if isinstance(base_type, BasicType) and qualifiers:
            base_type = BasicType(
                location=base_type.location,
                specifiers=base_type.specifiers,
                qualifiers=base_type.qualifiers | qualifiers,
            )
        return _DeclSpecs(
            storage_class=storage_class,
            is_inline=is_inline,
            base_type=base_type,
            qualifiers=frozenset(qualifiers),
        )

    def _parse_struct_or_union(self, *, is_union: bool) -> Type:
        kw_loc = self._advance().location  # konsumiere 'struct'/'union'
        self._skip_gcc_attributes()
        name: str | None = None
        tok = self._peek()
        if tok.kind is TokenKind.IDENTIFIER:
            name = self._advance().text
        members: tuple[Declaration, ...] | None = None
        if self._accept_punct("{"):
            collected: list[Declaration] = []
            while not self._check_punct("}") and not self._at_end():
                collected.extend(self._parse_struct_member())
            self._expect_punct("}")
            members = tuple(collected)
        self._skip_gcc_attributes()
        if is_union:
            return UnionType(location=kw_loc, name=name, members=members)
        return StructType(location=kw_loc, name=name, members=members)

    def _parse_struct_member(self) -> list[Declaration]:
        loc = self._peek().location
        specs = self._parse_declaration_specifiers()
        if self._accept_punct(";"):
            return [
                Declaration(
                    location=loc,
                    name=None,
                    type=specs.base_type,
                    storage_class=None,
                    initializer=None,
                )
            ]
        decls: list[Declaration] = [self._parse_struct_declarator(specs)]
        while self._accept_punct(","):
            decls.append(self._parse_struct_declarator(specs))
        self._expect_punct(";")
        return decls

    def _parse_struct_declarator(self, specs: _DeclSpecs) -> Declaration:
        # Bit-Field-Form: `:width` ohne Declarator
        if self._accept_punct(":"):
            self._parse_constant_expression()
            return Declaration(
                location=self._peek(-1).location,
                name=None,
                type=specs.base_type,
                storage_class=None,
            )
        decl = self._parse_init_declarator(specs, allow_initializer=False)
        if self._accept_punct(":"):
            self._parse_constant_expression()
        return decl

    def _parse_enum(self) -> Type:
        kw_loc = self._advance().location  # konsumiere 'enum'
        self._skip_gcc_attributes()
        name: str | None = None
        tok = self._peek()
        if tok.kind is TokenKind.IDENTIFIER:
            name = self._advance().text
        values: tuple[tuple[str, Expression | None], ...] | None = None
        if self._accept_punct("{"):
            collected: list[tuple[str, Expression | None]] = []
            while not self._check_punct("}") and not self._at_end():
                ident = self._expect(TokenKind.IDENTIFIER)
                value: Expression | None = None
                if self._accept_punct("="):
                    value = self._parse_constant_expression()
                collected.append((ident.text, value))
                if not self._accept_punct(","):
                    break
            self._expect_punct("}")
            values = tuple(collected)
        return EnumType(location=kw_loc, name=name, values=values)

    # ------------------------------------------------------------------ declarators

    def _parse_init_declarator(
        self, specs: _DeclSpecs, *, allow_initializer: bool = True
    ) -> Declaration:
        loc = self._peek().location
        name, type_builder = self._parse_declarator()
        full_type = type_builder(specs.base_type)
        self._skip_gcc_attributes()
        initializer: Expression | InitializerList | None = None
        if allow_initializer and self._accept_punct("="):
            initializer = self._parse_initializer()
        return Declaration(
            location=loc,
            name=name,
            type=full_type,
            storage_class=specs.storage_class,
            is_inline=specs.is_inline,
            initializer=initializer,
        )

    def _parse_declarator(
        self,
    ) -> tuple[str | None, object]:
        """Returns (name, type_builder), where type_builder takes a base
        type and returns the fully-constructed type."""
        # Prefix: Pointer (mit Qualifiers + GCC-Extensions)
        pointer_layers: list[frozenset[str]] = []
        while self._accept_punct("*"):
            quals: set[str] = set()
            while True:
                tok = self._peek()
                if tok.kind is TokenKind.KEYWORD and tok.text in _TYPE_QUALIFIERS:
                    quals.add(self._advance().text)
                elif tok.kind is TokenKind.KEYWORD and tok.text in _GCC_KEYWORD_QUALIFIERS:
                    quals.add(_GCC_KEYWORD_QUALIFIERS[self._advance().text])
                else:
                    break
            pointer_layers.append(frozenset(quals))

        name, inner_builder = self._parse_direct_declarator()

        def build(base: Type) -> Type:
            # ISO-C-Spiral-Rule: Pointer-Modifikatoren wirken auf den
            # Base-Type (wovon der eventuelle Function-/Array-Wrapper
            # zurückgibt), NICHT auf den schon-gewrapten Function-/Array-
            # Type. Daher Pointer-Layer ZUERST, dann inner_builder.
            t = base
            for quals in reversed(pointer_layers):
                t = PointerType(location=t.location, target=t, qualifiers=quals)
            return inner_builder(t)

        return name, build

    def _parse_direct_declarator(self) -> tuple[str | None, object]:
        loc = self._peek().location
        name: str | None = None
        inner_builder: object = lambda t: t  # noqa: E731 — identity

        if self._accept_punct("("):
            # Subdecl in parens (für Function-Pointer) ODER abstract decl.
            # Parens for grouping vs. parens of a function declarator are
            # disambiguated by whether the next token can start a parameter
            # list (i.e. type-specifier or `)` or `void`).
            if self._is_param_list_start():
                params, is_variadic = self._parse_parameter_list()
                self._expect_punct(")")
                inner_builder = self._wrap_function(inner_builder, params, is_variadic)
            else:
                inner_name, inner_builder = self._parse_declarator()
                self._expect_punct(")")
                name = inner_name
        elif self._peek().kind is TokenKind.IDENTIFIER:
            name = self._advance().text

        # Suffixes: array-subscripts und parenthesized parameter-lists
        while True:
            self._skip_gcc_attributes()
            if self._accept_punct("["):
                size: Expression | None = None
                if not self._check_punct("]"):
                    size = self._parse_assignment_expression()
                self._expect_punct("]")
                inner_builder = self._wrap_array(inner_builder, size, loc)
                continue
            if self._accept_punct("("):
                if self._accept_punct(")"):
                    inner_builder = self._wrap_function(inner_builder, (), False)
                else:
                    params, is_variadic = self._parse_parameter_list()
                    self._expect_punct(")")
                    inner_builder = self._wrap_function(inner_builder, params, is_variadic)
                continue
            break
        return name, inner_builder

    @staticmethod
    def _wrap_function(inner: object, params: tuple[Param, ...], is_variadic: bool):
        def build(base: Type) -> Type:
            ft = FunctionType(
                location=base.location,
                return_type=base,
                params=params,
                is_variadic=is_variadic,
            )
            return inner(ft)

        return build

    @staticmethod
    def _wrap_array(inner: object, size: Expression | None, loc: SourceLocation):
        def build(base: Type) -> Type:
            at = ArrayType(location=loc, element=base, size=size)
            return inner(at)

        return build

    def _is_param_list_start(self) -> bool:
        tok = self._peek()
        if tok.kind is TokenKind.PUNCTUATOR and tok.text == ")":
            return True
        if self._is_type_start(tok):
            return True
        return False

    def _parse_parameter_list(self) -> tuple[tuple[Param, ...], bool]:
        params: list[Param] = []
        is_variadic = False
        # `void` allein → 0 Params
        if (
            self._peek().kind is TokenKind.KEYWORD
            and self._peek().text == "void"
            and self._peek(1).kind is TokenKind.PUNCTUATOR
            and self._peek(1).text == ")"
        ):
            self._advance()
            return (), False
        while True:
            if self._check_punct("..."):
                self._advance()
                is_variadic = True
                break
            params.append(self._parse_parameter())
            if not self._accept_punct(","):
                break
        return tuple(params), is_variadic

    def _parse_parameter(self) -> Param:
        loc = self._peek().location
        specs = self._parse_declaration_specifiers()
        # Parameter darf abstract declarator haben (kein Name)
        name, type_builder = self._parse_declarator()
        full = type_builder(specs.base_type)
        return Param(location=loc, name=name, type=full)

    # ------------------------------------------------------------------ initializer

    def _parse_initializer(self) -> Expression | InitializerList:
        if self._accept_punct("{"):
            return self._parse_initializer_list()
        return self._parse_assignment_expression()

    def _parse_initializer_list(self) -> InitializerList:
        loc = self._peek(-1).location
        items: list[tuple[tuple[str, ...], Expression | InitializerList]] = []
        if self._accept_punct("}"):
            return InitializerList(location=loc, items=())
        while True:
            # Designated initializer: `.field = …` — wir sammeln den Pfad,
            # lehnen aber `[index]`-Designators ab (selten in Embedded-Code).
            designator: list[str] = []
            while self._accept_punct("."):
                ident = self._expect(TokenKind.IDENTIFIER)
                designator.append(ident.text)
            if designator:
                self._expect_punct("=")
            value = self._parse_initializer()
            items.append((tuple(designator), value))
            if not self._accept_punct(","):
                break
            if self._check_punct("}"):
                break
        self._expect_punct("}")
        return InitializerList(location=loc, items=tuple(items))

    # ------------------------------------------------------------------ statements

    def _parse_compound_statement(self) -> CompoundStmt:
        loc = self._expect_punct("{").location
        items: list[Statement | Declaration] = []
        while not self._check_punct("}") and not self._at_end():
            if self._is_declaration_start():
                items.extend(self._parse_external_declaration())
            else:
                items.append(self._parse_statement())
        self._expect_punct("}")
        return CompoundStmt(location=loc, items=tuple(items))

    def _is_declaration_start(self) -> bool:
        return self._is_type_start()

    def _parse_statement(self) -> Statement:
        loc = self._peek().location
        tok = self._peek()

        # Labeled-Statement
        if (
            tok.kind is TokenKind.IDENTIFIER
            and self._peek(1).kind is TokenKind.PUNCTUATOR
            and self._peek(1).text == ":"
            and tok.text not in self._typedef_names
        ):
            label = self._advance().text
            self._advance()  # konsumiere ":"
            body = self._parse_statement()
            return LabeledStmt(location=loc, label=label, body=body)

        if tok.kind is TokenKind.KEYWORD:
            if tok.text == "if":
                return self._parse_if_statement()
            if tok.text == "switch":
                return self._parse_switch_statement()
            if tok.text == "case":
                self._advance()
                value = self._parse_constant_expression()
                self._expect_punct(":")
                body = self._parse_statement()
                return CaseStmt(location=loc, value=value, body=body)
            if tok.text == "default":
                self._advance()
                self._expect_punct(":")
                body = self._parse_statement()
                return DefaultStmt(location=loc, body=body)
            if tok.text == "while":
                return self._parse_while_statement()
            if tok.text == "do":
                return self._parse_do_statement()
            if tok.text == "for":
                return self._parse_for_statement()
            if tok.text == "return":
                return self._parse_return_statement()
            if tok.text == "break":
                self._advance()
                self._expect_punct(";")
                return BreakStmt(location=loc)
            if tok.text == "continue":
                self._advance()
                self._expect_punct(";")
                return ContinueStmt(location=loc)
            if tok.text == "goto":
                self._advance()
                label = self._expect(TokenKind.IDENTIFIER).text
                self._expect_punct(";")
                return GotoStmt(location=loc, label=label)

        if tok.kind is TokenKind.PUNCTUATOR and tok.text == "{":
            return self._parse_compound_statement()
        if self._accept_punct(";"):
            return NullStmt(location=loc)

        # Expression-Statement
        expr = self._parse_expression()
        self._expect_punct(";")
        return ExpressionStmt(location=loc, expression=expr)

    def _parse_if_statement(self) -> IfStmt:
        loc = self._advance().location  # 'if'
        self._expect_punct("(")
        condition = self._parse_expression()
        self._expect_punct(")")
        then_branch = self._parse_statement()
        else_branch = None
        if self._accept_keyword("else"):
            else_branch = self._parse_statement()
        return IfStmt(
            location=loc,
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
        )

    def _parse_switch_statement(self) -> SwitchStmt:
        loc = self._advance().location  # 'switch'
        self._expect_punct("(")
        condition = self._parse_expression()
        self._expect_punct(")")
        body = self._parse_statement()
        return SwitchStmt(location=loc, condition=condition, body=body)

    def _parse_while_statement(self) -> WhileStmt:
        loc = self._advance().location  # 'while'
        self._expect_punct("(")
        condition = self._parse_expression()
        self._expect_punct(")")
        body = self._parse_statement()
        return WhileStmt(location=loc, condition=condition, body=body)

    def _parse_do_statement(self) -> DoStmt:
        loc = self._advance().location  # 'do'
        body = self._parse_statement()
        self._expect_keyword("while")
        self._expect_punct("(")
        condition = self._parse_expression()
        self._expect_punct(")")
        self._expect_punct(";")
        return DoStmt(location=loc, body=body, condition=condition)

    def _parse_for_statement(self) -> ForStmt:
        loc = self._advance().location  # 'for'
        self._expect_punct("(")
        init: Declaration | Expression | None = None
        if self._accept_punct(";"):
            init = None
        elif self._is_declaration_start():
            decl_list = self._parse_external_declaration()
            init = decl_list[0] if decl_list else None
        else:
            init = self._parse_expression()
            self._expect_punct(";")
        condition: Expression | None = None
        if not self._accept_punct(";"):
            condition = self._parse_expression()
            self._expect_punct(";")
        update: Expression | None = None
        if not self._check_punct(")"):
            update = self._parse_expression()
        self._expect_punct(")")
        body = self._parse_statement()
        return ForStmt(
            location=loc,
            init=init,
            condition=condition,
            update=update,
            body=body,
        )

    def _parse_return_statement(self) -> ReturnStmt:
        loc = self._advance().location  # 'return'
        value: Expression | None = None
        if not self._check_punct(";"):
            value = self._parse_expression()
        self._expect_punct(";")
        return ReturnStmt(location=loc, value=value)

    # ------------------------------------------------------------------ expressions

    def _parse_constant_expression(self) -> Expression:
        # ISO §6.6: constant-expression ist conditional-expression ohne
        # Assignments. Wir akzeptieren conditional-expression und
        # verlassen uns für die Konstanten-Eigenschaft auf spätere Phasen.
        return self._parse_conditional_expression()

    def _parse_expression(self) -> Expression:
        expr = self._parse_assignment_expression()
        while self._accept_punct(","):
            rhs = self._parse_assignment_expression()
            expr = BinaryOp(location=expr.location, op=",", lhs=expr, rhs=rhs)
        return expr

    def _parse_assignment_expression(self) -> Expression:
        # Wir parsen erst eine conditional-expression, dann schauen, ob
        # ein Assignment-Operator folgt. Das ist das klassische Muster,
        # das über Lookahead-Vermeidung den lvalue-Check verschiebt.
        lhs = self._parse_conditional_expression()
        op_tok = self._peek()
        if op_tok.kind is TokenKind.PUNCTUATOR and op_tok.text in _ASSIGNMENT_OPS:
            self._advance()
            rhs = self._parse_assignment_expression()
            return Assignment(location=lhs.location, op=op_tok.text, lhs=lhs, rhs=rhs)
        return lhs

    def _parse_conditional_expression(self) -> Expression:
        cond = self._parse_logical_or_expression()
        if self._accept_punct("?"):
            then_expr = self._parse_expression()
            self._expect_punct(":")
            else_expr = self._parse_conditional_expression()
            return TernaryOp(
                location=cond.location,
                condition=cond,
                then_expr=then_expr,
                else_expr=else_expr,
            )
        return cond

    def _parse_logical_or_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_logical_and_expression, ("||",))

    def _parse_logical_and_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_inclusive_or_expression, ("&&",))

    def _parse_inclusive_or_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_exclusive_or_expression, ("|",))

    def _parse_exclusive_or_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_and_expression, ("^",))

    def _parse_and_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_equality_expression, ("&",))

    def _parse_equality_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_relational_expression, ("==", "!="))

    def _parse_relational_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_shift_expression, ("<", ">", "<=", ">="))

    def _parse_shift_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_additive_expression, ("<<", ">>"))

    def _parse_additive_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_multiplicative_expression, ("+", "-"))

    def _parse_multiplicative_expression(self) -> Expression:
        return self._parse_left_assoc(self._parse_cast_expression, ("*", "/", "%"))

    def _parse_left_assoc(self, sub, ops: tuple[str, ...]) -> Expression:
        expr = sub()
        while True:
            tok = self._peek()
            if tok.kind is TokenKind.PUNCTUATOR and tok.text in ops:
                self._advance()
                rhs = sub()
                expr = BinaryOp(location=expr.location, op=tok.text, lhs=expr, rhs=rhs)
            else:
                break
        return expr

    def _parse_cast_expression(self) -> Expression:
        # Cast-Expression: `( type-name ) cast-expression`
        if self._check_punct("("):
            saved = self.pos
            self._advance()
            if self._is_type_start():
                # Tentative parse: type-name + ')' → es ist ein Cast.
                target_type = self._parse_type_name()
                if self._accept_punct(")"):
                    if self._check_punct("{"):
                        # Compound-Literal — wir parsen die Initializer-List
                        # und behandeln sie wie eine cast-expression mit
                        # Initializer-Operand.
                        init = self._parse_initializer_list()
                        return CastExpr(
                            location=target_type.location,
                            target_type=target_type,
                            operand=init,
                        )
                    operand = self._parse_cast_expression()
                    return CastExpr(
                        location=target_type.location,
                        target_type=target_type,
                        operand=operand,
                    )
                self.pos = saved
            else:
                self.pos = saved
        return self._parse_unary_expression()

    def _parse_unary_expression(self) -> Expression:
        loc = self._peek().location
        if self._accept_punct("++"):
            inner = self._parse_unary_expression()
            return UnaryOp(location=loc, op="++", operand=inner, prefix=True)
        if self._accept_punct("--"):
            inner = self._parse_unary_expression()
            return UnaryOp(location=loc, op="--", operand=inner, prefix=True)
        for op in ("&", "*", "+", "-", "~", "!"):
            if self._accept_punct(op):
                inner = self._parse_cast_expression()
                return UnaryOp(location=loc, op=op, operand=inner, prefix=True)
        if self._accept_keyword("sizeof"):
            return self._parse_sizeof(loc)
        return self._parse_postfix_expression()

    def _parse_sizeof(self, loc: SourceLocation) -> Expression:
        from .ast_nodes import SizeofExpr

        if self._check_punct("("):
            saved = self.pos
            self._advance()
            if self._is_type_start():
                target_type = self._parse_type_name()
                self._expect_punct(")")
                return SizeofExpr(location=loc, target=target_type)
            self.pos = saved
        operand = self._parse_unary_expression()
        return SizeofExpr(location=loc, target=operand)

    def _parse_postfix_expression(self) -> Expression:
        expr = self._parse_primary_expression()
        while True:
            tok = self._peek()
            if tok.kind is TokenKind.PUNCTUATOR and tok.text == "[":
                self._advance()
                index = self._parse_expression()
                self._expect_punct("]")
                expr = Subscript(location=expr.location, array=expr, index=index)
                continue
            if tok.kind is TokenKind.PUNCTUATOR and tok.text == "(":
                self._advance()
                args: list[Expression] = []
                if not self._check_punct(")"):
                    args.append(self._parse_assignment_expression())
                    while self._accept_punct(","):
                        args.append(self._parse_assignment_expression())
                self._expect_punct(")")
                expr = FunctionCall(location=expr.location, callee=expr, args=tuple(args))
                continue
            if tok.kind is TokenKind.PUNCTUATOR and tok.text == ".":
                self._advance()
                name = self._expect(TokenKind.IDENTIFIER).text
                expr = MemberAccess(location=expr.location, obj=expr, name=name, is_arrow=False)
                continue
            if tok.kind is TokenKind.PUNCTUATOR and tok.text == "->":
                self._advance()
                name = self._expect(TokenKind.IDENTIFIER).text
                expr = MemberAccess(location=expr.location, obj=expr, name=name, is_arrow=True)
                continue
            if tok.kind is TokenKind.PUNCTUATOR and tok.text == "++":
                self._advance()
                expr = UnaryOp(location=expr.location, op="++", operand=expr, prefix=False)
                continue
            if tok.kind is TokenKind.PUNCTUATOR and tok.text == "--":
                self._advance()
                expr = UnaryOp(location=expr.location, op="--", operand=expr, prefix=False)
                continue
            break
        return expr

    def _parse_primary_expression(self) -> Expression:
        tok = self._peek()
        loc = tok.location
        if tok.kind is TokenKind.IDENTIFIER:
            self._advance()
            return Identifier(location=loc, name=tok.text)
        if tok.kind is TokenKind.CONSTANT:
            self._advance()
            return self._parse_constant_token(tok)
        if tok.kind is TokenKind.STRING_LITERAL:
            self._advance()
            return StringLiteral(
                location=loc,
                text=_unquote_string(tok.text),
                is_wide=tok.text.startswith("L"),
            )
        if tok.kind is TokenKind.PUNCTUATOR and tok.text == "(":
            self._advance()
            inner = self._parse_expression()
            self._expect_punct(")")
            return ParenExpr(location=loc, inner=inner)
        raise ParserError(f"unexpected token in expression: {tok.text!r}", tok.location)

    @staticmethod
    def _parse_constant_token(tok: Token) -> Expression:
        text = tok.text
        # Char- und Wide-Char-Konstanten beginnen mit `'` oder `L'`
        if text.startswith("'") or text.startswith("L'"):
            return CharLiteral(location=tok.location, text=text, is_wide=text.startswith("L"))
        # Float: enthält '.' oder Exponent
        if any(c in text for c in ".eEpP") and not text.startswith(("0x", "0X")):
            return FloatLiteral(location=tok.location, text=text)
        if text.startswith(("0x", "0X")) and any(c in text for c in ".pP"):
            return FloatLiteral(location=tok.location, text=text)
        # Integer
        digits = text
        suffix_chars = ""
        while digits and digits[-1] in "uUlL":
            suffix_chars = digits[-1] + suffix_chars
            digits = digits[:-1]
        try:
            value = int(digits, 0)
        except ValueError as exc:
            raise ParserError(f"cannot parse integer constant {tok.text!r}", tok.location) from exc
        return IntLiteral(location=tok.location, value=value, suffix=suffix_chars)

    # ------------------------------------------------------------------ type-name

    def _parse_type_name(self) -> Type:
        specs = self._parse_declaration_specifiers()
        # Optional abstract-declarator
        _, type_builder = self._parse_declarator()
        return type_builder(specs.base_type)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unquote_string(text: str) -> str:
    if text.startswith('L"'):
        return text[2:-1]
    return text[1:-1]


def _origin() -> SourceLocation:
    return SourceLocation("<input>", 1, 1)


def _eof_token() -> Token:
    return Token(TokenKind.EOF, "", _origin())


__all__ = ["parse", "Parser", "ParserError", "TranslationUnit"]
