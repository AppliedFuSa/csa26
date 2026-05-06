# csa26 — Release-Vorgehen

Phase-1-Konvention. Setzt voraus, dass `main` grün ist (CI lint +
pytest + image-build + self-smoketest).

## Vor dem Tag

1. `CHANGELOG.md` — `[Unreleased]`-Block schließen, neue
   Versionsüberschrift `[X.Y.Z] — YYYY-MM-DD` einsetzen, Vergleichs-
   Links unten ergänzen.
2. `pyproject.toml` — `version = "X.Y.Z"` setzen.
3. `src/csa26/__init__.py` — `__version__ = "X.Y.Z"` setzen.
4. Commit `release: vX.Y.Z`.

## Tag + Image

```bash
git tag -a vX.Y.Z -m "csa26 vX.Y.Z"
git push origin vX.Y.Z

# Rolling-Branch v0/v1 nach Action-Konvention
git push origin vX.Y.Z:refs/heads/v0   # v0 = aktueller Major
```

Das Container-Image baut der `release.yml`-Workflow (TBD) auf
`workflow_dispatch` oder `push: tags`-Trigger und pusht nach
`ghcr.io/appliedfusa/csa26:X.Y.Z` plus den Major-Tag.

> **Phase-1-Vereinfachung:** action.yml verweist aktuell auf
> `image: 'Dockerfile'` — GitHub baut das Image bei jedem Aktions-
> Lauf neu. Sobald das ghcr-Image steht, lohnt sich der Wechsel auf
> `image: 'docker://ghcr.io/appliedfusa/csa26:vX'` für deutlich
> schnellere Aktions-Starts beim Kunden.

## Marketplace-Submission (einmalig vor v0.1.0)

GitHub-UI: Repo → Releases → Draft new release → „Publish this Action
to the GitHub Marketplace". Felder:

- Primary category: **Code quality**
- Secondary category: **Continuous integration**
- Logo: Platzhalter OK für v0.1.
- Beschreibung: aus README.md DE/EN-Schnellstart-Block extrahieren.

Nach Genehmigung: Marketplace-URL in `_org/README.md`-Repo-Tabelle
nachtragen und den vorbereiteten CRR „Produkt-Karte" an landing
versenden (siehe `_org/cross-repo-requests/2026-05-06-org-landing-csa26-produkt-karte.md`).

## Patch-Releases

```bash
# vX.Y.Z+1 nach Bugfix-Merge
git tag -a vX.Y.Z+1 -m "csa26 vX.Y.Z+1"
git push origin vX.Y.Z+1

# v0 zeigt jetzt auf den Patch
git push origin -f vX.Y.Z+1:refs/heads/v0
```

`-f` auf `v0` ist hier OK (Rolling-Branch nach Action-Konvention),
auf `main` weiterhin nicht.
