from textwrap import dedent

from csa26.rules import lookup_rule, normalize_rule_id


def test_normalize_rule_id_strips_misra_prefix():
    assert normalize_rule_id("misra-c2012-8.13") == "c2012-8.13"
    assert normalize_rule_id("c2012-8.13") == "c2012-8.13"
    assert normalize_rule_id("MISRA-C2012-8.13") == "c2012-8.13"


def test_lookup_rule_returns_placeholder_when_missing(tmp_path):
    rule = lookup_rule("misra-c2012-99.99", rules_dir=tmp_path)
    assert rule.is_placeholder
    assert "99.99" in rule.title
    assert rule.rule_id == "c2012-99.99"


def test_lookup_rule_parses_frontmatter(tmp_path):
    target = tmp_path / "c2012" / "8.13.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        dedent(
            """\
            ---
            rule_id: c2012-8.13
            title: Const-Korrektheit für reine Lese-Pointer
            ---

            Wenn ein Pointer-Ziel nicht geschrieben wird, sollte der
            Pointer-Typ const-qualifiziert sein.

            ```c
            void f(const int *x);
            ```
            """
        ),
        encoding="utf-8",
    )

    rule = lookup_rule("misra-c2012-8.13", rules_dir=tmp_path)
    assert not rule.is_placeholder
    assert rule.title == "Const-Korrektheit für reine Lese-Pointer"
    assert rule.description.startswith("Wenn ein Pointer-Ziel")
    assert "```" not in rule.description  # Code-Block ist eigener Absatz


def test_lookup_rule_without_frontmatter_uses_first_paragraph(tmp_path):
    target = tmp_path / "c2012" / "2.7.md"
    target.parent.mkdir(parents=True)
    target.write_text(
        "Erster Absatz als Beschreibung.\n\nZweiter Absatz mit Beispiel.\n",
        encoding="utf-8",
    )
    rule = lookup_rule("c2012-2.7", rules_dir=tmp_path)
    assert not rule.is_placeholder
    assert rule.description == "Erster Absatz als Beschreibung."
    # Default-Titel aus Rule-Nummer
    assert "2.7" in rule.title
