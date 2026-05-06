# csa26 — Smoketest-Konzept

Drei Ebenen, von schnell zu realistisch:

## 1) Eingebaute Fixture im csa26-Repo

Pfad: [`tests/fixtures/c-sample/`](../tests/fixtures/c-sample/)

Mini-`main.c` mit ein paar bewusst MISRA-verletzenden Mustern. Wird
von [`.github/workflows/self-smoketest.yml`](../.github/workflows/self-smoketest.yml)
bei jedem Push auf `main` und auf jeden PR ausgeführt. Zweck:

- End-to-End-Test, dass `Dockerfile` + `action.yml` + Wrapper
  zusammenspielen.
- Fängt Regressions wie „Cppcheck-Aufruf wirft einen anderen
  Returncode" oder „SARIF-JSON ist syntaktisch kaputt".
- Soll sehr schnell laufen (< 1 Min Wallclock).

Schwäche: zu klein, deckt keine realistische Code-Basis ab.

## 2) Separates Test-Repo `AppliedFuSa/csa26-testfixture`

**Status:** geplant, noch nicht angelegt.

Anlegen, wenn v0.1-Substanz im csa26-Repo steht und das erste
ghcr-Image gepusht wurde. Inhalt:

- Mehrere `.c`-Dateien mit unterschiedlichen Verletzungs-Mustern,
  organisiert nach groben Themen (Pointer/Const, Implicit-Conversion,
  Funktions-Hygiene, Control-Flow).
- `.github/workflows/csa26.yml`, der `AppliedFuSa/csa26@v0` einbindet
  und den Standard-User-Setup demonstriert.

Zweck: realistischere Smoketest-Basis, gleichzeitig Live-Demo für
Discovery-Gespräche (Auditor zeigt das Repo auf, sieht Findings im
Action-Tab + Security-Tab).

Anlege-Trigger: nach erstem grünen `self-smoketest`-Lauf gegen das
eigene Image.

## 3) Manueller Lauf gegen ein bekanntes Embedded-Beispiel

Auch als Discovery-Asset wertvoll: csa26 gegen ein populäres
Embedded-Open-Source-Repo laufen lassen (z.B. eine kleine
Mikrocontroller-Lib aus einer Vendor-SDK). Resultate als
Markdown-Report festhalten.

**Nicht** automatisieren in v0.1 — manuell, dokumentarisch. Für
Phase-2-Discovery interessant, weil Auditoren reale Befund-Zahlen
sehen wollen.

## Lokal smoketesten ohne GitHub

```bash
# Image bauen
docker build -t csa26:dev .

# Gegen die eingebaute Fixture laufen lassen
docker run --rm \
    -v "$(pwd)":/github/workspace \
    -e GITHUB_WORKSPACE=/github/workspace \
    -e CSA26_SRC_DIR=tests/fixtures/c-sample \
    -e CSA26_SEVERITY_THRESHOLD=style \
    csa26:dev

# SARIF anschauen
cat csa26.sarif | jq .runs[0].results
```

`GITHUB_STEP_SUMMARY` und `GITHUB_OUTPUT` werden lokal nicht
gesetzt — die entsprechenden Outputs erscheinen dort dann nicht,
aber Annotations und SARIF werden trotzdem geschrieben.
