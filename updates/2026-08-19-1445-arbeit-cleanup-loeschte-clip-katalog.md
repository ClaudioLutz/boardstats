---
datum: 2026-08-19
agent: main
typ: bugfix
commit: 034ae86
---

# Aufräum-Logik in run_report.py löschte den Clip-Katalog bei jedem Lauf

**Was:** `run_report.py`, Ende von `main()` (Zeile ~2229): die Aufräum-Logik
für alte Arbeitsordner filtert jetzt nur noch echte Datums-Ordner
(`YYYY-MM-DD` per Regex) unter `arbeit/`, bevor sie sortiert und alle ausser
den letzten `LAEUFE_BEHALTEN` löscht.

**Warum:** Overseer-Verifikation der heutigen Anpassungen (Nutzeranweisung:
kontrollieren, ob die Kette funktioniert, bevor der nächste Cron-Lauf sie
produktiv nutzt) deckte auf, dass `arbeit/clips/` (der kumulative
WebM/MP4-Clip-Katalog, seit `6c0dfb5` am 18.08.2026) nach jedem einzelnen
`run_report.py`-Lauf spurlos verschwand - ein bereits als "ungeklärt" im
Overseer-Skill vermerktes Phänomen. Ursache: `sorted(ARBEIT.iterdir(),
reverse=True)[LAEUFE_BEHALTEN:]` (Code vom 08.08.2026, also vor
`klip_katalog.py`) behandelte JEDEN Eintrag unter `arbeit/` gleich. In
absteigender alphabetischer Sortierung stehen Namen wie "thumbs",
"srt_nachzug", "motive" und eine lose Datei VOR jedem Datum
("t" > "s" > "m" > "2026-08-19" > ...) - bei `LAEUFE_BEHALTEN = 5` fiel
"clips" exakt auf den Schnitt und wurde bei jedem Lauf mitsamt
`katalog.json` (gesamte Clip-Bewertungshistorie) gelöscht, kurz nachdem
`klips_ernten()` sie gerade neu geschrieben hatte. Reproduziert live im
Overseer-Testlauf: ein Testvideo direkt nach einem `run_report.py`-Lauf
fand 0 verfügbare Clips, obwohl der Katalog Minuten zuvor 11 freigegebene
Clips enthielt.

**Auswirkung:** Der kumulative Clip-Katalog bleibt jetzt über Läufe hinweg
erhalten, wie ursprünglich in `groovy-weaving-rocket.md` vorgesehen
("Katalog kumulativ über Tage, nicht Pro-Tag-Snapshot"). Die
Wiederverwendungssperre (`VERWENDET_TAGE`, aktuell 5 Tage) und die
"gleicher Tag zählt als frei"-Ausnahme in `_klip_zuordnung()` können jetzt
tatsächlich wirken, weil der Katalog nicht mehr laufend auf null
zurückgesetzt wird. Kein Verhaltensunterschied bei den Datums-Ordnern
selbst (weiterhin die letzten 5 Tage behalten).

**Offen:** Der bisherige Datenverlust ist nicht rückwirkend behebbar -
alle vor heute freigegebenen/abgelehnten Clip-Bewertungen aus den
Katalog-Läufen der letzten Tage sind vermutlich schon vorher verloren
gegangen (Katalog wurde ja schon seit dem 18.08. nach jedem Lauf geleert).
Der Katalog baut sich jetzt neu und dauerhaft auf.
