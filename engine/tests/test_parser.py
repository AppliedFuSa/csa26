import pytest

from csa26_engine.ast_nodes import (
    ArrayType,
    Assignment,
    BasicType,
    BinaryOp,
    BreakStmt,
    CompoundStmt,
    Declaration,
    DoStmt,
    EnumType,
    ExpressionStmt,
    ForStmt,
    FunctionCall,
    FunctionDefinition,
    FunctionType,
    Identifier,
    IfStmt,
    InitializerList,
    IntLiteral,
    MemberAccess,
    PointerType,
    ReturnStmt,
    StringLiteral,
    StructType,
    Subscript,
    SwitchStmt,
    TernaryOp,
    TranslationUnit,
    TypedefName,
    UnaryOp,
    WhileStmt,
)
from csa26_engine.parser import ParserError, parse
from csa26_engine.preprocessor import preprocess


def _parse(src: str):
    return parse(preprocess(src))


# --- Translation unit shape --------------------------------------------------


def test_empty_translation_unit():
    tu = _parse("")
    assert isinstance(tu, TranslationUnit)
    assert tu.declarations == ()


def test_simple_int_variable_declaration():
    tu = _parse("int x;")
    assert len(tu.declarations) == 1
    decl = tu.declarations[0]
    assert isinstance(decl, Declaration)
    assert decl.name == "x"
    assert isinstance(decl.type, BasicType)
    assert decl.type.specifiers == ("int",)


def test_initializer_assignment_form():
    tu = _parse("int x = 42;")
    decl = tu.declarations[0]
    assert isinstance(decl, Declaration)
    assert isinstance(decl.initializer, IntLiteral)
    assert decl.initializer.value == 42


def test_multiple_declarators_in_one_declaration():
    tu = _parse("int a, b, c;")
    names = [d.name for d in tu.declarations if isinstance(d, Declaration)]
    assert names == ["a", "b", "c"]


# --- Storage class and qualifiers --------------------------------------------


def test_static_const_variable():
    tu = _parse("static const int x = 10;")
    decl = tu.declarations[0]
    assert isinstance(decl, Declaration)
    assert decl.storage_class == "static"
    assert isinstance(decl.type, BasicType)
    assert "const" in decl.type.qualifiers


# --- Pointers / arrays / functions -------------------------------------------


def test_pointer_to_int():
    tu = _parse("int *p;")
    decl = tu.declarations[0]
    assert isinstance(decl.type, PointerType)
    assert isinstance(decl.type.target, BasicType)
    assert decl.type.target.specifiers == ("int",)


def test_pointer_to_const_int():
    tu = _parse("const int *p;")
    decl = tu.declarations[0]
    assert isinstance(decl.type, PointerType)
    assert "const" in decl.type.target.qualifiers


def test_const_pointer_to_int():
    tu = _parse("int * const p;")
    decl = tu.declarations[0]
    assert isinstance(decl.type, PointerType)
    assert "const" in decl.type.qualifiers


def test_fixed_array():
    tu = _parse("int buf[16];")
    decl = tu.declarations[0]
    assert isinstance(decl.type, ArrayType)
    assert isinstance(decl.type.size, IntLiteral)
    assert decl.type.size.value == 16


def test_function_declaration():
    tu = _parse("int add(int a, int b);")
    decl = tu.declarations[0]
    assert isinstance(decl, Declaration)
    assert isinstance(decl.type, FunctionType)
    assert len(decl.type.params) == 2
    assert decl.type.params[0].name == "a"


def test_void_parameter_list_means_zero_params():
    tu = _parse("void f(void);")
    decl = tu.declarations[0]
    assert isinstance(decl.type, FunctionType)
    assert decl.type.params == ()


def test_variadic_function_declaration():
    tu = _parse("int printf(const char *fmt, ...);")
    decl = tu.declarations[0]
    assert isinstance(decl.type, FunctionType)
    assert decl.type.is_variadic


# --- Function definitions ----------------------------------------------------


def test_simple_function_definition():
    src = "int add(int a, int b) { return a + b; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    assert isinstance(fn, FunctionDefinition)
    assert fn.name == "add"
    assert isinstance(fn.body, CompoundStmt)
    ret = fn.body.items[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, BinaryOp)


