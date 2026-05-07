"""Unit-Tests für die 20 csa26-engine-Rules.

Pro Rule: mindestens ein True-Positive (Code, der die Rule verletzt
und gemeldet werden soll) und ein True-Negative (Code, der sauber
ist und NICHT gemeldet werden soll).
"""

from pathlib import Path

from csa26_engine.engine import analyze
from csa26_engine.preprocessor import InMemorySourceLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_SYSTEM_HEADERS = {
    "stdint.h": (
        "typedef unsigned char  uint8_t;\n"
        "typedef unsigned short uint16_t;\n"
        "typedef unsigned int   uint32_t;\n"
        "typedef signed char    int8_t;\n"
        "typedef signed short   int16_t;\n"
        "typedef signed int     int32_t;\n"
    ),
    "stddef.h": (
        "typedef unsigned long size_t;\n"
        "typedef long          ptrdiff_t;\n"
        "#define NULL ((void *)0)\n"
    ),
}


def _loader(extra=None):
    files = dict(_SYSTEM_HEADERS)
    if extra:
        files.update(extra)
    return InMemorySourceLoader(files)


def _has_rule(findings, rule_id):
    return any(f.rule_id == rule_id for f in findings)


# =============================================================================
# 10.1 — mixed-essential-type binary arithmetic
# =============================================================================


def test_rule_10_1_flags_int_plus_float():
    findings = analyze("int f(void) { return 1 + 2.0; }")
    assert _has_rule(findings, "misra-c2012-10.1")


def test_rule_10_1_clean_for_pure_int():
    findings = analyze("int f(void) { return 1 + 2; }")
    assert not _has_rule(findings, "misra-c2012-10.1")


# =============================================================================
# 10.3 — narrowing assignment / mismatched essential type
# =============================================================================


def test_rule_10_3_flags_float_to_int_assignment():
    findings = analyze("void f(void) { int x; x = 3.14; }")
    assert _has_rule(findings, "misra-c2012-10.3")


def test_rule_10_3_clean_for_int_to_int():
    findings = analyze("void f(void) { int x; x = 5; }")
    assert not _has_rule(findings, "misra-c2012-10.3")


# =============================================================================
# 10.4 — binary operator operands of different essential category
# =============================================================================


def test_rule_10_4_flags_pointer_compared_to_integer():
    src = "void f(int *p) { if (p == 0) { return; } }"
    findings = analyze(src)
    # Vergleich Pointer == Integer-Literal zählt
    assert _has_rule(findings, "misra-c2012-10.4")


def test_rule_10_4_clean_for_int_int_compare():
    findings = analyze("void f(int a, int b) { if (a == b) { return; } }")
    assert not _has_rule(findings, "misra-c2012-10.4")


# =============================================================================
# 10.5 — inappropriate cast
# =============================================================================


def test_rule_10_5_flags_float_to_pointer_cast():
    src = "void f(void) { int *p = (int *) 3.14; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-10.5")


def test_rule_10_5_clean_for_int_to_int_cast():
    findings = analyze("void f(void) { long x = (long) 5; }")
    assert not _has_rule(findings, "misra-c2012-10.5")


# =============================================================================
# 10.8 — narrower integer cast
# =============================================================================


def test_rule_10_8_flags_long_to_char_cast():
    findings = analyze("void f(long y) { char x = (char) y; }")
    assert _has_rule(findings, "misra-c2012-10.8")


def test_rule_10_8_clean_for_widening_cast():
    findings = analyze("void f(char y) { long x = (long) y; }")
    assert not _has_rule(findings, "misra-c2012-10.8")


# =============================================================================
# 14.3 — invariant controlling expression
# =============================================================================


def test_rule_14_3_flags_if_constant():
    findings = analyze("void f(void) { if (1) { return; } }")
    assert _has_rule(findings, "misra-c2012-14.3")


def test_rule_14_3_clean_for_while_one_with_break():
    src = "void f(int x) { while (1) { if (x > 0) { break; } } }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-14.3")


# =============================================================================
# 14.4 — non-boolean controlling expression
# =============================================================================


def test_rule_14_4_flags_if_with_assignment():
    findings = analyze("void f(int x) { if (x) { return; } }")
    assert _has_rule(findings, "misra-c2012-14.4")


def test_rule_14_4_clean_for_explicit_compare():
    findings = analyze("void f(int x) { if (x != 0) { return; } }")
    assert not _has_rule(findings, "misra-c2012-14.4")


# =============================================================================
# 15.5 — single exit point
# =============================================================================


def test_rule_15_5_flags_two_returns():
    src = "int f(int x) { if (x > 0) { return 1; } return 0; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-15.5")


def test_rule_15_5_clean_for_single_return():
    src = "int f(int x) { int r = 0; if (x > 0) { r = 1; } return r; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-15.5")


# =============================================================================
# 15.7 — if-else if chain without final else
# =============================================================================


def test_rule_15_7_flags_chain_without_else():
    src = """
    void f(int x) {
        if (x == 1) { return; }
        else if (x == 2) { return; }
    }
    """
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-15.7")


