from csa26_engine.ast_nodes import (
    BasicType,
    BinaryOp,
    Declaration,
    FunctionCall,
    FunctionDefinition,
    Identifier,
    PointerType,
    UnaryOp,
)
from csa26_engine.parser import parse
from csa26_engine.preprocessor import preprocess
from csa26_engine.symbols import bind
from csa26_engine.types import (
    infer_types,
    is_const_qualified,
    is_integer,
    is_pointer,
    pointer_target_is_const,
    pointer_types_compatible,
    types_strictly_equal,
    usual_arithmetic_conversion,
)


def _ast(src: str):
    return parse(preprocess(src))


# ---------------------------------------------------------------------------
# Symbol-Resolution
# ---------------------------------------------------------------------------


def test_top_level_variable_is_in_file_scope():
    tu = _ast("int x;")
    bindings = bind(tu)
    sym = bindings.file_scope.lookup_ordinary("x")
    assert sym is not None
    assert sym.kind == "variable"
    assert isinstance(sym.type, BasicType)


def test_function_parameter_resolves_in_function_body():
    tu = _ast("int add(int a, int b) { return a + b; }")
    bindings = bind(tu)

    fn = tu.declarations[0]
    assert isinstance(fn, FunctionDefinition)
    ret_value = fn.body.items[0].value  # type: ignore[union-attr]
    assert isinstance(ret_value, BinaryOp)

    a_ident = ret_value.lhs
    assert isinstance(a_ident, Identifier)
    sym = bindings.symbol_for(a_ident)
    assert sym is not None
    assert sym.kind == "param"
    assert sym.name == "a"


def test_typedef_is_recognised_as_typedef_kind():
    tu = _ast("typedef unsigned int u32; u32 x;")
    bindings = bind(tu)
    u32 = bindings.file_scope.lookup_ordinary("u32")
    assert u32 is not None
    assert u32.kind == "typedef"


def test_block_scope_shadows_outer():
    src = """
    int x = 1;
    void f(void) {
        int x = 2;
        x = x + 1;
    }
    """
    tu = _ast(src)
    bindings = bind(tu)
    fn = tu.declarations[1]
    assert isinstance(fn, FunctionDefinition)
    expr_stmt = fn.body.items[1]
    asg = expr_stmt.expression  # type: ignore[union-attr]
    rhs_x = asg.rhs.lhs  # x in (x + 1)
    sym = bindings.symbol_for(rhs_x)
    assert sym is not None
    # Im Block-Scope sollte das innere x gewählt werden, nicht das outer.
    # Beide haben Kind "variable", aber wir können über die Storage-Class
    # / Location distinguishen — outer ist file-scope (sym.location.line == 2),
    # inner Body-line == 4.
    # Prüfen: das innere x wurde gewählt — also sym.location ist innerhalb fn
    assert sym.location.line >= fn.location.line


def test_undeclared_identifier_records_diagnostic():
    tu = _ast("void f(void) { y = 1; }")
    bindings = bind(tu)
    assert any(level == "warning" and "unresolved" in msg for level, msg, _ in bindings.diagnostics)


def test_function_definition_appears_in_function_table():
    tu = _ast("int add(int a, int b) { return a + b; }")
    bindings = bind(tu)
    assert "add" in bindings.function_table


def test_for_init_decl_is_local_to_loop():
    src = "void f(void) { for (int i = 0; i < 10; i = i + 1) { i = i; } }"
    tu = _ast(src)
    bindings = bind(tu)
    fn = tu.declarations[0]
    assert isinstance(fn, FunctionDefinition)
    # Im Body des for-Loops muss `i` resolvable sein
    for_stmt = fn.body.items[0]
    body_stmt = for_stmt.body  # CompoundStmt mit `i = i;`
    asg = body_stmt.items[0].expression  # type: ignore[union-attr]
    sym = bindings.symbol_for(asg.lhs)
    assert sym is not None
    assert sym.name == "i"


# ---------------------------------------------------------------------------
# Type-Predicates
# ---------------------------------------------------------------------------


def test_is_pointer_basic():
    int_t = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    ptr = PointerType(location=_loc(), target=int_t, qualifiers=frozenset())
    assert is_pointer(ptr)
    assert not is_pointer(int_t)


def test_is_integer_recognises_char_short_int_long():
    for spec in (("char",), ("short",), ("int",), ("long",), ("long", "long")):
        t = BasicType(specifiers=spec, qualifiers=frozenset(), location=_loc())
        assert is_integer(t), spec
    float_t = BasicType(specifiers=("float",), qualifiers=frozenset(), location=_loc())
    assert not is_integer(float_t)


def test_is_const_qualified_on_target():
    target = BasicType(specifiers=("int",), qualifiers=frozenset({"const"}), location=_loc())
    ptr = PointerType(location=_loc(), target=target, qualifiers=frozenset())
    assert pointer_target_is_const(ptr)
    assert not is_const_qualified(ptr)
    target2 = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    ptr2 = PointerType(location=_loc(), target=target2, qualifiers=frozenset({"const"}))
    assert is_const_qualified(ptr2)
    assert not pointer_target_is_const(ptr2)


