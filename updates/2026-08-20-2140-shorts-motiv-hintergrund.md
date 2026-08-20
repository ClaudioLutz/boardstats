---
datum: 2026-08-20
agent: worktree-agent (Feature-Branch aus .claude/worktrees)
typ: feature
commit: siehe Merge auf main
---

# Shorts: Kapitel-Motiv des Hauptvideos als Hintergrund

**Was:** `shorts.py` rendert jedes Story-Short nicht mehr auf der reinen
Farbfläche, sondern mit dem passenden Kapitel-Motiv des Hauptvideos als
formatfüllendem Hintergrund. Dazu wurde die Kapitel-Motivwahl aus
`video_report.szenen_bauen()` (v7) in die neue Klasse
`video_report.MotivWahl` extrahiert (`pool_bild`, `eigenes_bild`,
`kapitel_reservieren`); `szenen_bauen` nutzt sie per Alias unverändert
weiter, `shorts.story_motive()` rechnet damit exakt dieselbe Zuordnung —
Story i trägt dasselbe Motiv wie Kapitel i (die Kapitel-Reservierung ist
im Hauptvideo der erste Pool-Zugriff auf frischem Zustand, eine frische
`MotivWahl` liefert also identische Ergebnisse). Neu in `shorts.py`:
`hintergrund_bauen()` (Center-Crop auf 1080×1920, Scrim: 60 % GRUND
uniform plus linear abklingende Zusatz-Abdunkelung bis 40 % über der
Titel-/Stichwort-Zone oben, `SCRIM`/`SCRIM_OBEN`/`SCRIM_BODEN`),
`frame_bauen(..., hintergrund=)`; Frame 1 (Shorts-Vorschaubild) trägt das
Motiv ebenfalls. Animierte Motive (GIF/WebM/MP4) laufen über ihr
Posterframe aus `motive.json`; ohne Poster fällt die Story aufs
Farbtheme zurück. Tests: `tests/test_shorts.py` um Zuordnungs-, Fallback-,
Poster- und Crop-Tests ergänzt; README-Shorts-Abschnitt aktualisiert.

**Warum:** Expliziter Nutzerauftrag 20.08.2026: die Shorts waren bewusst
v1-schlicht (reine Karten), sollen jetzt aber das Board-Bildmaterial des
Tages tragen wie das Hauptvideo — mit unveränderter Lesbarkeit.

**Auswirkung:** Ab dem nächsten Cron-Lauf (21:15 CEST) tragen die Shorts
das jeweilige Kapitel-Motiv hinter Titel, Stichworten und Kennzahl-Karte.
Sichtprüfung auf echten Frames vom 20.08. (Storys 1, 2, 4, 6, u. a.
DiCaprio-Meme, helles Pepe-Plüsch-Bild): Text und Karte klar lesbar,
Shorts-UI-Zonen (unten 420 px, rechts 190 px) unverändert frei. Fehlen
freigegebene Tagesbilder (kein brauchbares `motive.json`, auch nicht in
den 7 Rückgriff-Tagen), rendert das Short exakt wie bisher auf dem
Farbtheme — eine Logzeile, kein Absturz; der `tages_motiv`-Rückfall des
Hauptvideos (Vorschaubild) gilt für Shorts bewusst nicht. Bewusst nicht
geändert: die Clip-Zuteilung des Hauptvideos (Kapitel mit WebM-Clip als
Opener) bleibt außen vor — Shorts sind eine Standbild-Pipeline; Audio,
Schnittgrenzen, Upload-Metadaten und `extrakte/` unangetastet.

**Offen:** —
