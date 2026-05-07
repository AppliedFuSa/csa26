import pytest

from csa26_engine.preprocessor import (
    InMemorySourceLoader,
    Preprocessor,
    PreprocessorError,
    preprocess,
)
from csa26_engine.tokens import TokenKind


def _texts(tokens):
    return [t.text for t in tokens if t.kind is not TokenKind.EOF]


def _kinds(tokens):
    return [t.kind for t in tokens if t.kind is not TokenKind.EOF]


# --- Pass-through (no directives, no macros) ---------------------------------


def test_passthrough_keeps_normal_tokens():
    toks = preprocess("int x = 42;")
    assert _texts(toks) == ["int", "x", "=", "42", ";"]


def test_newlines_are_dropped_from_output():
    toks = preprocess("int x;\nint y;\n")
    assert _texts(toks) == ["int", "x", ";", "int", "y", ";"]


# --- #define / object-like macros --------------------------------------------


def test_define_replaces_identifier():
    toks = preprocess("#define LIMIT 10\nint x = LIMIT;")
    assert _texts(toks) == ["int", "x", "=", "10", ";"]


def test_define_without_value_yields_empty_replacement():
    toks = preprocess("#define EMPTY\nint x = EMPTY 1;")
    assert _texts(toks) == ["int", "x", "=", "1", ";"]


def test_undef_removes_macro():
    src = "#define FOO 1\nint a = FOO;\n#undef FOO\nint b = FOO;"
    toks = preprocess(src)
    assert _texts(toks) == ["int", "a", "=", "1", ";", "int", "b", "=", "FOO", ";"]


def test_macro_expansion_is_recursive_for_aliases():
    src = "#define A 1\n#define B A\nint x = B;"
    toks = preprocess(src)
    assert _texts(toks) == ["int", "x", "=", "1", ";"]


def test_macro_self_reference_is_not_infinite():
    # ISO C99 §6.10.3.4: a macro name cannot expand to itself recursively.
    src = "#define X X+1\nint y = X;"
    toks = preprocess(src)
    # `X` expands to `X + 1`; in the replacement, X is in the hide-set
    # and stays literal.
    assert _texts(toks) == ["int", "y", "=", "X", "+", "1", ";"]


def test_command_line_define_takes_effect():
    pp = Preprocessor(defines={"VERSION": "42", "DEBUG": ""})
    toks = pp.process(source="int v = VERSION; int d = DEBUG;", file="t.c")
    assert _texts(toks) == ["int", "v", "=", "42", ";", "int", "d", "=", "1", ";"]


def test_function_like_macro_in_iteration_1_raises():
    with pytest.raises(PreprocessorError, match="function-like macros"):
        preprocess("#define MAX(a,b) ((a)>(b)?(a):(b))\n")


# --- #ifdef / #ifndef / #else / #endif ---------------------------------------


def test_ifdef_active_branch():
    src = "#define ON 1\n#ifdef ON\nint a;\n#endif\nint b;"
    assert _texts(preprocess(src)) == ["int", "a", ";", "int", "b", ";"]


def test_ifdef_inactive_branch_skips_content():
    src = "#ifdef NOT_DEFINED\nint a;\n#endif\nint b;"
    assert _texts(preprocess(src)) == ["int", "b", ";"]


def test_ifndef_inverse():
    src = "#ifndef NOT_DEFINED\nint a;\n#else\nint b;\n#endif"
    assert _texts(preprocess(src)) == ["int", "a", ";"]


def test_else_branch():
    src = "#ifdef NOT_DEFINED\nint a;\n#else\nint b;\n#endif"
    assert _texts(preprocess(src)) == ["int", "b", ";"]


def test_nested_conditionals_inactive_outer_wins():
    src = (
        "#ifdef OUTER_OFF\n"
        "  #ifdef ANYTHING\n"
        "    int unreachable;\n"
        "  #endif\n"
        "  int also_unreachable;\n"
        "#endif\n"
        "int reachable;\n"
    )
    assert _texts(preprocess(src)) == ["int", "reachable", ";"]


def test_nested_conditionals_active_outer():
    src = (
        "#define OUTER 1\n"
        "#ifdef OUTER\n"
        "  #ifdef NESTED_ON\n"
        "    int a;\n"
        "  #else\n"
        "    int b;\n"
        "  #endif\n"
        "#endif\n"
    )
    assert _texts(preprocess(src)) == ["int", "b", ";"]


