# CLAUDE.md — csa26

## Wer Du bist

Du bist im `csa26`-Repo, einem der Applied-FuSa-Tool-Repos. Applied
FuSa ist die freiberufliche Ingenieurpraxis von Wolfgang Freese
(Overath, Deutschland) mit Fokus auf Funktionale Sicherheit
(ISO 26262, IEC 61508, IEC 62304) und Automotive SPICE.

Dieses Repo gehört zum Multi-Repo-Setup unten. Du hast direkten
Dateisystem-Zugriff nur auf dieses Repo; Nachbar-Repos sind nur über
den Cross-Repo-Request-Workflow erreichbar.

## Das Applied-FuSa-Multi-Repo-Setup

Alle Repos liegen unter `github.com/AppliedFuSa`, lokal unter
`/Users/wolfgangfreese/Development/AppliedFuSa/`:

| Repo | Zweck | Live-URL |
|---|---|---|
| `_org` | Organisations-Hub: ADRs, Policies, Infrastruktur, Cross-Repo-Requests | — |
| `landing` | Marketing-Site, GUI-Spec-Heimat | https://appliedfusa.de |
| `mcsa` | Minimal Cut-Set Analyzer (Fehlerbaumanalyse aus ArchDSL) | https://mcsa.appliedfusa.de |
| `safety-case` | Interview-driven Safety-Case-Generator | geplant: https://safety-case.appliedfusa.de |
| `archdsl-interview` | Interview-CLI für ArchDSL-Input | — |
| `csa26` | **Dieses Repo** — MISRA-C:2012 Pre-Audit als GitHub Action | GitHub Marketplace (Phase 1) |
| `mcsa-projekte` / `mcsa-dist` | Kunden-Beispielmodelle / Release-Pakete für mcsa | — |
| `aspice` | ASPICE-Audit-Assistent — archiviert 2026-04-30 | — |

Jedes Tool-Repo hat seinen eigenen Claude-Code-Chat mit eigenem
Gedächtnis. Cross-Tool-Änderungen laufen über den Request-Workflow
unter `_org/cross-repo-requests/`, nicht über direkte Edits in
fremden Repos.

## Dieses Tool — csa26

**Zweck:** GitHub-Action-natives Pre-Audit-Werkzeug für embedded-C-
Quellcode gegen ein 20er-Subset von MISRA-C:2012. Eigenständige
Engine in `engine/` (Lexer, Preprocessor, Parser, Symbol-/Type-
System, Rule-Engine), kein Drittanbieter-Static-Analyser im Stack.
Outputs: Job Summary, Inline-Annotations, SARIF.

**Stand seit v1.0.0 (2026-05-07):** Phase-1-Cppcheck-Wrapper-Code
wurde mit dem Cut-Over entfernt; die Engine ist die alleinige
Implementation. Tag `v0.1.0` und das ältere ghcr-Image bleiben als
historisches Backup verfügbar.

**Architektur-Memo:** `_org/architecture/csa26.md` (im _org-Repo) —
**Ground Truth.** Bei Konflikt mit dieser Datei oder mit
`HANDOVER.md` gilt das Architektur-Memo.

**Live-Ziel:** GitHub Marketplace. Kein Web-Service in Phase 1, keine
Subdomain.

**Aktueller Stand:** v0.1-Bootstrap. Action-Skelett, Dockerfile und
Python-Wrapper sind das aktuelle Arbeitsfeld.

## Bewusste Stack-Abweichungen vom Default-Pattern

Das Default-Pattern (`_org/bootstrap/CLAUDE.template.md`) ist
C++17 + CMake + FastAPI + Postgres + VPS. csa26 weicht ab:

- **Sprache:** Python 3.12 statt C++17 — Phase-1-Prototyp-
  Geschwindigkeit. C++-Reimplementierung ggf. in Phase 2.
- **Auslieferung:** GitHub Action statt Web-Service. Kein FastAPI,
  kein Postgres, kein VPS-Deploy in Phase 1.
- **Sichtbarkeit:** Repo **public** — Marketplace setzt Public voraus,
  außerdem ist „der Wrapper-Code ist sichtbar" ein Trust-Signal im
  Safety-Markt.
- **Kein User-Account-System.** Beta-Tester-Policy in Phase 1 nicht
  anwendbar.
- **Kein LLM** — auch nicht opt-in. Determinismus ist Produkt-
  Kernversprechen.

Phase 2 (offen, nach Discovery-Validierung) bringt potenziell
C++-Reimplementierung + teq18-Self-Qualifikation + optional Web-
Dashboard.

## MISRA-Lizenz-Pattern — zwingend einhalten

Klare Trennung:

