---
datum: 2026-08-19
agent: main
typ: infra
commit: 1dd9d03
---

# Overseer-Rolle als lokaler Skill persistiert

**Was:** Neue Datei `.claude/skills/pipeline-overseer/SKILL.md` — dokumentiert
die stehende Overseer-Rolle (Testvideos generieren, main-Updates prüfen,
Pipeline-Gesamtüberblick): Cron-Architektur (`run.sh`/`report.sh`/`video.sh`
auf hp-ubuntu), getrennte Python-Umgebungen (lokal vs. hp-ubuntu-venv),
Test-Video-Flags von `video_report.py` (`--vorschau`, `--nur-video`,
`--bett-bauen`), Prüf-Checkliste pro Commit (ruff/mypy/pytest, Story,
Activity-Log, hp-ubuntu-Sync), sowie Referenzwerte (TTS-Kontingent,
Intro-Länge, Tonwerte, Retention-Fristen).

**Warum:** Nutzeranweisung, die Overseer-Rolle explizit zu persistieren,
statt sie nur im Gesprächskontext/Gedächtnis zu halten — soll bei jeder
neuen Konversation zu diesem Repo sofort verfügbar sein und laufend
weitergepflegt werden.

**Auswirkung:** Keine Laufzeitänderung an der Pipeline. Neu: eine explizite,
im Repo versionierte Wissensquelle für die Overseer-Kontrolle. Enthält auch
eine bisher nur im persönlichen Memory dokumentierte Sicherheitsnotiz (lokale
`~/.config/boardstats/`-Credentials sind echte Produktionsdaten — lokale
Testläufe immer mit Test-Flag).

**Offen:** Skill-Inhalt ist ein Snapshot vom 19.08.2026 (Cron-Zeiten,
Paketstände, Kontingentwerte) — muss bei künftigen Änderungen an diesen
Fakten von der Overseer-Instanz selbst nachgeführt werden.
