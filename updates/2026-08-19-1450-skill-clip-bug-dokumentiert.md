---
datum: 2026-08-19
agent: main
typ: docs
commit: 451f9bd
---

# Overseer-Skill: Clip-Katalog-Bug als geklärt markiert

**Was:** `.claude/skills/pipeline-overseer/SKILL.md` — den bisher als
"ungeklärt" geführten Punkt zum Verschwinden von `arbeit/clips/` in einen
neuen Abschnitt "Geklärte Fälle" verschoben, mit Verweis auf den Fix in
`034ae86`, sowie die Reuse-Ausnahme (`zuletzt_verwendet == heute` zählt als
frei) bei den Betriebswerten ergänzt.

**Warum:** Direkte Folge der Root-Cause-Analyse in `034ae86` — der Skill
soll den aktuellen Wissensstand tragen, nicht einen inzwischen gelösten
Punkt weiter als offen führen.

**Auswirkung:** Keine Code-Änderung, nur Dokumentation.

**Offen:** —
