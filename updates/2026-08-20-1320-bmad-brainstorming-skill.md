---
datum: 2026-08-20
agent: feature/bmad-brainstorming
typ: feature
commit: <wird nach Commit ergänzt>
---

# BMAD-Brainstorming-Skill aus BMAD-METHOD übernommen

**Was:** Nur das Brainstorming-Modul der BMAD-METHOD (bmad-code-org/BMAD-METHOD,
MIT-Lizenz, v6.11.0) übernommen, nicht die volle Methode:

- `.claude/skills/bmad-brainstorming/` — SKILL.md, `references/` (Facilitator-/
  Partner-/Autonom-Modus, Konvergenz, Abschluss, Resume, Headless), `assets/`
  (Techniken-Katalog `brain-methods.csv`, `brain-selector.html`), `scripts/brain.py`
  (Techniken-Auswahl-CLI), `customize.toml`.
- `_bmad/scripts/` — `memlog.py`, `resolve_config.py`, `resolve_customization.py`,
  `config_utils.py` (Kern-Skripte, die der Skill über `uv run` aufruft).
- `_bmad/config.toml` — zentrale Konfiguration (Deutsch, `output_folder = "research"`,
  Projektname boardstats), handgeschrieben statt über den npm-Installer, da dieser
  fehlende Node-Dependencies (`commander`) hatte und ohnehin die volle Methode
  installiert hätte.

Alle drei Kern-Skripte lokal getestet (`resolve_config.py`, `resolve_customization.py`,
`memlog.py init`, `brain.py list --category structured`) — laufen mit `uv run`.

**Warum:** Nutzer wollte gezielt nur das Brainstorming-Modul, nicht die volle
BMAD-Method-Installation (die eigene Story-/Planungs-Kaskade (PRD/Architecture/Epics)
und Worktree-fremde Agentenrollen mitbringt, die mit den bestehenden Konventionen
dieses Repos kollidieren würden — siehe `updates/README.md` und die Worktree-Pflicht
in `CLAUDE.md`).

**Auswirkung:** Ab jetzt per `/bmad-brainstorming` (oder "hilf mir beim Brainstorming")
in Claude Code nutzbar. Sessions landen unter `research/brainstorming/` — bereits in
`.gitignore` gelistet, analog zu Messungen/Recherchen, kein Commit nötig. Ändert nichts
an der bestehenden Pipeline (Crawl/Bericht/Video) oder am `updates/`-Story-System.
Bewusst NICHT übernommen: die restlichen BMAD-Module (PM/Architect/Dev/QA-Agenten,
PRD-/Epic-Workflows), der npm-Installer selbst, `bmad-party-mode` und
`bmad-advanced-elicitation` (im SKILL.md erwähnt, aber nicht installiert — Erwähnung
im Begrüssungstext ist harmlos, da der Skill nur die tatsächlich vorhandenen nennt).

**Offen:** `_bmad/custom/config.toml` bzw. `.user.toml` für persönliche Overrides
(z.B. `favorite_techniques`) existieren noch nicht — bei Bedarf später anlegen.
