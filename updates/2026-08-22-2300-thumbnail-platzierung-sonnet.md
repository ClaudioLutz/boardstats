---
datum: 2026-08-22
agent: claude/video-thumbnail-meme-60c124
typ: feature
commit: <Hash, sobald bekannt>
---

# Sonnet entscheidet, wo die Schlagzeile im Meme-Vorschaubild steht

**Was:** `thumbnail.bauen()` nimmt jetzt `zone` (oben/mitte/unten) und
`ausrichtung` (links/mitte/rechts); `_block_oben()` und `_zeile_links()`
setzen sie um, `platzierung_messen()` bestimmt sie deterministisch aus der
Kantenaktivitaet des fertigen Zuschnitts (drei Baender, drei Spalten, Raster
160x90, `ImageFilter.FIND_EDGES`). Neu in `video_report.py`:
`_thumb_platzierung()` — ein Sonnet-Aufruf mit `rr.claude_ruf(..., tools="Read",
cwd=rr.BASE, effort="low")` und `THUMB_PROMPT_PLATZIERUNG`, der das Motiv
ansieht und Zone plus Ausrichtung mit Begruendung liefert. `vorschaubild()`
reicht das Urteil an `bauen()` weiter.

**Warum:** Ohne dunkle Abdeckung (siehe
`2026-08-22-2230-thumbnail-meme-ohne-abdeckung.md`) haengt die Lesbarkeit
daran, WO der Text steht — eine feste Zone verdeckt beim naechsten Motiv das
Gesicht oder die Pointe. Anweisung: die Platzierung soll jeweils Sonnet
machen.

**Auswirkung:** Ein zusaetzlicher Modellaufruf pro Video-Lauf (Sonnet, effort
low, Timeout 120 s). Das Urteil zaehlt nur mit eigener Bildbeschreibung von
mindestens 20 Zeichen — dasselbe Beleg-Prinzip wie
`run_report._sicht_antwort`, weil ein headless-Aufruf sonst ein
wohlgeformtes Urteil ohne Blick ins Bild liefern kann. Bei fehlendem Beleg,
Muell-Antwort, Timeout oder unbekannter Zone greift die Messung; ohne Motiv
entfaellt der Aufruf ganz. Das Vorschaubild entsteht in jedem Fall.
Bewusst nicht geaendert: das bereits gesetzte Live-Thumbnail von
`0V9DGLtRkdk` (steht mit Zone oben und ist so abgenommen).

**Offen:** Probe am Rage-Wojak-Motiv: Messung und Sonnet waehlen beide
`unten/rechts` (Sonnet-Grund: "Gesicht mit Augen und Mund fuellt oben und
links das Bild komplett aus"). Ob das Urteil bei ruhigeren Motiven
(Chart-Screenshots, Textbilder) genauso gut trifft, zeigt erst der Lauf am
23.08.