def test_unterminated_conditional_raises():
    with pytest.raises(PreprocessorError, match="unterminated conditional"):
        preprocess("#ifdef X\nint a;\n")


def test_endif_without_if_raises():
    with pytest.raises(PreprocessorError, match="without matching #if"):
        preprocess("#endif\n")


# --- #if defined / #elif / bare 0|1 ------------------------------------------


def test_if_defined_paren_form():
    src = "#define X\n#if defined(X)\nint a;\n#endif"
    assert _texts(preprocess(src)) == ["int", "a", ";"]


def test_if_defined_bare_form():
    src = "#define X\n#if defined X\nint a;\n#endif"
    assert _texts(preprocess(src)) == ["int", "a", ";"]


def test_if_not_defined():
    src = "#if !defined(X)\nint a;\n#endif"
    assert _texts(preprocess(src)) == ["int", "a", ";"]


def test_if_constant_zero_skips_block():
    src = "#if 0\nint unreachable;\n#endif\nint reachable;"
    assert _texts(preprocess(src)) == ["int", "reachable", ";"]


def test_if_constant_one_keeps_block():
    src = "#if 1\nint reachable;\n#endif"
    assert _texts(preprocess(src)) == ["int", "reachable", ";"]


def test_elif_takes_first_match():
    src = (
        "#define B\n"
        "#if defined(A)\n"
        "int a;\n"
        "#elif defined(B)\n"
        "int b;\n"
        "#elif defined(C)\n"
        "int c;\n"
        "#else\n"
        "int d;\n"
        "#endif\n"
    )
    assert _texts(preprocess(src)) == ["int", "b", ";"]


def test_elif_complex_if_expression_raises():
    with pytest.raises(PreprocessorError, match="iteration 1 supports only"):
        preprocess("#if X + 1\n#endif\n")


# --- #include -----------------------------------------------------------------


def test_include_pulls_in_header_tokens():
    loader = InMemorySourceLoader({"local.h": "int from_header;\n"})
    toks = preprocess('#include "local.h"\nint from_main;\n', source_loader=loader)
    assert _texts(toks) == ["int", "from_header", ";", "int", "from_main", ";"]


def test_include_propagates_macros_to_main_unit():
    loader = InMemorySourceLoader({"defs.h": "#define MAX 99\n"})
    toks = preprocess('#include "defs.h"\nint x = MAX;\n', source_loader=loader)
    assert _texts(toks) == ["int", "x", "=", "99", ";"]


def test_include_with_angle_brackets():
    loader = InMemorySourceLoader({"sys.h": "int sysvar;\n"})
    toks = preprocess("#include <sys.h>\n", source_loader=loader)
    assert _texts(toks) == ["int", "sysvar", ";"]


def test_include_missing_file_raises():
    loader = InMemorySourceLoader({})
    with pytest.raises(PreprocessorError, match="not in test loader"):
        preprocess('#include "missing.h"\n', source_loader=loader)


def test_include_recursion_through_headers():
    loader = InMemorySourceLoader(
        {
            "outer.h": '#include "inner.h"\nint outer;\n',
            "inner.h": "int inner;\n",
        }
    )
    toks = preprocess('#include "outer.h"\n', source_loader=loader)
    assert _texts(toks) == ["int", "inner", ";", "int", "outer", ";"]


# --- #error / #warning --------------------------------------------------------


def test_error_directive_raises():
    with pytest.raises(PreprocessorError, match="#error"):
        preprocess('#error "compile-time problem"\n')


def test_warning_does_not_raise_but_records_diagnostic():
    pp = Preprocessor()
    pp.process(source='#warning "be careful"\nint x;', file="t.c")
    assert any(level == "warning" for level, _, _ in pp.diagnostics)


def test_pragma_and_line_are_ignored():
    src = '#pragma once\n#line 100 "other.c"\nint x;\n'
    toks = preprocess(src)
    assert _texts(toks) == ["int", "x", ";"]


# --- Predefined macros --------------------------------------------------------


def test_line_macro_expands_to_current_line():
    src = "int a = __LINE__;\nint b = __LINE__;\n"
    toks = preprocess(src, file="t.c")
    # Token stream: int a = <const> ; int b = <const> ;
    constants = [t.text for t in toks if t.kind is TokenKind.CONSTANT]
    assert constants == ["1", "2"]


def test_file_macro_expands_to_current_file():
    toks = preprocess("char *f = __FILE__;\n", file="my.c")
    strings = [t.text for t in toks if t.kind is TokenKind.STRING_LITERAL]
    assert strings == ['"my.c"']
