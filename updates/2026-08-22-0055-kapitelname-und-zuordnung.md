---
datum: 2026-08-22
agent: main (Branch retention-a-bis-d)
typ: bugfix
commit: <Hash, sobald bekannt>
---

# Härtung zu B/C: Kapitelname hart gekappt, Still-true-Eintrag aus der Zuordnung

**Was:**

- `video_report.kapitel_bauen()`: neue Konstante `KAPITELNAME_MAX = 44`; der
  YouTube-Kapitelname wird nach dem Tag-Strip an der Wortgrenze gekappt.
- `video_report.folien_zuordnen()`: Drehbuch-Einträge zum Sammelabschnitt
  „Still true from yesterday" werden aus `eintraege` gefiltert.

**Warum:** Zwei Lücken, die beim Durchgehen der B/C-Änderung auffielen, bevor sie
produktiv liefen:

1. Die 40-Zeichen-Grenze der Headline stand nur als **Prompt-Prosa** in Regel 4a.
   Prompt-Prosa ist keine Zusicherung — hält sich das Modell nicht daran, schneidet
   der YouTube-Player selbst ab, und zwar mitten im Wort. Gekappt wird bewusst nur
   diese eine Darstellung, **nicht** die Überschrift im `bericht.md`: an der hängen
   die Verbatim-Anker des Drehbuchs, ein Schnitt dort würde sie desynchronisieren.
2. Seit C wird der „Still true"-Abschnitt nicht mehr vertont — es gibt also keinen
   Kopf mehr, der seinen Drehbuch-Eintrag über die Überschrift aufnimmt. Über den
   „Rest der Reihe nach"-Pfad in `folien_zuordnen()` wären seine zwei Stichworte
   in ein echtes Kapitel gerutscht, sobald ein anderes Kapitel seinen Heading-Match
   verfehlt. Das Kapitel liefe dann mit fremden Bulletpoints — ein stiller Fehler,
   der erst im fertigen Video auffällt.

**Auswirkung:** Kapitelnamen bleiben lesbar, auch wenn das Modell die Zeichengrenze
reisst. Die Stichwort-Zuordnung kann nicht mehr um einen Eintrag verrutschen.

**Offen:** —
