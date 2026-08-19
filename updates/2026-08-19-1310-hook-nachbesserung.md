---
datum: 2026-08-19
agent: main
typ: infra
commit: 30161ca
---

# Story-Hook: PowerShell-Lücke und Cron-Fehlalarme geschlossen

**Was:** Drei Nachbesserungen am Story-Reminder-Hook, alle in `~/.claude/` (ausserhalb
dieses Repos):

1. Matcher in `settings.json` von `Bash` auf `Bash|PowerShell` erweitert.
2. Alters-Gate `MAX_ALTER_S = 3600` in `story-reminder.py`: Commits, deren
   Committer-Timestamp älter als eine Stunde ist, lösen keine Story-Pflicht aus.
3. Der Worktree-Pfad ist jetzt nicht mehr nur plausibel, sondern getestet.

**Warum:** Zu 1 — diese Umgebung hat neben Bash auch ein PowerShell-Tool; ein Agent,
der darüber committet, wäre am Reminder vorbeigelaufen, obwohl der Anspruch «alle
Agenten» war. Zu 2 — der Cron auf hp-ubuntu committet täglich zwei Datei-Commits
(«Extrakte vom …», «Bericht vom …»). Nach jedem `git pull` wäre so ein Commit HEAD,
ohne Story, und `CLAUDE.md` sagt «dieser Erinnerung folgen» — das hätte täglich
Junk-Stories für automatische Daten-Commits erzeugt. Ein Commit der laufenden Session
ist Sekunden alt, ein gepullter Stunden; der Timestamp trennt das ohne
Author-Heuristik. Nebeneffekt, ebenfalls gewollt: manuelle Commits ausserhalb einer
Claude-Session erzeugen keine Story-Pflicht.

**Auswirkung:** Verifiziert in einem Wegwerf-Repo: alter Commit ohne Story → still;
frischer Commit ohne Story → Reminder; Commit in einem echten `git worktree` →
Reminder, State landet korrekt in `.git/worktrees/<name>/story-reminded`. Wer ein
Cron-Commit doch dokumentieren will, schreibt die Story von Hand — der Hook fordert
sie nur nicht mehr ein.

**Offen:** Das Alters-Gate greift auch, wenn ein Agent länger als eine Stunde nach dem
eigenen Commit weiterarbeitet, ohne die Story geschrieben zu haben. Dann bleibt nur
die `CLAUDE.md`-Regel.
