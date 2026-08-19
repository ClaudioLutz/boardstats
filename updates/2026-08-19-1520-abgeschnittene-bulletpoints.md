---
datum: 2026-08-19
agent: worktree-bullet-kappung
typ: bugfix
commit: 05593a6
---

# Abgeschnittene Bulletpoints: Kappung am Wort statt an der Zeichenzahl

**Was:** Fallback-Stichpunkte werden nicht mehr mitten im Satzteil gekappt, und
die Themen-Karte umbricht gegen ihre echte Textbreite.

- `video_report.py`: `_luecken_bullet()` strippt Anführungszeichen, kappt am
  Wort und bevorzugt eine Klausel-Grenze; endet der Punkt auf einem Füllwort
  (`BULLET_FUELLWORT`), fällt es weg und eine Auslassung markiert den Schnitt.
  Längenziel `BULLET_MAX = 42`.
- `szenen.py`: `KARTE_INNEN` rechnet ab `KARTE_TEXT_X` statt ab der
  Marker-Kante; neue `karte_passt()` als Kapazitätsprüfung.
- `run_report.py`: `_wortgrenze()` ersetzt die harten `[:38]`/`[:40]`-Schnitte
  in `_stichwort()`.
- `tests/test_bullet_kappung.py`: 14 Tests.

**Warum:** Nutzermeldung 19.08.2026 mit Screenshot — im Bild stand
`LIQUID INVESTABLE USD IN`. Die Kausalkette, nachgerechnet:

1. Der Satz-Cue lautete `liquid investable USD in millions" - net worth ...`
   (`_satz_cues` bricht auch am Doppelpunkt, daher der Beginn mitten im Zitat).
2. Der Rumpf `LIQUID INVESTABLE USD IN MILLIONS"` ist mit dem schliessenden
   Anführungszeichen **genau 34 Zeichen** — ein Zeichen über der alten Grenze.
3. `kurz[:kurz.rfind(" ")]` warf daraufhin das letzte volle Wort weg. Übrig
   blieb eine hängende Präposition.

Das Anführungszeichen allein kostete also den Punkt. Der Fehler ist aber
keine Einzelfallpanne: über die Satz-Cues des heutigen Berichts gemessen
endeten **31 von 186** Fallback-Bullets auf einem Füllwort (`... AND`,
`... FOR`, `... TO`). Nach der Änderung: 0.

**Auswirkung:**

- Gemessen am selben Korpus: 0 Füllwort-Enden, 0 Punkte, die beim Parken Text
  verlieren (`karte_text(b) == b`), Medianlänge 37 Zeichen (max. 44).
- **Bewusst kein Pixel-Budget als Ziel.** Kappt man erst an der echten
  Zwei-Zeilen-Kapazität der Karte, werden die Fallbacks im Median 41 und bis zu
  82 Zeichen lang — das ist ein eingebrannter Untertitel, und genau den hat der
  User am 19.08. abgelehnt. Die Kapazität (`karte_passt`) bleibt deshalb nur
  die harte Grenze dahinter, das Längenziel ist `BULLET_MAX`.
- `KARTE_INNEN` war 412 px, der Text hat aber nur 390 px Platz (Einzug 56,
  rechter Innenrand 24): 6 von 84 geparkten Zeilen liefen bis zu 14 px über den
  Kastenrand aufs rohe Board-Motiv. Folge der Korrektur: mehr Punkte werden
  zweizeilig, die Karte wird höher, die Verdrängung der ältesten Punkte greift
  entsprechend früher — das ist der ehrliche Preis der richtigen Breite.
- `_stichwort()` schnitt bisher mitten im Wort. Heute schlummernd (längster
  Bullet 31 Zeichen), aber dieselbe Defektklasse.

**Geprüft:** ruff, mypy, 85 Tests. Echter ffmpeg-Render mit gefüllter
Themen-Karte und Flug: der Punkt steht als `LIQUID INVESTABLE USD IN MILLIONS`
vollständig im Bild, die geparkten Zeilen bleiben im Kasten, das Flugziel aus
`karte_punkt_ziel()` sitzt nach der Breitenkorrektur richtig.
