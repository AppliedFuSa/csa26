"""Type-System-Helper für csa26-engine.

Liefert strukturelle Type-Eigenschaften und Type-Inferenz für
Expressions. Reicht für die ausgewählten 20 MISRA-C:2012-Rules —
keine vollständige ISO-Type-Maschine.

Funktionsumfang:
- Eigenschaften: `is_pointer`, `is_arithmetic`, `is_integer`,
  `is_floating`, `is_void`, `is_function`, `is_array`,
  `is_const_qualified`.
- Pointer-Helper: `pointed_type`.
- Pointer-Type-Compatibility: `pointer_types_compatible`.
- Type-Inferenz für Expressions: `infer_types`.
- Implicit-Conversion-Helper: `usual_arithmetic_conversion`,
  `integer_promotion`.
"""

from __future__ import annotations

from typing import cast

from .ast_nodes import (
    ArrayType,
    Assignment,
    BasicType,
    BinaryOp,
    CastExpr,
    CharLiteral,
    Expression,
    FloatLiteral,
    FunctionCall,
    FunctionType,
    Identifier,
    IntLiteral,
    MemberAccess,
    ParenExpr,
    PointerType,
    SizeofExpr,
    StringLiteral,
    StructType,
    Subscript,
    TernaryOp,
    Type,
    TypedefName,
    UnaryOp,
    UnionType,
)
from .symbols import SymbolBindings
from .tokens import SourceLocation

# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def is_pointer(t: Type | None) -> bool:
    return isinstance(t, PointerType)


def is_array(t: Type | None) -> bool:
    return isinstance(t, ArrayType)


def is_function(t: Type | None) -> bool:
    return isinstance(t, FunctionType)


def is_void(t: Type | None) -> bool:
    return isinstance(t, BasicType) and t.specifiers == ("void",)


_INTEGER_SPECIFIER_KEYWORDS = frozenset(
    {"char", "short", "int", "long", "signed", "unsigned", "_Bool"}
)
_FLOATING_SPECIFIER_KEYWORDS = frozenset({"float", "double"})


def is_integer(t: Type | None) -> bool:
    if isinstance(t, BasicType):
        return any(s in _INTEGER_SPECIFIER_KEYWORDS for s in t.specifiers)
    return False


def is_floating(t: Type | None) -> bool:
    if isinstance(t, BasicType):
        return any(s in _FLOATING_SPECIFIER_KEYWORDS for s in t.specifiers)
    return False


def is_arithmetic(t: Type | None) -> bool:
    return is_integer(t) or is_floating(t)


def is_const_qualified(t: Type | None) -> bool:
    if isinstance(t, BasicType):
        return "const" in t.qualifiers
    if isinstance(t, PointerType):
        return "const" in t.qualifiers
    return False


def pointed_type(t: Type) -> Type | None:
    if isinstance(t, PointerType):
        return t.target
    if isinstance(t, ArrayType):
        return t.element
    return None


def pointer_target_is_const(t: Type) -> bool:
    """Für `const int *p`: True. Für `int * const p`: False (das ist
    der Pointer selbst, nicht das Target)."""
    target = pointed_type(t)
    if target is None:
        return False
    return is_const_qualified(target)


# ---------------------------------------------------------------------------
# Type-Equivalence (subset)
# ---------------------------------------------------------------------------


def types_strictly_equal(a: Type, b: Type) -> bool:
    """Streng strukturell-gleich. Ignoriert Source-Location."""
    if isinstance(a, BasicType) and isinstance(b, BasicType):
        return a.specifiers == b.specifiers and a.qualifiers == b.qualifiers
    if isinstance(a, PointerType) and isinstance(b, PointerType):
        return a.qualifiers == b.qualifiers and types_strictly_equal(a.target, b.target)
    if isinstance(a, ArrayType) and isinstance(b, ArrayType):
        return types_strictly_equal(a.element, b.element)
    if isinstance(a, FunctionType) and isinstance(b, FunctionType):
        if not types_strictly_equal(a.return_type, b.return_type):
            return False
        if len(a.params) != len(b.params) or a.is_variadic != b.is_variadic:
            return False
        return all(
            types_strictly_equal(p1.type, p2.type)
            for p1, p2 in zip(a.params, b.params, strict=True)
        )
    if isinstance(a, StructType) and isinstance(b, StructType):
        return a.name == b.name
    if isinstance(a, UnionType) and isinstance(b, UnionType):
        return a.name == b.name
    if isinstance(a, TypedefName) and isinstance(b, TypedefName):
        return a.name == b.name
    return False


