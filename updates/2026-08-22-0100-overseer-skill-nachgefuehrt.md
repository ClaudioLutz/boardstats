---
datum: 2026-08-22
agent: main
typ: docs
commit: 0c2a5ad
---

# Overseer-Skill auf den Stand der A–D-Serie gebracht

**Was:** `.claude/skills/pipeline-overseer/SKILL.md` aktualisiert:

- **Intro-Länge**: der als „offener Kritikpunkt" geführte Eintrag (29.6 → 37.0 →
  48.9 s, „eine Decke gibt es nicht") ist ersetzt — es gibt jetzt Boden 11.5 s
  *und* Decke 15 s, gemessen 16.4 s im Kettentest, Kapitel 1 bei 0:17. Inklusive
  der Regel, dass das Kürzen am Boden abbricht (sonst kommt der längere
  Serien-Satz).
- **Wortzahl-Kalibrierung** des Retention-Blocks: von „Neuer Befund" auf
  „behoben mit `6bd295f`", samt der praktischen Folge — solange weniger als fünf
  Messungen vorliegen, kommt keine Laufzeitwirkung mehr aus der Berichtslänge.
- Neuer Abschnitt **„Serie A–D gegen die Abbruchwand"** mit der Nachweistabelle
  des Kettentests (je Stossrichtung die belegende Log-Zeile bzw. der geprüfte
  Frame) und fünf Prüfpunkten für den nächsten produktiven Lauf.
- Die **Falle** dokumentiert, die bei diesem Kettentest zugeschnappt ist:
  `extrakte/` ist die einzige Testausgabe, die *nicht* gitignored ist —
  `git add -A` nimmt sie mit.

**Warum:** Die Wartungsklausel des Skills verlangt, ihn nach jeder
Overseer-relevanten Erkenntnis nachzuführen. Zwei dort als offen geführte Befunde
sind mit `6bd295f` erledigt und hätten sonst als aktuell weitergegolten — ein Skill,
der behobene Probleme als offen führt, schickt die nächste Session auf eine falsche
Fährte.

**Auswirkung:** Der Skill beschreibt wieder den tatsächlichen Stand der Pipeline.
Der nächste Overseer-Durchgang hat eine konkrete Prüfliste für den Abendlauf vom
22.08. — insbesondere die Frage, ob das Modell den `## `-Marker auch produktiv
setzt (`grep -c '^## '` muss ~5–8 ergeben, nicht 0–1).

Ebenfalls nachgeführt (ausserhalb des Repos): das Memory
`video-intro-laenge` — die dort festgehaltenen 29.6 s waren veraltet.

**Offen:** —
