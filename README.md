# csa26 — MISRA-C:2012 Pre-Audit-Check als GitHub Action

> **Status v1.0:** Eigenständige MISRA-C:2012-Analyse-Engine.
> Komplett Apache-2.0, kein Drittanbieter-Static-Analyser im Stack.
> Phase-1 (Cppcheck-Wrapper, v0.1.0) wurde mit dem Cut-Over zu v1.0.0
> ersetzt — der Tag bleibt als Backup verfügbar.

csa26 prüft embedded-C-Quellcode bei jedem Push gegen einen sorgfältig
ausgewählten Subset von **20 FuSa-priorisierten MISRA-C:2012-Regeln**.
Die Action läuft in der GitHub-CI Ihres eigenen Repositorys, schreibt
Findings als Inline-Annotations in den Pull Request, eine Übersicht ins
Action-Job-Summary und optional eine SARIF-Datei in den Security-Tab.

> **Ihr Quellcode verlässt Ihr Repo nicht.** Die Analyse passiert in
> einem Container, den GitHub auf Ihrem CI-Runner startet. Applied
> FuSa hat keinen Zugriff auf Ihren Code, keine Telemetrie zu Ihren
> Findings, keine Logs Ihrer Builds.

---

## Schnellstart (Deutsch)

Eine Datei `.github/workflows/csa26.yml` in Ihrem Repo anlegen:

```yaml
name: csa26

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write   # nur nötig für den SARIF-Upload

jobs:
  misra-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: csa26 — MISRA-C:2012 Pre-Audit
        uses: AppliedFuSa/csa26@v1
        with:
          src-dir: src
          severity-threshold: warning

      - name: Upload SARIF nach Security-Tab
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: csa26.sarif
```

### Action-Inputs

| Input | Default | Beschreibung |
|---|---|---|
| `src-dir` | `.` | Verzeichnis im Repo, das geprüft wird (rekursiv) |
| `rule-set` | `misra-c-2012` | Aktuell einziger unterstützter Wert |
| `severity-threshold` | `warning` | Mindest-Severity: `error`, `warning`, `note` |
| `fail-on-findings` | `false` | Wenn `true`, Workflow-Fail bei mindestens einem Finding |
| `include-paths` | `''` | Newline-separierte Liste von Include-Pfaden (relativ zum Repo-Root) |
| `defines` | `''` | Preprocessor-Defines, je `NAME` oder `NAME=VALUE` |
| `undefines` | `''` | Preprocessor-Symbole, die undefiniert werden sollen |
| `sarif-output` | `csa26.sarif` | Pfad für die SARIF-Datei |

### Outputs

- **Job Summary** im Action-Tab (Markdown-Tabelle, Funde nach Severity gruppiert)
- **Inline-Annotations** im PR-Diff
- **SARIF-Datei** für `actions/upload-sarif`

---

## Quick start (English)

```yaml
- uses: AppliedFuSa/csa26@v1
  with:
    src-dir: src
    include-paths: |
      vendor/cmsis/include
      src/include
    defines: |
      STM32F407xx
      USE_HAL_DRIVER
    severity-threshold: warning
```

The action exits zero unless `fail-on-findings: true` is set and at
least one finding is reported.

---

## Geprüfte Regeln (20 von 143 MISRA-C:2012-Regeln)

csa26 v1.0 implementiert ein FuSa-priorisiertes Subset, fokussiert
auf die Rule-Cluster, die in ASIL-/SIL-Audits am häufigsten
relevant sind:

| Cluster | Rules |
|---|---|
| Type-Safety | 10.1, 10.3, 10.4, 10.5, 10.8 |
| Control-Flow-Disziplin | 14.3, 14.4, 15.5, 15.7 |
| Pointer-Disziplin | 8.13, 11.3, 11.5, 18.4 |
| Funktions-Hygiene | 8.4, 8.7, 17.2, 17.7 |
| Toter/Unbenutzter Code | 2.1, 2.2, 2.5 |

Alle übrigen MISRA-Guidelines werden **nicht** von csa26 geprüft.
Die Auswahl war bewusst — siehe Architektur-Memo. Erweiterungen
folgen bei Bedarf in v1.x.

## Was csa26 ist und was nicht

**csa26 ist ein Pre-Audit-Werkzeug.** Es findet wahrscheinliche
MISRA-C:2012-Regelverletzungen in Ihrem Code und macht sie im PR
sichtbar. Es **ersetzt keine offizielle Compliance-Bewertung**
gegenüber MISRA-C:2012; der formale Compliance-Nachweis bleibt
Aufgabe Ihres Safety-Managers.

csa26 v1.0 ist außerdem **noch nicht tool-qualifiziert nach
ISO 26262-8**. Der Eigenbau-Pfad ist die Voraussetzung für die
geplante teq18-Self-Qualifikation in einer kommenden Version.

## MISRA-Hinweis

MISRA und MISRA C sind eingetragene Marken von The MISRA Consortium
Limited. csa26 ist **nicht mit dem MISRA-Konsortium verbunden, von
diesem nicht unterstützt und nicht zertifiziert**. Die Erwähnung von
MISRA-C:2012 in dieser Doku, im Tool-Output und im Marketing ist
faktischer Sachhinweis (nominative fair use). csa26 redistribuiert
**keinen wortgetreuen MISRA-Rule-Text** — die Regel-Beschreibungen im
Output sind eigenständige Paraphrasen der csa26-Maintainer.
Details in [NOTICE](NOTICE).

## Sub-Prozessoren / Datenfluss

- **GitHub (Microsoft):** stellt den CI-Runner und das Container-
  Registry-Hosting für das csa26-Action-Image. Datenverarbeitung
  nach den Bedingungen Ihres GitHub-Vertrags.
- **Keine weiteren Sub-Prozessoren.**

Applied FuSa speichert keine Daten über csa26-Läufe. Findings,
SARIF-Reports und Annotations bleiben vollständig in Ihrem
GitHub-Repo unter Ihrer Kontrolle.

## Lizenz

[Apache-2.0](LICENSE) — siehe auch [NOTICE](NOTICE).

## Repo-Struktur

- `engine/` — die csa26-Engine (Lexer, Preprocessor, Parser,
  Symbol/Type-System, Rules, Output, CLI). Eigenes Python-Package
  `csa26-engine`.
- `Dockerfile`, `action.yml` — die GitHub-Action, die `csa26-engine`
  als Console-Script aufruft.
- `.github/workflows/` — eigene CI-Workflows (engine-test,
  self-smoketest, release).
- `CHANGELOG.md`, `LICENSE`, `NOTICE` — Doku und Lizenz.

Repo: <https://github.com/AppliedFuSa/csa26>
