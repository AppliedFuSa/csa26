# csa26 — MISRA-C:2012 Coverage

Dieses Dokument trennt zwei Dinge, die in der Marketplace-Kommunikation
gerne vermischt werden:

1. **Strukturelle Tool-Obergrenze** — was eine statische Analyse-Tool-
   Klasse wie csa26 *prinzipiell* prüfen kann. Diese Grenze gilt für
   jeden Konkurrenten, auch für die 25-k-EUR-Suiten.
2. **csa26-Implementation** — was csa26 in der aktuellen Version
   *tatsächlich* prüft. Eine Teilmenge der Tool-Obergrenze.

Beide Zahlen sind transparent — wir versprechen keine Compliance-
Vollabdeckung, weil das fachlich nicht haltbar wäre.

## MISRA-C:2012 — Übersicht

MISRA-C:2012 definiert **143 Rules + 16 Directives = 159 Guidelines**
(plus Amendments). Jede Rule ist klassifiziert nach:

- **Required / Advisory / Mandatory** — Schweregrad der Anforderung.
- **Decidable / Undecidable** — kann ein Tool eindeutig entscheiden,
  oder nur eine Heuristik liefern (Halteproblem-verwandt).

## Strukturelle Tool-Obergrenze für csa26-Tool-Klasse

| Klasse | Anzahl (ca.) | Tool-tauglich? | Begründung |
|---|---:|---|---|
| Directives | 16 | überwiegend nein | Prozess-/Doku-orientiert, kein Code-Pattern. ~2–3 indirekt prüfbar (z.B. D.4.10 Header-Guard-Mehrfach-Inklusion). |
| Rules — decidable, lokal entscheidbar | ~95 | **ja** | Klassisches statisches-Analyse-Material. AST-Pattern-Matching plus Symbol-Tabelle reichen aus. |
| Rules — decidable, whole-program-nötig | ~20 | **ja**, mit Cross-TU-Sicht | Erfordert globale Symbol-Auflösung (alle TUs), aber prinzipiell mechanisch entscheidbar. |
| Rules — undecidable | ~26 | nur Heuristik | Halteproblem-verwandt; Tool kann „wahrscheinlich verletzt" melden, kein eindeutiges Verdikt. |
| Rules — Compiler-/Toolchain-spezifisch | ~5 | nein | Brauchen Compiler-Hook (implementation-defined behaviour); ohne Toolchain-Integration nicht prüfbar. |

**Realistische Obergrenze csa26:** etwa **115–125 von 143 Rules**
plus null bis drei Directives.

**Strukturell außerhalb der Tool-Klasse** (gilt für jeden statischen
Analyse-Wrapper):

- Alle 16 Directives (mit ggf. 2–3 indirekten Treffern).
- ~5 Compiler-/Toolchain-abhängige Rules.
- ~26 Undecidable Rules — bestenfalls Heuristik.

Das sind zusammen **~25–30% der MISRA-Guidelines, die strukturell
nicht durch ein Tool wie csa26 abgedeckt werden können**.

### Beispiele für Rules außerhalb der Tool-Klasse

**Directives (Prozess/Doku):**
- D.1.1 — Sprach-Standard einhalten
- D.4.1 — Run-time failures minimieren
- D.4.7 — Returnwerte testen, wenn Fehler signalisierbar
- D.4.9 — Funktionen vor Function-Like-Macros bevorzugen

**Compiler-abhängig:**
- Rule 1.1 — Compiler comply with implementation-defined behaviour
- Rule 1.3 — Kein Undefined Behavior gegen Implementation

**Undecidable:**
- Rule 2.1 — Kein unreachable code (Halteproblem-Verwandtschaft)
- Rule 17.2 — Keine direkte oder indirekte Rekursion (über mehrere
  TUs nicht eindeutig entscheidbar)
- Rule 18.1 — Pointer-Arithmetik innerhalb desselben Arrays
  (Aliasing-Analyse mit unbekannter Heap-Topologie)

## csa26-Implementation — Phase 1

Phase-1-Strategie: csa26 wrappt das Cppcheck-MISRA-Addon und liefert
ergänzend eigene Regel-Paraphrasen, GitHub-native Outputs und
MISRA-Filterung.

**Was Cppcheck-MISRA-Addon implementiert:** Teilmenge der ~115–125
strukturell tool-tauglichen Rules. Eine genaue Liste muss aus dem
`misra.py`-Skript extrahiert werden — typische Größenordnung sind
**80–110 Rules**, variiert mit Cppcheck-Version.

In den drei Test-Beispielen (`AppliedFuSa/csa26-testfixture`) hat
csa26 v0.1 folgende Rule-IDs aktiv produziert: `2.5, 8.4, 10.8, 11.4,
14.4, 17.7`. Das ist **kein** Coverage-Beweis — viele Rules sind in
diesen Beispielen einfach nicht verletzt — sondern eine Stichprobe.

Eine extrahierte vollständige `misra.py`-Coverage-Liste folgt mit
v0.2 als generierte Tabelle, sobald das Inventar-Skript steht.

## Was wir Kunden gegenüber NICHT versprechen

- **Vollständige MISRA-C:2012-Compliance-Prüfung.** Strukturell nicht
  möglich für eine ganze Tool-Klasse.
- **Kein Schutz gegen Falsch-Negative bei undecidable Rules.** Tool-
  Heuristiken können Verstöße übersehen — der Safety-Manager bleibt
  in der Verantwortung.
- **Keine Tool-Qualifikation gegenüber ISO 26262-8 in Phase 1.**
  Prototyp-Status, Tool-Confidence-Argumentation liegt beim Anwender.

## Was wir Kunden gegenüber sehr wohl versprechen

- **Transparente Coverage-Liste:** klar dokumentiert, welche Rules
  geprüft werden und welche nicht (ab v0.2 maschinell aktuell).
- **Reproduzierbare Befunde** (deterministisch, kein LLM, kein
  Sampling).
- **MISRA-Lizenz-Hygiene:** keine Volltext-Redistribution, eigene
  Paraphrasen unter Apache-2.0.
- **Code verlässt das Kunden-Repo nicht** (Container läuft auf
  Kunden-CI-Runner).

## Verweise

- MISRA-C:2012 — The MISRA Consortium, ISBN 978-1-906400-10-1.
  Volltext nur über offizielle Lizenz; csa26 redistribuiert keinen
  Volltext (siehe [NOTICE](../NOTICE)).
- Cppcheck-MISRA-Addon: `misra.py` im Cppcheck-Upstream-Repo.
- ISO 26262-8:2018, Clause 11 — „Confidence in the use of software
  tools" (für die Tool-Qualifikations-Frage in Phase 2).
