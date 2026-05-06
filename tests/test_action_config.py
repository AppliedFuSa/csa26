from pathlib import Path

from csa26.action import Config
from csa26.findings import Severity


def test_config_defaults_when_env_empty(tmp_path):
    env = {"GITHUB_WORKSPACE": str(tmp_path)}
    cfg = Config.from_env(env)
    assert cfg.src_dir == tmp_path / "."
    assert cfg.rule_set == "misra-c-2012"
    assert cfg.severity_threshold is Severity.STYLE
    assert cfg.fail_on_findings is False
    assert cfg.sarif_output == tmp_path / "csa26.sarif"


def test_config_reads_all_inputs(tmp_path: Path):
    env = {
        "GITHUB_WORKSPACE": str(tmp_path),
        "CSA26_SRC_DIR": "firmware",
        "CSA26_RULE_SET": "misra-c-2012",
        "CSA26_SEVERITY_THRESHOLD": "warning",
        "CSA26_FAIL_ON_FINDINGS": "true",
        "CSA26_SARIF_OUTPUT": "out/csa26.sarif",
    }
    cfg = Config.from_env(env)
    assert cfg.src_dir == tmp_path / "firmware"
    assert cfg.severity_threshold is Severity.WARNING
    assert cfg.fail_on_findings is True
    assert cfg.sarif_output == tmp_path / "out" / "csa26.sarif"


def test_config_falls_back_when_inputs_blank(tmp_path: Path):
    env = {
        "GITHUB_WORKSPACE": str(tmp_path),
        "CSA26_SRC_DIR": "  ",
        "CSA26_RULE_SET": "",
        "CSA26_SEVERITY_THRESHOLD": "",
        "CSA26_SARIF_OUTPUT": "",
    }
    cfg = Config.from_env(env)
    assert cfg.src_dir == tmp_path / "."
    assert cfg.rule_set == "misra-c-2012"
    assert cfg.severity_threshold is Severity.STYLE
    assert cfg.sarif_output == tmp_path / "csa26.sarif"


def test_truthy_values():
    from csa26.action import _truthy

    for v in ["1", "true", "TRUE", "Yes", "on"]:
        assert _truthy(v), v
    for v in ["0", "false", "no", "off", "", "  "]:
        assert not _truthy(v), v
