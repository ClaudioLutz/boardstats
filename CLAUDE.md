# CLAUDE.md — boardstats

## Worktrees — Pflicht für alle Agenten

Jeder Agent, der am Repo etwas ändert (Subagent, Workflow-Agent, Task), arbeitet
**immer** in einem eigenen Git-Worktree auf einem eigenen Feature-Branch — nie direkt
im Haupt-Checkout auf `main`:

- Agent-Tool: `isolation: "worktree"`; Workflow-Agenten: `opts.isolation: 'worktree'`
- Grund: im Haupt-Checkout laufen parallel Generierungen und andere Agenten; direkte
  Schreibzugriffe kollidieren (halbfertige Dateien, verlorene Änderungen)
- Reine Lese-/Recherche-Agenten brauchen keinen Worktree; im Zweifel trotzdem einen

**Abschluss ist Pflicht:** Sobald die Arbeit im Worktree fertig ist (Validierung grün,
Commit sauber, Story dabei), den Feature-Branch ohne Rückfrage nach `main` mergen
(`git merge --no-ff <branch>`) und pushen. Danach auf `hp-ubuntu` pullen
(`ssh hp-ubuntu "cd /home/hp-ubuntu/boardstats && git pull --ff-only origin main"`),
sonst läuft die Cron-Produktion weiter auf altem Code. Ein Worktree, der nicht in
`main` landet, ist wertlos.

## Update-Tracking — Pflicht für alle Agenten

Nach **jeder** abgeschlossenen Änderung am Repo (Haupt-Session, Subagent, Worktree-Agent)
eine Story in `updates/` ablegen:

- Eine Datei pro Story: `updates/YYYY-MM-DD-HHMM-kurz-slug.md`
- Niemals in eine gemeinsame Sammeldatei anhängen (Merge-Konflikte bei parallelen Agenten)
- Im **selben Commit** wie die beschriebene Änderung
- Format und Vorlage: `updates/README.md`
- Aus einem Worktree wandert die Story mit dem Feature-Branch nach `main`

Reine Recherche/Messung ohne Code-Änderung gehört nach `research/`, nicht nach `updates/`.

Ein PostToolUse-Hook (`~/.claude/hooks/story-reminder.py`) erinnert nach jedem Commit,
der keine Story mitbringt. Dieser Erinnerung folgen, nicht ignorieren.

Das ersetzt das `activity-log`-MCP nicht — dort weiterhin den Einzeiler pro Commit
protokollieren.

## Struktur (Kurzorientierung)

- `run_report.py` — Bericht-Pipeline (Crawl → Extrakt → Bericht)
- `video_report.py`, `szenen.py`, `folien.py`, `thumbnail.py` — Video-Pipeline
- `youtube_auth.py`, `analytics_bericht.py` — Upload und Erfolgskontrolle
- `research/` — Messungen und Recherchen (lokal, nicht im Git)
- `updates/` — Story-Verlauf der Änderungen (im Git)

## Validierung

Nach Python-Änderungen: `ruff check` und `mypy` ausführen.