def test_rule_15_7_clean_for_chain_with_else():
    src = """
    void f(int x) {
        if (x == 1) { return; }
        else if (x == 2) { return; }
        else { return; }
    }
    """
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-15.7")


# =============================================================================
# 8.13 — const-qualified pointer parameter
# =============================================================================


def test_rule_8_13_flags_read_only_pointer_param():
    src = "int sum(int *data, int n) { int s = 0; s = s + data[0]; return s; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-8.13")


def test_rule_8_13_clean_for_already_const():
    src = "int sum(const int *data, int n) { int s = 0; s = s + data[0]; return s; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-8.13")


def test_rule_8_13_clean_when_param_is_written():
    src = "void f(int *p) { *p = 1; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-8.13")


# =============================================================================
# 11.3 — cast between pointers to different object types
# =============================================================================


def test_rule_11_3_flags_int_to_char_pointer_cast():
    src = "void f(int *p) { char *c = (char *) p; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-11.3")


def test_rule_11_3_clean_for_compatible_pointer_cast():
    src = "void f(int *p) { int *q = (int *) p; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-11.3")


# =============================================================================
# 11.5 — pointer-to-void → pointer-to-object
# =============================================================================


def test_rule_11_5_flags_void_pointer_to_int_pointer():
    src = "void f(void *v) { int *p = (int *) v; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-11.5")


# =============================================================================
# 18.4 — pointer arithmetic
# =============================================================================


def test_rule_18_4_flags_pointer_plus_int():
    src = "int *advance(int *p) { return p + 1; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-18.4")


def test_rule_18_4_clean_for_subscript():
    src = "int read(int *p) { return p[1]; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-18.4")


# =============================================================================
# 8.4 — function definition without prior declaration
# =============================================================================


def test_rule_8_4_flags_function_without_forward_decl():
    findings = analyze("int compute(int x) { return x + 1; }")
    assert _has_rule(findings, "misra-c2012-8.4")


def test_rule_8_4_clean_with_forward_decl():
    src = """
    int compute(int x);
    int compute(int x) { return x + 1; }
    """
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-8.4")


def test_rule_8_4_clean_for_static_function():
    findings = analyze("static int compute(int x) { return x + 1; }")
    assert not _has_rule(findings, "misra-c2012-8.4")


# =============================================================================
# 8.7 — function only used in one TU could be static
# =============================================================================


def test_rule_8_7_flags_unreferenced_function():
    src = "void unreferenced(void) { return; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-8.7")


def test_rule_8_7_clean_for_static_function():
    src = "static void unreferenced(void) { return; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-8.7")


# =============================================================================
# 17.2 — recursion
# =============================================================================


def test_rule_17_2_flags_direct_recursion():
    src = "int fact(int n) { if (n <= 1) { return 1; } return n * fact(n - 1); }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-17.2")


def test_rule_17_2_clean_for_non_recursive():
    src = "int square(int n) { return n * n; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-17.2")


# =============================================================================
# 17.7 — unused return value
# =============================================================================


def test_rule_17_7_flags_unused_return():
    src = """
    int compute(int x);
    void f(void) { compute(5); }
    """
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-17.7")


def test_rule_17_7_clean_for_void_call():
    src = """
    void log_event(int x);
    void f(void) { log_event(5); }
    """
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-17.7")


def test_rule_17_7_clean_for_void_cast():
    src = """
    int compute(int x);
    void f(void) { (void) compute(5); }
    """
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-17.7")


# =============================================================================
# 2.1 — unreachable code
# =============================================================================


def test_rule_2_1_flags_code_after_return():
    src = """
    int f(void) {
        return 1;
        return 2;
    }
    """
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-2.1")


def test_rule_2_1_clean_for_normal_flow():
    src = "int f(int x) { int r = x + 1; return r; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-2.1")


# =============================================================================
# 2.2 — dead statements
# =============================================================================


def test_rule_2_2_flags_pure_expression_statement():
    src = "void f(int x) { x + 1; }"
    findings = analyze(src)
    assert _has_rule(findings, "misra-c2012-2.2")


def test_rule_2_2_clean_for_assignment():
    src = "void f(int x) { x = x + 1; }"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-2.2")


# =============================================================================
# 2.5 — unused macros
# =============================================================================


def test_rule_2_5_flags_unused_macro():
    findings = analyze("#define UNUSED_LIMIT 100\nint x;")
    assert _has_rule(findings, "misra-c2012-2.5")


def test_rule_2_5_clean_for_used_macro():
    findings = analyze("#define LIMIT 100\nint x = LIMIT;")
    assert not _has_rule(findings, "misra-c2012-2.5")


def test_rule_2_5_clean_for_header_guard_via_ifndef():
    src = "#ifndef MY_GUARD\n#define MY_GUARD\nint x;\n#endif\n"
    findings = analyze(src)
    assert not _has_rule(findings, "misra-c2012-2.5")
