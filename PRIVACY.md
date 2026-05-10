# csa26 — Privacy Notice

**Stand:** 2026-05-10 (csa26 v1.0.x)
**Verantwortlich:** Wolfgang Freese / Applied FuSa, Overath, Deutschland
**Kontakt:** <info@appliedfusa.de>

Diese Datei ist die Privacy-Notice für csa26 als GitHub-Marketplace-
Action. Sie ergänzt das in [`NOTICE`](NOTICE) und auf
<https://appliedfusa.de/sicherheit/#csa26> Gesagte und ist die
Privacy Policy im Sinne des
GitHub-Marketplace-Developer-Agreements §A1-4.a.

## Datenfluss in einem Satz

csa26 läuft in einem Container, den GitHub auf dem CI-Runner Ihres
Repositorys startet. **Ihr Quellcode verlässt Ihr Repository nicht.**
Applied FuSa hat keinen Zugriff auf Ihren Code, sieht keine Findings,
empfängt keine Telemetrie, speichert keine Logs.

## Welche personenbezogenen Daten verarbeitet csa26?

**Keine.** Für den End-User der Action gibt es keine persönliche
Datenverarbeitung durch Applied FuSa:

- **Code-Inhalte** (einschließlich eventueller personenbezogener
  Daten in Quellcode-Kommentaren wie Author-Namen oder E-Mail-
  Adressen) werden im Container des Anwenders verarbeitet und nie
  an Applied FuSa übertragen.
- **Findings, SARIF-Reports, Annotations** entstehen im Container
  und bleiben in der GitHub-Infrastruktur des Anwenders (Action-
  Logs, Pull-Request-Annotations, Security-Tab). Sie verlassen den
  Anwender-Account nicht in Richtung Applied FuSa.
- **Build-/Lauf-Telemetrie** wird nicht eingesammelt — csa26 sendet
  keine Heartbeats, keine Crash-Reports, keine Usage-Statistiken
  zurück.
- **Identifizierende Daten des Anwenders** (E-Mail-Adresse,
  GitHub-Handle, IP-Adresse, etc.) werden nicht erfasst.

## Sub-Prozessoren

- **GitHub, Inc. (Microsoft):** stellt den CI-Runner und das
  Container-Registry-Hosting für das csa26-Action-Image bereit.
  Datenverarbeitung ausschließlich nach den Bedingungen Ihres
  GitHub-Vertrags.
- **Keine weiteren Sub-Prozessoren.**

## Wie werden Daten gespeichert?

Applied FuSa speichert **keine** Daten über csa26-Läufe. Was an
Daten entsteht (Findings, SARIF-Reports, Annotations), bleibt
vollständig in Ihrem GitHub-Repository unter Ihrer Kontrolle.

## Rechte des End-Users (DSGVO)

Da Applied FuSa keine personenbezogenen Daten verarbeitet, gibt es
auf unserer Seite keine Daten zum Auskunfts-, Berichtigungs- oder
Löschungs-Anspruch. Eventuelle personenbezogene Daten in Ihrer
GitHub-Infrastruktur (Action-Logs, Findings, Repository-Inhalte)
unterliegen Ihrer eigenen GDPR-Verantwortlichkeit gegenüber Ihrem
GitHub-Vertrag.

## Automatisierte Entscheidungen

csa26 erzeugt MISRA-Findings, die als technischer Hinweis im
Code-Review dienen. Diese Findings sind **keine automatisierten
Entscheidungen mit Rechtswirkung** im Sinne von Art. 22 DSGVO oder
GitHub-Marketplace-Agreement §A1-5.c — sie betreffen weder
Beschäftigungsverhältnisse noch Kreditwürdigkeit, Gesundheit oder
sonstige Personenrechte.

## KI-Einsatz

csa26 enthält keinen LLM- oder generative-AI-Anteil. Lexer,
Preprocessor, Parser und Rule-Engine arbeiten deterministisch:
gleicher Input → gleicher Finding-Set, jedes Mal.

## Kontakt

Privacy-, Sicherheits- oder DSGVO-Anfragen:

**E-Mail:** <info@appliedfusa.de>
**Postanschrift:** Wolfgang Freese / Applied FuSa, Overath, Deutschland

Sicherheitslücken bitte über das
[GitHub Security Advisory Reporting](https://github.com/AppliedFuSa/csa26/security/advisories/new)
melden, damit wir sie verantwortungsvoll behandeln können.

## Updates dieser Notice

Änderungen werden über das [`CHANGELOG.md`](CHANGELOG.md) und im
Git-History dieses Repos nachgeführt. Datierte Versionen sind über
die Git-Tags abrufbar.
