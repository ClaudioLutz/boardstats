---
datum: 2026-08-19
agent: main
typ: feature
commit: <folgt>
---

# Musikbett im Vorspann 7 dB lauter

**Was:** `video_report.py`:

- Neue Funktion `kapitel_eins_start()` liefert den Startzeitpunkt des ersten
  gesprochenen Worts der ersten `##`-Überschrift — also das Ende des
  Vorspanns.
- Neue Funktion `_intro_anhebung()` baut daraus einen `volume`-Ausdruck, der
  das Bett bis dahin anhebt und über `BETT_INTRO_RAMPE` (2.5 s) auf
  Normalpegel zurückfährt.
- Der Zeitpunkt wird durch `szenen_video()` / `video_erzeugen()` →
  `ton_argumente()` → `_ton_kette()` und `_loudnorm_gemessen()` gereicht;
  bisher kannte die Tonmischung nur `ende`.
- Neue Konstanten `BETT_INTRO_ANHEBUNG = 7.0` dB und `BETT_INTRO_RAMPE = 2.5` s.
- Neu `tests/test_tonmischung.py` (9 Tests).

**Warum:** Die ersten dreissig Sekunden sind unter jeder Hypothese der
wertvollste Teil des Videos — die Analytics-Messung vom 19.08.2026 zeigt
24 % Abgang in den ersten 17 Sekunden. Dort trägt die Musik den Schwung,
während später der Inhalt trägt. Die gemessene Vorspannlänge liegt bei rund
30 s bis Kapitel 1.

**Auswirkung:** Gegen ffmpeg mit dem echten `bett.opus` gemessen (Stille als
Sprachspur, damit der Sidechain nicht duckt): ohne Anhebung liegt das Intro
3.56 dB unter dem Rumpf, mit Anhebung 3.44 dB darüber — eine Verschiebung von
exakt 7.00 dB.

Die Anhebung sitzt **hinter** `sidechaincompress`, nicht davor: das Ducking
formt weiter wie bisher, nur auf höherem Grundpegel. `_loudnorm_gemessen()`
misst dieselbe Kette, die Endlautheit bleibt also auf `ZIEL_LUFS`. Ohne
bekannte Kapitelmarke (`kapitel1 = 0`) bleibt die Kette unverändert — lieber
gar keine Anhebung als eine auf geratenem Zeitpunkt.

Bewusst **nicht** umgesetzt: eine entsprechende Anhebung im Outro. Dafür gäbe
es keinen eigenen Zeitpunkt in der Tonmischung, und die vorhandene
`BETT_AUSBLENDE` von 4 s deckt den Schluss bereits ab.

**Offen:** Ob 7 dB der richtige Wert ist, entscheidet das Ohr am fertigen
Video — die Zahl ist eine Starthypothese, so wie `STUDIO_KAPITEL_RATE` und
`STUDIO_ZAHL_RATE` aus derselben Runde.
