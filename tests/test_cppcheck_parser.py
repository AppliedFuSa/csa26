from textwrap import dedent

from csa26.cppcheck import _clean_message, parse_cppcheck_xml
from csa26.findings import Severity


def test_clean_message_strips_rule_texts_hint():
    raw = "misra violation (use --rule-texts=<file> to get proper output): c2012-8.13"
    assert _clean_message(raw) == "misra violation : c2012-8.13"


def test_clean_message_passthrough_when_hint_absent():
    assert _clean_message("undefined behavior") == "undefined behavior"


def test_parse_cppcheck_xml_extracts_findings(tmp_path):
    misra_msg = "misra violation (use --rule-texts=&lt;file&gt; to get proper output)"
    xml = dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <results version="2">
          <cppcheck version="2.10"/>
          <errors>
            <error id="misra-c2012-8.13" severity="style" msg="{misra_msg}" verbose="">
              <location file="src/main.c" line="42" column="5"/>
            </error>
            <error id="nullPointer" severity="error" msg="Null pointer dereference">
              <location file="src/util.c" line="10" column="3"/>
            </error>
            <error id="missingInclude" severity="information" msg="Cannot find header"/>
          </errors>
        </results>
        """
    )
    xml_path = tmp_path / "report.xml"
    xml_path.write_text(xml, encoding="utf-8")

    findings = parse_cppcheck_xml(xml_path)

    # Drittes Finding ohne Location wird unterdrückt.
    assert len(findings) == 2

    misra = findings[0]
    assert misra.rule_id == "misra-c2012-8.13"
    assert misra.severity is Severity.STYLE
    assert "use --rule-texts" not in misra.message
    assert misra.file == "src/main.c"
    assert misra.line == 42
    assert misra.column == 5

    null = findings[1]
    assert null.rule_id == "nullPointer"
    assert null.severity is Severity.ERROR


def test_parse_cppcheck_xml_handles_missing_file(tmp_path):
    assert parse_cppcheck_xml(tmp_path / "missing.xml") == []


def test_parse_cppcheck_xml_handles_empty_file(tmp_path):
    empty = tmp_path / "empty.xml"
    empty.write_text("", encoding="utf-8")
    assert parse_cppcheck_xml(empty) == []
