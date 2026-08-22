---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Datengrafik-Beats (C2): Sparkline aus dem Text, TL;DR als Small Multiples

**Was:**

- **Sparkline (C2, Kernbeat):** `video_report._sparkline_daten()` liest
  aus den Kennzahl-Feldern das Muster «down/up … from 61k» — nur wenn
  BEIDE Werte im Berichtstext stehen, entsteht eine Grafik (Leitplanke 7).
  `szenen.zahl_tafel(spark=…)` zeichnet GENAU zwei Punkte und eine gerade
  Verbindung (keine interpolierte Kurve), beschriftet mit den
  Original-Schreibweisen («61k» → «-12%»), farbig nach Richtung. Sie
  erscheint erst auf dem Count-up-Endstand. Prozentwerte ≥100 % fallen
  bewusst weg (sprengen die Mini-Skala).
- **Small Multiples (C2, Kernbeat):** die TL;DR-Übersicht ist keine
  Zeilentafel mehr, sondern vier Mini-Karten im 2×2-Raster
  (`szenen.zahlen_multiples`; `zahlen_uebersicht` komponiert sie weiter
  zu einem Bild). Im Video fliegen die Karten gestaffelt ein
  (`MULTIPLES_VERSATZ` 0,12 s) — die Null-Objekt-Hierarchie aus C1: eine
  Bewegung, die Elemente folgen versetzt. Werte tragen Farbe+Pfeil (A#35).

**Warum:** Die beiden ⭐-Kernbeats des Genre-Entscheids (Datenjournalismus)
aus Stufe C2, in der Form, die Leitplanke 7 vorschreibt: die Form
behauptet nie mehr Genauigkeit als der Board-Post.

**Auswirkung:** Kennzahlen mit belegtem Bezugswert bekommen ein
Verhältnis-Bild, die Tageszahlen lesen sich als vier eigenständige Karten.
Visuell verifiziert (Sparkline-Tafel, 2×2-Multiples).

**Offen:** Der Drehbuch-Prompt könnte künftig einen expliziten
`vergleich`-Bezugswert liefern (heute nur Text-Parsing) — getrennte
Prompt-Änderung in run_report.py.
