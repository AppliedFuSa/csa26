# Cross-Repo-Request

**Von:** csa26-Chat
**An:** _org-Chat (`AppliedFuSa/_org`)
**Datum:** 2026-05-10
**Betreff:** Trust-Block + Produkt-Karte — Updates für csa26 v1.0 + Versand-Freigabe an landing
**Status:** erledigt — siehe _org Commit `2108b4c`

> **Hinweis Wolfgang:** csa26-Chat hat keinen Schreibzugriff auf
> `_org`. Diese Quell-Datei liegt im csa26-Repo unter
> `docs/cross-repo-requests/`. Bitte den Inhalt in den _org-Chat
> kopieren.

## Kontext

Am 2026-05-06 hat _org-Chat zwei CRRs an landing-Chat **vorbereitet**,
aber nicht versendet:

- `2026-05-06-org-landing-csa26-trust-block.md`
- `2026-05-06-org-landing-csa26-produkt-karte.md`

Versand-Trigger waren: „v0.1-Substanz im Repo" bzw. „Marketplace-
Listing live". Erste Bedingung ist erfüllt; die zweite ist noch
offen, aber für die Trust-Seite irrelevant — die kann sofort raus.

Inzwischen ist v1.0.0 (2026-05-07) und v1.0.1 (heute) released — der
Stack hat sich vom Cppcheck-Wrapper zum Eigenbau-Engine geändert.
Beide Drafts sind grosso modo stack-neutral (gut!), brauchen aber an
zwei Stellen kleine Updates und einen neuen Trust-Punkt, den die
Eigenbau-Strategie überhaupt erst ermöglicht.

## Ask

### A. Trust-Block — drei Mini-Updates

1. „Phase 1"-Vorbehalte entfernen (zweimal: Sub-Prozessoren-Block und
   Datenspeicherungs-Block). Beide Aussagen gelten ab v1.0 dauerhaft.

   **Sub-Prozessoren — Ersetzen**
   - alt (DE): „— **Keine weiteren Sub-Prozessoren** in Phase 1."
   - neu (DE): „— **Keine weiteren Sub-Prozessoren.**"
   - alt (EN): „— **No further sub-processors** in Phase 1."
   - neu (EN): „— **No further sub-processors.**"

   **Datenspeicherung — Ersetzen**
   - alt (DE): „Applied FuSa speichert keine Daten ueber csa26-Lauefe
     in Phase 1."
   - neu (DE): „Applied FuSa speichert keine Daten ueber csa26-Lauefe."
   - alt (EN): „Applied FuSa stores no data about csa26 runs in
     Phase 1."
   - neu (EN): „Applied FuSa stores no data about csa26 runs."

2. **Neuer Vertrauens-Bullet ergänzen** (zwischen Datenfluss-Block
   und Sub-Prozessoren-Block sinnvoll platziert): Eigenbau-Stack als
   IP-/Audit-Argument.

   **Vorschlag DE:**
   > **Komplett eigenständig.** csa26 enthält keinen Drittanbieter-
   > Static-Analyser. Lexer, Preprocessor, Parser, Symbol- und Type-
   > System sowie die Rule-Engine sind Apache-2.0-IP der Applied
   > FuSa und vollständig im offenen Repo nachvollziehbar.

   **Vorschlag EN:**
   > **Fully self-contained.** csa26 wraps no third-party static
   > analyser. The lexer, preprocessor, parser, symbol/type system
   > and rule engine are Apache-2.0 IP of Applied FuSa and fully
   > traceable in the public repository.

3. **Hinweis-Block am Ende ergänzen** um die Coverage-Aussage:

   **Vorschlag DE-Ergänzung am Ende des bestehenden Blocks:**
   > csa26 v1 prüft ein bewusst gewähltes Subset von 20 FuSa-
   > priorisierten MISRA-C:2012-Regeln (siehe README im Repo).
   > Eine vollständige MISRA-Compliance-Prüfung war nie versprochen
   > und ist auch von keinem Tool dieser Klasse leistbar.

   **Vorschlag EN-Ergänzung am Ende des bestehenden Blocks:**
   > csa26 v1 covers a deliberately curated subset of 20 FuSa-
   > prioritised MISRA-C:2012 rules (see README in the repository).
   > Full MISRA-compliance verification was never claimed and is
   > out of reach for any tool of this class.

