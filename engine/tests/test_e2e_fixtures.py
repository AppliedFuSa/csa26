"""End-to-End-Tests: `analyze()` läuft komplett gegen die drei
csa26-testfixture-Beispiele und produziert Findings.

Testet keine exakten Finding-Mengen (das wäre fragil bei Heuristik-
Tweaks), sondern dass für jedes Beispiel mindestens ein erwarteter
Rule-ID-Cluster getroffen wird.
"""

from pathlib import Path

from csa26_engine.engine import analyze
from csa26_engine.preprocessor import InMemorySourceLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_SYSTEM_HEADERS = {
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


def _loader(extra=None):
    files = dict(_SYSTEM_HEADERS)
    if extra:
        files.update(extra)
    return InMemorySourceLoader(files)


def _rule_ids(findings):
    return {f.rule_id for f in findings}


# ---------------------------------------------------------------------------
# 01-basic
# ---------------------------------------------------------------------------


def test_e2e_basic_produces_misra_findings():
    src = (FIXTURES_DIR / "basic" / "crc8.c").read_text(encoding="utf-8")
    findings = analyze(src, file="crc8.c", source_loader=_loader())
    assert findings, "expected at least one finding for the basic fixture"
    ids = _rule_ids(findings)
    # `compute_crc8` und `main` haben keine Forward-Decl → 8.4
    assert "misra-c2012-8.4" in ids
    # `if (crc & 0x80U)` ist nicht boolesch → 14.4
    assert "misra-c2012-14.4" in ids


# ---------------------------------------------------------------------------
# 02-medium
# ---------------------------------------------------------------------------


def test_e2e_medium_sensor_produces_misra_findings():
    medium_dir = FIXTURES_DIR / "medium"
    header = (medium_dir / "include" / "sensor.h").read_text(encoding="utf-8")
    loader = _loader({"sensor.h": header})
    src = (medium_dir / "src" / "sensor.c").read_text(encoding="utf-8")

    findings = analyze(src, file="sensor.c", source_loader=loader)
    assert findings
    ids = _rule_ids(findings)
    # `samples` should be const-qualified — 8.13
    assert "misra-c2012-8.13" in ids


def test_e2e_medium_main_produces_findings():
    medium_dir = FIXTURES_DIR / "medium"
    header = (medium_dir / "include" / "sensor.h").read_text(encoding="utf-8")
    loader = _loader({"sensor.h": header})
    src = (medium_dir / "src" / "main.c").read_text(encoding="utf-8")

    findings = analyze(src, file="main.c", source_loader=loader)
    assert findings
    # `main()` zählt als Sonderfall → 8.4 nicht erwartet, aber sensor_smooth-
    # Aufruf ohne benutzten Return-Wert würde 17.7 triggern, falls
    # forward-decl da ist (ist sie via header).
    # Wir verifizieren nur, dass eine Analyse läuft und Findings entstehen.


# ---------------------------------------------------------------------------
# 03-complex
# ---------------------------------------------------------------------------


def test_e2e_complex_leds_produces_misra_findings():
    complex_dir = FIXTURES_DIR / "complex"
    headers = {
        "stm32f4xx.h": (complex_dir / "vendor/cmsis/include/stm32f4xx.h").read_text(),
        "stm32f4xx_hal_gpio.h": (
            complex_dir / "vendor/stm32hal/include/stm32f4xx_hal_gpio.h"
        ).read_text(),
        "leds.h": (complex_dir / "src/include/leds.h").read_text(),
    }
    loader = _loader(headers)
    src = (complex_dir / "src" / "leds.c").read_text(encoding="utf-8")

    findings = analyze(
        src,
        file="leds.c",
        source_loader=loader,
        defines={"STM32F407xx": "1", "USE_HAL_DRIVER": "1"},
    )
    assert findings
    ids = _rule_ids(findings)
    # `if (state)` ist nicht boolesch → 14.4
    assert "misra-c2012-14.4" in ids
    # `HAL_GPIO_Init`-Aufrufe ignorieren den Return-Wert → 17.7
    assert "misra-c2012-17.7" in ids


def test_e2e_findings_are_sorted_by_location():
    src = (FIXTURES_DIR / "basic" / "crc8.c").read_text(encoding="utf-8")
    findings = analyze(src, file="crc8.c", source_loader=_loader())
    sorted_keys = [
        (f.location.file, f.location.line, f.location.column, f.rule_id) for f in findings
    ]
    assert sorted_keys == sorted(sorted_keys)
