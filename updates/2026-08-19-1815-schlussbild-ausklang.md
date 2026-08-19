---
datum: 2026-08-19
agent: worktree/schlussbild-und-zitatdauer
typ: bugfix
commit: <folgt>
---

# Schlussbild steht 5 Sekunden und blendet nach Schwarz

**Was:** Vier zusammenhaengende Aenderungen in `video_report.py`:

1. `AUSKLANG = 5.0` ersetzt den bisherigen 3-Sekunden-Puffer;
   `ende = sprech_ende + AUSKLANG`.
2. `_ton_kette()` polstert die Sprache mit `apad=whole_dur={ende}` bis
   dorthin. Mit Bett wird der gepolsterte Strom per `asplit` verdoppelt,
   weil `sidechaincompress` denselben Strom als Trigger braucht und keine
   framesync-Optionen kennt — endet der Trigger, endet auch sein Ausgang.
3. `szenen_bauen()` bekommt `sprech_ende`: der Aktivitaets-Chart wird gegen
   das Ende der **Sprache** bemessen, der stumme Ausklang gehoert ganz der
   Abschluss-Tafel. Die Tafel blendet ueber `SCHLUSS_FADE` (1.5 s) aus.
4. `_szene_clip()` legt bei der letzten Szene ein `fade=t=out` auf das
   fertige Bild — die Blende steckt im Clip, der Zusammenschnitt bleibt ein
   Streamcopy.

**Warum:** Nutzerwunsch: «das Schlussbild muss laenger sichtbar sein und
ausfaden». Der Befund dahinter ist haerter als der Wunsch — das Schlussbild
war ueberhaupt nicht sichtbar. Gemessen am Video vom 19.08.2026: Laufzeit
718.4 s, letzter Untertitel-Cue endet 718.5 s. `amix=duration=first` band
die Tonspur an das letzte gesprochene Wort, `-shortest` kappte das Video
dort, und die 3 Sekunden Puffer kamen nie an. Mit ihnen fiel auch die
`BETT_AUSBLENDE` weg: die Musik brach mitten in ihrer eigenen Ausblende ab.

**Auswirkung:** Video wird rund 2 s laenger als bisher geplant und 5 s
laenger als bisher tatsaechlich. Gegen ffmpeg gemessen: 5.0 s Sprache mit
`ende=12.0` ergibt 12.000 s Mischung (vorher 5.000 s), und der Pegel im
Ausklang deckt sich auf 0.0 dB mit dem ungeduckten Bett — das Ducking loest
sauber, die Musik traegt das Schlussbild und faedet mit ihm aus. Suite 88
Tests gruen.

**Offen:** `SCHLUSS_FADE` (1.5 s) und `AUSKLANG` (5.0 s) sind gesetzt, nicht
am fertigen Video geprueft — Sichtpruefung am Lauf vom 20.08.2026.
