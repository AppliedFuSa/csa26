# csa26-engine — Eigenbau-MISRA-C-Analyse-Engine

> **Status:** Prototyp, in aktiver Entwicklung. Lebt auf dem
> `engine`-Branch, nicht auf `main`. Ziel: csa26 v1.0.0 als
> komplett eigenständige Implementation, ohne Cppcheck.

## Zweck

`engine/` ist die **eigenständige Reimplementierung** der csa26-
MISRA-C-Analyse, ohne Cppcheck oder andere Drittanbieter-
Komponenten. Eigener Lexer, Preprocessor, Parser, Symbol-/Type-System
und Rule-Engine.

## Warum?

Die Phase-1-csa26 (auf `main`, eingefroren auf v0.1.0) wrappte das
Cppcheck-MISRA-Addon. Das funktionierte für Discovery-Validierung,
ist aber für **Tool-Qualifikation nach ISO 26262-8** problematisch:
fremde Drittanbieter-Komponenten lassen sich nur über aufwändige
Use-History-Argumentation in eine Tool-Confidence-Begründung
einbinden.

Eigenbau bedeutet:
- **Volle Kontrolle** über Implementation, Tests, Versionierung
- **Eigene IP** unter Apache-2.0
- **Klarer teq18-Self-Qualifikations-Pfad** in Phase 2
- **Fokus statt Breite**: 20 sorgfältig ausgewählte FuSa-relevante
  Rules statt voller MISRA-Coverage

Die Phase-2-csa26-Strategie steht im Architektur-Memo
`_org/architecture/csa26.md` (im _org-Repo).

## Subset — die 20 Rules

| Cluster | Rules |
|---|---|
| Type-Safety | 10.1, 10.3, 10.4, 10.5, 10.8 |
| Control-Flow-Disziplin | 14.3, 14.4, 15.5, 15.7 |
| Pointer-Disziplin | 8.13, 11.3, 11.5, 18.4 |
| Funktions-Hygiene | 8.4, 8.7, 17.2, 17.7 |
| Toter/Unbenutzter Code | 2.1, 2.2, 2.5 |

## Architektur

```
                 ┌────────────────────────────────────┐
   .c-Quelldatei │                                    │
                 │  Lexer  →  Preprocessor  →  Parser │
                 │                                  ↓ │
                 │                              AST mit │
                 │                          Source-Loc │
                 │                                  ↓ │
                 │      ┌────────────────────────────┘ │
                 │      ↓                              │
                 │  Symbol-Resolution                  │
                 │  (Scopes, Tags, Labels, Idents)     │
                 │      ↓                              │
                 │  Type-System                        │
                 │  (Subset für die 20 Rules)          │
                 │      ↓                              │
                 │  Rule-Engine                        │
                 │  (20 Module, ein File pro Rule)     │
                 │      ↓                              │
                 └──────┼──────────────────────────────┘
                        ↓
              Findings → Reporter (Phase-1-Output-Code wiederverwendet:
                          Job Summary, Annotations, SARIF 2.1.0)
```

## Modul-Layout

```
engine/
├── README.md                      # ← diese Datei
├── pyproject.toml                 # eigenes Python-Package
├── src/
│   └── csa26_engine/
│       ├── __init__.py
│       ├── tokens.py              # Token-Typen + Source-Locations
│       ├── lexer.py               # C-Lexer
│       ├── preprocessor.py        # #include, #define, #if, …
│       ├── ast_nodes.py           # AST-Knoten-Klassen
│       ├── parser.py              # C99-Subset-Parser → AST
│       ├── symbols.py             # Symbol-Tabelle, Scope-Stack
│       ├── types.py               # Type-System (Subset)
│       ├── engine.py              # Rule-Runner / Orchestrator
│       └── rules/
│           ├── __init__.py
│           ├── _base.py           # Rule-Basisklasse + Visitor-Hooks
│           ├── rule_8_13.py       # Pointer const-correctness
│           ├── rule_14_4.py       # Boolean-Kontrollausdruck
│           └── …                  # 18 weitere
└── tests/
    ├── test_lexer.py
    ├── test_preprocessor.py
    ├── test_parser.py
    ├── test_symbols.py
    ├── test_types.py
    └── rules/
        ├── test_rule_8_13.py
        └── …
```

## Sprach-Scope

- **Sprach-Standard:** C99-Basis. Kein K&R-Syntax, kein C11-`_Generic`,
  kein C99-VLA, kein C99-Komplexes-Zahlen.
- **GCC-Extensions:** **parsen, nicht semantisch auswerten.**
  `__attribute__((...))`, statement-expressions `({...})`, inline asm
  (`__asm__`, `asm`), `__builtin_*`-Aufrufe, GCC-spezifische
  Type-Specifier (`__restrict__`, `__inline__`).
- **Preprocessor:** Eigenbau, „good enough for embedded". Nicht
  ISO-corner-case-perfekt — wenn ein Edge-Case auftaucht, wird er
  dokumentiert und als Limitation akzeptiert oder gefixt.
- **Symbol-Resolution:** Full block-scope-handling. File-, Function-,
  Block-Scope. Separate Namespaces für Tags (struct/union/enum),
  Labels (goto-Targets), Identifier (Variablen/Funktionen),
  Members (struct/union-Felder).
- **Type-System:** Subset für die 20 Rules — Pointer-Compatibility
  (Rule 11.x), Integer-Promotions und Usual-Arithmetic-Conversions
  (Rule 10.x), const-Qualifizierung (Rule 8.13).

## Test-Strategie

Drei Ebenen:

1. **Unit-Tests** pro Modul (Lexer, Preprocessor, Parser, …) gegen
   handgeschriebene C-Snippets.
2. **Frontend-Validierung** gegen das `csa26-testfixture`-Repo
   (privat, drei Beispiele basic / medium / complex), insbesondere
   gegen das `03-complex`-Beispiel mit STM32-HAL-Stubs.
3. **Rule-Tests:** pro Rule mindestens ein True-Positive- und ein
   True-Negative-Test plus, wo möglich, ein dokumentierter False-
   Positive- oder Halt-False-Negative-Fall.

## Aufwands-Erwartung

Realistisch **~46–92 Personentage / 2–4 Monate Solo-Vollzeit** für
Frontend, 20 Rules und Tests. Risiko-Stellen:

- **Preprocessor-Korrektheit** — Macro-Expansion mit Token-Pasting,
  Variadic-Macros, Stringification ist berüchtigt für Subtilitäten.
- **GCC-Extension-Akzeptanz** — STM32-HAL und vergleichbare SDKs
  müssen ohne Parser-Crash durchlaufen.
- **Type-Equivalence** — Rule 11.3 braucht ISO-C-Type-Compatibility-
  Regeln korrekt; Pointer-zu-`int` ≠ Pointer-zu-`signed int`-artige
  Subtilitäten.

Frühwarn-Signale:
- Preprocessor an Tag 14 noch nicht durch → Architektur-Review.
- STM32-Beispiel an Tag 30 noch nicht durch den Frontend → Architektur-Review.

## Was NICHT in der Engine ist

- **Output-Pipeline** (Job Summary, Annotations, SARIF) — wird aus
  `src/csa26/outputs.py` (Phase-1-Code auf `main`) wiederverwendet,
  sobald die Engine Findings produziert.
- **GitHub-Action-Wrapper** (`action.yml`, `Dockerfile`) — wird mit
  v1.0.0-Cut-Over auf die Engine umgestellt, vorher unverändert.
- **Cppcheck** — komplett raus.
