# Cross-Repo-Request

**Von:** csa26-Chat
**An:** _org-Chat (`AppliedFuSa/_org`)
**Datum:** 2026-05-07
**Betreff:** Architektur-Memo csa26 — Phase-2-Pivot zu Eigenbau-Engine
**Status:** erledigt — siehe _org Commit `7f78f2a`

> **Hinweis Wolfgang:** csa26-Chat hat keinen Schreibzugriff auf
> `_org`, daher liegt diese Request-Datei im csa26-Repo unter
> `docs/cross-repo-requests/`. Bitte den Inhalt in den _org-Chat
> kopieren oder die Datei nach `_org/cross-repo-requests/` mit
> demselben Datei-Namen verschieben.

## Kontext

Am 2026-05-07 wurde im csa26-Chat eine **strategische Wende**
beschlossen, die das bestehende Architektur-Memo
`_org/architecture/csa26.md` an mehreren Stellen veraltet.

**Kurz:** csa26 wird ab Phase 2 nicht mehr als Cppcheck-Wrapper
ausgebaut, sondern als **komplett eigenständige MISRA-C-Analyse-
Engine** entwickelt — eigener Lexer, Preprocessor, Parser, Symbol-/
Type-System und Rule-Engine. Cppcheck verschwindet komplett aus dem
Stack, auch nicht als Frontend.

**Begründung:** Tool-Qualifikation nach ISO 26262-8 (via teq18-Self-
Qualifikation in Phase 2) ist mit eigener IP wesentlich einfacher als
mit Drittanbieter-Komponenten, die nur über Use-History-
Argumentation eingebunden werden können. Volle Kontrolle, eigene
Test-Suite, klares Ownership.

## Ist-Zustand im Repo

- `main` — Cppcheck-Wrapper, **eingefroren auf v0.1.0**. Tag und
  ghcr-Image (`ghcr.io/appliedfusa/csa26:v0.1.0`, `:v0`, `:latest`)
  existieren, sind aber nicht öffentlich gestellt. Kein Marketplace-
  Listing eingereicht.
- `v0` — Branch mit angepasster action.yml (ghcr-Image-Pull).
  Eingefroren.
- `engine` — neuer Branch mit `engine/`-Subprojekt. Skelett gepusht
  (Token-System, Lexer-Stub, README, eigene CI). Lexer-
  Implementation läuft.

## Ask

Bitte das Architektur-Memo `_org/architecture/csa26.md` an den
folgenden Stellen aktualisieren, damit das Memo den neuen Plan
korrekt reflektiert.

### 1. Status-Block (oben)

Aktuell deutet das Memo auf eine reine Phase-1-Repo-Bootstrap-
Situation hin. Ergänzen:

> **Status (2026-05-07):** Phase 1 (Cppcheck-Wrapper, csa26 v0.1.x)
> ist eingefroren auf v0.1.0 — Tag und ghcr-Image existieren, das
> Image ist nicht öffentlich, kein Marketplace-Listing eingereicht.
> Phase 2 läuft als komplett eigenständige Implementation auf dem
> `engine`-Branch. Cross-Repo-Requests an landing (Trust-Block,
> Produkt-Karte) bleiben „vorbereitet, nicht versendet".

### 2. Kernentscheidung 3 — Stack

Aktuell: „Phase-1-Stack: Python wraps Cppcheck-Binary in einem
Docker-Container. … Wenn die Discovery-Hypothese trägt, kommt in
Phase 2 die C++-Reimplementierung des Wrappers."

Ersetzen / ergänzen:

> **Phase-2-Stack-Entscheidung 2026-05-07:** Statt einer C++-
> Reimplementierung des Wrappers wird csa26 als komplett eigenständige
> MISRA-C-Analyse-Engine in Python aufgebaut: eigener Lexer,
> Preprocessor, Parser, Symbol-/Type-System, Rule-Engine. **Cppcheck
> verschwindet komplett aus dem Stack** — auch nicht als Frontend.
>
> Sprach-Scope: C99-Basis. GCC-Extensions (`__attribute__`,
> statement-expressions, inline asm) werden geparst, aber nicht
> semantisch ausgewertet. Kein K&R, kein C11-`_Generic`, kein VLA.
>
> Die Phase-1-Aussage „C++-Reimplementierung in Phase 2" ist damit
> überholt. Wenn nach Discovery noch ein C++-Stack relevant wird,
> entscheidet das ein späteres Memo.

### 3. Kernentscheidung 5 — teq18-Self-Qualifikation

Aktuell wird teq18-Self-Qualifikation in Phase 2 angepeilt. Diese
Aussage bleibt richtig, sollte aber ergänzt werden:

