---
datum: 2026-08-22
agent: worktree-lesezeit-verstoesse
typ: bugfix
commit: 9343181
---

# Lesezeit-Verstoesse: Quelle in der Warnung, Schluss-Zitat bekommt Vorlauf

**Was:** Drei Aenderungen, davon wirkt eine auf die gemeldeten Verstoesse:

1. **Diagnose (wirkt):** `Overlay` und `KartenStand` tragen neu
   `lese_quelle`, an allen 13 Boden-Stellen gesetzt. Die Warnung nennt jetzt
   den Beat und das Defizit:
   `LESEZEIT-VERSTOSS [fokus-punkt]: '...' effektiv 2.60s, Boden 2.70s
   (fehlen 0.10s)`. Vorher stand dort nur der Text — um zu wissen, woher
   der Boden kommt, musste man ihn im Code suchen.
2. **Schluss-Zitat (wirkt):** Das Fenster zwischen Zitat und Cliffhanger
   gibt die Sprechzeit vor und traegt `ZITAT_MIN` nicht. Nach hinten ist
   kein Platz (dort spricht die Frage), also faengt der Beat frueher an —
   begrenzt durch das Ende des vorherigen Satzes. **Defizit 1.17s → 0.37s.**
3. **Count-up (wirkt hier nicht, aber richtig):** `max(0.4, ...)` erzwang
   ein Zaehlwerk auch dann, wenn dafuer die Standzeit des Endwerts unter
   `ZAHL_COUNTUP_MIN` fiel. Jetzt faellt bei knappem Fenster das Zaehlwerk
   weg statt der Lesezeit (`COUNTUP_MIN_DAUER`). Neu ausserdem
   `FRAME_PUFFER` (2 Frames): die Planung rechnet in Sekunden, gerendert
   wird in Frames.

**Warum:** Der produktive Lauf vom 22.08. meldete 4 Verstoesse (im
Kettentest derselben Nacht waren es 0 — der echte Tagestext ist dichter).

**Auswirkung, ehrlich gerechnet:**

| Quelle | vorher | nachher |
|---|---|---|
| schluss-zitat | 1.17s | **0.37s** |
| zahl-countup | 0.15s | 0.15s (unveraendert) |
| fokus-punkt | 0.10s | 0.10s (unveraendert) |
| fokus-punkt | 0.07s | 0.07s (unveraendert) |

`ruff`/`mypy` sauber, 289 Tests gruen, an den echten Daten des 22.08.
gegengeprueft (Vertonung aus dem Cache, keine TTS-Kosten).

**Offen — und was ich ausgeschlossen habe:** Meine Hypothese fuer die drei
kleinen Defizite war die Frame-Rundung. Sie ist widerlegt: mit
`FRAME_PUFFER` in `boden` (Zeile ~3415) aendert sich an ihnen **nichts**.
Die betroffenen Fokus-Punkte laufen also nicht ueber die dort geprueften
Fenster, oder `sicht_bis()` liefert ein groesseres Fenster als das
Overlay am Ende wirklich hat. Naechster Schritt waere, in der Planung
und in `lesezeit_verifizieren()` fuer denselben Punkt die Zwischenwerte
(`von`, `bis`, `flug_ab`, `einblend`, `ausblend`) nebeneinander
auszugeben — die Abweichung sitzt zwischen diesen beiden Rechnungen.
Verdacht, nicht belegt: bei **fliegenden** Punkten prueft die Planung
gegen `z = ab + FLUG_DAUER`, die Verifikation aber gegen `flug_ab` — zwei
verschiedene Fensterenden.

Die Defizite sind mit 0.07–0.15s klein (2–4 Frames); dass sie ueberhaupt
sichtbar sind, ist ein Verdienst der Verifikation, nicht ein neuer Schaden.
