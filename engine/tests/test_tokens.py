from csa26_engine.tokens import (
    ALL_KEYWORDS,
    C99_KEYWORDS,
    GCC_EXTENSION_KEYWORDS,
    SourceLocation,
    Token,
    TokenKind,
)


def test_c99_keyword_set_size():
    # ISO/IEC 9899:1999 §6.4.1 — 37 Keywords
    assert len(C99_KEYWORDS) == 37


def test_no_overlap_between_c99_and_gcc_extension_keywords():
    assert C99_KEYWORDS.isdisjoint(GCC_EXTENSION_KEYWORDS)


def test_all_keywords_is_union():
    assert ALL_KEYWORDS == C99_KEYWORDS | GCC_EXTENSION_KEYWORDS


def test_source_location_string_format():
    loc = SourceLocation("foo.c", 42, 7)
    assert str(loc) == "foo.c:42:7"


def test_token_is_keyword_matches_text_and_kind():
    loc = SourceLocation("a.c", 1, 1)
    tok = Token(TokenKind.KEYWORD, "const", loc)
    assert tok.is_keyword("const")
    assert tok.is_keyword("static", "const")
    assert not tok.is_keyword("volatile")


def test_token_is_keyword_rejects_non_keywords():
    loc = SourceLocation("a.c", 1, 1)
    tok = Token(TokenKind.IDENTIFIER, "const", loc)
    # Identifier mit Keyword-Text ist kein Keyword.
    assert not tok.is_keyword("const")


def test_token_is_punctuator():
    loc = SourceLocation("a.c", 1, 1)
    tok = Token(TokenKind.PUNCTUATOR, "{", loc)
    assert tok.is_punctuator("{")
    assert tok.is_punctuator("(", "{", "[")
    assert not tok.is_punctuator(";")


def test_token_is_identifier_without_filter_matches_any():
    loc = SourceLocation("a.c", 1, 1)
    tok = Token(TokenKind.IDENTIFIER, "my_var", loc)
    assert tok.is_identifier()
    assert tok.is_identifier("my_var")
    assert not tok.is_identifier("other")
