import pytest

from csa26_engine.lexer import LexerError, tokenize
from csa26_engine.tokens import TokenKind


def _kinds(tokens):
    return [t.kind for t in tokens]


def _texts(tokens):
    return [t.text for t in tokens]


# --- Whitespace, Newlines, Comments -------------------------------------------


def test_empty_source_emits_only_eof():
    toks = tokenize("")
    assert _kinds(toks) == [TokenKind.EOF]


def test_whitespace_is_skipped_but_newlines_emit_token():
    toks = tokenize("   \t  \n  \t \n")
    assert _kinds(toks) == [TokenKind.NEWLINE, TokenKind.NEWLINE, TokenKind.EOF]


def test_block_comment_is_skipped():
    toks = tokenize("/* hello\nworld */ x")
    # Newline inside comment counts toward source line tracking but no NEWLINE token.
    assert _kinds(toks) == [TokenKind.IDENTIFIER, TokenKind.EOF]
    assert toks[0].text == "x"
    assert toks[0].location.line == 2


def test_line_comment_consumes_to_newline_only():
    toks = tokenize("// kommentar\nfoo")
    assert _kinds(toks) == [TokenKind.NEWLINE, TokenKind.IDENTIFIER, TokenKind.EOF]
    assert toks[1].text == "foo"


def test_unterminated_block_comment_raises():
    with pytest.raises(LexerError, match="unterminated block comment"):
        tokenize("/* never closed")


# --- Identifiers and keywords -------------------------------------------------


def test_identifier_starts_with_letter_or_underscore():
    toks = tokenize("foo _bar baz123")
    assert _kinds(toks)[:3] == [TokenKind.IDENTIFIER] * 3
    assert _texts(toks)[:3] == ["foo", "_bar", "baz123"]


def test_c99_keyword_is_recognised():
    toks = tokenize("const int x")
    assert toks[0].kind is TokenKind.KEYWORD and toks[0].text == "const"
    assert toks[1].kind is TokenKind.KEYWORD and toks[1].text == "int"
    assert toks[2].kind is TokenKind.IDENTIFIER and toks[2].text == "x"


def test_gcc_extension_keyword_is_recognised():
    toks = tokenize("__attribute__ asm")
    assert toks[0].kind is TokenKind.KEYWORD and toks[0].text == "__attribute__"
    assert toks[1].kind is TokenKind.KEYWORD and toks[1].text == "asm"


# --- Number constants ---------------------------------------------------------


def test_decimal_integer():
    toks = tokenize("42")
    assert toks[0].kind is TokenKind.CONSTANT and toks[0].text == "42"


def test_hex_integer_with_suffix():
    toks = tokenize("0xCAFEU 0xfeedULL 0xDEAD_naa")  # last one tests stop boundary
    assert toks[0].text == "0xCAFEU"
    assert toks[1].text == "0xfeedULL"
    # 0xDEAD stops at '_' because that starts a new identifier in C lexing
    assert toks[2].text == "0xDEAD"


def test_octal_integer():
    toks = tokenize("0755")
    assert toks[0].text == "0755"


def test_decimal_float():
    toks = tokenize("3.14 .5 2. 1e10 1.5e-3 2.5f")
    texts = [t.text for t in toks if t.kind is TokenKind.CONSTANT]
    assert texts == ["3.14", ".5", "2.", "1e10", "1.5e-3", "2.5f"]


def test_hex_float_with_p_exponent():
    toks = tokenize("0x1.fp10 0x1p-3")
    texts = [t.text for t in toks if t.kind is TokenKind.CONSTANT]
    assert texts == ["0x1.fp10", "0x1p-3"]


def test_integer_suffix_parsing_rejects_mixed_long():
    with pytest.raises(LexerError, match="mixed long suffix"):
        tokenize("123lL")


# --- Char and string ----------------------------------------------------------


def test_simple_char_constant():
    toks = tokenize("'a' '\\n' '\\\\'")
    texts = [t.text for t in toks if t.kind is TokenKind.CONSTANT]
    assert texts == ["'a'", "'\\n'", "'\\\\'"]


def test_wide_char_constant():
    toks = tokenize("L'a'")
    assert toks[0].kind is TokenKind.CONSTANT
    assert toks[0].text == "L'a'"


def test_simple_string_literal():
    toks = tokenize('"hello"')
    assert toks[0].kind is TokenKind.STRING_LITERAL
    assert toks[0].text == '"hello"'


def test_wide_string_literal():
    toks = tokenize('L"hi"')
    assert toks[0].kind is TokenKind.STRING_LITERAL
    assert toks[0].text == 'L"hi"'


def test_string_with_escaped_quote():
    toks = tokenize(r'"say \"hi\""')
    assert toks[0].kind is TokenKind.STRING_LITERAL
    assert toks[0].text == r'"say \"hi\""'


def test_unterminated_string_raises():
    with pytest.raises(LexerError, match="unterminated string"):
        tokenize('"oops')


# --- Punctuators --------------------------------------------------------------


def test_three_char_punctuators():
    toks = tokenize("... <<= >>=")
    texts = [t.text for t in toks if t.kind is TokenKind.PUNCTUATOR]
    assert texts == ["...", "<<=", ">>="]


def test_two_char_punctuators_longest_match_first():
    toks = tokenize("a <= b -> c == d != e && f || g")
    texts = [t.text for t in toks if t.kind is TokenKind.PUNCTUATOR]
    assert texts == ["<=", "->", "==", "!=", "&&", "||"]


def test_one_char_punctuators():
    toks = tokenize("{ } [ ] ( ) ; , .")
    texts = [t.text for t in toks if t.kind is TokenKind.PUNCTUATOR]
    assert texts == ["{", "}", "[", "]", "(", ")", ";", ",", "."]


def test_increment_does_not_collide_with_plus():
    toks = tokenize("a++ + b")
    texts = [t.text for t in toks]
    assert texts == ["a", "++", "+", "b", ""]


# --- Source locations ---------------------------------------------------------


def test_locations_track_line_and_column():
    toks = tokenize("a\n  b\n   c")
    a, _nl1, b, _nl2, c, _eof = toks
    assert (a.location.line, a.location.column) == (1, 1)
    assert (b.location.line, b.location.column) == (2, 3)
    assert (c.location.line, c.location.column) == (3, 4)


# --- Realistic snippet --------------------------------------------------------


def test_small_real_function():
    src = (
        "static const uint8_t crc_init = 0xFFu;\n"
        "uint8_t crc8(const uint8_t *data, size_t len) {\n"
        "    return data[0] ^ 0x07; /* poly */\n"
        "}\n"
    )
    toks = tokenize(src)
    # No exceptions, we end with EOF, and we got a sensible token stream.
    assert toks[-1].kind is TokenKind.EOF
    # The keywords static and const must be recognised, identifier types resolve.
    keywords = [t.text for t in toks if t.kind is TokenKind.KEYWORD]
    assert "static" in keywords
    assert "const" in keywords
    assert "return" in keywords
    # Two distinct hex integer constants.
    constants = [t.text for t in toks if t.kind is TokenKind.CONSTANT]
    assert "0xFFu" in constants
    assert "0x07" in constants
    assert "0" in constants  # data[0]
