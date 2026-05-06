# csa26 — Übergabe-Notiz

**Adressat:** csa26-Chat (frisch gestartet im csa26-Repo)
**Absender:** _org-Chat
**Datum:** 2026-05-06
**Zweck:** Du übernimmst die Implementierung von csa26. Diese Notiz
liefert alles, was du brauchst, ohne dass Wolfgang dir die Bootstrap-
Geschichte nochmal erzählen muss.

## Was ist csa26?

GitHub-Action-natives **Pre-Audit-Werkzeug für MISRA-C:2012**.
Wrapper über Cppcheck mit MISRA-Addon, Output als Job Summary +
Inline-Annotations + SARIF. Zielgruppe: KMU/Mittelstand-Embedded-
Häuser ohne Budget für Helix QAC / Polyspace / LDRA. Phase-1-Prototyp
zur Konzept-Validierung — nicht produktreif, nicht qualifiziert.

Name = "C Static Analysis ISO 26262" (Norm-Suffix-Pattern wie
teq18). Ohne MISRA-Bezug im Tool-Namen aus Markenrechts-Gründen.

## Stand bei Übergabe (2026-05-06)

- ✅ Repo `AppliedFuSa/csa26` angelegt, **public**, leer
- ✅ Lizenz-Entscheidung: **Apache-2.0** (LICENSE + NOTICE in diesem
  Repo committed beim Bootstrap-Push)
- ✅ Architektur-Memo im _org-Repo: `_org/architecture/csa26.md`
- ✅ Markt-Memo im _org-Repo:
  `_org/research/2026-05-06-misra-tool-market.md`