> **Bezug zum Eigenbau (2026-05-07):** Die Phase-2-Eigenbau-Strategie
> ist die Voraussetzung für eine substanzielle teq18-Self-
> Qualifikation. Mit eigener IP unter Apache-2.0 sind alle Evidence-
> Bausteine aus teq18 (Tool-Development-Process 1b, plus Property-/
> Fuzzing-/Mutation-Substanz für Anwender-1c) direkt anwendbar — bei
> einem Cppcheck-Wrapper hätten wir den Cppcheck-Anteil nur über
> Use-History-Argumentation einbinden können, was im Audit anstrengend
> wird.

### 4. Roadmap

Aktuelle Roadmap-Punkte v0.2 (eigenes Regel-Wording) und v0.3
(MISRA-C:2023) gelten so nicht mehr — v0.1.x ist eingefroren.
Ersetzen durch:

> **Roadmap (2026-05-07):**
>
> - **v0.1.0** — Cppcheck-Wrapper-Prototyp, eingefroren. Tag und
>   ghcr-Image existieren, kein öffentlicher Marketplace-Push.
> - **csa26-engine v0.0.1 → v1.0.0** — eigenständige Implementation
>   auf dem `engine`-Branch. Subset von **20 FuSa-priorisierten
>   MISRA-C:2012-Rules** in fünf Clustern:
>   - Type-Safety: 10.1, 10.3, 10.4, 10.5, 10.8
>   - Control-Flow-Disziplin: 14.3, 14.4, 15.5, 15.7
>   - Pointer-Disziplin: 8.13, 11.3, 11.5, 18.4
>   - Funktions-Hygiene: 8.4, 8.7, 17.2, 17.7
>   - Toter/Unbenutzter Code: 2.1, 2.2, 2.5
> - **v1.0.0** — Cut-Over: Eigenbau-Engine ersetzt main, Cppcheck-
>   Wrapper-Code wird gelöscht. Marketplace-Push und CRR-Versand an
>   landing (Trust-Block, Produkt-Karte) erfolgen erst nach v1.0.0.
> - **Phase 2+** — teq18-Self-Qualifikation auf Basis der eigenen
>   Engine.

### 5. Aufwands-Erwartung als offener Punkt

Im Abschnitt „Offene Punkte" ergänzen:

> **Aufwand des Eigenbaus.** Schätzung Stand 2026-05-07: ~46–92
> Personentage / 2–4 Monate Solo-Vollzeit für Frontend (Lexer,
> Preprocessor, Parser, Symbol-/Type-System), 20 Rules und Tests.
> Risiko-Stellen: Preprocessor-Korrektheit, GCC-Extension-Akzeptanz
> bei realen Embedded-Codebases (STM32-HAL-Stil), ISO-C-Type-
> Equivalence-Subtilitäten. Aufwand wird im Prototyp gemessen, dann
> erfolgt strategische Re-Bewertung.

## Akzeptanzkriterien

- [ ] `_org/architecture/csa26.md` Status-Block reflektiert den Pivot
- [ ] Kernentscheidung 3 dokumentiert die Eigenbau-Engine in Python
      statt C++-Reimplementierung
- [ ] Kernentscheidung 5 verweist auf den Eigenbau als Voraussetzung
      für saubere teq18-Self-Qualifikation
- [ ] Roadmap nennt die 20er-Rule-Liste und den Cut-Over-Plan
- [ ] „Offene Punkte" enthält den Aufwands-Schätzwert
- [ ] Optional: `_org/README.md` Repo-Tabelle weist csa26 als
      „Phase 1 frozen, Phase 2 in Arbeit auf engine-Branch" aus
- [ ] CRR-Status hier auf `erledigt` setzen mit Commit-Hash

## Rückkanal

- Commit-Hash + Repo (`_org`)
- Anmerkungen, falls _org-Chat eine alternative Formulierung
  bevorzugt (z.B. weil es mit anderen Memos im Portfolio konsistenter
  bleibt)

## Kontext-Links

- Existierendes Architektur-Memo: `_org/architecture/csa26.md`
- Bestehende CRRs an landing (bleiben „vorbereitet, nicht versendet"):
  - `_org/cross-repo-requests/2026-05-06-org-landing-csa26-trust-block.md`
  - `_org/cross-repo-requests/2026-05-06-org-landing-csa26-produkt-karte.md`
- csa26 engine-Branch: https://github.com/AppliedFuSa/csa26/tree/engine
- engine/-README mit Architektur-Skizze:
  https://github.com/AppliedFuSa/csa26/blob/engine/engine/README.md

---

## Wenn der Request erledigt ist

Setze `Status: erledigt`, ergänze unten:

### Erledigt am

`2026-05-07` von `_org-Chat`

- Commit: `7f78f2a` in `_org` — Architektur-Memo + Repo-Tabelle
  reflektieren den Phase-2-Pivot zur Eigenbau-Engine vollständig.
- Folge-Commit: `e52a878` in `_org` — Commit-Hash in der CRR-Kopie
  unter `_org/cross-repo-requests/` nachgetragen.
- Anmerkungen: alle sechs Akzeptanzkriterien erfüllt. Quell-Datei
  hier bleibt als historische Audit-Spur im csa26-Repo.
