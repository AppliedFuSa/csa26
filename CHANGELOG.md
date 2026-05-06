# Changelog

Alle wesentlichen Änderungen an csa26 werden hier dokumentiert.

Format orientiert sich lose an [Keep a Changelog](https://keepachangelog.com/);
Versionen folgen [Semver](https://semver.org/lang/de/).

## [Unreleased]

### Added

- Bootstrap des Repos: `LICENSE` (Apache-2.0), `NOTICE` (MISRA-Disclaimer +
  Pre-Audit-Abgrenzung), `HANDOVER.md` (übergangsweise).
- `action.yml` als GitHub-Docker-Action mit Inputs `src-dir`,
  `rule-set`, `severity-threshold`, `fail-on-findings`, `sarif-output`
  und Outputs `sarif-file`, `finding-count`.
- `Dockerfile` auf Basis `python:3.12-slim` mit Cppcheck + MISRA-Addon.
- Python-Wrapper unter `src/csa26/`: Cppcheck-Aufruf, XML-Parsing,
  drei Outputs (Job Summary, Inline-Annotations, SARIF 2.1.0).
- Pflege-Asset für eigene Regel-Paraphrasen unter `rules/c2012/`
  (Format-Spec + zwei Beispiele für 8.13 und 2.7).
- Pytest-Test-Suite (Severity-Ordering, XML-Parser, SARIF-Builder,
  Annotation-Format, Rules-Lookup, Config-Defaults).
- CI-Workflows: `test` (Lint + Pytest + Image-Build) und
  `self-smoketest` (csa26 läuft gegen die eingebaute C-Fixture).
- `docs/smoketest.md` mit Drei-Ebenen-Smoketest-Konzept.

## [0.1.0] — geplant

Erste öffentliche Version. Marketplace-Listing-Einreichung folgt.

[Unreleased]: https://github.com/AppliedFuSa/csa26/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AppliedFuSa/csa26/releases/tag/v0.1.0