- ✅ Infrastruktur, Kosten, Repo-Tabelle in _org aktualisiert
- ✅ Cross-Repo-Requests an Landing-Chat **vorbereitet** (nicht
  versendet — siehe „Wann CRRs senden" unten)
- ⏳ **Repo-Skelett, action.yml, Dockerfile, Python-Wrapper, README,
  CLAUDE.md** — deine Aufgaben

## Ground Truth — zwingend lesen, in dieser Reihenfolge

1. `_org/architecture/csa26.md` — alle Architektur-Entscheidungen,
   die Wolfgang und ich getroffen haben. Wenn dort etwas anders steht
   als hier, gilt das Architektur-Memo.
2. `_org/research/2026-05-06-misra-tool-market.md` — Markt-Kontext,
   Pricing-Schätzungen, Discovery-Plan, teq18-Synergie.
3. `_org/bootstrap/CLAUDE.template.md` — Default-Stack des Applied-
   FuSa-Portfolios. csa26 weicht bewusst ab (siehe nächster
   Abschnitt).
4. `_org/architecture/teq18.md` — Schwester-Tool mit ähnlichem
   Distributions-Pattern (GitHub Action). Gute Referenz für
   action.yml-Aufbau, Output-Format, Versionierung.

## Bewusste Stack-Abweichungen vom Default

Das Applied-FuSa-Portfolio ist sonst C++17 + CMake + FastAPI + Postgres
+ VPS. csa26 weicht ab:

- **Sprache:** Python 3.12 statt C++17 — Phase-1-Prototyp-
  Geschwindigkeit. Tage statt Wochen für ersten lauffähigen Stand.
- **Auslieferung:** GitHub Action statt Web-Service. Kein FastAPI,
  kein Postgres, kein VPS-Deploy in Phase 1.
- **Sichtbarkeit:** **Public** statt Privat-Default. GitHub Marketplace
  setzt Public voraus.
- **Kein User-Account-System.** Beta-Tester-Policy
  (`_org/policies/beta-tester-access.md`) nicht anwendbar.
- **Kein LLM** — nicht einmal opt-in. Determinismus ist Produkt-
  Kernversprechen, konsistent mit teq18 / mcsa / fmea / safety-case.

Phase 2 (offen, nach Discovery-Validierung) bringt C++-Reimplementierung
+ teq18-Self-Qualifikation + optional Web-Dashboard. Das ist nicht
deine Aufgabe.

## MISRA-Lizenz-Pattern — zwingend einhalten

Der einzige Bereich, in dem wir uns ein Eigentor schießen können.
Klare Regeln aus der Diskussion zwischen Wolfgang und _org-Chat:

**Erlaubt** (Cppcheck-Präzedenzfall, nominative fair use):
- Tool-Doku, README, Marketplace-Listing dürfen sagen „prüft
  MISRA-C:2012-Regeln"
- Output zeigt Rule-IDs („MISRA C:2012 Rule 8.13")
- Output zeigt **eigene Umschreibung** der Regel in eigenen Worten
- Output zeigt **eigene** Code-Beispiele

**Verboten** (Urheberrecht / Markenrecht):
- Tool-Name darf MISRA NICHT enthalten (deshalb csa26, nicht
  „MisraCheck")
- **Wortgetreuer MISRA-Rule-Text darf nirgends vorkommen** —
  nicht im Repo, nicht in Action-Logs, nicht in Reports, nicht in
  der Doku, nicht in Kommentaren im Quellcode
- „MISRA-zertifiziert" / „MISRA-compliant" als Marketing-Aussage
  ohne offizielle Lizenz

**Aufgabe pro Regel:** 1–2 Sätze eigene Beschreibung schreiben +
1 kleines eigenes Code-Beispiel. Aufwand für die ~140
MISRA-C:2012-Regeln, die das Cppcheck-Addon abdeckt: 1–2 Tage
konzentrierte Schreibarbeit. Pflege diese Beschreibungen als
gepflegtes Tool-Asset unter `rules/` im Repo.

## Erste konkrete Tasks (in dieser Reihenfolge)

1. **Repo-Grundgerüst:**
   - `.gitignore` für Python (`__pycache__/`, `.venv/`, `*.pyc`,
     `.env`, `.env.*`, Editor-Metadaten)
   - `README.md` (DE primär, EN sekundär — beide nötig wegen
     internationaler Marketplace-Discovery). Inhalt: Tool-Zweck,
     Workflow-Beispiel zum Copy-Paste, MISRA-Lizenz-Hinweis,
     Verweis auf NOTICE
   - `CLAUDE.md` aus `_org/bootstrap/CLAUDE.template.md` kopieren
     und mit csa26-Spezifika füllen
2. **`action.yml`** — Composite-Action, die einen Docker-Container
   ausführt. Inputs: `src-dir` (default `.`), `rule-set` (default
   `misra-c-2012`), `severity-threshold` (default `style`).
3. **`Dockerfile`** — Basis `python:3.12-slim`, installiert
   Cppcheck + sein MISRA-Addon, kopiert den Wrapper-Code, setzt
   ENTRYPOINT.
4. **Python-Wrapper** unter `src/csa26/`:
   - Ruft Cppcheck mit dem MISRA-Addon auf den `src-dir` auf
   - Parst Cppcheck-XML- oder JSON-Output
   - Mappt jede Finding auf eine eigene Regel-Beschreibung aus
     `rules/`
   - Schreibt drei Outputs: Job Summary
     (`$GITHUB_STEP_SUMMARY`), Inline-Annotations
     (`::warning file=...`), SARIF-Datei (`csa26.sarif`)
5. **GitHub Action `actions/upload-sarif`-Step im action.yml**
   für GitHub-Security-Tab-Integration.
6. **Smoketest auf einem öffentlichen C-Test-Repo.** Vorschlag:
   ein kleines Standalone-Test-Repo `AppliedFuSa/csa26-testfixture`
   mit absichtlich MISRA-verletzendem C-Code, gegen das wir die
   Action laufen lassen. Alternative: ein bekanntes Embedded-
   Beispiel auf GitHub.
7. **v0.1.0 taggen + `v0`-Branch anlegen** (rollender Patch-Update-
   Pin für Kunden, GitHub-Action-Konvention).
8. **Marketplace-Listing einreichen** — Logo, Kategorie
   („Code quality"), Beschreibung. Logo kann ein simpler Platzhalter
   sein, blockiert v0.1 nicht.

## Was NICHT bauen in Phase 1

- VS-Code-Extension (kommt evtl. in Phase 2)
- Web-API auf appliedfusa.de oder Subdomain (in Markt-Recherche
  als unrealistisch bewertet)
- License-Server / Paywall (Phase 1 ist frei)
- User-Accounts, Magic-Link-Auth, Postgres
- LLM-Integration (auch nicht opt-in)
- Tool-Qualifikations-Anspruch in Doku oder Output (siehe Disclaimer
  in NOTICE und im Architektur-Memo)

## Output-Mechanik (Default-Kombi für v0.1)

Drei parallele Outputs aus einem Cppcheck-Lauf:

1. **Job Summary** in `$GITHUB_STEP_SUMMARY`:
   Markdown-Tabelle, Funde nach Severity gruppiert, Total-Zähler oben.
2. **Inline-Annotations** über `echo "::warning file=path,line=N::msg"`:
   Erscheinen direkt im PR-Diff als gelbe Marker.
3. **SARIF-Upload** über `actions/upload-sarif@v3`: Erscheint im
   „Security"-Tab des Repos, integriert mit GitHub Code Scanning.

Optional in v0.2:
- Artifact-Upload (volle JSON-Daten zum Download)
- Markdown-Report-Commit zurück ins Kunden-Repo
  (`reports/csa26-latest.md`) — opt-in, eigene Permission

## Branch Protection / CI

- Wolfgang ist Solo-Entwickler — Require-PR ist Friction. Default:
  No-Force-Push auf main, sonst nichts.
- Wenn du CI-Workflows anlegst (`.github/workflows/test.yml`,
  `lint.yml`), kannst du diese später als Required-Status-Checks
  schalten via `gh api repos/AppliedFuSa/csa26/branches/main/protection`.
- Apache-2.0-Lizenz-Header in Source-Files ist NICHT zwingend
  (Apache erlaubt das Weglassen, NOTICE deckt es global). Wenn du
  Header willst, halte sie minimal (3 Zeilen).

## Discovery-Plan (läuft parallel, NICHT deine Aufgabe)

Wolfgang wird parallel 5–8 Discovery-Gespräche mit DACH-Mittelstand-
Embedded-FuSa-Managern führen. Go-Schwelle für Phase-2-Investition:

- ≥3 von 8 Gesprächen mit klarem „würde ich kaufen"
- **plus** zweistellige Marketplace-Installs in den ersten 4 Wochen
  nach Veröffentlichung

Discovery liegt im _org-Chat. Du fokussierst auf Implementierung —
wenn Wolfgang Discovery-Ergebnisse einspielt, könnten sich Roadmap-
Prioritäten verschieben. Bis dahin: stick to v0.1 wie spezifiziert.

## Wann die Cross-Repo-Requests an Landing senden

Zwei Drafts liegen bereit unter `_org/cross-repo-requests/`:

- **Trust-Block** (`...-csa26-trust-block.md`): senden, sobald
  v0.1-Substanz im csa26-Repo steht. Kunden müssen verstehen, dass
  ihr Code das Repo nicht verlässt — das ist ein Verkaufs-Argument.
- **Produkt-Karte** (`...-csa26-produkt-karte.md`): senden, sobald
  Marketplace-Listing live ist. Karte verlinkt direkt aufs Listing,
  also brauchen wir die URL.

Beide haben Status „vorbereitet — nicht versendet". Du:
1. Status auf „offen" ändern
2. Inhalt der Datei in den Landing-Chat kopieren
3. Landing-Chat arbeitet ab und meldet Commit-Hash zurück
4. Du setzt Status auf „erledigt" und ergänzt den Hash

## Wichtige Verweise

- **Repo:** https://github.com/AppliedFuSa/csa26
- **Architektur-Memo:** `_org/architecture/csa26.md`
- **Markt-Memo:** `_org/research/2026-05-06-misra-tool-market.md`
- **CRR Trust-Block:**
  `_org/cross-repo-requests/2026-05-06-org-landing-csa26-trust-block.md`
- **CRR Produkt-Karte:**
  `_org/cross-repo-requests/2026-05-06-org-landing-csa26-produkt-karte.md`
- **Schwester-Tool teq18 (Norm-Suffix-Pattern, Action-Distribution,
  Phase-2-Self-Qualifikation):** `_org/architecture/teq18.md`
- **Default-Stack-Pattern (zur Erklärung der Abweichungen):**
  `_org/bootstrap/CLAUDE.template.md`
- **Bootstrap-Checkliste (zur Orientierung über _org-seitige
  Schritte, größtenteils erledigt):**
  `_org/bootstrap/new-project-checklist.md`

## Wenn du den Bootstrap abgeschlossen hast

- Update Status in der `project_csa26_bootstrap.md`-Memory im
  _org-Folder auf „v0.1 in Arbeit" oder „v0.1 released"
- Trag den Marketplace-Listing-Link im _org-Repo nach
  (`_org/README.md` Repo-Tabelle, Live-URL-Spalte)
- Lösche bei Bedarf diese HANDOVER.md aus dem csa26-Repo (sie ist
  Übergabe-Artefakt, nicht laufende Doku)

Viel Erfolg.