def test_void_function_returns_nothing():
    tu = _parse("void noop(void) { return; }")
    fn = tu.declarations[0]
    assert isinstance(fn, FunctionDefinition)
    assert isinstance(fn.body.items[0], ReturnStmt)
    assert fn.body.items[0].value is None


# --- Struct, union, enum, typedef --------------------------------------------


def test_struct_definition():
    tu = _parse("struct Point { int x; int y; };")
    decl = tu.declarations[0]
    assert isinstance(decl, Declaration)
    assert isinstance(decl.type, StructType)
    assert decl.type.name == "Point"
    assert len(decl.type.members) == 2


def test_enum_with_explicit_values():
    tu = _parse("enum Color { RED = 0, GREEN = 1, BLUE = 2 };")
    decl = tu.declarations[0]
    assert isinstance(decl.type, EnumType)
    assert [v[0] for v in decl.type.values] == ["RED", "GREEN", "BLUE"]


def test_typedef_declares_new_type_name():
    src = "typedef unsigned int u32; u32 x;"
    tu = _parse(src)
    # Erste Decl ist typedef, zweite nutzt es
    second = tu.declarations[1]
    assert isinstance(second.type, TypedefName)
    assert second.type.name == "u32"


def test_typedef_used_as_pointer_target():
    src = "typedef int *intp; intp p;"
    tu = _parse(src)
    second = tu.declarations[1]
    assert isinstance(second.type, TypedefName)


# --- Statements --------------------------------------------------------------


def test_if_else_chain():
    src = "void f(void) { if (a) { x = 1; } else { x = 2; } }"
    tu = _parse(src)
    fn = tu.declarations[0]
    assert isinstance(fn, FunctionDefinition)
    if_stmt = fn.body.items[0]
    assert isinstance(if_stmt, IfStmt)
    assert if_stmt.else_branch is not None


def test_while_loop():
    src = "void f(void) { while (x > 0) { x--; } }"
    tu = _parse(src)
    fn = tu.declarations[0]
    while_stmt = fn.body.items[0]
    assert isinstance(while_stmt, WhileStmt)


def test_do_while_loop():
    src = "void f(void) { do { x--; } while (x > 0); }"
    tu = _parse(src)
    fn = tu.declarations[0]
    do_stmt = fn.body.items[0]
    assert isinstance(do_stmt, DoStmt)


def test_for_loop_with_init_decl():
    src = "void f(void) { for (int i = 0; i < 10; i++) { sum += i; } }"
    tu = _parse(src)
    fn = tu.declarations[0]
    for_stmt = fn.body.items[0]
    assert isinstance(for_stmt, ForStmt)
    assert isinstance(for_stmt.init, Declaration)
    assert for_stmt.init.name == "i"


def test_switch_with_case_default():
    src = "void f(int x) { switch (x) { case 1: break; default: break; } }"
    tu = _parse(src)
    fn = tu.declarations[0]
    sw = fn.body.items[0]
    assert isinstance(sw, SwitchStmt)
    body = sw.body
    assert isinstance(body, CompoundStmt)


def test_break_in_loop():
    src = "void f(void) { while (1) { break; } }"
    tu = _parse(src)
    fn = tu.declarations[0]
    body = fn.body.items[0].body
    assert isinstance(body, CompoundStmt)
    assert isinstance(body.items[0], BreakStmt)


# --- Expressions -------------------------------------------------------------


def test_arithmetic_with_precedence():
    tu = _parse("int x = 1 + 2 * 3;")
    init = tu.declarations[0].initializer
    assert isinstance(init, BinaryOp) and init.op == "+"
    rhs = init.rhs
    assert isinstance(rhs, BinaryOp) and rhs.op == "*"


def test_assignment_is_right_associative():
    src = "void f(void) { a = b = c; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    expr_stmt = fn.body.items[0]
    assert isinstance(expr_stmt, ExpressionStmt)
    outer = expr_stmt.expression
    assert isinstance(outer, Assignment)
    assert isinstance(outer.rhs, Assignment)


def test_ternary():
    tu = _parse("int x = a > 0 ? a : -a;")
    init = tu.declarations[0].initializer
    assert isinstance(init, TernaryOp)


def test_function_call():
    src = 'void f(void) { printf("hi", 42); }'
    tu = _parse(src)
    fn = tu.declarations[0]
    expr = fn.body.items[0].expression
    assert isinstance(expr, FunctionCall)
    assert len(expr.args) == 2
    assert isinstance(expr.args[0], StringLiteral)