**Erlaubt** (Cppcheck-Präzedenz, nominative fair use):
- Tool-Doku, README, Marketplace-Listing dürfen sagen „prüft
  MISRA-C:2012-Regeln"
- Output zeigt Rule-IDs („MISRA C:2012 Rule 8.13")
- Output zeigt **eigene Umschreibung** der Regel + **eigenes**
  Code-Beispiel

**Verboten** (Urheberrecht / Markenrecht):
- Tool-Name darf MISRA NICHT enthalten (deshalb csa26)
- **Wortgetreuer MISRA-Rule-Text darf nirgends vorkommen** — nicht im
  Repo, nicht in Action-Logs, nicht in Reports, nicht in der Doku,
  nicht in Quellcode-Kommentaren
- „MISRA-zertifiziert" / „MISRA-compliant" als Marketing-Aussage

Pro Regel: 1–2 Sätze eigene Beschreibung + ein eigenes Mini-
Code-Beispiel. Asset unter `rules/`.

## Output-Mechanik (Default-Kombi für v0.1)

Drei parallele Outputs aus einem Cppcheck-Lauf:

1. **Job Summary** in `$GITHUB_STEP_SUMMARY` — Markdown-Tabelle,
   Funde nach Severity gruppiert.
2. **Inline-Annotations** über `echo "::warning file=path,line=N::msg"`
   — gelbe Marker im PR-Diff.
3. **SARIF-Datei** `csa26.sarif` im Workspace —
   `actions/upload-sarif`-Step lädt sie in den Security-Tab.

Optional in v0.2: Artifact-Upload (volle JSON-Daten), Markdown-
Report-Commit zurück ins Kunden-Repo (opt-in).

## Was NICHT bauen in Phase 1

- VS-Code-Extension (evtl. Phase 2)
- Web-API auf appliedfusa.de oder Subdomain
- License-Server / Paywall (Phase 1 frei)
- User-Accounts, Magic-Link-Auth, Postgres
- LLM-Integration (auch nicht opt-in)
- Tool-Qualifikations-Anspruch in Doku oder Output

## Branding und Sprache

- **Tool-Name in Prosa:** lowercase (`csa26`), auch am Satzanfang.
  Standard-Begriffe (ISO 26262, MISRA, SARIF) bleiben in Caps.
- **README:** DE primär, EN sekundär — beide nötig wegen
  internationaler Marketplace-Discovery.
- **Code-Kommentare / Dev-Doku:** Default Deutsch.
- **Tool-Output (Action-Logs, Job Summary, SARIF-Texte):** Englisch
  — passt zur GitHub-Action-Ergonomie und zur internationalen
  Zielgruppe.
- **Umlaute:** in neuen Dateien native Umlaute (ü, ö, ä, ß).

## Cross-Repo-Workflow (Erinnerung)

Alle Requests, die über dieses Repo hinausgehen, laufen über
`_org/cross-repo-requests/`. Vorbereitete Drafts für csa26:

- **Trust-Block** (`...-csa26-trust-block.md`): senden, sobald
  v0.1-Substanz im Repo steht.
- **Produkt-Karte** (`...-csa26-produkt-karte.md`): senden, sobald
  Marketplace-Listing live ist (URL nötig).

Nicht direkt in landing schreiben. Nicht GUI-Layout für Phase-2-Web-
Dashboard selbst festlegen.

## Branch Protection / CI

- Wolfgang ist Solo-Entwickler — Require-PR ist Friction. Default:
  No-Force-Push auf `main`.
- Eigene CI-Workflows (`.github/workflows/test.yml`, `lint.yml`)
  können später als Required-Status-Checks geschaltet werden.
- Apache-2.0-Lizenz-Header in Source-Files NICHT zwingend (NOTICE
  deckt es global). Wenn doch, dann minimal (max. 3 Zeilen).

## Versionierung (GitHub-Action-Konvention)

- Semver-Tags: `v0.1.0`, `v0.1.1`, …
- Rolling-Branch `v0` zeigt immer auf den neuesten Patch — Kunden
  pinnen `@v0` und kriegen Patches automatisch.
- Container-Image: `ghcr.io/appliedfusa/csa26:vX`.

## Wichtige Verweise

- **Repo:** https://github.com/AppliedFuSa/csa26
- **Architektur-Memo (Ground Truth):** `_org/architecture/csa26.md`
- **Markt-Memo:** `_org/research/2026-05-06-misra-tool-market.md`
- **Schwester-Tool teq18 (Action-Distributions-Pattern):**
  `_org/architecture/teq18.md`
- **Default-Stack-Pattern:** `_org/bootstrap/CLAUDE.template.md`
