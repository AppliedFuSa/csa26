from pathlib import Path

from csa26.cppcheck import build_cppcheck_args


def test_build_args_minimal():
    args = build_cppcheck_args(
        Path("/work/src"),
        Path("/work/.csa26/report.xml"),
        misra_addon=Path("/usr/share/cppcheck/addons/misra.py"),
    )
    assert args[0] == "cppcheck"
    assert "--xml" in args
    assert "--xml-version=2" in args
    assert "--addon=/usr/share/cppcheck/addons/misra.py" in args
    assert "--output-file=/work/.csa26/report.xml" in args
    # Source-Verzeichnis steht zuletzt — wichtig, sonst interpretiert
    # cppcheck Folge-Args als Dateien.
    assert args[-1] == "/work/src"


def test_build_args_appends_includes_defines_undefines():
    args = build_cppcheck_args(
        Path("/work/src"),
        Path("/work/r.xml"),
        misra_addon=Path("/m.py"),
        include_paths=[Path("/work/vendor/sdk"), Path("/work/src/include")],
        defines=["STM32F4=1", "__ARM_ARCH_7EM__"],
        undefines=["DEBUG"],
    )
    assert "-I/work/vendor/sdk" in args
    assert "-I/work/src/include" in args
    assert "-DSTM32F4=1" in args
    assert "-D__ARM_ARCH_7EM__" in args
    assert "-UDEBUG" in args
    # Source bleibt am Ende — auch mit zusätzlichen Args.
    assert args[-1] == "/work/src"


def test_build_args_no_include_or_define_when_empty():
    args = build_cppcheck_args(
        Path("/work/src"),
        Path("/work/r.xml"),
        misra_addon=Path("/m.py"),
    )
    assert not any(a.startswith("-I") for a in args)
    assert not any(a.startswith("-D") for a in args)
    assert not any(a.startswith("-U") for a in args)
