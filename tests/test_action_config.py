from pathlib import Path

from csa26.action import Config, parse_multiline
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


def test_parse_multiline_strips_and_drops_blanks():
    raw = "  vendor/sdk/include  \n\nsrc/include\n   \nthird/party\n"
    assert parse_multiline(raw) == ("vendor/sdk/include", "src/include", "third/party")


def test_parse_multiline_empty_returns_empty_tuple():
    assert parse_multiline("") == ()
    assert parse_multiline("\n  \n") == ()


def test_config_reads_include_paths_resolved_against_workspace(tmp_path: Path):
    (tmp_path / "vendor" / "sdk").mkdir(parents=True)
    env = {
        "GITHUB_WORKSPACE": str(tmp_path),
        "CSA26_INCLUDE_PATHS": "vendor/sdk\nsrc/include\n",
    }
    cfg = Config.from_env(env)
    assert cfg.include_paths[0] == (tmp_path / "vendor" / "sdk").resolve()
    assert cfg.include_paths[1] == (tmp_path / "src" / "include").resolve()


def test_config_reads_defines_and_undefines(tmp_path: Path):
    env = {
        "GITHUB_WORKSPACE": str(tmp_path),
        "CSA26_DEFINES": "STM32F4=1\n__ARM_ARCH_7EM__\n",
        "CSA26_UNDEFINES": "DEBUG\n",
    }
    cfg = Config.from_env(env)
    assert cfg.defines == ("STM32F4=1", "__ARM_ARCH_7EM__")
    assert cfg.undefines == ("DEBUG",)


def test_config_defaults_have_empty_paths_defines(tmp_path: Path):
    cfg = Config.from_env({"GITHUB_WORKSPACE": str(tmp_path)})
    assert cfg.include_paths == ()
    assert cfg.defines == ()
    assert cfg.undefines == ()