### B. Produkt-Karte — vier kleine Updates + Versand-Trigger

1. **Feature-Bullet generalisieren:**
   - alt: „Public, Open Source, kostenlos in Phase 1 / Public, open
     source, free in Phase 1"
   - neu (DE): „Public, Open Source, kostenlos"
   - neu (EN): „Public, open source, free"

2. **Eigenbau-Bullet ergänzen** (vierte Bullet-Zeile):
   - DE: „Komplett eigenständige Implementation — kein Cppcheck,
     kein Drittanbieter-Static-Analyser im Stack"
   - EN: „Fully self-contained engine — no cppcheck, no third-party
     static analyser involved"

3. **Intro-Absatz präzisieren** (eine Aussage über den Subset-
   Charakter, damit kein Compliance-Anspruch entsteht):

   Bestehende Formulierung „findet Regelverletzungen, ersetzt aber
   keine offizielle Compliance-Bewertung" bleibt — ergänzend nach
   dem zweiten Absatz hinzufügen:

   - DE: „v1 prüft ein gezielt gewähltes Subset von 20 FuSa-
     relevanten MISRA-Regeln. Erweiterungen folgen in v1.x nach
     Discovery-Feedback."
   - EN: „v1 checks a deliberately curated subset of 20 FuSa-
     relevant MISRA rules. Extensions follow in v1.x based on
     discovery feedback."

4. **Versand-Trigger neu setzen:**
   Der ursprüngliche Trigger („Marketplace-Listing live") ist nicht
   mehr zwingend für den Versand der Produkt-Karte, weil die Karte
   inzwischen sinnvoll auf das Repo (`https://github.com/AppliedFuSa/csa26`)
   verlinken kann. Mein Vorschlag: Versand jetzt freigeben mit dem
   Repo als Primary-CTA, Karte nach Marketplace-Submission auf das
   Listing umleiten.

   Alternativ: warten bis Marketplace-Listing live, dann beides
   gemeinsam versenden. Wolfgang entscheidet.

### C. Trust-Block jetzt versenden

Trust-Block ist nicht vom Marketplace-Listing abhängig (er beschreibt
nur den Datenfluss). Vorschlag: nach Übernahme der drei Updates
unter A. **jetzt** an landing-Chat versenden.

## Akzeptanzkriterien

- [ ] _org-Chat aktualisiert
      `_org/cross-repo-requests/2026-05-06-org-landing-csa26-trust-block.md`
      gemäß Abschnitt A.
- [ ] _org-Chat aktualisiert
      `_org/cross-repo-requests/2026-05-06-org-landing-csa26-produkt-karte.md`
      gemäß Abschnitt B.
- [ ] Trust-Block-Status auf „offen" setzen, Inhalt an landing-Chat
      übergeben.
- [ ] Produkt-Karte-Versand: entweder jetzt freigeben (Repo-CTA) oder
      explizit auf Marketplace-Listing-Live warten — Entscheidung
      dokumentieren.

## Rückkanal

- Aktualisierte Diff-Stand der zwei Drafts (Commit-Hash in `_org`).
- Versand-Status der Trust-Block-CRR.
- Falls Empfehlung in B.4 nicht gefolgt wird: Begründung.

## Kontext-Links

- csa26 v1.0.1: `https://github.com/AppliedFuSa/csa26`
- Architektur-Memo (post-Pivot): `_org/architecture/csa26.md`
- Original-Drafts:
  - `_org/cross-repo-requests/2026-05-06-org-landing-csa26-trust-block.md`
  - `_org/cross-repo-requests/2026-05-06-org-landing-csa26-produkt-karte.md`

---

## Wenn der Request erledigt ist

Setze `Status: erledigt`, ergänze unten:

### Erledigt am

`2026-05-10` von `_org-Chat`

- Commit: `2108b4c` in `_org` — Trust-Block + Produkt-Karte
  enthalten alle Updates aus den Abschnitten A und B.
- Trust-Block-Versand: Status `offen`, bereit zur Übergabe an
  landing-Chat.
- Produkt-Karte-Versand: Status `offen`, bereit zur Übergabe an
  landing-Chat (Repo-CTA-Variante).
- Folge-CRR vorgemerkt: nach Marketplace-Listing-Live schickt
  csa26-Chat einen kleinen Switch-CRR mit der Marketplace-URL und
  Bitte um CTA-Umstellung in der Produkt-Karte.
