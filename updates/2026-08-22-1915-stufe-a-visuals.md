---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Stufe-A-Visuals: Kapitel-Akzente, Rot/Grün-Pfeile, echtes Zählwerk, Kamera-Rauschen

**Was:** Vier Beats der Intent-Stufe A:

- **#136 Akzentfarbe je Kapitelthema:** `design_tokens.KAPITEL_AKZENT`
  (Krypto = Serien-Amber, Aktien = Blau, Meme = Grün),
  `szenen.akzent_setzen()` schaltet den Modul-Akzent um,
  `video_report.kapitel_akzent()` klassifiziert per Wortliste über
  Überschrift/Titel/Stichworte; nach dem Kapitelblock Rückstellung auf
  Amber (Intro/Zahlen/Outro bleiben Serienrahmen).
- **#35 Farbe UND Pfeil bei gerichteten Zahlen:** neue Tokens
  `GRUEN`/`ROT`, `szenen.zahl_farbe()`; `zahl_tafel` färbt Wert+Icon,
  `zahlen_uebersicht` zeigt jetzt pro Zeile Trend-Icon und Farbwert.
  Die Herleitung bleibt `_zahl_richtung` (nur explizite Vorzeichen —
  Leitplanke 7 unangetastet).
- **#82 Count-up als echtes Zählwerk:** `countup_werte()` erzeugt bis zu
  13 ease-out-verteilte Zwischenstände (dedupliziert), Ziellänge 1,3 s
  statt 0,64 s, gedeckelt auf 45 % des Fensters; beim Einrasten blitzt
  der Endwert kurz weiss auf (`zahl_tafel(flash=True)`, C1
  Flash-on-change; das Abbremsen ins Ziel ist zugleich das C1
  Time-Remapping).
- **#145 Sub-Pixel-Rauschen:** zoompan-Kameraposition schwingt mit ~0,5
  Ausgabepixeln bei ~1 Hz (x/y inkommensurabel).

**Warum:** Brainstorm-Intent 22.08.2026, Stufe A («wirkt sofort, ändert
nichts an der Architektur»).

**Auswirkung:** Kapitel sind farblich unterscheidbar («wer Minute 3 sah,
sah Minute 8» entfällt), gerichtete Zahlen lesen sich auf einen Blick,
der Count-up ist erstmals wahrnehmbar. Visuell verifiziert (farbige
Übersicht, blaues Aktien-Kapitel).

**Offen:** Musikbett-Aussetzer (#137) und Kapitel-Schwarzblende (#80/69)
folgen mit dem Sound-Design (B5) im nächsten Schritt — die Schwarzblende
ohne Ton wäre laut Intent nicht zu empfehlen.
