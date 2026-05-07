"""AST-Walker — Generator über alle Knoten im AST.

Eine Rule kann einfach `for node in walk(tu): if isinstance(node, IfStmt): …`
schreiben, statt einen kompletten Visitor zu definieren.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .ast_nodes import (
    ArrayType,
    Assignment,
    BinaryOp,
    CaseStmt,
    CastExpr,
    CompoundStmt,
    Declaration,
    DefaultStmt,
    DoStmt,
    EnumType,
    ExpressionStmt,
    ForStmt,
    FunctionCall,
    FunctionDefinition,
    FunctionType,
    IfStmt,
    InitializerList,
    LabeledStmt,
    MemberAccess,
    Node,
    Param,
    ParenExpr,
    PointerType,
    ReturnStmt,
    SizeofExpr,
    StructType,
    Subscript,
    SwitchStmt,
    TernaryOp,
    TranslationUnit,
    UnaryOp,
    UnionType,
    WhileStmt,
)


def walk(node: Node | None) -> Iterator[Node]:
    """Yields `node` and all transitive children."""
    if node is None:
        return
    yield node
    for child in _children(node):
        if child is None:
            continue
        if isinstance(child, Node):
            yield from walk(child)


def _children(node: Any) -> Iterator[Any]:
    if isinstance(node, TranslationUnit):
        yield from node.declarations
        return
    if isinstance(node, FunctionDefinition):
        yield node.return_type
        yield from node.params
        yield node.body
        return
    if isinstance(node, Declaration):
        yield node.type
        if node.initializer is not None:
            yield node.initializer
        return
    if isinstance(node, Param):
        yield node.type
        return
    if isinstance(node, CompoundStmt):
        yield from node.items
        return
    if isinstance(node, ExpressionStmt):
        yield node.expression
        return
    if isinstance(node, IfStmt):
        yield node.condition
        yield node.then_branch
        if node.else_branch is not None:
            yield node.else_branch
        return
    if isinstance(node, SwitchStmt):
        yield node.condition
        yield node.body
        return
    if isinstance(node, CaseStmt):
        yield node.value
        yield node.body
        return
    if isinstance(node, DefaultStmt):
        yield node.body
        return
    if isinstance(node, WhileStmt):
        yield node.condition
        yield node.body
        return
    if isinstance(node, DoStmt):
        yield node.body
        yield node.condition
        return
    if isinstance(node, ForStmt):
        if node.init is not None:
            yield node.init
        if node.condition is not None:
            yield node.condition
        if node.update is not None:
            yield node.update
        yield node.body
        return
    if isinstance(node, ReturnStmt):
        if node.value is not None:
            yield node.value
        return
    if isinstance(node, LabeledStmt):
        yield node.body
        return
    if isinstance(node, ParenExpr):
        yield node.inner
        return
    if isinstance(node, UnaryOp):
        yield node.operand
        return
    if isinstance(node, BinaryOp):
        yield node.lhs
        yield node.rhs
        return
    if isinstance(node, Assignment):
        yield node.lhs
        yield node.rhs
        return
    if isinstance(node, TernaryOp):
        yield node.condition
        yield node.then_expr
        yield node.else_expr
        return
    if isinstance(node, CastExpr):
        yield node.target_type
        yield node.operand
        return
    if isinstance(node, SizeofExpr):
        yield node.target
        return
    if isinstance(node, Subscript):
        yield node.array
        yield node.index
        return
    if isinstance(node, MemberAccess):
        yield node.obj
        return
    if isinstance(node, FunctionCall):
        yield node.callee
        yield from node.args
        return
    if isinstance(node, InitializerList):
        for _designator, value in node.items:
            yield value
        return
    if isinstance(node, PointerType):
        yield node.target
        return
    if isinstance(node, ArrayType):
        yield node.element
        if node.size is not None:
            yield node.size
        return
    if isinstance(node, FunctionType):
        yield node.return_type
        yield from node.params
        return
    if isinstance(node, (StructType, UnionType)) and node.members is not None:
        yield from node.members
        return
    if isinstance(node, EnumType) and node.values is not None:
        for _name, value in node.values:
            if value is not None:
                yield value
        return


__all__ = ["walk"]
