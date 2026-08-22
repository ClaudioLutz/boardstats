---
datum: 2026-08-22
agent: main
typ: docs
commit: 240c164
---

# Overseer-Skill: Reichweiten-Diagnose und die neuen Prüfpunkte

**Was:** `.claude/skills/pipeline-overseer/SKILL.md` um den Abschnitt
„Reichweite: der Engpass ist die Klickrate (22.08.2026)" erweitert, die
Cron-Tabelle auf den erweiterten 23:30-Lauf nachgeführt (`737dcdb`), und den
A/B-Titel-Punkt aus der A–D-Serie präzisiert.

**Warum:** Die Wartungsklausel des Skills verlangt den Nachtrag jeder
Overseer-relevanten Erkenntnis. Zwei davon waren heute nicht im Dokument:

1. Der **Messwert aus YouTube Studio** — 205 Impressionen, 0,0 % Klickrate,
   0 Wiedergaben aus Impressionen für das Video vom 21.08. Das verschiebt die
   Diagnose vom Verteilungs- zum Klickproblem und macht die Serie A–D für
   *diese* Kennzahl wirkungslos (sie wirkt nach dem Klick).
2. Die **API-Grenzen mit Gegentest**: `impressions`/`impressionClickThroughRate`
   existieren nicht (HTTP 400), `day,country` und
   `video,insightTrafficSourceType` sind unzulässige Dimensionskombinationen,
   und der Analytics-Nachlauf ist real ~3 Tage statt der 2 aus `NACHLAUF_TAGE`.
   Ohne diese Notizen läuft der nächste Durchgang dieselben 400er erneut.

**Auswirkung:** Drei datierte Prüfpunkte stehen jetzt im Skill — die neuen
Schlüssel in der JSON von morgen früh, der `EXT_URL`-Ausschlag am 24.08. als
Antwort auf das /biz/-Seeding, und `YT_BROWSE` als laufendes Signal dafür, dass
der Feed anspringt.

**Auch festgehalten:** Der Faktor 15 zwischen Shorts (44 Views) und Hauptvideo
(3 Views) desselben Abends — der bislang stärkste Hinweis, dass der Hebel beim
Format liegt.

**Offen:** Der A/B-Titel-Test aus D bleibt ungelöst, ist nach dem CTR-Befund
aber der wichtigste offene Punkt. Er braucht einen anderen Messweg als die API.
