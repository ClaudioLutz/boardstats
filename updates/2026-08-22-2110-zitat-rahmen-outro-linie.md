---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Zitat-Highlight-Rahmen (C2) und selbstzeichnende Outro-Linie (C1 Trim Paths)

**Was:**

- **Zitat-Rahmen:** `szenen.zitat_rahmen()` zeichnet eine Akzent-Kontur
  exakt um die selbst gerenderte Post-Karte (gemeinsame Geometrie über
  neues `_zitat_kasten()`). `_zitat_rahmen_auflegen()` blendet ihn 0,9 s
  nach der Karte für 2,2 s ein — bei Kapitel- UND Schluss-Zitat; nie in
  fremden Screenshots (C2-Vorbehalt), nie bei zu kurzen Fenstern.
- **Trim Paths:** die Amber-Linie der Outro-Tafel zeichnet sich in sechs
  hart geschnittenen Stufen selbst (`szenen.outro_linie_stufen()`,
  `outro_tafel(linie=False)` trägt sie nicht mehr eingebacken) — derselbe
  Stufen-Mechanismus wie beim Count-up, beginnend nachdem die Tafel
  eingefahren ist.

**Warum:** Intent C1 («Trim Paths — über wandernde Maske; am Bild
verifiziert» — hier als Stufenfolge, der Masken-Weg des PNG-Pfads) und
C2 (Highlight-Rahmen nur in der eigenen Post-Karte).

**Auswirkung:** Zitate bekommen einen geführten Blick-Moment, der Abbinder
einen gezeichneten Abschluss statt einer stehenden Linie.

**Offen:** —
