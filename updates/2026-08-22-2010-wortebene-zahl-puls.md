---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Wortebene (B3): die Zahl im Fokus-Punkt färbt sich, wenn sie gesprochen wird

**Was:** Neuer Renderer `szenen.fokus_zahl_overlay()` — rendert NUR die
Zahl-Tokens des Stichpunkts (farbig per `zahl_farbe`: Grün/Rot bei
Vorzeichen, sonst Kapitel-Akzent) pixel-deckungsgleich über der
Fokus-Karte (Positionierung über Präfix-Breiten derselben Schrift, kein
zweiter Kasten — Doppel-Alpha vermieden). `szenen_bauen` findet den
Sprechmoment der Zahl über dieselbe Fundort-Suche wie die
Detail-Fragmente (`_detail_fundort`) und legt den Puls `ZAHL_PULS_DAUER`
(1,1 s, Blende 0,18 s) über die Karte; Ende immer vor Flugbeginn.

**Warum:** Intent B3 («das TikTok-Paket») in der Form, die die C2-Hürde
respektiert: der Text im Bild ist nicht der gesprochene Text — Wort-Pop im
TikTok-Sinn geht nicht, aber «die Zahl darin färbt sich, wenn sie
gesprochen wird» ist der Effekt ohne den Mechanismus. Deckt zugleich
Idee 28 (Puls auf harten Zahlen) und die Keyword-Färbung (32) ab; das
Stichwort selbst erscheint ohnehin an seiner Ankerstelle (Einflug = Puls).

**Auswirkung:** Jeder Fokus-Punkt mit Zahl bekommt einen synchronen
Farb-Moment. Kein Puls, wenn der Fundort fehlt oder das Fenster unter
0,4 s liegt — lieber kein Effekt als ein versetzter (Intent-B5-Regel gilt
sinngemäss auch hier). Deckungsgleichheit visuell verifiziert.

**Offen:** —
