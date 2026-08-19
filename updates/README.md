# Update-Tracking — Stories

Jede abgeschlossene Änderung an diesem Repo wird hier als **Story** abgelegt:
eine Datei pro Story, damit parallel arbeitende Agenten (Worktrees, Subagenten)
sich nicht gegenseitig Merge-Konflikte bauen.

## Regeln

1. **Eine Datei pro Story**, niemals eine gemeinsame Sammeldatei anhängen.
2. **Dateiname:** `YYYY-MM-DD-HHMM-kurz-slug.md` — z.B. `2026-08-19-1240-update-tracking.md`.
3. **Im selben Commit** wie die Code-Änderung, die sie beschreibt.
4. **Nur echte Änderungen** — reine Recherche/Messung gehört nach `research/`,
   nicht hierher.
5. **Nachträglich nicht umschreiben.** Korrigiert eine spätere Story eine frühere,
   verlinkt sie diese, statt die alte zu ändern.
6. Aus einem **Worktree** wird die Story mit dem Feature-Branch nach `main` gemerged —
   sie ist Teil der Änderung, nicht ein separater Schritt.

## Vorlage

```markdown
---
datum: YYYY-MM-DD
agent: <Agentname / "main" / Branch>
typ: feature | bugfix | refactor | infra | docs | chore
commit: <Hash, sobald bekannt>
---

# <Titel in einer Zeile>

**Was:** Was wurde geändert — konkret, Dateien/Funktionen benennen.

**Warum:** Der Auslöser. Welches Problem, welche Messung, welche Anweisung.

**Auswirkung:** Was verhält sich ab jetzt anders — für die Pipeline, den Cron-Lauf,
das fertige Video. Auch: was bewusst *nicht* geändert wurde.

**Offen:** Was noch aussteht, oder `—`.
```

## Verhältnis zum activity-log

Das `activity-log`-MCP bleibt der projektübergreifende Einzeiler-Verlauf pro Commit.
Die Stories hier sind die ausführliche, repo-lokale Fassung mit Begründung und
Auswirkung. Beides wird geführt, keines ersetzt das andere.
