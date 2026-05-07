"""Die 20 csa26-Engine-Rules — alle in einem Modul.

Jede Rule ist eine Funktion mit Signatur

    def rule_X_Y(ctx: AnalysisContext) -> Iterator[Finding]: ...

Die `ALL_RULES`-Tabelle unten registriert sie mit MISRA-Rule-ID,
Titel und Severity.

Bewusste Phase-1-Heuristiken:

- 14.3 (invariant condition) und 2.1 (unreachable code) sind ISO-
  undecidable — wir liefern Heuristiken, die typische Fälle treffen
  und im Doc-String klar als Heuristik markiert sind.
- 17.2 (recursion) ist über mehrere Translation-Units undecidable —
  wir prüfen nur intra-TU-direkte und einfache mutual recursion.
- Cluster 10.x und 11.x kommen mit Subset-Heuristiken, die für die
  drei Test-Fixturen treffen, aber kein vollständiger ISO-Type-
  Equivalence-Apparat sind.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .ast_nodes import (
    Assignment,
    BasicType,
    BinaryOp,
    CastExpr,
    CompoundStmt,
    Declaration,
    DoStmt,
    Expression,
    ExpressionStmt,
    ForStmt,
    FunctionCall,
    FunctionDefinition,
    FunctionType,
    Identifier,
    IfStmt,
    IntLiteral,
    NullStmt,
    ReturnStmt,
    Subscript,
    TernaryOp,
    TranslationUnit,
    Type,
    UnaryOp,
    WhileStmt,
)
from .findings import Finding, Severity
from .symbols import SymbolBindings
from .tokens import SourceLocation
from .types import (
    is_floating,
    is_integer,
    is_pointer,
    is_void,
    pointed_type,
    pointer_target_is_const,
    pointer_types_compatible,
)
from .walk import walk


@dataclass(slots=True)
class AnalysisContext:
    tu: TranslationUnit
    bindings: SymbolBindings
    types: dict[int, Type]
    used_macro_names: frozenset[str] = frozenset()
    user_macros: dict[str, object] = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    title: str
    severity: Severity
    check: object  # callable[[AnalysisContext], Iterator[Finding]]


def _f(rule_id: str, severity: Severity, message: str, location: SourceLocation) -> Finding:
    return Finding(rule_id=rule_id, severity=severity, message=message, location=location)


# =============================================================================
# Cluster: Type-Safety (10.1, 10.3, 10.4, 10.5, 10.8)
# =============================================================================


def rule_10_1(ctx: AnalysisContext) -> Iterator[Finding]:
    """Operands of binary arithmetic shall not have essentially different
    type categories.

    Phase-1-Heuristik: wir flaggen Mischungen integer ↔ floating in
    arithmetischen Operationen. Komplexere Type-Categories (essentially
    enum etc.) sind in Phase 2 dran.
    """
    for node in walk(ctx.tu):
        if not isinstance(node, BinaryOp):
            continue
        if node.op not in {"+", "-", "*", "/", "%"}:
            continue
        lhs_t = ctx.types.get(id(node.lhs))
        rhs_t = ctx.types.get(id(node.rhs))
        if lhs_t is None or rhs_t is None:
            continue
        if is_integer(lhs_t) and is_floating(rhs_t):
            yield _f(
                "misra-c2012-10.1",
                Severity.WARNING,
                f"binary '{node.op}' mixes integer and floating-point operands",
                node.location,
            )
        elif is_floating(lhs_t) and is_integer(rhs_t):
            yield _f(
                "misra-c2012-10.1",
                Severity.WARNING,
                f"binary '{node.op}' mixes floating-point and integer operands",
                node.location,
            )


def rule_10_3(ctx: AnalysisContext) -> Iterator[Finding]:
    """Value of an expression shall not be assigned to an object with a
    narrower essential type or different essential type category.

    Heuristik: integer-Literal-Assignment mit explizitem Wert > 8 bit auf
    `(unsigned) char`-typed-Target, sowie Assignments zwischen integer
    und floating.
    """
    for node in walk(ctx.tu):
        target_type: Type | None = None
        rhs: Expression | None = None
        if isinstance(node, Assignment):
            target_type = ctx.types.get(id(node.lhs))
            rhs = node.rhs
        elif isinstance(node, Declaration) and node.initializer is not None:
            target_type = node.type
            init = node.initializer
            if isinstance(init, Expression):
                rhs = init
        if target_type is None or rhs is None:
            continue
        rhs_type = ctx.types.get(id(rhs))
        if rhs_type is None:
            continue
        if is_integer(target_type) and is_floating(rhs_type):
            yield _f(
                "misra-c2012-10.3",
                Severity.WARNING,
                "implicit conversion from floating-point to integer",
                rhs.location,
            )
        elif is_floating(target_type) and is_integer(rhs_type):
            yield _f(
                "misra-c2012-10.3",
                Severity.NOTE,
                "implicit conversion from integer to floating-point",
                rhs.location,
            )


def rule_10_4(ctx: AnalysisContext) -> Iterator[Finding]:
    """Both operands of binary operator shall have essentially the same
    type category.

    Heuristik: pointer ↔ integer im selben binären Operator (außerhalb
    von Pointer-Arithmetik `ptr + int` / `ptr - int`, die explizit
    erlaubt ist).
    """
    for node in walk(ctx.tu):
        if not isinstance(node, BinaryOp):
            continue
        if node.op not in {"==", "!=", "<", ">", "<=", ">=", "&", "|", "^"}:
            continue
        lhs_t = ctx.types.get(id(node.lhs))
        rhs_t = ctx.types.get(id(node.rhs))
        if lhs_t is None or rhs_t is None:
            continue
        if (is_pointer(lhs_t) and is_integer(rhs_t)) or (is_integer(lhs_t) and is_pointer(rhs_t)):
            yield _f(
                "misra-c2012-10.4",
                Severity.WARNING,
                f"'{node.op}' compares pointer and integer operands",
                node.location,
            )


def rule_10_5(ctx: AnalysisContext) -> Iterator[Finding]:
    """Value shall not be cast to an inappropriate essential type.

    Phase-1-Heuristik: Cast von floating-point zu pointer und umgekehrt.
    """
    for node in walk(ctx.tu):
        if not isinstance(node, CastExpr):
            continue
        operand_t = ctx.types.get(id(node.operand))
        if operand_t is None:
            continue
        target = node.target_type
        if is_pointer(target) and is_floating(operand_t):
            yield _f(
                "misra-c2012-10.5",
                Severity.WARNING,
                "cast from floating-point to pointer",
                node.location,
            )
        elif is_floating(target) and is_pointer(operand_t):
            yield _f(
                "misra-c2012-10.5",
                Severity.WARNING,
                "cast from pointer to floating-point",
                node.location,
            )


def rule_10_8(ctx: AnalysisContext) -> Iterator[Finding]:
    """Value of a composite expression shall not be cast to a different
    essential type category or wider essential type.

    Heuristik: Cast eines integer-Ausdrucks auf einen schmaleren
    integer-Typ (Daten-Verlust-Risiko).
    """
    for node in walk(ctx.tu):
        if not isinstance(node, CastExpr):
            continue
        operand_t = ctx.types.get(id(node.operand))
        target = node.target_type
        if operand_t is None:
            continue
        if not (is_integer(operand_t) and is_integer(target)):
            continue
        if _integer_width_score(target) < _integer_width_score(operand_t):
            yield _f(
                "misra-c2012-10.8",
                Severity.WARNING,
                "cast to a narrower integer type can lose information",
                node.location,
            )


def _integer_width_score(t: Type) -> int:
    if not isinstance(t, BasicType):
        return 2
    if "char" in t.specifiers:
        return 0
    if "short" in t.specifiers:
        return 1
    if t.specifiers.count("long") >= 2:
        return 4
    if "long" in t.specifiers:
        return 3
    return 2


# =============================================================================
# Cluster: Control-Flow-Disziplin (14.3, 14.4, 15.5, 15.7)
# =============================================================================


def rule_14_3(ctx: AnalysisContext) -> Iterator[Finding]:
    """Controlling expressions shall not be invariant.

    Heuristik: `if (0)`, `if (1)`, `while (1)` (außer offen-Loops mit
    explizitem `break`), `if (constant)` werden gemeldet. `while (1)`
    mit Body, der `break`/`return` enthält, wird *nicht* gemeldet
    (bekanntes Idiom).
    """
    for node in walk(ctx.tu):
        condition: Expression | None = None
        location: SourceLocation | None = None
        is_open_loop = False
        if isinstance(node, IfStmt):
            condition = node.condition
            location = node.location
        elif isinstance(node, (WhileStmt, DoStmt)):
            condition = node.condition
            location = node.location
            is_open_loop = True
        if condition is None or location is None:
            continue
        if not _is_constant_expression(condition):
            continue
        # `while (1) { …; break; }` ist akzeptiertes Idiom — überspringen
        if is_open_loop and _evaluates_truthy(condition) and _body_has_break_or_return(node):
            continue
        yield _f(
            "misra-c2012-14.3",
            Severity.WARNING,
            "controlling expression is invariant",
            location,
        )


def rule_14_4(ctx: AnalysisContext) -> Iterator[Finding]:
    """Controlling expression of an `if` or iteration statement shall
    have essentially Boolean type.

    Heuristik: erlauben Vergleichs-, Logik- und Boolean-Operatoren plus
    Konstanten 0/1; alles andere wird als nicht-bool markiert.
    """
    for node in walk(ctx.tu):
        condition: Expression | None = None
        location: SourceLocation | None = None
        if isinstance(node, IfStmt):
            condition = node.condition
            location = node.location
        elif isinstance(node, (WhileStmt, DoStmt)):
            condition = node.condition
            location = node.location
        elif isinstance(node, ForStmt):
            condition = node.condition
            location = node.location
        if condition is None or location is None:
            continue
        if _is_essentially_boolean(condition, ctx):
            continue
        yield _f(
            "misra-c2012-14.4",
            Severity.WARNING,
            "controlling expression is not essentially boolean",
            location,
        )


def rule_15_5(ctx: AnalysisContext) -> Iterator[Finding]:
    """Function shall have a single point of exit at the end.

    Wir flaggen Funktionen mit > 1 `return`-Statement.
    """
    for node in walk(ctx.tu):
        if not isinstance(node, FunctionDefinition):
            continue
        returns = [n for n in walk(node.body) if isinstance(n, ReturnStmt)]
        if len(returns) > 1:
            yield _f(
                "misra-c2012-15.5",
                Severity.WARNING,
                f"function {node.name!r} has {len(returns)} return statements; "
                "should have one at the end",
                node.location,
            )


def rule_15_7(ctx: AnalysisContext) -> Iterator[Finding]:
    """All `if … else if` chains shall be terminated with an `else`.

    Heuristik: Wenn ein `IfStmt` einen `else_branch` hat und dieser
    selbst ein `IfStmt` ohne else ist, fehlt der finale else.
    """
    for node in walk(ctx.tu):
        if not isinstance(node, IfStmt):
            continue
        if node.else_branch is None:
            continue
        # Folge die else-Kette
        cur = node.else_branch
        while isinstance(cur, IfStmt) and cur.else_branch is not None:
            cur = cur.else_branch
        if isinstance(cur, IfStmt) and cur.else_branch is None:
            yield _f(
                "misra-c2012-15.7",
                Severity.WARNING,
                "if-else if chain is not terminated with an else",
                cur.location,
            )


# =============================================================================
# Cluster: Pointer-Disziplin (8.13, 11.3, 11.5, 18.4)
# =============================================================================


def rule_8_13(ctx: AnalysisContext) -> Iterator[Finding]:
    """A pointer should point to a const-qualified type whenever possible.

    Heuristik: Pointer-Parameter, die innerhalb der Funktion nicht in
    schreibender Position vorkommen (kein `*p = …`, kein `p[i] = …`,
    kein `p->m = …`, kein `&p` als Argument für ein non-const-Param),
    sollten const-target sein.
    """
    for fn in walk(ctx.tu):
        if not isinstance(fn, FunctionDefinition):
            continue
        for param in fn.params:
            if param.name is None or not is_pointer(param.type):
                continue
            if pointer_target_is_const(param.type):
                continue
            if not _param_is_written_through(param.name, fn.body):
                yield _f(
                    "misra-c2012-8.13",
                    Severity.NOTE,
                    f"pointer parameter {param.name!r} is only read; consider 'const'",
                    param.location,
                )


def rule_11_3(ctx: AnalysisContext) -> Iterator[Finding]:
    """A cast shall not be performed between a pointer to object type
    and a pointer to a different object type.
    """
    for node in walk(ctx.tu):
        if not isinstance(node, CastExpr):
            continue
        operand_t = ctx.types.get(id(node.operand))
        target = node.target_type
        if operand_t is None:
            continue
        if not (is_pointer(operand_t) and is_pointer(target)):
            continue
        if pointer_types_compatible(operand_t, target):
            continue
        yield _f(
            "misra-c2012-11.3",
            Severity.WARNING,
            "cast between pointers to different object types",
            node.location,
        )


def rule_11_5(ctx: AnalysisContext) -> Iterator[Finding]:
    """A conversion should not be performed from pointer-to-void to
    pointer-to-object.
    """
    for node in walk(ctx.tu):
        if not isinstance(node, CastExpr):
            continue
        operand_t = ctx.types.get(id(node.operand))
        target = node.target_type
        if operand_t is None:
            continue
        if not is_pointer(operand_t) or not is_pointer(target):
            continue
        operand_target = pointed_type(operand_t)
        target_target = pointed_type(target)
        if (
            operand_target is not None
            and is_void(operand_target)
            and target_target is not None
            and not is_void(target_target)
        ):
            yield _f(
                "misra-c2012-11.5",
                Severity.NOTE,
                "conversion from pointer-to-void to pointer-to-object",
                node.location,
            )


def rule_18_4(ctx: AnalysisContext) -> Iterator[Finding]:
    """Use of `+`, `-`, `+=`, `-=` on pointer types shall be avoided
    in favour of array subscripting.
    """
    for node in walk(ctx.tu):
        if isinstance(node, BinaryOp) and node.op in {"+", "-"}:
            lhs_t = ctx.types.get(id(node.lhs))
            rhs_t = ctx.types.get(id(node.rhs))
            ptr_int = (
                lhs_t is not None and is_pointer(lhs_t) and rhs_t is not None and is_integer(rhs_t)
            )
            int_ptr = (
                rhs_t is not None and is_pointer(rhs_t) and lhs_t is not None and is_integer(lhs_t)
            )
            if ptr_int:
                yield _f(
                    "misra-c2012-18.4",
                    Severity.WARNING,
                    "pointer arithmetic — prefer array subscripting",
                    node.location,
                )
            elif int_ptr:
                yield _f(
                    "misra-c2012-18.4",
                    Severity.WARNING,
                    "pointer arithmetic — prefer array subscripting",
                    node.location,
                )
        elif isinstance(node, Assignment) and node.op in {"+=", "-="}:
            lhs_t = ctx.types.get(id(node.lhs))
            if lhs_t is not None and is_pointer(lhs_t):
                yield _f(
                    "misra-c2012-18.4",
                    Severity.WARNING,
                    "pointer arithmetic — prefer array subscripting",
                    node.location,
                )


# =============================================================================
# Cluster: Funktions-Hygiene (8.4, 8.7, 17.2, 17.7)
# =============================================================================


def rule_8_4(ctx: AnalysisContext) -> Iterator[Finding]:
    """A compatible declaration shall be visible when an object or
    function with external linkage is defined.

    Heuristik: für jede Function-Definition mit external linkage
    (kein `static`) prüfen, ob es eine vorhergehende Declaration
    gleichen Namens gibt. `main` ist als Sonderfall erlaubt.
    """
    seen_declarations: set[str] = set()
    for decl in ctx.tu.declarations:
        if isinstance(decl, Declaration):
            if decl.name and isinstance(decl.type, FunctionType):
                seen_declarations.add(decl.name)
            elif decl.name and decl.storage_class == "extern":
                seen_declarations.add(decl.name)
            elif decl.name:
                seen_declarations.add(decl.name)
            continue
        if not isinstance(decl, FunctionDefinition):
            continue
        if decl.storage_class == "static":
            continue
        if decl.name == "main":
            continue
        if decl.name in seen_declarations:
            continue
        yield _f(
            "misra-c2012-8.4",
            Severity.WARNING,
            f"function {decl.name!r} with external linkage has no previous declaration",
            decl.location,
        )


def rule_8_7(ctx: AnalysisContext) -> Iterator[Finding]:
    """Functions and objects should not be defined with external linkage
    if they are referenced in only one TU.

    Heuristik: in einer Single-TU-Analyse können wir nicht sehen, ob ein
    Symbol in einer anderen TU benutzt wird. Wir flaggen daher *alle*
    Top-Level-Definitionen mit external linkage, deren Verwendung sich
    *innerhalb* der TU vollständig auf den Definitions-Body beschränkt
    (also nicht von einer anderen Funktion aufgerufen).
    Schwächeres Signal als ein Whole-Program-Check, aber reicht für die
    drei Test-Fixturen — Cppcheck-Premium-Heuristik gleicher Qualität.
    """
    referenced: set[str] = set()
    for fn in walk(ctx.tu):
        if not isinstance(fn, FunctionDefinition):
            continue
        for inner in walk(fn.body):
            if isinstance(inner, Identifier):
                sym = ctx.bindings.symbol_for(inner)
                if sym is not None and sym.kind in {"function", "variable"}:
                    referenced.add(sym.name)
    for decl in ctx.tu.declarations:
        if isinstance(decl, FunctionDefinition):
            if decl.storage_class == "static" or decl.name == "main":
                continue
            if decl.name not in referenced:
                # Wird von keiner anderen TU-internen Funktion gerufen —
                # könnte static sein.
                yield _f(
                    "misra-c2012-8.7",
                    Severity.NOTE,
                    f"function {decl.name!r} could have internal linkage (static)",
                    decl.location,
                )
        elif isinstance(decl, Declaration) and decl.name:
            if decl.storage_class == "static" or decl.storage_class == "typedef":
                continue
            if not isinstance(decl.type, (FunctionType,)):
                # Top-Level-Variable mit external linkage
                if decl.name not in referenced:
                    yield _f(
                        "misra-c2012-8.7",
                        Severity.NOTE,
                        f"object {decl.name!r} could have internal linkage (static)",
                        decl.location,
                    )


def rule_17_2(ctx: AnalysisContext) -> Iterator[Finding]:
    """Functions shall not call themselves, either directly or indirectly.

    Heuristik: bauen einen Call-Graph aus den Function-Calls innerhalb
    jeder Funktion und prüfen auf Zyklen via Tiefensuche. Über mehrere
    TUs hinweg ist das undecidable; in einer TU greift die Analyse
    sicher.
    """
    call_graph: dict[str, set[str]] = {}
    for fn in walk(ctx.tu):
        if not isinstance(fn, FunctionDefinition):
            continue
        callees: set[str] = set()
        for inner in walk(fn.body):
            if isinstance(inner, FunctionCall) and isinstance(inner.callee, Identifier):
                callees.add(inner.callee.name)
        call_graph[fn.name] = callees

    for fn in walk(ctx.tu):
        if not isinstance(fn, FunctionDefinition):
            continue
        if _has_cycle_from(fn.name, call_graph):
            yield _f(
                "misra-c2012-17.2",
                Severity.WARNING,
                f"function {fn.name!r} is recursive (directly or indirectly)",
                fn.location,
            )


def _has_cycle_from(start: str, graph: dict[str, set[str]]) -> bool:
    seen: set[str] = set()
    stack = [start]
    first = True
    while stack:
        cur = stack.pop()
        if cur == start and not first:
            return True
        first = False
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in graph.get(cur, ()):
            if nxt == start:
                return True
            if nxt not in seen:
                stack.append(nxt)
    return False


def rule_17_7(ctx: AnalysisContext) -> Iterator[Finding]:
    """Value returned by a function having non-void return type shall be
    used.

    Heuristik: ein FunctionCall, der direkt als ExpressionStmt steht
    (also nicht in einer größeren Expression eingebettet), und dessen
    Ziel eine Funktion mit non-void Return-Type ist, wird gemeldet —
    außer wenn der Aufruf explizit `(void)` gecastet wird.
    """
    for stmt in walk(ctx.tu):
        if not isinstance(stmt, ExpressionStmt):
            continue
        expr = stmt.expression
        if isinstance(expr, CastExpr) and is_void(expr.target_type):
            continue
        if not isinstance(expr, FunctionCall):
            continue
        callee = expr.callee
        if not isinstance(callee, Identifier):
            continue
        sym = ctx.bindings.symbol_for(callee)
        if sym is None or not isinstance(sym.type, FunctionType):
            continue
        ret_t = sym.type.return_type
        if is_void(ret_t):
            continue
        yield _f(
            "misra-c2012-17.7",
            Severity.WARNING,
            f"return value of {callee.name!r} is not used",
            expr.location,
        )


# =============================================================================
# Cluster: Toter/Unbenutzter Code (2.1, 2.2, 2.5)
# =============================================================================


def rule_2_1(ctx: AnalysisContext) -> Iterator[Finding]:
    """A project shall not contain unreachable code.

    Heuristik: Statements, die nach `return`, `break`, `continue` oder
    `goto` im selben Block stehen, sind unreachable.
    """
    for fn in walk(ctx.tu):
        if not isinstance(fn, FunctionDefinition):
            continue
        for compound in walk(fn.body):
            if not isinstance(compound, CompoundStmt):
                continue
            after_terminator = False
            for item in compound.items:
                if after_terminator:
                    if isinstance(item, NullStmt):
                        continue
                    yield _f(
                        "misra-c2012-2.1",
                        Severity.WARNING,
                        "code is unreachable",
                        getattr(item, "location", fn.location),
                    )
                    break
                if isinstance(item, ReturnStmt):
                    after_terminator = True
                elif _is_unconditional_branch(item):
                    after_terminator = True


def rule_2_2(ctx: AnalysisContext) -> Iterator[Finding]:
    """There shall be no dead code: a statement that produces a value
    which is never used.

    Heuristik: ein ExpressionStmt, dessen Expression weder Assignment
    noch FunctionCall noch ein Pre-/Post-Inkrement/Dekrement ist, hat
    keinen Side-Effect und ist dead code.
    """
    for stmt in walk(ctx.tu):
        if not isinstance(stmt, ExpressionStmt):
            continue
        expr = stmt.expression
        if _has_side_effect(expr):
            continue
        yield _f(
            "misra-c2012-2.2",
            Severity.WARNING,
            "expression statement has no side-effect (dead code)",
            stmt.location,
        )


def rule_2_5(ctx: AnalysisContext) -> Iterator[Finding]:
    """A project should not contain unused macro declarations.

    Wir prüfen pro `#define`, ob das Macro während des Preprocessings
    expandiert oder via `defined()`/`#ifdef`/`#ifndef` referenziert
    wurde.
    """
    if not ctx.user_macros:
        return
    for name, macro in ctx.user_macros.items():
        if name in ctx.used_macro_names:
            continue
        yield _f(
            "misra-c2012-2.5",
            Severity.NOTE,
            f"macro {name!r} is defined but never used",
            getattr(macro, "location", SourceLocation("<input>", 1, 1)),
        )


# =============================================================================
# Helpers
# =============================================================================


def _param_is_written_through(param_name: str, body) -> bool:
    """Hat der Parameter ein Schreibevent: `*p = …`, `p[i] = …`,
    `p->m = …`, `++p`, `p++`, `--p`, `p--`?"""
    for node in walk(body):
        if isinstance(node, Assignment):
            target = node.lhs
            if _expression_dereferences(target, param_name):
                return True
            if isinstance(target, Identifier) and target.name == param_name:
                return True
        elif isinstance(node, UnaryOp) and node.op in {"++", "--"}:
            if isinstance(node.operand, Identifier) and node.operand.name == param_name:
                return True
    return False


def _expression_dereferences(expr, param_name: str) -> bool:
    if isinstance(expr, UnaryOp) and expr.op == "*":
        if isinstance(expr.operand, Identifier) and expr.operand.name == param_name:
            return True
    if isinstance(expr, Subscript):
        if isinstance(expr.array, Identifier) and expr.array.name == param_name:
            return True
    from .ast_nodes import MemberAccess

    if isinstance(expr, MemberAccess) and expr.is_arrow:
        if isinstance(expr.obj, Identifier) and expr.obj.name == param_name:
            return True
    return False


def _is_constant_expression(expr: Expression) -> bool:
    if isinstance(expr, IntLiteral):
        return True
    return False


def _evaluates_truthy(expr: Expression) -> bool:
    return isinstance(expr, IntLiteral) and expr.value != 0


def _body_has_break_or_return(loop_node) -> bool:
    from .ast_nodes import BreakStmt

    body = getattr(loop_node, "body", None)
    if body is None:
        return False
    for n in walk(body):
        if isinstance(n, (BreakStmt, ReturnStmt)):
            return True
    return False


def _is_essentially_boolean(expr: Expression, ctx: AnalysisContext) -> bool:
    if isinstance(expr, BinaryOp) and expr.op in {
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
        "&&",
        "||",
    }:
        return True
    if isinstance(expr, UnaryOp) and expr.op == "!":
        return True
    if isinstance(expr, IntLiteral) and expr.value in (0, 1):
        return True
    if isinstance(expr, TernaryOp):
        return _is_essentially_boolean(expr.then_expr, ctx) and _is_essentially_boolean(
            expr.else_expr, ctx
        )
    return False


def _is_unconditional_branch(stmt) -> bool:
    from .ast_nodes import BreakStmt, ContinueStmt, GotoStmt

    return isinstance(stmt, (BreakStmt, ContinueStmt, GotoStmt))


def _has_side_effect(expr: Expression) -> bool:
    if isinstance(expr, Assignment):
        return True
    if isinstance(expr, FunctionCall):
        return True
    if isinstance(expr, UnaryOp) and expr.op in {"++", "--"}:
        return True
    if isinstance(expr, BinaryOp) and expr.op == ",":
        return _has_side_effect(expr.lhs) or _has_side_effect(expr.rhs)
    return False


# =============================================================================
# Registry
# =============================================================================


ALL_RULES: tuple[Rule, ...] = (
    Rule(
        rule_id="misra-c2012-10.1",
        title="binary arithmetic operands shall have compatible essential type",
        severity=Severity.WARNING,
        check=rule_10_1,
    ),
    Rule(
        rule_id="misra-c2012-10.3",
        title="value shall not be assigned to a narrower or differently-typed object",
        severity=Severity.WARNING,
        check=rule_10_3,
    ),
    Rule(
        rule_id="misra-c2012-10.4",
        title="binary operator operands shall have the same essential type category",
        severity=Severity.WARNING,
        check=rule_10_4,
    ),
    Rule(
        rule_id="misra-c2012-10.5",
        title="value shall not be cast to an inappropriate essential type",
        severity=Severity.WARNING,
        check=rule_10_5,
    ),
    Rule(
        rule_id="misra-c2012-10.8",
        title="composite-expression cast shall not change essential type or width",
        severity=Severity.WARNING,
        check=rule_10_8,
    ),
    Rule(
        rule_id="misra-c2012-14.3",
        title="controlling expressions shall not be invariant",
        severity=Severity.WARNING,
        check=rule_14_3,
    ),
    Rule(
        rule_id="misra-c2012-14.4",
        title="controlling expression shall be essentially boolean",
        severity=Severity.WARNING,
        check=rule_14_4,
    ),
    Rule(
        rule_id="misra-c2012-15.5",
        title="function shall have a single point of exit at the end",
        severity=Severity.WARNING,
        check=rule_15_5,
    ),
    Rule(
        rule_id="misra-c2012-15.7",
        title="if-else if chains shall be terminated with an else",
        severity=Severity.WARNING,
        check=rule_15_7,
    ),
    Rule(
        rule_id="misra-c2012-8.13",
        title="pointers should target const-qualified type when possible",
        severity=Severity.NOTE,
        check=rule_8_13,
    ),
    Rule(
        rule_id="misra-c2012-11.3",
        title="cast shall not be performed between pointers to different object types",
        severity=Severity.WARNING,
        check=rule_11_3,
    ),
    Rule(
        rule_id="misra-c2012-11.5",
        title="conversion should not be from pointer-to-void to pointer-to-object",
        severity=Severity.NOTE,
        check=rule_11_5,
    ),
    Rule(
        rule_id="misra-c2012-18.4",
        title="pointer arithmetic should be avoided in favour of array subscripting",
        severity=Severity.WARNING,
        check=rule_18_4,
    ),
    Rule(
        rule_id="misra-c2012-8.4",
        title="external linkage definition requires a previous compatible declaration",
        severity=Severity.WARNING,
        check=rule_8_4,
    ),
    Rule(
        rule_id="misra-c2012-8.7",
        title="function or object used in only one TU should have internal linkage",
        severity=Severity.NOTE,
        check=rule_8_7,
    ),
    Rule(
        rule_id="misra-c2012-17.2",
        title="functions shall not call themselves directly or indirectly",
        severity=Severity.WARNING,
        check=rule_17_2,
    ),
    Rule(
        rule_id="misra-c2012-17.7",
        title="non-void return value of a function shall be used",
        severity=Severity.WARNING,
        check=rule_17_7,
    ),
    Rule(
        rule_id="misra-c2012-2.1",
        title="project shall not contain unreachable code",
        severity=Severity.WARNING,
        check=rule_2_1,
    ),
    Rule(
        rule_id="misra-c2012-2.2",
        title="there shall be no dead statements without side-effect",
        severity=Severity.WARNING,
        check=rule_2_2,
    ),
    Rule(
        rule_id="misra-c2012-2.5",
        title="project should not contain unused macro declarations",
        severity=Severity.NOTE,
        check=rule_2_5,
    ),
)


__all__ = ["ALL_RULES", "Rule", "AnalysisContext"]