def test_member_access_dot_and_arrow():
    src = "void f(void) { a.b = c->d; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    asg = fn.body.items[0].expression
    assert isinstance(asg, Assignment)
    assert isinstance(asg.lhs, MemberAccess) and not asg.lhs.is_arrow
    assert isinstance(asg.rhs, MemberAccess) and asg.rhs.is_arrow


def test_array_subscript():
    src = "void f(int *a) { a[0] = 1; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    asg = fn.body.items[0].expression
    assert isinstance(asg.lhs, Subscript)


def test_unary_address_of_and_dereference():
    src = "void f(void) { int x; int *p = &x; *p = 1; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    p_decl = fn.body.items[1]
    assert isinstance(p_decl, Declaration)
    assert isinstance(p_decl.initializer, UnaryOp)
    assert p_decl.initializer.op == "&"


def test_postfix_increment():
    src = "void f(int x) { x++; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    expr = fn.body.items[0].expression
    assert isinstance(expr, UnaryOp)
    assert expr.op == "++" and not expr.prefix


def test_cast_expression():
    tu = _parse("int x = (int) 3.14;")
    init = tu.declarations[0].initializer
    from csa26_engine.ast_nodes import CastExpr

    assert isinstance(init, CastExpr)


# --- Initializers ------------------------------------------------------------


def test_array_initializer_list():
    tu = _parse("int a[3] = {1, 2, 3};")
    init = tu.declarations[0].initializer
    assert isinstance(init, InitializerList)
    assert len(init.items) == 3


def test_struct_designated_initializer():
    src = "struct P { int x; int y; }; struct P p = {.x = 1, .y = 2};"
    tu = _parse(src)
    p_decl = tu.declarations[1]
    assert isinstance(p_decl, Declaration)
    init = p_decl.initializer
    assert isinstance(init, InitializerList)
    designators = [item[0] for item in init.items]
    assert designators == [("x",), ("y",)]


# --- GCC extensions accepted -------------------------------------------------


def test_gcc_attribute_on_declaration_is_silently_accepted():
    tu = _parse("__attribute__((packed)) struct S { int x; };")
    decl = tu.declarations[0]
    assert isinstance(decl, Declaration)
    assert isinstance(decl.type, StructType)


def test_function_pointer_declarator():
    """`void (*handler)(int);` — Pointer zu Funktion, die int nimmt
    und nichts zurückgibt. Klassischer Spiral-Rule-Test."""
    tu = _parse("void (*handler)(int);")
    decl = tu.declarations[0]
    assert isinstance(decl.type, PointerType)
    assert isinstance(decl.type.target, FunctionType)


# --- Errors ------------------------------------------------------------------


def test_missing_semicolon_raises():
    with pytest.raises(ParserError):
        _parse("int x")


def test_unexpected_token_in_expression_raises():
    with pytest.raises(ParserError):
        _parse("int x = ;")


# --- Realistic snippet -------------------------------------------------------


def test_small_realistic_module():
    src = """
    #include <stdint.h>

    static uint32_t crc_seed = 0xFFFFFFFFu;

    uint32_t crc32(const uint8_t *data, size_t len) {
        uint32_t crc = crc_seed;
        for (size_t i = 0; i < len; i = i + 1) {
            crc = crc ^ data[i];
        }
        return crc;
    }
    """
    # `<stdint.h>` ist nicht da — wir benutzen einen InMemorySourceLoader.
    from csa26_engine.preprocessor import InMemorySourceLoader, preprocess

    loader = InMemorySourceLoader(
        {
            "stdint.h": (
                "typedef unsigned char uint8_t;\n"
                "typedef unsigned int uint32_t;\n"
                "typedef unsigned long size_t;\n"
            )
        }
    )
    tokens = preprocess(src, source_loader=loader)
    tu = parse(tokens)
    # Wir erwarten 3 Typedefs + 1 static var + 1 function-def
    fn = [d for d in tu.declarations if isinstance(d, FunctionDefinition)]
    assert len(fn) == 1 and fn[0].name == "crc32"


def test_identifier_evaluates_as_expression_term():
    src = "void f(int x) { y = x; }"
    tu = _parse(src)
    fn = tu.declarations[0]
    asg = fn.body.items[0].expression
    assert isinstance(asg.rhs, Identifier)
    assert asg.rhs.name == "x"
