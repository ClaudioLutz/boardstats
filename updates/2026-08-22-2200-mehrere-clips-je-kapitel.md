---
datum: 2026-08-22
agent: worktree-clip-ernte-ganzer-snapshot
typ: feature
commit: a625289
---

# Ein Kapitel bekommt bis zu drei verschiedene Clips statt einem

**Was:** `_klip_zuordnung()` liefert jetzt `dict[int, list[Path]]` statt
`dict[int, Path]`; `KLIP_PROMPT_ZUORDNUNG` fordert eine Liste je Abschnitt
(neu `KLIP_JE_ABSCHNITT = 3`). Im Szenenbau traegt der erste Clip weiterhin
die Opener-Szene, die weiteren wandern ueber `naechstes_motiv()` in die
Story-Szenen desselben Kapitels — **nie zwei hintereinander**, dazwischen
liegt immer ein Bild. Ein einzelner String in der Modellantwort bleibt
gueltig (bei `effort="low"` faellt das Modell gelegentlich auf die alte Form
zurueck). Neue Testdatei `tests/test_clip_zuordnung.py` mit 9 Tests — es gab
bis heute **keinen einzigen** Test fuer Ernte oder Zuordnung.

**Warum:** Die Ernte aus dem ganzen Snapshot (`1fb9dfc`) fuellt den Katalog,
aber mehr Clips im Katalog heissen noch nicht mehr Bewegtbild im Video.
Gemessen am Lauf vom 22.08.: 4 Clips zugeteilt, 3 normalisiert gerendert —
und weil ein Clip nur die **erste Szene** seines Kapitels trug, waren das
rund **3 von 50 Szenen**. Nutzerhinweis am selben Abend: "die clips ernte
muss auch im video gerendert werden."

Der naheliegende Weg — denselben Clip laenger stehen lassen — ist
ausgeschlossen und steht als Warnung im Code (`naechstes_motiv`):
Nutzerbefund vom 18.08.2026, "Clip 10x am Berichtsende wiederholt, 0
Relevanz und 0 Unterhaltungswert". Also mehr VERSCHIEDENE Clips statt
laengere Standzeit. Moeglich wird das erst durch den groesseren Pool aus
der Snapshot-weiten Ernte.

**Auswirkung:** Bei voller Zuteilung koennen 8 Kapitel x 3 Clips plus Intro
statt bisher hoechstens 8+1 Clips laufen; realistisch begrenzt der Pool das.
Bewegtbild verteilt sich ueber das Kapitel statt nur an seinem Anfang zu
stehen, ohne dass sich ein Clip wiederholt — die Doppelvergabe ist an drei
Stellen gesperrt (innerhalb der Liste, ueber Abschnitte hinweg, und gegen
den Intro-Clip). Die Bild-Kulisse bleibt die Grundlage: der Wechsel
Bild/Clip/Bild ist fest verdrahtet, ein Kapitel kann nie ganz aus Clips
bestehen. `ruff`/`mypy` sauber, **281 Tests gruen** (272 + 9).

**Offen:** Im echten Video noch nicht nachgemessen — der Effekt zeigt sich
erst im Lauf vom 23.08. Gegenprobe im Log: die Zeile "Clip-Zuordnung:
Kapitel N -> a.webm, b.webm" nennt jetzt mehrere Dateien je Kapitel, und
`video/<datum>/normalisiert/` sollte deutlich mehr als die 3 Dateien von
heute enthalten. Ausserdem offen: ob die Sichtpruefung mit ~18 statt 3
Kandidaten taeglich die Laufzeit der Report-Stufe spuerbar verlaengert
(22.08.: 18s fuer 3 Kandidaten, 21.08.: 99s fuer 9).
