# Beiträge zu csa26

Vielen Dank für Dein Interesse an csa26. csa26 ist ein
freiberufliches Solo-Projekt von Wolfgang Freese / Applied FuSa
mit klarem Phase-1-Scope — entsprechend strukturiert die Beitrags-
Aufnahme.

## Was csa26 v1.x macht und was nicht

csa26 v1 prüft ein **bewusst gewähltes Subset von 20 FuSa-priorisierten
MISRA-C:2012-Rules**. Die Auswahl steht in der README. Das Subset
ist Phase-1-Scope und **eingefroren** — wir nehmen während Phase 1
keine zusätzlichen Rules in v1.x auf, weil das laufende Discovery-
Validierungs-Phase ist.

Was wir gerne aufnehmen:
- **Reproduzierbare Bugs**: falsche Findings, Crashes, kaputter
  SARIF-Output, Kompatibilitäts-Probleme mit realen Embedded-Codebases
- **Frontend-Robustheits-Lücken**: C-Konstrukte, an denen die Engine
  scheitert (mit Minimal-Repro)
- **Dokumentations-Verbesserungen**: README-, FAQ-, usage-md-Ergänzungen

Was als Issue/Discussion willkommen, aber nicht zwingend in v1.x
landet:
- **Zusätzliche Rule-Vorschläge**: gerne dokumentieren, wir
  priorisieren danach für Phase 2 / v2.x
- **Output-Format-Erweiterungen**: gerne diskutieren

## Bevor Du einen Pull-Request öffnest

**Bitte zuerst ein Issue öffnen** und die Änderung dort skizzieren.
Solo-Maintainer-Projekte können keine PRs ohne vorherige Diskussion
sinnvoll betreuen — wir möchten Dir nicht 200 LoC review-Aufwand
schenken, um dann „passt nicht in den Phase-1-Scope" sagen zu müssen.

## Build & Test lokal

```bash
cd engine
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check .
ruff format --check .
```

Alle Tests müssen grün bleiben (CI prüft das ohnehin).

## Coding-Konventionen

- **Sprache der Implementierung**: Python 3.12, Type-Annotations,
  dataclasses bevorzugt.
- **Coding-Style**: `ruff format` (automatisch im CI geprüft).
- **Code-Kommentare**: Default Deutsch, wenn das Konzept FuSa-/
  Domänen-spezifisch ist; Englisch, wenn rein technisch.
- **Tool-Output (Logs, Annotations, SARIF, Job Summary)**: Englisch.
- **Tests**: pytest, ein Test pro Verhaltens-Aspekt, nicht pro
  Implementierungs-Detail.

## MISRA-Lizenz-Hygiene (zwingend)

Beiträge dürfen **keinen wortgetreuen MISRA-Rule-Text** enthalten —
nicht in Code-Kommentaren, nicht in Doku, nicht in Test-Fixtures,
nicht in Output-Strings. Eigene Paraphrasen (1–2 Sätze) sind OK.
Mehr Kontext im [NOTICE](NOTICE).

## Lizenz

Beiträge stehen unter [Apache-2.0](LICENSE) — durch das Öffnen eines
Pull-Requests bestätigst Du, dass Dein Beitrag unter diesen
Bedingungen aufgenommen werden kann.
