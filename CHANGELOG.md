# Changelog

Alle wesentlichen Änderungen an csa26 werden hier dokumentiert.

Format orientiert sich lose an [Keep a Changelog](https://keepachangelog.com/);
Versionen folgen [Semver](https://semver.org/lang/de/).

## [Unreleased]

## [0.1.0] — 2026-05-07

Erste öffentliche Version. Public-Repo, Apache-2.0, GitHub-Action-
Distribution. Phase-1-Prototyp für Konzept-Validierung.

### Added

- Bootstrap des Repos: `LICENSE` (Apache-2.0), `NOTICE` (MISRA-Disclaimer +
  Pre-Audit-Abgrenzung).
- `action.yml` als GitHub-Docker-Action mit Inputs `src-dir`,
  `rule-set`, `severity-threshold`, `fail-on-findings`, `sarif-output`,
  `include-paths`, `defines`, `undefines` und Outputs `sarif-file`,
  `finding-count`. Newline-separierte Multiline-Inputs für reale
  Vendor-SDK-Setups.
- `Dockerfile` auf Basis `python:3.12-slim` mit Cppcheck (apt) und dem
  passenden Addons-Tarball aus dem Cppcheck-Upstream-Repo, version-
  synchron zur installierten Cppcheck-Version.
- Python-Wrapper unter `src/csa26/`: Cppcheck-Aufruf, XML-Parsing, drei
  Outputs (Job Summary, Inline-Annotations, SARIF 2.1.0).
- MISRA-only-Filterung: Cppcheck-Built-in-Findings (`nullPointer`,
  `constParameterPointer`, …) werden verworfen. csa26 ist gezielt
  MISRA-Pre-Audit.
- Annotation-Message beginnt mit `[<rule-id>]`-Prefix, damit Reviewer
  im PR-Diff die Regel sofort sehen.
- Hard-Wraps in Regel-Markdown-Dateien werden zu Leerzeichen
  kollabiert (verhindert mehrzeilige Annotations).
- Pflege-Asset für eigene Regel-Paraphrasen unter `rules/c2012/` (Format-
  Spec + zwei Beispiele für 8.13 und 2.7).
- Pytest-Test-Suite mit 40 Tests (Severity-Ordering, XML-Parser,
  Cppcheck-Args, SARIF-Builder, Annotation-Format, Rules-Lookup,
  Config-Defaults inkl. Multiline-Inputs, MISRA-Filter).
- CI-Workflows: `test` (Lint + Pytest + Image-Build), `self-smoketest`
  (csa26 läuft gegen die eingebaute C-Fixture mit SARIF-IDs-Check),
  `release` (tag-getriggert: ghcr-Image-Build und vN-Branch-Patch).
- `docs/smoketest.md` mit Drei-Ebenen-Smoketest-Konzept,
  `docs/release.md` mit Tag-Prozedur.

[Unreleased]: https://github.com/AppliedFuSa/csa26/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AppliedFuSa/csa26/releases/tag/v0.1.0
