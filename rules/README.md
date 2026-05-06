# csa26 — Eigene Regel-Beschreibungen

Dieses Verzeichnis ist das **Tool-Asset** der csa26-Action: pro
abgedeckter Regel eine kurze Eigen-Beschreibung in eigenen Worten
plus ein eigenes Mini-Code-Beispiel.

## Warum Eigen-Texte?

csa26 darf den **wortgetreuen MISRA-C:2012-Rule-Text nicht
redistribuieren** — siehe [`NOTICE`](../NOTICE) im Repo-Root und
das Cppcheck-Präzedenz-Pattern (Rule-IDs zitieren = nominative fair
use, Volltext kopieren = Lizenzverletzung).

Die Texte hier sind **eigenständige Paraphrasen der csa26-
Maintainer**. Sie beschreiben das fachliche Anliegen einer Regel in
1–2 Sätzen aus eigener Kenntnis und stehen unter Apache-2.0 wie der
Rest des Repos.

**Verboten beim Schreiben dieser Dateien:**

- Wortgetreuen MISRA-Rule-Text reinkopieren — auch nicht als
  „temporären Platzhalter".
- Aus dem MISRA-PDF abschreiben, auch nicht „in eigenen Worten" mit
  eng am Original klebender Formulierung.
- KI-generierte Texte ungeprüft übernehmen, falls die KI MISRA-
  Volltext als Trainingsdaten gesehen hat — Risiko von
  Re-Production.

**Empfohlene Quelle:** eigene Erfahrung mit dem Konzept, generische
Coding-Guideline-Literatur (CERT-C, Misra-aligned Style Guides ohne
MISRA-Volltext), Cppcheck-Wiki / Diskussionen im Cppcheck-Repo.

## Datei-Format

Eine Markdown-Datei pro Regel unter `c2012/<rule-number>.md`,
optional mit YAML-Frontmatter:

```markdown
---
rule_id: c2012-8.13
title: Pointer auf nicht-modifiziertes Ziel sollten const sein
---

Wenn ein Pointer-Ziel innerhalb der Funktion nicht verändert wird,
soll der Pointer-Typ const-qualifiziert sein. Das macht die
Lese-Absicht im Schnittstellen-Vertrag sichtbar und erlaubt dem
Optimierer, mehr Annahmen über Aliasing zu treffen.

```c
/* Eigenes Code-Beispiel */
void log_buffer(const uint8_t *data, size_t len);  /* OK */
void log_buffer(uint8_t *data, size_t len);        /* zu locker */
```
```

**Frontmatter-Felder:**

- `rule_id` — csa26-interner Schlüssel (`c2012-X.Y`). Optional, wird
  sonst aus dem Datei-Namen gefolgert.
- `title` — kurzer eigener Titel, erscheint in Annotations und
  SARIF.

**Body:** Erster Absatz nach der Frontmatter ist die Beschreibung,
die in Job Summary und SARIF angezeigt wird. Code-Beispiele und
weitere Hinweise dürfen folgen — der Wrapper liest in v0.1 nur den
ersten Absatz.

## Coverage-Status

Was csa26 in v0.1 abdeckt, entspricht dem, was das Cppcheck-MISRA-
Addon prüft. Eine Datei in diesem Verzeichnis ersetzt den
Platzhalter-Text durch eine Eigen-Paraphrase. Fehlt die Datei, gibt
csa26 einen freundlichen Platzhalter aus und markiert die Regel im
SARIF mit `csa26_paraphrase: false`.

Aktuelle Abdeckung sieht man via:

```bash
ls rules/c2012/ | wc -l
```

Die offizielle MISRA-C:2012-Regelliste (Identifikation, nicht
Volltext) lebt in der Spezifikation des MISRA Consortium. Anhand der
Cppcheck-MISRA-Addon-Quellen lässt sich die geprüfte Teilmenge
ermitteln — diese Liste ist die **realistische Phase-1-Coverage** und
gehört in die README.

## Autoren-Checkliste

Pro neuer Regel-Datei:

- [ ] Konzept aus eigener Kenntnis paraphrasieren — nicht aus dem
      MISRA-Dokument.
- [ ] 1–2 Sätze, deutsch oder englisch (Tool-Output ist EN; DE-
      Texte sind in Phase 1 OK, werden ggf. später übersetzt).
- [ ] Eigenes Mini-Code-Beispiel in `c`-Code-Block — kurz, illustriert
      Verstoß und/oder konformes Pendant.
- [ ] Frontmatter `rule_id` und `title` setzen.
- [ ] Bei Unsicherheit über Lizenz-Hygiene: lieber leer lassen, als
      zu nah am Original kleben.
