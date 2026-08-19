# Clip lief zweimal im selben Video: Intro und Kapitel-Opener

## Was war

Ein freigegebener WebM/MP4-Clip konnte im selben Video zweimal auftauchen —
einmal als Intro-Kulisse in den ersten Sekunden, wenige Minuten später
nochmals als Opener-Motiv eines Kapitels.

## Warum

`_klip_zuordnung()` in `video_report.py` führt eine Sperrliste `vergeben`,
damit ein Clip nur einem Abschnitt zufällt. Der Intro-Zweig darunter prüfte
diese Liste nicht (`if isinstance(intro_md5, str) and intro_md5 in frei:`),
und `KLIP_PROMPT_ZUORDNUNG` erlaubte die Doppelung ausdrücklich:
"notfalls auch derselbe Clip, der bereits einem Abschnitt zugeteilt wurde".
Prompt und Code waren sich also einig — es war kein vergessener Check,
sondern eine bewusste, aber falsche Vorgabe.

Nicht die Ursache (geprüft): der `naechstes_motiv()`-Pfad (die 10×-
Wiederholung vom 18.08.2026 ist dort weiterhin gesperrt), Repost-Duplikate
mit abweichendem MD5 (Katalog auf hp-ubuntu: 11 freie Clips, alle
Beschreibungen einmalig), mehrere Überschriften-Blöcke pro Abschnitt
(`abschnitte_erzeugen()` legt je `##`-Zeile genau einen an).

## Was jetzt

- Prompt fordert für "intro" einen Clip, der KEINEM Abschnitt zugeteilt ist;
  bleibt keiner übrig, ist `null` die vorgesehene Antwort.
- Code prüft `intro_md5 in vergeben` als Backstop und verwirft die Nominierung
  mit Log-Zeile. Das Intro fällt dann auf `tages_motiv` zurück — die
  Kapitel-Zuordnung bleibt unangetastet.

Unverändert bleibt das `-stream_loop -1` in `_szene_clip()`: ein kurzer Clip
wiederholt sich innerhalb seiner Szene, solange die Szene läuft. Das ist die
beabsichtigte Kulissen-Schleife, keine Doppelung im Drehbuch.

## Validierung

`ruff check` und `mypy` auf `video_report.py` sauber.
