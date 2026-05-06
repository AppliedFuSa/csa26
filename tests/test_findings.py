from csa26.findings import Finding, Severity


def test_severity_from_str_known_label():
    assert Severity.from_str("error") is Severity.ERROR
    assert Severity.from_str("Warning") is Severity.WARNING
    assert Severity.from_str("STYLE") is Severity.STYLE


def test_severity_from_str_unknown_falls_back_to_information():
    assert Severity.from_str("not-a-severity") is Severity.INFORMATION
    assert Severity.from_str("") is Severity.INFORMATION


def test_severity_at_least_as_severe_as():
    assert Severity.ERROR.at_least_as_severe_as(Severity.STYLE)
    assert Severity.STYLE.at_least_as_severe_as(Severity.STYLE)
    assert not Severity.INFORMATION.at_least_as_severe_as(Severity.STYLE)


def test_severity_ordering_for_sorting():
    s = sorted([Severity.STYLE, Severity.ERROR, Severity.INFORMATION, Severity.WARNING])
    # „kleiner" = ernster, also Error zuerst
    assert s == [Severity.ERROR, Severity.WARNING, Severity.STYLE, Severity.INFORMATION]


def test_finding_misra_detection():
    misra = Finding("misra-c2012-8.13", Severity.STYLE, "msg", "f.c", 1, 1)
    other = Finding("nullPointer", Severity.ERROR, "msg", "f.c", 1, 1)
    assert misra.is_misra
    assert misra.misra_rule_number == "8.13"
    assert not other.is_misra
    assert other.misra_rule_number is None
