---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Feel-Paket (B2): Anticipation, Overshoot, gestaffelter Aufbau mit Bewegung

**Was:** Die Bewegungssprache in `video_report._lage()` umgestellt:

- **Einflug** fährt jetzt mit ease-out-back statt cubic ease-out — die
  Karte schiesst ~10 % über ihr Ziel hinaus und setzt zurück. Neues
  Overlay-Feld `einflug_weg` erlaubt kleinen Elementen kürzere Wege.
- **Flug des Fokus-Punkts** (der Signature-Move) läuft mit
  ease-in-out-back statt smoothstep: kurzes Zurücknehmen gegen die
  Flugrichtung (Anticipation), Fahrt, leichtes Überschiessen am Ziel.
- **Detail-Zeilen** bauen sich gestaffelt MIT Bewegung auf: jede Zeile
  fährt 16 Layout-Pixel ein statt nur aufzublenden (nur die Zeilen, nie
  die Kastenstufen — die lösen sich weiterhin hart ab).

Ease-Konstanten als `EASE_C1/C2/C3` (Standard-Back-Easing). Die
ffmpeg-Ausdrücke sind gegen einen echten ffmpeg-Lauf validiert.

**Warum:** Intent B2 — «einzeln Deko, gemeinsam der ganze Unterschied
zwischen PowerPoint-Bewegung und After Effects». B1 (Signature-Move
verallgemeinern) profitiert direkt: derselbe Move trägt jetzt das Feel.

**Auswirkung:** Alle Einflüge (Lower Thirds, Karten, Zitate) und alle
Flüge in die Randspalte wirken physisch statt linear. Keine
Timing-Änderung — nur die Kurvenform; Lesezeit-Verifikation unberührt.
Bewusst NICHT gebaut: Bounce mit Schatten und Motion Blur — beide
brauchen Skalierung/Blur pro Frame, was der PNG/ffmpeg-Weg nicht kann
(Memlog-Befund: nur über PIL-per-Frame; separat zu entscheiden).

**Offen:** Bounce/Motion-Blur nur über einen Per-Frame-Renderweg (§5
offene Entscheidung 1 des Intents).
