---
datum: 2026-08-20
agent: feature/bmad-deep-recon
typ: feature
commit: <wird nach Commit ergänzt>
---

# BMAD-Deep-Recon-Skill (Research) übernommen

**Was:** Analog zu [[2026-08-20-1320-bmad-brainstorming-skill]] das zweite eigenständige
Core-Skill aus BMAD-METHOD (bmad-code-org/BMAD-METHOD, MIT-Lizenz, v6.11.0) übernommen:

- `.claude/skills/bmad-deep-recon/` — SKILL.md, `references/` (Draft/Process/Run/
  Verification/Synthesis/Finalize/Selection/Lifecycle/HTML-Briefing), `types/`
  (market, domain, technical, competitive, user-voice, academic-lit), `assets/
  research.template.md`, `scripts/recon_kit.py` (deterministische Helfer: Zitat-Check,
  Memlog-Tally, Staleness-Check, Slug-Erzeugung — reines stdlib, `uv run`).
- `_bmad/custom/bmad-deep-recon.toml` — Team-Override: `research_output_path` explizit
  auf `{output_folder}` gesetzt statt Default `{planning_artifacts}/research`, weil
  `planning_artifacts` auf reinen Core-Installs (kein bmm-Modul) auf `output_folder`
  zurückfällt und sonst `research/research/` verschachtelt hätte.
- Keine weiteren Kern-Skripte nötig — `_bmad/scripts/{memlog,resolve_config,
  resolve_customization,config_utils}.py` sind bereits aus dem Brainstorming-Merge
  vorhanden, deep-recon nutzt dieselben.

Bewusst NICHT übernommen: die drei Deprecated-Shims (`bmad-market-research`,
`bmad-domain-research`, `bmad-technical-research` — leiten nur an deep-recon weiter),
der Web-Bundle (`web-bundles/market-and-industry-research/`, für ChatGPT/Gemini-Web-UI
gedacht, nicht Claude Code), sowie der `web-researcher`-Subagent aus dem PRFAQ-
Produktmanagement-Workflow (setzt PRD-Infrastruktur voraus, die wir nicht wollen).

`recon_kit.py` und `resolve_customization.py` (inkl. des neuen Overrides) lokal
getestet.

**Warum:** Nutzer wollte nach dem Brainstorming-Skill auch "der research skill etc"
— ein Recherche-Agent-Modul im selben schlanken Format (SKILL.md + references +
assets/scripts, keine PM/Analyst-Agentenrollen).

**Auswirkung:** Ab jetzt per `/bmad-deep-recon` in Claude Code nutzbar. Recherche-Runs
(Draft/Process/Run) landen unter `research/<typ>-<slug>-<datum>/` — bereits gitignored,
kein Commit nötig. Ändert nichts an der bestehenden Pipeline oder am `updates/`-System.

**Offen:** `external_sources`/`preferred_sources`/`subagent_models` sind leer (Default)
— bei Bedarf in `_bmad/custom/bmad-deep-recon.user.toml` persönlich ergänzen.
