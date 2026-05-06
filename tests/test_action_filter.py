from csa26.action import filter_misra_only
from csa26.findings import Finding, Severity


def _f(rule_id: str) -> Finding:
    return Finding(rule_id, Severity.STYLE, "msg", "f.c", 1, 1)


def test_filter_drops_cppcheck_builtins():
    findings = [
        _f("misra-c2012-8.13"),
        _f("constParameterPointer"),
        _f("misra-c2012-2.7"),
        _f("nullPointer"),
    ]
    kept, dropped = filter_misra_only(findings)
    assert [f.rule_id for f in kept] == ["misra-c2012-8.13", "misra-c2012-2.7"]
    assert dropped == 2


def test_filter_passthrough_when_all_misra():
    findings = [_f("misra-c2012-8.13"), _f("misra-c2012-2.7")]
    kept, dropped = filter_misra_only(findings)
    assert kept == findings
    assert dropped == 0


def test_filter_empty_input():
    kept, dropped = filter_misra_only([])
    assert kept == []
    assert dropped == 0
