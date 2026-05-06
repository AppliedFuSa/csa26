# csa26 — MISRA-C:2012 Pre-Audit-Check als GitHub Action

> **Status:** v0.1-Prototyp — Phase 1 / Konzept-Validierung. Frei,
> Open Source (Apache-2.0), öffentlich auf dem GitHub Marketplace.
> Nicht produkt-zertifiziert, nicht tool-qualifiziert.

csa26 prüft embedded-C-Quellcode bei jedem Push gegen die
MISRA-C:2012-Regeln. Die Action läuft in der GitHub-CI Ihres eigenen
Repositorys, schreibt Findings als Inline-Annotations in den Pull
Request, eine Übersicht ins Action-Job-Summary und optional eine
SARIF-Datei in den Security-Tab.

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
        uses: AppliedFuSa/csa26@v0
        with:
          src-dir: .
          rule-set: misra-c-2012
          severity-threshold: style

      - name: Upload SARIF nach Security-Tab
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: csa26.sarif
```

Das war es. Nach dem ersten Push erscheinen Findings im PR und im
Action-Tab.

### Action-Inputs

| Input | Default | Beschreibung |
|---|---|---|
| `src-dir` | `.` | Verzeichnis im Repo, das geprüft wird |
| `rule-set` | `misra-c-2012` | Aktuell einziger unterstützter Wert |
| `severity-threshold` | `style` | Mindest-Severity, ab der Findings gemeldet werden: `error` < `warning` < `style` < `performance` < `portability` < `information` |
| `fail-on-findings` | `false` | Wenn `true`, schlägt die Action bei mindestens einem Finding fehl |

### Outputs

- **Job Summary** im Action-Tab (Markdown-Tabelle, Funde nach Severity gruppiert)
- **Inline-Annotations** im PR-Diff (gelbe Marker an betroffenen Zeilen)
- **SARIF-Datei** `csa26.sarif` im Workspace (mit `actions/upload-sarif` in den Security-Tab)

---

## Quick start (English)

Add a workflow file `.github/workflows/csa26.yml` to your repo:

```yaml
name: csa26

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write   # only required for SARIF upload

jobs:
  misra-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: csa26 — MISRA-C:2012 pre-audit
        uses: AppliedFuSa/csa26@v0
        with:
          src-dir: .
          rule-set: misra-c-2012
          severity-threshold: style

      - name: Upload SARIF to security tab
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: csa26.sarif
```

That's it. After the first push, findings appear in the pull request
and in the action tab.

### Action inputs

| Input | Default | Description |
|---|---|---|
| `src-dir` | `.` | Directory to analyse |
| `rule-set` | `misra-c-2012` | Currently the only supported value |
| `severity-threshold` | `style` | Minimum severity to report |
| `fail-on-findings` | `false` | Fail the workflow if any finding is reported |

---

## Was csa26 ist und was nicht

**csa26 ist ein Pre-Audit-Werkzeug.** Es findet wahrscheinliche
MISRA-C:2012-Regelverletzungen in Ihrem Code und macht sie im Pull
Request sichtbar. Es **ersetzt keine offizielle Compliance-
Bewertung** gegenüber MISRA-C:2012; der formale Compliance-Nachweis
bleibt Aufgabe Ihres Safety-Managers.

csa26 ist außerdem **nicht tool-qualifiziert nach ISO 26262-8** in
Phase 1. Wenn Sie csa26 in einem qualifizierten Tool-Lebenszyklus
einsetzen wollen, müssen Sie die Tool-Confidence-Argumentation selbst
führen. Eine Self-Qualifikation via teq18 ist Phase-2-Roadmap, nicht
v0.1.

## MISRA-Hinweis

MISRA und MISRA C sind eingetragene Marken von The MISRA Consortium
Limited. csa26 ist **nicht mit dem MISRA-Konsortium verbunden, von
diesem nicht unterstützt und nicht zertifiziert**. Die Erwähnung von
MISRA-C:2012 in dieser Doku, im Tool-Output und im Marketing ist
faktischer Sachhinweis (nominative fair use). csa26 redistribuiert
**keinen wortgetreuen MISRA-Rule-Text** — die Regel-Beschreibungen im
Output sind eigenständige Paraphrasen der csa26-Maintainer. Details
in [NOTICE](NOTICE).

## Coverage und Grenzen

csa26 wrappt das offizielle Cppcheck-MISRA-Addon. Die abgedeckten
Regeln entsprechen dem, was dieses Addon prüft — eine vollständige
Liste mit dem konkreten Mapping pflegen wir unter
[`rules/`](rules/) im Repo. Regeln, die das Addon nicht abdeckt,
werden auch von csa26 nicht abgedeckt; dort ergänzt typischerweise
Cppcheck Premium oder eine Enterprise-Suite.

In v0.1 werden Findings mit Rule-IDs und einer kurzen eigenen
Paraphrase ausgegeben; der Ausbau der pro-Regel-Beschreibungen läuft
parallel und kommt mit v0.2 in vollem Umfang.

## Sub-Prozessoren / Datenfluss

- **GitHub (Microsoft):** stellt den CI-Runner und das Container-
  Registry-Hosting für das csa26-Action-Image. Datenverarbeitung nach
  den Bedingungen Ihres GitHub-Vertrags.
- **Keine weiteren Sub-Prozessoren** in Phase 1.

Applied FuSa speichert keine Daten über csa26-Läufe in Phase 1.
Findings, SARIF-Reports und Annotations bleiben vollständig in Ihrem
GitHub-Repo unter Ihrer Kontrolle.

## Lizenz

[Apache-2.0](LICENSE) — siehe auch [NOTICE](NOTICE) für die
Trademark- und Pre-Audit-Hinweise.

## Bezug

Hauptsächlicher Auslieferungs-Kanal: **GitHub Marketplace**
(Listing-Link folgt mit dem v0.1.0-Release).

Repo: <https://github.com/AppliedFuSa/csa26>
