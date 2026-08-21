---
datum: 2026-08-21
agent: main (Branch retention-a-bis-d)
typ: feature
commit: <Hash, sobald bekannt>
---

# Stossrichtung A: Vorspann gedeckelt, Retention-Rückkopplung neu kalibriert

**Was:**

- `video_report.py`: neue Decke `INTRO_DECKEL = 15.0 s` für den Vorspann. Bisher gab
  es nur den Boden `INTRO_BODEN` (11.5 s, YouTube-Kapitelregel). Überschreitet die
  Schätzung die Decke, fällt in `praesentations_bloecke()` der jeweils letzte
  gesprochene Zahlensatz weg (einer bleibt immer stehen).
- `PRAES_HOOK` ist von `"Today's top story: {hook}"` auf `"{hook}"` verkürzt — der
  Hook ist jetzt das erste gesprochene Wort des Videos.
- `ZAHLEN_GESPROCHEN = 2`: von den vier TL;DR-Zahlen werden nur noch zwei
  vorgelesen. **Im Bild stehen weiterhin alle vier** — neue Tafel
  `szenen.zahlen_uebersicht()` im Szenen-Pfad (v7), im Folien-Pfad (v6) klappen
  beim letzten gesprochenen Satz alle Karten auf.
- Neu `_zahl_satz()`: kappt das Drehbuch-Feld `satz` auf den ersten Satz und
  `ZAHL_SATZ_WORTE = 12` Wörter. Das Feld war unbegrenzt.
- `PRAES_OUTRO` von drei Sätzen auf einen gekürzt.
- `run_report.py`: `_retention_block()` rechnet das Wortziel nicht mehr über das
  Soll-Budget `WORTBUDGET`, sondern über die neue `_sprechrate()` — die
  Ist-Wortzahl der zu den gemessenen Videos gehörenden Berichte
  (`bericht_woerter()`) gegen deren Ist-Laufzeit.
- Neues Gate `RETENTION_MIN_N = 5`: unter fünf auswertbaren Videos gibt der Block
  nur noch den qualitativen Befund aus und lässt das Wortbudget des Prompts stehen.
- `_thumb_bereinigen()` verwirft Schlagwort-Wörter, die nicht im Hook vorkommen;
  `TITEL_PROMPT` fordert das zusätzlich ein und verlangt eine harte Zahl im Hook.
- `_retention_kennwerte()` reicht `veroeffentlicht`, `kapitel` und `punkte` durch
  (Grundlage für die Kapitel-Messung, Stossrichtung D).

**Warum:** Brainstorming-Session vom 21.08.2026
(`research/brainstorming/brainstorm-reporttexte-retention-2026-08-21/`),
Stossrichtung A. Ausgangsbefund: Abbruchwand bei 1:08, unter 30 % Verbleib nach
0:45. Der Vorspann wuchs gegenläufig dazu von 29.6 s (20.08.) über 37.0 s auf
**48.9 s** im produktiven Lauf vom 21.08. und verbrannte damit drei Viertel der
mittleren Verweildauer vor dem ersten Kapitelinhalt. Ursache war nicht die Anzahl
Zahlen, sondern die unbegrenzte Länge des Feldes `satz`.

Die Fehlkalibrierung des Retention-Blocks war im Overseer-Skill bereits als Befund
festgehalten: die Formel skalierte das **Soll**-Budget (700–1000 Wörter) mit der
**Ist**-Laufzeit einer Messung, die zu Berichten mit ~1800 Wörtern gehörte — das
Wortziel fiel dadurch rund um Faktor 2 zu niedrig aus.

**Auswirkung:** Der Vorspann liegt ab dem nächsten Lauf zwischen 11.5 s und 15 s.
Das Wortziel der Rückkopplung entspricht ab fünf gemessenen Videos der tatsächlich
gemessenen Sprechrate; darunter verändert die Messung das Wortbudget gar nicht mehr
(vorher wirkte sie schon ab einem Video). Bewusst **nicht** geändert: der Boden
`INTRO_BODEN` und die Dämpfungsklausel `max(t30, laufzeit/2)` — beide bleiben.

**Offen:** Stossrichtungen B, C und D dieser Session.
