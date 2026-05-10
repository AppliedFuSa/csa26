# Changelog

Alle wesentlichen Änderungen an csa26 werden hier dokumentiert.

Format orientiert sich lose an [Keep a Changelog](https://keepachangelog.com/);
Versionen folgen [Semver](https://semver.org/lang/de/).

## [Unreleased]

## [1.0.3] — 2026-05-10

### Changed

- `action.yml`-`description` auf 99 Zeichen gekürzt — das GitHub-
  Marketplace-Validation lehnt ab >125 Zeichen ab. Neue Variante:
  „Pre-audit MISRA-C:2012 checker for embedded C. Runs in your CI,
  curated 20-rule subset, Apache-2.0."
- Die ausführliche Selbst-Beschreibung (mit Tool-Qualifikations-
  und AS-IS-Disclaimer + Feedback-Hinweis) bleibt im README-Status-
  Block, der direkt unter der Marketplace-Description verlinkt wird.

## [1.0.2] — 2026-05-10

### Changed

- **README** bekommt einen prominenten Status-Block ganz oben mit
  sechs klar formulierten Bullets: Pre-Audit-Charakter, Coverage,
  Tool-Qualifikations-Stand, Lizenz-Disclaimer, Stabilisierungs-
  Phase und ausdrückliche Feedback-Einladung. Der bestehende
  Datenfluss-Hinweis bleibt direkt darunter.
- **`action.yml`-`description`** komplett neu — der Marketplace
  zeigt diese Zeile prominent. Neuer Text: „Pre-audit MISRA-C:2012
  checker … v1 covers a curated 20-rule subset; not tool-qualified
  per ISO 26262-8; AS IS under Apache-2.0. Feedback shapes future
  rule additions."

Vorbereitung auf das GitHub-Marketplace-Listing — nichts an der
Engine-Funktionalität geändert, 220 Tests bleiben grün.

## [1.0.1] — 2026-05-08

### Changed

- `action.yml` description und Input-Beschreibungen von Phase-1-
  Cppcheck-Texten auf den csa26-engine-Stack aktualisiert.
- `severity-threshold`-Default von `style` (Phase-1-Cppcheck-Severity,
  von der Engine als `note` interpretiert) auf `warning` umgestellt —
  konsistent mit der CLI und dem README v1.0.

## [1.0.0] — 2026-05-07

Strategische Wende von Phase 1 (Cppcheck-Wrapper) zur **eigenständigen
csa26-Engine**. Komplettes Stack-Eigentum: Lexer, Preprocessor,
Parser, Symbol-/Type-System, Rule-Engine — kein Drittanbieter-Static-
Analyser mehr im Stack. Vorbereitung für teq18-Self-Qualifikation
(siehe `_org/architecture/csa26.md`).

### Added

- **Eigenständige Engine** unter `engine/src/csa26_engine/`:
  - Hand-geschriebener C-Lexer (ISO C99 §6.4)
  - Preprocessor mit object-/function-like Macros, `__VA_ARGS__`,
    `#`/`##`, vollwertiger `#if`-Konstanten-Auswertung, Adjacent-
    String-Concatenation
  - Recursive-Descent-Parser für ein C99-Subset inkl. typedef-Tracker,
    Spiral-Rule-Declarators, GCC-Extensions (`__attribute__`, asm,
    Statement-Expressions)
  - Symbol-Resolution mit Scope-Stack (file/function/block) und
    Namespace-Trennung (ordinaries, tags, labels)
  - Type-System mit Pointer-Compat, Const-Tracking, Integer-
    Promotions, Usual-Arithmetic-Conversions
  - 20-Rule-Engine mit FuSa-priorisierter Rule-Auswahl in fünf
    Clustern (Type-Safety / Control-Flow / Pointer-Disziplin /
    Funktions-Hygiene / Toter-Code)
  - Built-in-Header-Stubs für `<stdint.h>`, `<stddef.h>`,
    `<stdbool.h>`, `<string.h>`, `<stdio.h>`, `<stdlib.h>` —
    funktioniert ohne System-libc im Container
- **Output-Pipeline**: Job-Summary-Markdown, GitHub-Workflow-
  Annotations, SARIF 2.1.0 — strukturell kompatibel mit dem
  Phase-1-Output-Format.
- **CLI**: `csa26-engine` als Console-Script. Inputs werden über
  `CSA26_*`-Environment-Variablen aus `action.yml` gelesen.
- **220 Engine-Unit-Tests** und **5 End-to-End-Tests** gegen die
  drei `csa26-testfixture`-Beispiele (basic / medium / complex).

### Changed

- **Dockerfile** drastisch vereinfacht: kein `cppcheck` mehr,
  kein Addons-Tarball, kein Net-Pull beim Build. Nur
  `python:3.12-slim` + `pip install ./engine`.
- **action.yml**-Inputs unverändert (rückwärtskompatibel zu v0.1):
  `src-dir`, `rule-set`, `severity-threshold`, `fail-on-findings`,
  `sarif-output`, `include-paths`, `defines`, `undefines`.
- Self-Smoketest-Workflow läuft jetzt gegen die drei Engine-
  Fixtures (basic / complex), prüft Findings-Anzahl und MISRA-
  only-IDs im SARIF.

### Removed

- **Phase-1-Cppcheck-Wrapper** (`src/csa26/`, `tests/`, `rules/`,
  Top-Level-`pyproject.toml`) — vollständig durch die Eigenbau-
  Engine ersetzt.
- v0.1.0-Tag und das gepushte ghcr-Image bleiben als Backup
  bestehen und sind weiter unter `@v0.1.0` aufrufbar.

### Migration

Bestehende Workflows mit `uses: AppliedFuSa/csa26@v0` müssen NICHT
geändert werden — die Action-Inputs sind kompatibel. Die produzierten
Findings unterscheiden sich aber: csa26-engine prüft die 20 selbst
implementierten FuSa-priorisierten Rules anstelle der ~80–110 Cppcheck-
MISRA-Addon-Rules. Coverage und Charakteristik sind in
`docs/coverage.md` (Phase 1) bzw. dem Architektur-Memo dokumentiert.

## [0.1.0] — 2026-05-07

Erste öffentliche Version (Phase-1-Cppcheck-Wrapper). Eingefroren
auf diesem Tag. Code wurde mit dem v1.0.0-Cut-Over entfernt.

[Unreleased]: https://github.com/AppliedFuSa/csa26/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/AppliedFuSa/csa26/releases/tag/v1.0.3
[1.0.2]: https://github.com/AppliedFuSa/csa26/releases/tag/v1.0.2
[1.0.1]: https://github.com/AppliedFuSa/csa26/releases/tag/v1.0.1
[1.0.0]: https://github.com/AppliedFuSa/csa26/releases/tag/v1.0.0
[0.1.0]: https://github.com/AppliedFuSa/csa26/releases/tag/v0.1.0