def test_pointer_types_compatible_strict():
    int_t = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    p1 = PointerType(location=_loc(), target=int_t, qualifiers=frozenset())
    p2 = PointerType(location=_loc(), target=int_t, qualifiers=frozenset())
    assert pointer_types_compatible(p1, p2)


def test_pointer_types_compatible_through_void():
    int_t = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    void_t = BasicType(specifiers=("void",), qualifiers=frozenset(), location=_loc())
    p_int = PointerType(location=_loc(), target=int_t, qualifiers=frozenset())
    p_void = PointerType(location=_loc(), target=void_t, qualifiers=frozenset())
    assert pointer_types_compatible(p_int, p_void)


def test_pointer_types_incompatible():
    int_t = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    char_t = BasicType(specifiers=("char",), qualifiers=frozenset(), location=_loc())
    p_int = PointerType(location=_loc(), target=int_t, qualifiers=frozenset())
    p_char = PointerType(location=_loc(), target=char_t, qualifiers=frozenset())
    assert not pointer_types_compatible(p_int, p_char)


def test_usual_arithmetic_conversion_int_int():
    int_t = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    assert types_strictly_equal(usual_arithmetic_conversion(int_t, int_t), int_t)


def test_usual_arithmetic_conversion_float_int_yields_float():
    float_t = BasicType(specifiers=("float",), qualifiers=frozenset(), location=_loc())
    int_t = BasicType(specifiers=("int",), qualifiers=frozenset(), location=_loc())
    result = usual_arithmetic_conversion(int_t, float_t)
    assert types_strictly_equal(result, float_t)


# ---------------------------------------------------------------------------
# Type-Inference
# ---------------------------------------------------------------------------


def test_infer_int_literal_is_int():
    tu = _ast("int x = 1;")
    bindings = bind(tu)
    types = infer_types(bindings)
    init = tu.declarations[0].initializer
    t = types[id(init)]
    assert isinstance(t, BasicType)
    assert t.specifiers == ("int",)


def test_infer_addition_yields_arithmetic_type():
    tu = _ast("int x = 1 + 2;")
    bindings = bind(tu)
    types = infer_types(bindings)
    init = tu.declarations[0].initializer
    t = types[id(init)]
    assert isinstance(t, BasicType)
    assert is_integer(t)


def test_infer_address_of_variable_is_pointer_to_its_type():
    src = "void f(void) { int x; int *p = &x; }"
    tu = _ast(src)
    bindings = bind(tu)
    types = infer_types(bindings)
    fn = tu.declarations[0]
    p_decl = fn.body.items[1]
    assert isinstance(p_decl, Declaration)
    init = p_decl.initializer
    assert isinstance(init, UnaryOp) and init.op == "&"
    inferred = types[id(init)]
    assert is_pointer(inferred)


def test_infer_function_call_returns_function_return_type():
    src = """
    int compute(int a) { return a + 1; }
    void f(void) { int y = compute(5); }
    """
    tu = _ast(src)
    bindings = bind(tu)
    types = infer_types(bindings)
    f_def = tu.declarations[1]
    y_decl = f_def.body.items[0]
    assert isinstance(y_decl, Declaration)
    init = y_decl.initializer
    assert isinstance(init, FunctionCall)
    t = types[id(init)]
    assert isinstance(t, BasicType) and t.specifiers == ("int",)


def test_infer_pointer_dereference_yields_target_type():
    src = "void f(int *p) { int x = *p; }"
    tu = _ast(src)
    bindings = bind(tu)
    types = infer_types(bindings)
    fn = tu.declarations[0]
    x_decl = fn.body.items[0]
    init = x_decl.initializer
    assert isinstance(init, UnaryOp) and init.op == "*"
    t = types[id(init)]
    assert is_integer(t)


def test_infer_subscript_yields_element_type():
    src = "void f(int *a) { int x = a[0]; }"
    tu = _ast(src)
    bindings = bind(tu)
    types = infer_types(bindings)
    fn = tu.declarations[0]
    init = fn.body.items[0].initializer
    t = types[id(init)]
    assert is_integer(t)


def test_infer_pointer_arithmetic_yields_pointer():
    src = "void f(int *p) { int *q = p + 1; }"
    tu = _ast(src)
    bindings = bind(tu)
    types = infer_types(bindings)
    fn = tu.declarations[0]
    q_decl = fn.body.items[0]
    init = q_decl.initializer
    assert isinstance(init, BinaryOp)
    t = types[id(init)]
    assert is_pointer(t)


def test_infer_member_access_through_struct_pointer():
    src = """
    struct P { int x; int y; };
    void f(struct P *p) { int v = p->x; }
    """
    tu = _ast(src)
    bindings = bind(tu)
    types = infer_types(bindings)
    fn = tu.declarations[1]
    init = fn.body.items[0].initializer
    t = types[id(init)]
    assert is_integer(t)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _loc():
    from csa26_engine.tokens import SourceLocation

    return SourceLocation("<t>", 1, 1)
