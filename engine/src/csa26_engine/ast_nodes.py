"""AST-Knoten für csa26-engine.

Knoten-Hierarchie für C99-Subset (siehe `parser.py`-Modul-Doc für den
exakten Sprach-Scope). Alle Knoten sind dataclasses mit `location`-
Feld; Listen-Felder werden als `tuple` gespeichert, damit AST-Knoten
hashable bleiben.

Kategorien:
- TranslationUnit (Top-Level)
- Type-Knoten (BasicType, PointerType, ArrayType, FunctionType,
  StructType, UnionType, EnumType, TypedefName)
- Declaration-Knoten (Declaration, FunctionDefinition, Param)
- Statement-Knoten (CompoundStmt, IfStmt, SwitchStmt, …)
- Expression-Knoten (BinaryOp, UnaryOp, Assignment, …)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .tokens import SourceLocation

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Node:
    location: SourceLocation


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Type(Node):
    pass


@dataclass(frozen=True, slots=True)
class BasicType(Type):
    """Primitive C-Typ-Bezeichnung wie `int`, `unsigned long`, `float`.

    `specifiers` enthält die Sequenz der Type-Specifier-Tokens als
    sortiertes Tupel (z.B. `("long", "long", "unsigned")`), damit
    `unsigned long long` und `long long unsigned` als gleich gelten.
    """

    specifiers: tuple[str, ...]
    qualifiers: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class PointerType(Type):
    target: Type
    qualifiers: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class ArrayType(Type):
    element: Type
    size: Expression | None  # None für `[]` (incomplete array)


@dataclass(frozen=True, slots=True)
class FunctionType(Type):
    return_type: Type
    params: tuple[Param, ...]
    is_variadic: bool = False


@dataclass(frozen=True, slots=True)
class StructType(Type):
    name: str | None
    members: tuple[Declaration, ...] | None  # None bei reiner Forward-Ref


@dataclass(frozen=True, slots=True)
class UnionType(Type):
    name: str | None
    members: tuple[Declaration, ...] | None


@dataclass(frozen=True, slots=True)
class EnumType(Type):
    name: str | None
    values: tuple[tuple[str, Expression | None], ...] | None


@dataclass(frozen=True, slots=True)
class TypedefName(Type):
    name: str


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Declarator(Node):
    """Verbindung Identifier ↔ Type-Modifikatoren.

    Im Parser bauen wir den Type beim Declaration-Sammeln; Declarator
    selbst wird dann nicht mehr im fertigen AST gehalten — wir
    speichern stattdessen direkt `type` und `name` in der `Declaration`.
    Diese Klasse existiert als Zwischenrepräsentation während des
    Parsens.
    """

    name: str | None
    type_builder: object  # Closure, die den Type aus einem Base-Type baut


@dataclass(frozen=True, slots=True)
class Declaration(Node):
    """Eine `T x, y, z = init;`-Zeile, möglicherweise mit Storage-Class.

    Bei einer Multi-Declarator-Zeile wie `int a, *b, c[10];` produziert
    der Parser eine separate `Declaration` pro Declarator, alle mit
    derselben `storage_class` und derselben `base_type`.
    """

    name: str | None  # None bei anonymen struct-/union-Members
    type: Type
    storage_class: str | None  # "static", "extern", "typedef", "register", "auto"
    is_inline: bool = False
    initializer: Expression | InitializerList | None = None


@dataclass(frozen=True, slots=True)
class Param(Node):
    name: str | None
    type: Type


@dataclass(frozen=True, slots=True)
class FunctionDefinition(Node):
    name: str
    return_type: Type
    params: tuple[Param, ...]
    is_variadic: bool
    storage_class: str | None
    is_inline: bool
    body: CompoundStmt


@dataclass(frozen=True, slots=True)
class TranslationUnit(Node):
    declarations: tuple[FunctionDefinition | Declaration, ...]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Statement(Node):
    pass


@dataclass(frozen=True, slots=True)
class NullStmt(Statement):
    pass


@dataclass(frozen=True, slots=True)
class CompoundStmt(Statement):
    items: tuple[Statement | Declaration, ...]


@dataclass(frozen=True, slots=True)
class ExpressionStmt(Statement):
    expression: Expression


@dataclass(frozen=True, slots=True)
class IfStmt(Statement):
    condition: Expression
    then_branch: Statement
    else_branch: Statement | None


@dataclass(frozen=True, slots=True)
class SwitchStmt(Statement):
    condition: Expression
    body: Statement


@dataclass(frozen=True, slots=True)
class CaseStmt(Statement):
    value: Expression
    body: Statement


@dataclass(frozen=True, slots=True)
class DefaultStmt(Statement):
    body: Statement


@dataclass(frozen=True, slots=True)
class WhileStmt(Statement):
    condition: Expression
    body: Statement


@dataclass(frozen=True, slots=True)
class DoStmt(Statement):
    body: Statement
    condition: Expression


@dataclass(frozen=True, slots=True)
class ForStmt(Statement):
    init: Declaration | Expression | None
    condition: Expression | None
    update: Expression | None
    body: Statement


@dataclass(frozen=True, slots=True)
class ReturnStmt(Statement):
    value: Expression | None


@dataclass(frozen=True, slots=True)
class BreakStmt(Statement):
    pass


@dataclass(frozen=True, slots=True)
class ContinueStmt(Statement):
    pass


@dataclass(frozen=True, slots=True)
class GotoStmt(Statement):
    label: str


@dataclass(frozen=True, slots=True)
class LabeledStmt(Statement):
    label: str
    body: Statement


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Expression(Node):
    pass


@dataclass(frozen=True, slots=True)
class IntLiteral(Expression):
    value: int
    suffix: str  # "", "u", "l", "ll", "ul", "ull", "lu", "llu", …


@dataclass(frozen=True, slots=True)
class FloatLiteral(Expression):
    text: str  # roher Text, weil Float-Parsing platform-abhängig sein kann


@dataclass(frozen=True, slots=True)
class CharLiteral(Expression):
    text: str
    is_wide: bool


@dataclass(frozen=True, slots=True)
class StringLiteral(Expression):
    text: str
    is_wide: bool


@dataclass(frozen=True, slots=True)
class Identifier(Expression):
    name: str


@dataclass(frozen=True, slots=True)
class ParenExpr(Expression):
    inner: Expression


@dataclass(frozen=True, slots=True)
class UnaryOp(Expression):
    op: str  # "+", "-", "!", "~", "*", "&", "++", "--", "sizeof"
    operand: Expression
    prefix: bool


@dataclass(frozen=True, slots=True)
class BinaryOp(Expression):
    op: str  # "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
    #         "<<", ">>", "&", "|", "^", "&&", "||", ","
    lhs: Expression
    rhs: Expression


@dataclass(frozen=True, slots=True)
class Assignment(Expression):
    op: str  # "=", "+=", "-=", "*=", "/=", "%=", "<<=", ">>=", "&=", "|=", "^="
    lhs: Expression
    rhs: Expression


@dataclass(frozen=True, slots=True)
class TernaryOp(Expression):
    condition: Expression
    then_expr: Expression
    else_expr: Expression


@dataclass(frozen=True, slots=True)
class CastExpr(Expression):
    target_type: Type
    operand: Expression


@dataclass(frozen=True, slots=True)
class SizeofExpr(Expression):
    target: Type | Expression


@dataclass(frozen=True, slots=True)
class Subscript(Expression):
    array: Expression
    index: Expression


@dataclass(frozen=True, slots=True)
class MemberAccess(Expression):
    obj: Expression
    name: str
    is_arrow: bool  # True für `->`, False für `.`


@dataclass(frozen=True, slots=True)
class FunctionCall(Expression):
    callee: Expression
    args: tuple[Expression, ...]


@dataclass(frozen=True, slots=True)
class InitializerList(Expression):
    """`{1, 2, 3}` oder `{.x = 1, .y = 2}`.

    Designators werden als String-Pfade vor dem Item gespeichert; bei
    nicht-designierter Initialisierung ist der Designator-Pfad leer.
    """

    items: tuple[tuple[tuple[str, ...], Expression | InitializerList], ...]


__all__ = [
    "Node",
    "Type",
    "BasicType",
    "PointerType",
    "ArrayType",
    "FunctionType",
    "StructType",
    "UnionType",
    "EnumType",
    "TypedefName",
    "Declaration",
    "Declarator",
    "Param",
    "FunctionDefinition",
    "TranslationUnit",
    "Statement",
    "NullStmt",
    "CompoundStmt",
    "ExpressionStmt",
    "IfStmt",
    "SwitchStmt",
    "CaseStmt",
    "DefaultStmt",
    "WhileStmt",
    "DoStmt",
    "ForStmt",
    "ReturnStmt",
    "BreakStmt",
    "ContinueStmt",
    "GotoStmt",
    "LabeledStmt",
    "Expression",
    "IntLiteral",
    "FloatLiteral",
    "CharLiteral",
    "StringLiteral",
    "Identifier",
    "ParenExpr",
    "UnaryOp",
    "BinaryOp",
    "Assignment",
    "TernaryOp",
    "CastExpr",
    "SizeofExpr",
    "Subscript",
    "MemberAccess",
    "FunctionCall",
    "InitializerList",
]
