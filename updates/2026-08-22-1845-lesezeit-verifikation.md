---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Lesezeit-Verifikation im Lauf: Böden gelten gegen die effektive Lesezeit

**Was:** Leitplanke 3 des Brainstorm-Intents umgesetzt — die Voraussetzung
für alle Animations-Beats der Stufen B und C:

1. `Overlay`, `KartenStand` und `FokusKarte` tragen jetzt `lese_text` und
   `lese_boden`; jede textgebende Erzeugungsstelle in `szenen_bauen`
   (Hook, Agenda, Opener, Zwischenthema, Zitat, Kennzahl-Endstand,
   Zahlen-Übersicht, Fokus-Punkte, Detail-Fragmente) taggt ihren Text und
   den zugehörigen Boden.
2. Neue Funktion `lesezeit_verifizieren(folge, ende)`: rechnet am fertigen
   Szenenplan für jedes Textelement die **effektive** Lesezeit nach
   (Standzeit minus Einflug/Aufblende, minus Ausblende, minus Zeit ab
   Flugbeginn; über Szenengrenzen geteilte Stücke zählen zusammen) und
   meldet jeden Verstoss als `LESEZEIT-VERSTOSS:`-Logzeile plus Summe.
3. Die Planungs-Böden rechnen den Einblendverlust jetzt mit ein
   (`EINBLEND_VERLUST = 0.40`): Fokus-Entscheidung, Opener-Mindestdauer,
   Zitat-Mindestdauer, Detail-Fenster (−0.3 s erste Kastenblende).

**Entscheid warnen vs. korrigieren:** Die Verifikation WARNT nur. Die
Korrekturen sitzen in der Planung (Fenster ohne genug effektive Zeit
bekommen keine Fokus-Karte, Fragmente fallen von hinten weg) — dort gibt es
den Kontext für eine sinnvolle Korrektur; eine nachträgliche pauschale
Verlängerung würde gegen die TTS-verankerten Zeitpunkte arbeiten.

**Warum:** Nutzeranforderung 22.08.2026: «wichtig ist, dass die Zeit
gemessen wird, wie lange Text sichtbar ist». Ein Einflug (0,40 s) plus
Aufblende (0,35 s) plus Ausblende (0,35 s) frisst rund 1,1 s — genau den
bisherigen absoluten Fokus-Boden. Ohne diese Prüfung zerstört jeder
zusätzliche Beat schleichend die Lesbarkeit.

**Auswirkung:** Kurze Fenster kippen etwas früher in «Punkt erscheint
direkt in der Liste» statt einer nicht lesbaren Fokus-Karte; Zitat- und
Opener-Szenen stehen 0,4 s länger. Jeder Lauf loggt
`Lesezeit-Verifikation: N Textelemente, …`. Tests: `tests/test_lesezeit.py`
neu, Zitat-Replika in `test_schlussbild.py` nachgeführt.

**Offen:** —
