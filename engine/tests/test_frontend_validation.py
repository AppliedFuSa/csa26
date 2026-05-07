"""End-to-End-Frontend-Smoketests gegen die `csa26-testfixture`-Beispiele.

Wir importieren keine externen Header-Stubs für `<stdint.h>` /
`<stddef.h>` — stattdessen liefern wir minimale In-Memory-Typedefs
über einen Test-SourceLoader. Das spiegelt das, was der echte Toolchain
aus dem System-SDK ziehen würde.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from csa26_engine.parser import parse
from csa26_engine.preprocessor import InMemorySourceLoader, preprocess
from csa26_engine.symbols import bind
from csa26_engine.types import infer_types

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Minimale Stubs für die System-Header — eine Test-Toolchain.
_SYSTEM_HEADERS: dict[str, str] = {
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


def _make_loader(extra: dict[str, str] | None = None) -> InMemorySourceLoader:
    files = dict(_SYSTEM_HEADERS)
    if extra:
        files.update(extra)
    return InMemorySourceLoader(files)


def _frontend_smoketest(
    file: Path,
    *,
    loader: InMemorySourceLoader,
    defines: dict[str, str] | None = None,
) -> None:
    """Komplette Frontend-Pipeline auf einer Datei. Wirft, wenn was crasht."""
    source = file.read_text(encoding="utf-8")
    tokens = preprocess(source, file=str(file), source_loader=loader, defines=defines or {})
    tu = parse(tokens)
    bindings = bind(tu)
    types = infer_types(bindings)
    assert tu is not None
    assert bindings is not None
    assert isinstance(types, dict)


# ---------------------------------------------------------------------------
# 01-basic
# ---------------------------------------------------------------------------


def test_basic_fixture_passes_frontend():
    loader = _make_loader()
    _frontend_smoketest(FIXTURES_DIR / "basic" / "crc8.c", loader=loader)


def test_basic_fixture_recognises_function_definitions():
    loader = _make_loader()
    source = (FIXTURES_DIR / "basic" / "crc8.c").read_text(encoding="utf-8")
    tokens = preprocess(source, file="crc8.c", source_loader=loader)
    tu = parse(tokens)
    bindings = bind(tu)
    # `compute_crc8` und `main` müssen beide in der Function-Tabelle stehen
    assert "compute_crc8" in bindings.function_table
    assert "main" in bindings.function_table


# ---------------------------------------------------------------------------
# 02-medium
# ---------------------------------------------------------------------------


def test_medium_sensor_module_passes_frontend():
    """Header `sensor.h` muss über `include-paths`-Mechanismus gefunden
    werden — wir simulieren das, indem wir den Header als Filesystem-
    relativen Pfad ins Loader-Dict packen."""
    medium_dir = FIXTURES_DIR / "medium"
    header = (medium_dir / "include" / "sensor.h").read_text(encoding="utf-8")
    loader = _make_loader({"sensor.h": header})

    _frontend_smoketest(medium_dir / "src" / "sensor.c", loader=loader)
    _frontend_smoketest(medium_dir / "src" / "main.c", loader=loader)


def test_medium_sensor_function_table_complete():
    medium_dir = FIXTURES_DIR / "medium"
    header = (medium_dir / "include" / "sensor.h").read_text(encoding="utf-8")
    loader = _make_loader({"sensor.h": header})

    src = (medium_dir / "src" / "sensor.c").read_text(encoding="utf-8")
    tokens = preprocess(src, file="sensor.c", source_loader=loader)
    tu = parse(tokens)
    bindings = bind(tu)
    assert "sensor_calibrate" in bindings.function_table
    assert "sensor_smooth" in bindings.function_table


# ---------------------------------------------------------------------------
# 03-complex (Vendor-SDK-Stubs + Defines)
# ---------------------------------------------------------------------------


_COMPLEX_DEFINES = {"STM32F407xx": "1", "USE_HAL_DRIVER": "1"}


def _complex_loader() -> InMemorySourceLoader:
    complex_dir = FIXTURES_DIR / "complex"
    headers: dict[str, str] = {}
    headers["stm32f4xx.h"] = (
        complex_dir / "vendor" / "cmsis" / "include" / "stm32f4xx.h"
    ).read_text(encoding="utf-8")
    headers["stm32f4xx_hal_gpio.h"] = (
        complex_dir / "vendor" / "stm32hal" / "include" / "stm32f4xx_hal_gpio.h"
    ).read_text(encoding="utf-8")
    headers["leds.h"] = (complex_dir / "src" / "include" / "leds.h").read_text(encoding="utf-8")
    return _make_loader(headers)


def test_complex_leds_module_passes_frontend_with_defines():
    """Vendor-Stubs nutzen `#error`-Direktiven, wenn die erwarteten
    Defines nicht gesetzt sind — dieser Test beweist, dass der
    `defines`-Mechanismus durch die ganze Frontend-Pipeline trägt."""
    loader = _complex_loader()
    _frontend_smoketest(
        FIXTURES_DIR / "complex" / "src" / "leds.c",
        loader=loader,
        defines=_COMPLEX_DEFINES,
    )


def test_complex_leds_module_fails_without_defines():
    """Sanity-Check der Sanity-Check: ohne Defines greift `#error`."""
    loader = _complex_loader()
    with pytest.raises(Exception):  # noqa: B017
        _frontend_smoketest(FIXTURES_DIR / "complex" / "src" / "leds.c", loader=loader)


def test_complex_main_passes_frontend():
    loader = _complex_loader()
    _frontend_smoketest(
        FIXTURES_DIR / "complex" / "src" / "main.c",
        loader=loader,
        defines=_COMPLEX_DEFINES,
    )


def test_complex_leds_function_table_complete():
    loader = _complex_loader()
    src = (FIXTURES_DIR / "complex" / "src" / "leds.c").read_text(encoding="utf-8")
    tokens = preprocess(src, file="leds.c", source_loader=loader, defines=_COMPLEX_DEFINES)
    tu = parse(tokens)
    bindings = bind(tu)
    assert "leds_init" in bindings.function_table
    assert "leds_set" in bindings.function_table
