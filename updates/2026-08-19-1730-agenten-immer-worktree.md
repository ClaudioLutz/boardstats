---
datum: 2026-08-19
agent: main
typ: docs
commit: <folgt>
---

# Worktree-Pflicht für alle Agenten in CLAUDE.md verankert

**Was:** Neuer Abschnitt "Worktrees — Pflicht für alle Agenten" in `CLAUDE.md`,
oberhalb des Update-Trackings. Er schreibt fest, dass jeder schreibende Agent
(Subagent, Workflow-Agent, Task) mit `isolation: "worktree"` bzw.
`opts.isolation: 'worktree'` in einem eigenen Worktree auf eigenem Feature-Branch
arbeitet, und dass der Branch am Ende ohne Rückfrage nach `main` gemerged, gepusht
und auf `hp-ubuntu` gepullt wird.

**Warum:** Anweisung des Users ("es müssen alle Agenten immer mit git worktrees
arbeiten" / "und dann in main pushen wenn fertig"). Bisher stand die Merge-Pflicht
nur im persönlichen Memory; im Repo selbst fand ein frisch gestarteter Subagent
keine Regel dazu.

**Auswirkung:** Agenten in diesem Repo lesen die Regel direkt aus `CLAUDE.md`, auch
ohne Memory-Kontext. Am Code der Pipeline ändert sich nichts.

**Offen:** —
