---
datum: 2026-08-19
agent: main
typ: infra
commit: (dieser Commit)
---

# Update-Tracking als Stories eingeführt

**Was:** Neues Verzeichnis `updates/` mit Story-Konvention (`updates/README.md`) und
eine Repo-`CLAUDE.md`, die alle Agenten auf diese Konvention verpflichtet. Eine Datei
pro Story, Dateiname `YYYY-MM-DD-HHMM-slug.md`, Story im selben Commit wie die
beschriebene Änderung.

**Warum:** An diesem Repo arbeiten mehrere Agenten, teils parallel in Worktrees
(`.claude/worktrees/`). Bisher war der einzige Verlauf das `activity-log`-MCP —
zentral, einzeilig, und aus Worktrees heraus nicht bedient. Es fehlte eine
repo-lokale Spur mit Begründung und Auswirkung, die mit dem Branch nach `main`
mitwandert.

**Auswirkung:** Ab jetzt schreibt jeder Agent nach einer abgeschlossenen Änderung eine
Story. Einzeldateien statt Sammeldatei, damit parallele Worktree-Merges konfliktfrei
bleiben. Das `activity-log`-MCP bleibt unverändert in Betrieb — die Stories ergänzen
es, ersetzen es nicht. Bewusst *nicht* gebaut: ein erzwingender PostToolUse-Hook;
die Regel steht vorerst nur in `CLAUDE.md`.

**Offen:** Hook analog `activity-log-reminder.py`, falls die CLAUDE.md-Regel in der
Praxis übergangen wird.
