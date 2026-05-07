"""Symbol-Resolution für csa26-engine.

Erster Analyse-Pass nach dem Parser. Walkt den AST, baut die Symbol-
Tabelle mit Scopes auf und produziert eine `Side-Table`, die jeden
Identifier-Knoten auf sein Symbol zurückführt.

Scopes (ISO/IEC 9899:1999 §6.2.1):
- file scope (top-level)
- function-prototype scope (Parameter im Prototyp)
- function scope (Labels)
- block scope (Compound-Statements, plus die `for`-Init-Klausel)

Namespaces:
- ordinary identifiers (Variablen, Funktionen, Typedefs, Enum-Konstanten)
- tags (struct/union/enum-Namen)
- labels (goto-Targets, function-scope)
- struct/union members — pro Struct-Type separat (nicht hier)

Phase-1-Limitationen:
- Forward-References zwischen Top-Level-Decls werden nicht aufgelöst —
  Symbol muss vor Use deklariert sein. Reicht für die 20 Rules.
- Member-Namespaces werden nicht von hier verwaltet; Rules, die Member
  auflösen müssen (z.B. Rule 8.13 auf struct-Pointer-Members), greifen
  direkt auf den `StructType` aus dem Type-Inferer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from .ast_nodes import (
    CompoundStmt,
    Declaration,
    DoStmt,
    EnumType,
    ForStmt,
    FunctionCall,
    FunctionDefinition,
    Identifier,
    IfStmt,
    LabeledStmt,
    MemberAccess,
    Param,
    Statement,
    StructType,
    SwitchStmt,
    TranslationUnit,
    Type,
    UnionType,
    WhileStmt,
)
from .tokens import SourceLocation


class SymbolError(ValueError):
    def __init__(self, message: str, location: SourceLocation) -> None:
        super().__init__(f"{location}: {message}")
        self.location = location


SymbolKind = str  # "variable", "function", "typedef", "enum_constant", "param"


@dataclass(slots=True)
class Symbol:
    name: str
    kind: SymbolKind
    type: Type
    location: SourceLocation
    storage_class: str | None = None
    declaration: Declaration | FunctionDefinition | Param | None = None
    enum_value: int | None = None  # für enum_constant


@dataclass(slots=True)
class Scope:
    """Ein Lexikalischer Scope. `parent` ist None für file-scope."""

    parent: Scope | None
    ordinaries: dict[str, Symbol] = field(default_factory=dict)
    tags: dict[str, Type] = field(default_factory=dict)

    def lookup_ordinary(self, name: str) -> Symbol | None:
        if name in self.ordinaries:
            return self.ordinaries[name]
        if self.parent is None:
            return None
        return self.parent.lookup_ordinary(name)

    def lookup_tag(self, name: str) -> Type | None:
        if name in self.tags:
            return self.tags[name]
        if self.parent is None:
            return None
        return self.parent.lookup_tag(name)


@dataclass(slots=True)
class SymbolBindings:
    """Ergebnis von `bind()`: die Symbol-Tabelle plus eine Side-Table,
    die für jeden Identifier-Knoten das aufgelöste Symbol enthält.

    Über `id(node)` wird auf den Knoten gemappt — geht, weil wir den AST
    nicht klonen und in CPython die Identität stabil ist."""

    file_scope: Scope
    identifier_to_symbol: dict[int, Symbol] = field(default_factory=dict)
    function_table: dict[str, FunctionDefinition] = field(default_factory=dict)
    diagnostics: list[tuple[str, str, SourceLocation]] = field(default_factory=list)

    def symbol_for(self, ident: Identifier) -> Symbol | None:
        return self.identifier_to_symbol.get(id(ident))


def bind(tu: TranslationUnit) -> SymbolBindings:
    binder = _Binder()
    binder.bind_translation_unit(tu)
    return binder.bindings


class _Binder:
    """Walkt den AST und baut die Symbol-Tabelle auf."""

    def __init__(self) -> None:
        file_scope = Scope(parent=None)
        self.bindings = SymbolBindings(file_scope=file_scope)
        self._scope: Scope = file_scope

    # ------------------------------------------------------------------ scopes

    def _push_scope(self) -> Scope:
        new_scope = Scope(parent=self._scope)
        self._scope = new_scope
        return new_scope

    def _pop_scope(self) -> None:
        if self._scope.parent is None:
            raise RuntimeError("attempted to pop file-scope")
        self._scope = self._scope.parent

    # ------------------------------------------------------------------ entry

    def bind_translation_unit(self, tu: TranslationUnit) -> None:
        for decl in tu.declarations:
            if isinstance(decl, FunctionDefinition):
                self._bind_function_definition(decl)
            else:
                self._bind_declaration(decl)

    # ------------------------------------------------------------------ decls

    def _bind_declaration(self, decl: Declaration) -> None:
        # struct/union/enum-Tags eintragen
        self._register_tag_if_present(decl.type, location=decl.location)

        if decl.name is None:
            return

        # Enum-Konstanten als ordinary identifiers eintragen
        if isinstance(decl.type, EnumType) and decl.type.values is not None:
            for ident, _value in decl.type.values:
                self._define_ordinary(
                    Symbol(
                        name=ident,
                        kind="enum_constant",
                        type=decl.type,
                        location=decl.location,
                    )
                )

        kind: SymbolKind = "variable"
        if decl.storage_class == "typedef":
            kind = "typedef"
        elif _is_function_type(decl.type):
            kind = "function"

        sym = Symbol(
            name=decl.name,
            kind=kind,
            type=decl.type,
            location=decl.location,
            storage_class=decl.storage_class,
            declaration=decl,
        )
        self._define_ordinary(sym)

        if decl.initializer is not None:
            self._bind_initializer(decl.initializer)

    def _bind_function_definition(self, fn: FunctionDefinition) -> None:
        # Funktion in file-scope eintragen
        from .ast_nodes import FunctionType

        function_type = FunctionType(
            location=fn.location,
            return_type=fn.return_type,
            params=fn.params,
            is_variadic=fn.is_variadic,
        )
        sym = Symbol(
            name=fn.name,
            kind="function",
            type=function_type,
            location=fn.location,
            storage_class=fn.storage_class,
            declaration=fn,
        )
        self._define_ordinary(sym)
        self.bindings.function_table[fn.name] = fn

        # Function-Scope mit Parametern
        self._push_scope()
        for param in fn.params:
            if param.name is None:
                continue
            self._define_ordinary(
                Symbol(
                    name=param.name,
                    kind="param",
                    type=param.type,
                    location=param.location,
                    declaration=param,
                )
            )
        self._bind_compound_body(fn.body)
        self._pop_scope()

    # ------------------------------------------------------------------ tags

    def _register_tag_if_present(self, t: Type, *, location: SourceLocation) -> None:
        if isinstance(t, StructType | UnionType) and t.name and t.members is not None:
            self._scope.tags[t.name] = t
        elif isinstance(t, EnumType) and t.name and t.values is not None:
            self._scope.tags[t.name] = t

    # ------------------------------------------------------------------ ordinary

    def _define_ordinary(self, sym: Symbol) -> None:
        existing = self._scope.ordinaries.get(sym.name)
        if existing is not None:
            # Re-Declaration im selben Scope: in C erlaubt, wenn die Typen
            # kompatibel sind. Wir loggen es und behalten den ersten Eintrag.
            self.bindings.diagnostics.append(
                (
                    "info",
                    f"redeclaration of {sym.name!r}",
                    sym.location,
                )
            )
            return
        self._scope.ordinaries[sym.name] = sym

    # ------------------------------------------------------------------ statements

    def _bind_compound_body(self, body: CompoundStmt) -> None:
        # Compound-Statement öffnet einen eigenen Block-Scope. Bei einer
        # Function-Definition ist das der Function-Scope, also nicht
        # zusätzlich pushen — wir trennen das, indem der Caller schon
        # einen Scope geöffnet hat.
        for item in body.items:
            if isinstance(item, Declaration):
                self._bind_declaration(item)
            else:
                self._bind_statement(cast(Statement, item))

    def _bind_block(self, body: CompoundStmt) -> None:
        self._push_scope()
        self._bind_compound_body(body)
        self._pop_scope()

    def _bind_statement(self, stmt: Statement) -> None:
        from .ast_nodes import (
            BreakStmt,
            CaseStmt,
            ContinueStmt,
            DefaultStmt,
            ExpressionStmt,
            GotoStmt,
            NullStmt,
            ReturnStmt,
        )

        if isinstance(stmt, CompoundStmt):
            self._bind_block(stmt)
            return
        if isinstance(stmt, ExpressionStmt):
            self._bind_expression(stmt.expression)
            return
        if isinstance(stmt, IfStmt):
            self._bind_expression(stmt.condition)
            self._bind_statement(stmt.then_branch)
            if stmt.else_branch is not None:
                self._bind_statement(stmt.else_branch)
            return
        if isinstance(stmt, SwitchStmt):
            self._bind_expression(stmt.condition)
            self._bind_statement(stmt.body)
            return
        if isinstance(stmt, CaseStmt):
            self._bind_expression(stmt.value)
            self._bind_statement(stmt.body)
            return
        if isinstance(stmt, DefaultStmt):
            self._bind_statement(stmt.body)
            return
        if isinstance(stmt, WhileStmt):
            self._bind_expression(stmt.condition)
            self._bind_statement(stmt.body)
            return
        if isinstance(stmt, DoStmt):
            self._bind_statement(stmt.body)
            self._bind_expression(stmt.condition)
            return
        if isinstance(stmt, ForStmt):
            self._push_scope()
            if isinstance(stmt.init, Declaration):
                self._bind_declaration(stmt.init)
            elif stmt.init is not None:
                self._bind_expression(stmt.init)
            if stmt.condition is not None:
                self._bind_expression(stmt.condition)
            if stmt.update is not None:
                self._bind_expression(stmt.update)
            self._bind_statement(stmt.body)
            self._pop_scope()
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                self._bind_expression(stmt.value)
            return
        if isinstance(stmt, LabeledStmt):
            self._bind_statement(stmt.body)
            return
        if isinstance(stmt, (BreakStmt, ContinueStmt, GotoStmt, NullStmt)):
            return
        # Unbekannter Statement-Typ — ignorieren
        return

    # ------------------------------------------------------------------ expressions

    def _bind_expression(self, expr: object) -> None:
        from .ast_nodes import (
            Assignment,
            BinaryOp,
            CastExpr,
            CharLiteral,
            FloatLiteral,
            InitializerList,
            IntLiteral,
            ParenExpr,
            SizeofExpr,
            StringLiteral,
            Subscript,
            TernaryOp,
            UnaryOp,
        )

        if isinstance(expr, Identifier):
            sym = self._scope.lookup_ordinary(expr.name)
            if sym is None:
                self.bindings.diagnostics.append(
                    ("warning", f"unresolved identifier {expr.name!r}", expr.location)
                )
                return
            self.bindings.identifier_to_symbol[id(expr)] = sym
            return
        if isinstance(expr, ParenExpr):
            self._bind_expression(expr.inner)
            return
        if isinstance(expr, UnaryOp):
            self._bind_expression(expr.operand)
            return
        if isinstance(expr, BinaryOp):
            self._bind_expression(expr.lhs)
            self._bind_expression(expr.rhs)
            return
        if isinstance(expr, Assignment):
            self._bind_expression(expr.lhs)
            self._bind_expression(expr.rhs)
            return
        if isinstance(expr, TernaryOp):
            self._bind_expression(expr.condition)
            self._bind_expression(expr.then_expr)
            self._bind_expression(expr.else_expr)
            return
        if isinstance(expr, CastExpr):
            self._bind_expression(expr.operand)
            return
        if isinstance(expr, SizeofExpr):
            if not isinstance(expr.target, Type):
                self._bind_expression(expr.target)
            return
        if isinstance(expr, Subscript):
            self._bind_expression(expr.array)
            self._bind_expression(expr.index)
            return
        if isinstance(expr, MemberAccess):
            self._bind_expression(expr.obj)
            return
        if isinstance(expr, FunctionCall):
            self._bind_expression(expr.callee)
            for arg in expr.args:
                self._bind_expression(arg)
            return
        if isinstance(expr, InitializerList):
            for _designator, value in expr.items:
                self._bind_expression(value)
            return
        # IntLiteral, FloatLiteral, CharLiteral, StringLiteral —
        # keine Resolution nötig.
        if isinstance(expr, (IntLiteral, FloatLiteral, CharLiteral, StringLiteral)):
            return
        return

    # ------------------------------------------------------------------ initializer

    def _bind_initializer(self, init: object) -> None:
        from .ast_nodes import InitializerList

        if isinstance(init, InitializerList):
            for _designator, value in init.items:
                self._bind_initializer(value)
            return
        self._bind_expression(init)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_function_type(t: Type) -> bool:
    from .ast_nodes import FunctionType

    return isinstance(t, FunctionType)


__all__ = ["bind", "Symbol", "Scope", "SymbolBindings", "SymbolError"]