def pointer_types_compatible(a: Type, b: Type) -> bool:
    """Rule-11.3-Kern: zwei Pointer-Typen sind kompatibel, wenn ihre
    Target-Typen strukturell gleich sind (nach Qualifier-Drop) und einer
    der beiden mindestens dieselben Qualifier wie der andere hat oder
    einer der Targets `void` ist (Rule 11.5).
    """
    if not (is_pointer(a) and is_pointer(b)):
        return False
    a = cast(PointerType, a)
    b = cast(PointerType, b)
    a_target = a.target
    b_target = b.target
    if is_void(a_target) or is_void(b_target):
        return True
    return types_strictly_equal(a_target, b_target)


# ---------------------------------------------------------------------------
# Implicit conversions
# ---------------------------------------------------------------------------


def integer_promotion(t: Type) -> Type:
    """ISO §6.3.1.1: char/short → int (oder unsigned int, falls nicht
    representable). Wir produzieren immer `int`, weil die exakten
    Implementations-Details für unsere Rules nicht relevant sind."""
    if isinstance(t, BasicType) and any(s in {"char", "short"} for s in t.specifiers):
        return BasicType(location=t.location, specifiers=("int",), qualifiers=frozenset())
    return t


def usual_arithmetic_conversion(a: Type, b: Type) -> Type:
    """ISO §6.3.1.8: 'usual arithmetic conversions' produzieren einen
    gemeinsamen Typ. Wir liefern eine vereinfachte, aber für unsere
    Rules ausreichende Logik."""
    a = integer_promotion(a)
    b = integer_promotion(b)
    if is_floating(a) and is_floating(b):
        return _wider_floating(a, b)
    if is_floating(a):
        return a
    if is_floating(b):
        return b
    return _wider_integer(a, b)


def _floating_rank(t: Type) -> int:
    if isinstance(t, BasicType):
        if "double" in t.specifiers and "long" in t.specifiers:
            return 3
        if "double" in t.specifiers:
            return 2
        if "float" in t.specifiers:
            return 1
    return 0


def _wider_floating(a: Type, b: Type) -> Type:
    return a if _floating_rank(a) >= _floating_rank(b) else b


def _integer_rank(t: Type) -> int:
    if isinstance(t, BasicType):
        if any(s == "long" for s in t.specifiers) and t.specifiers.count("long") >= 2:
            return 4
        if "long" in t.specifiers:
            return 3
        if "int" in t.specifiers:
            return 2
        if "short" in t.specifiers:
            return 1
        if "char" in t.specifiers:
            return 0
    return 2


def _wider_integer(a: Type, b: Type) -> Type:
    return a if _integer_rank(a) >= _integer_rank(b) else b


# ---------------------------------------------------------------------------
# Type-Inference für Expressions
# ---------------------------------------------------------------------------


_INT_TYPE = BasicType(
    location=SourceLocation("<builtin>", 0, 0),
    specifiers=("int",),
    qualifiers=frozenset(),
)


def infer_types(
    bindings: SymbolBindings,
) -> dict[int, Type]:
    """Berechnet für jede Expression im AST den Type. Liefert eine
    `id(expr) → Type`-Map."""
    inferer = _TypeInferer(bindings)
    return inferer.run()


