---
datum: 2026-08-19
agent: main
typ: infra
commit: 8b20ad4
---

# Story-Reminder-Hook: Update-Tracking wird erzwungen

**Was:** Neuer PostToolUse-Hook `~/.claude/hooks/story-reminder.py` (Matcher `Bash`),
registriert in `~/.claude/settings.json` neben dem bestehenden
`activity-log-reminder.py`. Er erkennt nach jedem Bash-Aufruf einen neuen HEAD-Commit
und erinnert, wenn dieser keine Datei unter `updates/` mitbringt (`updates/README.md`
zählt nicht als Story). Der Hinweis darauf steht neu in `CLAUDE.md`.

**Warum:** Die in `updates/` festgelegte Konvention war bisher nur eine Bitte in
`CLAUDE.md` — ein Agent, der sie überliest, hinterlässt keine Spur. Ein Hook ist der
Mechanismus, der die Regel tatsächlich vor jeden Agenten trägt, analog zum bereits
bewährten Activity-Log-Reminder.

**Auswirkung:** Ab sofort erscheint nach einem Commit ohne Story ein Reminder im
Kontext — genau einmal pro Commit (State in `<git-dir>/story-reminded`). Der Hook ist
**opt-in per Verzeichnis**: ohne `updates/` im Repo-Root tut er nichts, deshalb kann er
global registriert sein, ohne andere Repos zu stören. Merge-Commits werden
übersprungen, da die Story in den gemergten Commits steckt. Der Git-Dir kommt aus
`git rev-parse --absolute-git-dir`, damit der State auch in Worktrees am richtigen Ort
landet — dort ist `.git` eine Datei, kein Verzeichnis. Non-blocking: der Hook kann
einen Commit nicht verhindern, nur erinnern.

**Offen:** —
