# csa26 — Nutzungs-Anleitungen

Drei typische Projekt-Setups Schritt für Schritt. Wenn Dein Projekt
nicht in eines davon passt, mach bitte eine
[Discussion](https://github.com/AppliedFuSa/csa26/discussions) mit
einer Skizze Deiner Verzeichnis-Struktur auf — wir tragen häufige
Fälle hier nach.

## Voraussetzungen

- **Public-Repo oder GitHub-Auth** zum Pullen von
  `ghcr.io/appliedfusa/csa26:v1`. Bei einem Public-Image und einem
  Public-Source-Repo brauchst Du keine zusätzlichen Tokens.
- **Permissions im Workflow:**
  ```yaml
  permissions:
    contents: read
    security-events: write   # nur für SARIF-Upload
  ```

## Setup A — Standalone C, keine externen Header

Anwendungsfall: kleines Tool, das nur gegen die C-Standard-Library
(`<stdio.h>`, `<stdint.h>` etc.) baut, alle Sources liegen flach
unter einem Verzeichnis.

```yaml
name: csa26
on: [pull_request]
permissions:
  contents: read
  security-events: write

jobs:
  misra-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: AppliedFuSa/csa26@v1
        with:
          src-dir: src
          severity-threshold: warning
          fail-on-findings: 'false'

      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: csa26.sarif
```

csa26 bringt eingebaute Stubs für `<stdint.h>`, `<stddef.h>`,
`<stdbool.h>`, `<string.h>`, `<stdio.h>` und `<stdlib.h>` mit — die
sind ausreichend für das meiste C-Code, der nur Standard-Library
benutzt.

## Setup B — Modul mit lokalem `include/`-Verzeichnis

Anwendungsfall: typisches C-Modul mit Public-Header in `include/`
und Implementierungen in `src/`.

```
mein-modul/
├── include/
│   └── crc.h
└── src/
    └── crc.c
```

```yaml
- uses: AppliedFuSa/csa26@v1
  with:
    src-dir: src
    include-paths: |
      include
    severity-threshold: warning
```

Wichtig: `include-paths` ist relativ zum Repo-Root, nicht zum
`src-dir`. csa26 sucht in dieser Reihenfolge:
1. Verzeichnis der `#include`-anrufenden Datei (für `"local.h"`-Form)
2. Die in `include-paths` angegebenen Verzeichnisse
3. Die eingebauten C99-System-Stubs

## Setup C — Vendor-SDK (STM32-Stil)

Anwendungsfall: STM32-Projekt mit CMSIS und ST HAL als Vendor-SDK.

```
mein-stm32-projekt/
├── vendor/
│   ├── cmsis/
│   │   └── include/stm32f4xx.h
│   └── stm32hal/
│       └── include/stm32f4xx_hal_*.h
├── src/
│   ├── include/
│   │   └── leds.h
│   ├── leds.c
│   └── main.c
```

```yaml
- uses: AppliedFuSa/csa26@v1
  with:
    src-dir: src
    include-paths: |
      vendor/cmsis/include
      vendor/stm32hal/include
      src/include
    defines: |
      STM32F407xx
      USE_HAL_DRIVER
    severity-threshold: warning
```

`defines:` setzen den Wert auf `1`, falls Du nichts anderes angibst
(`STM32F407xx` wird zu `#define STM32F407xx 1`). Wenn Du einen
expliziten Wert brauchst, schreibe `STM32F407xx=1U` o.ä.

### Vendor-Header verlangt ein Define mit `#error`

Vendor-Headers haben oft Wachen wie:
```c
#if !defined(STM32F407xx)
#error "STM32F407xx must be defined"
#endif
```

Wenn Du das siehst, schau Dir die `#define`s in Deinem Vendor-SDK
oder Build-System an und reichere `defines:` entsprechend an. Im
typischen Embedded-Projekt findest Du sie in:

- `CMakeLists.txt` als `target_compile_definitions(...)`
- `Makefile` als `CFLAGS += -DSTM32F407xx`
- `platformio.ini` als `build_flags = -DSTM32F407xx`
- IAR/Keil-Projektdateien (XML/JSON-Settings für „Defined symbols")

## Setup-Patterns, die NICHT funktionieren

- **Header-only-Libraries** mit ausschließlich `.h`-Dateien — csa26
  scannt rekursiv nur `.c`. Header werden über `#include` erreicht,
  nicht direkt geprüft.
- **K&R-Style-Function-Definitions** (`void foo(a, b) int a; int b; { … }`) —
  Phase-1-Subset der Engine unterstützt nur ANSI/ISO-Syntax.
- **VLAs (variable-length arrays)** und C11-`_Generic` — Phase-1-
  Subset, kommt ggf. in v1.x.

## Findings interpretieren

| Severity | Bedeutung |
|---|---|
| `error` | Klare ISO-/MISRA-Verletzung, fast immer fixen |
| `warning` | Wahrscheinliche Verletzung, mit kurzem Review fixen |
| `note` | Hinweis-Charakter, oft ein Idiom-Vorschlag (z.B. „könnte const sein") |

Default-`severity-threshold` ist `warning` — `note`-Findings werden
nicht angezeigt, bis Du explizit `severity-threshold: note` setzt.

## Fragen, Bug-Reports, Feature-Vorschläge

- **Frage zur Nutzung / MISRA-Auslegung:** [Discussions](https://github.com/AppliedFuSa/csa26/discussions)
- **Reproduzierbarer Bug:** [Bug-Report](https://github.com/AppliedFuSa/csa26/issues/new?template=bug_report.yml)
- **Feature-Vorschlag:** [Feature-Request](https://github.com/AppliedFuSa/csa26/issues/new?template=feature_request.yml)