class _TypeInferer:
    def __init__(self, bindings: SymbolBindings) -> None:
        self.bindings = bindings
        self.types: dict[int, Type] = {}

    def run(self) -> dict[int, Type]:
        for fn in self.bindings.function_table.values():
            self._visit_block(fn.body)
        for sym in self.bindings.file_scope.ordinaries.values():
            decl = sym.declaration
            if decl is not None and hasattr(decl, "initializer") and decl.initializer is not None:
                self._visit(decl.initializer)
        return self.types

    # ---- statements -----------------------------------------------------------

    def _visit_block(self, body) -> None:
        from .ast_nodes import (
            BreakStmt,
            CaseStmt,
            CompoundStmt,
            ContinueStmt,
            Declaration,
            DefaultStmt,
            DoStmt,
            ExpressionStmt,
            ForStmt,
            GotoStmt,
            IfStmt,
            LabeledStmt,
            NullStmt,
            ReturnStmt,
            SwitchStmt,
            WhileStmt,
        )

        for item in body.items:
            if isinstance(item, Declaration):
                if item.initializer is not None:
                    self._visit(item.initializer)
                continue
            if isinstance(item, CompoundStmt):
                self._visit_block(item)
                continue
            if isinstance(item, ExpressionStmt):
                self._visit(item.expression)
                continue
            if isinstance(item, IfStmt):
                self._visit(item.condition)
                self._visit_stmt(item.then_branch)
                if item.else_branch is not None:
                    self._visit_stmt(item.else_branch)
                continue
            if isinstance(item, (WhileStmt, DoStmt)):
                self._visit(item.condition)
                self._visit_stmt(item.body)
                continue
            if isinstance(item, ForStmt):
                if isinstance(item.init, Declaration):
                    if item.init.initializer is not None:
                        self._visit(item.init.initializer)
                elif item.init is not None:
                    self._visit(item.init)
                if item.condition is not None:
                    self._visit(item.condition)
                if item.update is not None:
                    self._visit(item.update)
                self._visit_stmt(item.body)
                continue
            if isinstance(item, SwitchStmt):
                self._visit(item.condition)
                self._visit_stmt(item.body)
                continue
            if isinstance(item, (CaseStmt, DefaultStmt, LabeledStmt)):
                if isinstance(item, CaseStmt):
                    self._visit(item.value)
                self._visit_stmt(item.body)
                continue
            if isinstance(item, ReturnStmt) and item.value is not None:
                self._visit(item.value)
                continue
            if isinstance(item, (BreakStmt, ContinueStmt, GotoStmt, NullStmt)):
                continue

    def _visit_stmt(self, stmt) -> None:
        from .ast_nodes import CompoundStmt

        if isinstance(stmt, CompoundStmt):
            self._visit_block(stmt)
            return
        # Wrapping als Single-Item-Block, damit alle Pfade durchs gleiche Tor
        self._visit_block(_SingleItemBlock(stmt))

    # ---- expressions ----------------------------------------------------------

    def _visit(self, expr: Expression | object) -> Type:
        from .ast_nodes import InitializerList

        if isinstance(expr, InitializerList):
            for _designator, value in expr.items:
                self._visit(value)
            return _INT_TYPE  # ungenau, aber für unsere Rules ausreichend

        if not isinstance(expr, Expression):
            return _INT_TYPE

        cached = self.types.get(id(expr))
        if cached is not None:
            return cached
        result = self._compute(expr)
        self.types[id(expr)] = result
        return result

    def _compute(self, expr: Expression) -> Type:
        if isinstance(expr, IntLiteral):
            return _INT_TYPE
        if isinstance(expr, FloatLiteral):
            return BasicType(location=expr.location, specifiers=("double",), qualifiers=frozenset())
        if isinstance(expr, CharLiteral):
            return BasicType(location=expr.location, specifiers=("int",), qualifiers=frozenset())
        if isinstance(expr, StringLiteral):
            char = BasicType(
                location=expr.location, specifiers=("char",), qualifiers=frozenset({"const"})
            )
            return PointerType(location=expr.location, target=char, qualifiers=frozenset())
        if isinstance(expr, Identifier):
            sym = self.bindings.symbol_for(expr)
            if sym is None:
                return _INT_TYPE
            return sym.type
        if isinstance(expr, ParenExpr):
            return self._visit(expr.inner)
        if isinstance(expr, UnaryOp):
            return self._compute_unary(expr)
        if isinstance(expr, BinaryOp):
            return self._compute_binary(expr)
        if isinstance(expr, Assignment):
            self._visit(expr.rhs)
            return self._visit(expr.lhs)
        if isinstance(expr, TernaryOp):
            self._visit(expr.condition)
            t1 = self._visit(expr.then_expr)
            t2 = self._visit(expr.else_expr)
            if is_arithmetic(t1) and is_arithmetic(t2):
                return usual_arithmetic_conversion(t1, t2)
            return t1
        if isinstance(expr, CastExpr):
            self._visit(expr.operand)
            return expr.target_type
        if isinstance(expr, SizeofExpr):
            if not isinstance(expr.target, Type):
                self._visit(expr.target)
            return _INT_TYPE
        if isinstance(expr, Subscript):
            arr_t = self._visit(expr.array)
            self._visit(expr.index)
            target = pointed_type(arr_t)
            return target if target is not None else _INT_TYPE
        if isinstance(expr, MemberAccess):
            obj_t = self._visit(expr.obj)
            return self._lookup_member(obj_t, expr.name) or _INT_TYPE
        if isinstance(expr, FunctionCall):
            callee_t = self._visit(expr.callee)
            for arg in expr.args:
                self._visit(arg)
            if isinstance(callee_t, FunctionType):
                return callee_t.return_type
            if isinstance(callee_t, PointerType) and isinstance(callee_t.target, FunctionType):
                return callee_t.target.return_type
            return _INT_TYPE
        return _INT_TYPE

    def _compute_unary(self, expr: UnaryOp) -> Type:
        operand_t = self._visit(expr.operand)
        if expr.op == "&":
            return PointerType(location=expr.location, target=operand_t, qualifiers=frozenset())
        if expr.op == "*":
            return pointed_type(operand_t) or _INT_TYPE
        if expr.op == "!":
            return _INT_TYPE
        # ++, --, +, -, ~ behalten den Type
        return operand_t

    def _compute_binary(self, expr: BinaryOp) -> Type:
        lhs_t = self._visit(expr.lhs)
        rhs_t = self._visit(expr.rhs)
        op = expr.op
        if op in {"==", "!=", "<", ">", "<=", ">=", "&&", "||"}:
            return _INT_TYPE
        if op == ",":
            return rhs_t
        # Pointer + integer / Pointer - integer
        if op in {"+", "-"}:
            if is_pointer(lhs_t) and is_integer(rhs_t):
                return lhs_t
            if is_pointer(rhs_t) and is_integer(lhs_t):
                return rhs_t
            if is_pointer(lhs_t) and is_pointer(rhs_t) and op == "-":
                return _INT_TYPE  # ptrdiff_t simplified
        if is_arithmetic(lhs_t) and is_arithmetic(rhs_t):
            return usual_arithmetic_conversion(lhs_t, rhs_t)
        return lhs_t

    def _lookup_member(self, obj_t: Type, name: str) -> Type | None:
        # Bei Pointer auf struct durchgreifen
        if isinstance(obj_t, PointerType):
            obj_t = obj_t.target
        if isinstance(obj_t, (StructType, UnionType)) and obj_t.members:
            for member in obj_t.members:
                if member.name == name:
                    return member.type
        return None


class _SingleItemBlock:
    """Wrapper, der ein einzelnes Statement wie ein CompoundStmt-Body
    aussehen lässt — vereinfacht den Visit-Code."""

    __slots__ = ("items",)

    def __init__(self, item) -> None:
        self.items = (item,)


__all__ = [
    "is_pointer",
    "is_array",
    "is_function",
    "is_void",
    "is_integer",
    "is_floating",
    "is_arithmetic",
    "is_const_qualified",
    "pointed_type",
    "pointer_target_is_const",
    "types_strictly_equal",
    "pointer_types_compatible",
    "integer_promotion",
    "usual_arithmetic_conversion",
    "infer_types",
]
