# Cross-Repo-Request

**Von:** csa26-Chat
**An:** _org-Chat (`AppliedFuSa/_org`) → weiter an landing-Chat (`AppliedFuSa/landing`)
**Datum:** 2026-05-10
**Betreff:** Produkt-Karte CTA-Switch — Marketplace-Listing ist live
**Status:** erledigt — siehe _org Commit `db35740`

> **Hinweis Wolfgang:** csa26-Chat hat keinen Schreibzugriff auf
> `_org` oder `landing`. Diese Datei liegt im csa26-Repo unter
> `docs/cross-repo-requests/`. Bitte den Inhalt in den _org-Chat
> kopieren — _org-Chat reicht weiter an landing-Chat oder gibt Dir
> die Schritte zum direkten Versand.

## Kontext

Im 2026-05-10-Trust-und-Produkt-CRR (erledigt, _org-Commit
`2108b4c`, landing-Commit `c5af7b8`) wurde die Produkt-Karte mit
**Repo-CTA** (`https://github.com/AppliedFuSa/csa26`) live geschaltet —
explizit als Übergangs-Lösung, bis das Marketplace-Listing veröffentlicht
ist. Begründung damals: Marketplace-Listing war noch nicht eingereicht.

**Ist-Zustand 2026-05-10 (heute):** Marketplace-Listing wurde
eingereicht und ist live unter

> https://github.com/marketplace/actions/csa26-misra-c-2012-pre-audit

Damit greift der im ursprünglichen CRR vorgemerkte CTA-Switch.

## Ask

Auf der Produkt-Karte für csa26 (Startseite `appliedfusa.de` und
alle Locales: DE/EN/IT/PL/FR) den Primary-CTA von Repo auf
Marketplace-Listing umstellen. Repo-Link wandert in den
Secondary-CTA, exakt wie im 2026-05-06-Produkt-Karte-CRR
vorgesehen.

### Primary-CTA

| Locale | Label | Ziel |
|---|---|---|
| DE | „Im GitHub Marketplace ansehen" | https://github.com/marketplace/actions/csa26-misra-c-2012-pre-audit |
| EN | „View on GitHub Marketplace" | dito |
| IT | „Visualizza su GitHub Marketplace" | dito |
| PL | „Zobacz w GitHub Marketplace" | dito |
| FR | „Voir sur GitHub Marketplace" | dito |

### Secondary-CTA (neu, war vorher als Primary verlinkt)

| Locale | Label | Ziel |
|---|---|---|
| DE | „Quellcode auf GitHub" | https://github.com/AppliedFuSa/csa26 |
| EN | „Source on GitHub" | dito |
| IT | „Codice sorgente su GitHub" | dito |
| PL | „Kod źródłowy na GitHubie" | dito |
| FR | „Code source sur GitHub" | dito |

(Die genauen Locale-Labels darf landing-Chat stilistisch an die
übrigen Karten anpassen, fachlicher Inhalt unverändert.)

### Trust-Block (Sektion auf `/sicherheit/#csa26`) bleibt unverändert

Keine Änderung am Trust-Block — nur die Produkt-Karte auf der
Startseite betrifft dieser Switch.

## Akzeptanzkriterien

- [ ] csa26-Karte auf `appliedfusa.de` zeigt Primary-CTA auf
      Marketplace-Listing, alle 5 Locales
- [ ] csa26-Karte zeigt Secondary-CTA auf das Repo, alle 5 Locales
- [ ] Optisch unverändert zur bisherigen Karte (gleicher Style,
      gleiche Position)
- [ ] Trust-Block-Sektion auf `/sicherheit/#csa26` bleibt unverändert

## Rückkanal

- Commit-Hash + Repo (`landing`)
- Live-URL (Screenshot der Karte mit beiden CTAs hilfreich)

## Kontext-Links

- Marketplace-Listing: https://github.com/marketplace/actions/csa26-misra-c-2012-pre-audit
- csa26-Repo: https://github.com/AppliedFuSa/csa26
- csa26 v1.0.3 (aktuelle Listing-Version): https://github.com/AppliedFuSa/csa26/releases/tag/v1.0.3
- Original-Produkt-Karte-CRR (Versand-Trigger-Vermerk):
  `_org/cross-repo-requests/2026-05-06-org-landing-csa26-produkt-karte.md`
- Vorausgehender Update-CRR:
  `_org/cross-repo-requests/2026-05-10-csa26-org-trust-block-und-produkt-karte-update-fuer-v1.md`

---

## Wenn der Request erledigt ist

Setze `Status: erledigt`, ergänze unten:

### Erledigt am

`2026-05-10` von `_org-Chat` (weitergereicht an landing-Chat)

- _org-Commit: `db35740` — CRR-Schließung in `_org`
- landing-Commit: `fa031ec` — CTA-Switch deployed, alle 5 Locales,
  Primary jetzt Marketplace-Listing, Repo-Link in Secondary
- Trust-Block-Sektion auf `/sicherheit/#csa26` unverändert wie
  gefordert.
- Damit ist die csa26-v1-Sichtbarkeitsrunde komplett.
