---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Sound-Design (B5), Kapitel-Schwarzblende mit Knall (A#80/69), Bett-Aussetzer (#137)

**Was:**

- **Neues Modul `sounds.py`:** vier synthetische, deterministische
  Geräusche (Whoosh für den Flug, Klick fürs Parken, Impact für die Zahl,
  tieferer Impact für den Kapitelwechsel) — kein Sample-Pack, kein
  Content-ID-Risiko, wie beim synthetischen Musikbett. `effekt_spur()`
  mischt die Ereignisliste in eine 48-kHz-WAV (int16-Array, punktuelle
  Mischung).
- **`szenen_bauen` liefert jetzt `(folge, klang)`:** die Klangzeitpunkte
  entstehen aus denselben Planwerten wie die Bewegungen (flug_ab,
  Count-up-Endstand, kopf_start) — die Intent-Bedingung «exakt auf der
  Bewegung» ist damit konstruktiv erfüllt.
- **Kapitelwechsel:** jede Kapitel-Szene trägt `kapitel_knall`; die
  Vorszene endet mit 0,16 s Schwarzblende statt Kreuzblende
  (`SCHWARZ_BLENDE`, im 0,1–0,25-s-Retention-Fenster des Intents), der
  Kapitel-Impact liegt auf dem Opener-Start. Die 2,5-s-Sprechpause vor
  jeder Überschrift liefert die Ton-Stille gratis.
- **Bett-Aussetzer vor der grössten Zahl (#137):** `_zahl_senke()` senkt
  das Bett 0,5 s vor dem ersten TL;DR-Count-up auf 5 % und bringt es nach
  dem Zählwerk weich zurück; verkettet hinter Ducking und Intro-Anhebung.
- **Tonkette:** `_ton_kette`/`ton_argumente`/`szenen_video` nehmen
  `zahl_moment` und `effekte`; Effekte laufen als dritter amix-Eingang
  bewusst NICHT durchs Ducking. Fällt der Effektbau aus, läuft der Ton
  wie bisher (try/except in main).

**Warum:** Intent B5 («der billigste Sprung Richtung produziert») und die
Kopplung aus Stufe A: die Schwarzblende ohne Ton liest sich als Fehler —
beide zusammen gebaut, wie gefordert.

**Auswirkung:** Sieben Kapitel-Beats pro Video (Schwarz + Knall), hörbare
Flüge/Parkvorgänge, ein akustisch abgesetzter Zahlen-Moment. Pegel in
`sounds.PEGEL` bewusst leise (Leitplanke 5) — Feinabstimmung per Ohr am
ersten echten Video. Tests: `tests/test_sound_design.py` (8 neue).

**Offen:** Pegel-Feinabstimmung nach dem ersten Cron-Lauf.
