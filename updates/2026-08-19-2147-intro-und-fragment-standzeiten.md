---
datum: 2026-08-19
agent: fix/intro-und-fragment-standzeiten (Worktree)
typ: bugfix
commit: Feature-Branch fix/intro-und-fragment-standzeiten (Hash siehe Merge nach main)
---

# Erster Titel und Stichwort-Fragmente stehen lange genug zum Lesen

**Was:** Drei Timing-Änderungen in `video_report.py`:

1. **Kaltstart-Schlagwort:** `KALTSTART` 2.0 → 3.5 s als Wunschdauer, neu mit
   Boden `KALTSTART_MIN = 2.0`. Der Wechsel zur Hook-Karte ist jetzt adaptiv:
   `hook_ab = min(KALTSTART, max(KALTSTART_MIN, intro_bis − Hook-Lesezeit))`.
   Die Hook-Lesezeit rechnet mit `HOOK_CPS = 17` (Untertitel-Norm statt
   Nebenher-Tempo, weil der Hook wörtlich mitgesprochen wird) plus
   `HOOK_VORLAUF = 0.5`.
2. **Stichwort-Fragmente:** Lesezeit-Böden angehoben — `DETAIL_FRAG_MIN`
   1.4 → 2.0 s, `DETAIL_CPS` 12 → 10.
3. **Messbarkeit:** `szenen_bauen()` loggt neu, wie viele Fragmente gezeigt
   und wie viele wegen zu enger Fenster von hinten weggekürzt wurden.

**Warum:** Nutzer-Feedback 19.08.2026: der erste Titel am Videoanfang (das
Schlagwort des Tages, z.B. «$120K GONE») war nur 2.0 s im Bild — ein
Aufblitzen; und gewisse Stichwort-Fragmente standen zu kurz, um lesbar zu
sein. Nachgerechnet am Video vom 19.08.: Schlagwort 0–2.0 s, kürzeste
Fragmente exakt auf dem 1.4-s-Boden.

**Auswirkung:** Beim 19.08.-Timing steht das Schlagwort neu ~3.1 s statt 2.0 s,
die Hook-Karte behält ≥ ihre entspannte Lesezeit (~4.3 s). Jedes Fragment
steht mindestens 2.0 s bzw. Zeichenzahl/10 s. Engere Fenster zeigen dafür
bewusst weniger Fragmente (Kürzung von hinten) statt unlesbare — der neue
Log-Zähler macht sichtbar, ob die höheren Böden das Feature auffressen; dann
wären die Böden zurückzunehmen (Richtung 1.8 / 11), nicht die Fragmente.
Bewusst nicht geändert: `DETAIL_VERSATZ`, `DETAIL_MIN`, der Cold Open ohne
Aufblende.

**Offen:** Fragment-Wegfallquote im nächsten Cron-Log (`Stichwort-Fragmente:`)
prüfen.
