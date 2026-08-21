---
datum: 2026-08-21
agent: main
typ: docs
commit: <wird beim Commit ergänzt>
---

# Overseer-Skill: Abendrhythmus-Serie vom 20.08. geprüft und nachgetragen

**Was:** `.claude/skills/pipeline-overseer/SKILL.md` um die acht seit dem
letzten Abgleich (`2806ca6`) auf `main` gelandeten Feature-Commits ergänzt,
nach vollem Checklisten-Durchlauf (ruff/mypy/pytest lokal, hp-ubuntu-Sync,
Story-/Activity-Log-Abgleich, Code-Lese-Verifikation der Integrationsnähte):

- Cron-Tabelle auf den neuen Abendrhythmus umgestellt (20:35/21:15/23:30,
  `231c51a`), Crontab auf hp-ubuntu per `crontab -l` gegengeprüft — passt.
- Neuer "Geklärte Fälle"-Eintrag: Snapshot-Race-Condition behoben (`3b3f4d5`,
  atomarer Rename via `.tmp`) — schliesst den in der Vorsession selbst
  geflaggten Task.
- Neue Sektion "Neue Pipeline-Stufe: Tages-Shorts" (`shorts.py`,
  `4d4b34e`/`6a26128`): Marker, Ähnlichkeits-Guard, eigenständiges
  `--datum`-Flag zum Testen unabhängig von der Report→Video-Kette.
- Neuer Hinweis in "Testvideos generieren": der Report→Video-Kettentest ist
  seit `7191699`/`c33885c` nicht mehr ohne Weiteres möglich, weil
  `video_report.py` hart `extrakte/<heutiges Datum>/` liest, ein
  `--trockenlauf` von `run_report.py` aber genau dorthin nichts mehr
  schreibt (Zustandsschutz) — Konsequenz selbst erlebt: kein echter
  End-to-End-Testlauf für die ganze Serie möglich, ohne entweder auf den
  echten Cron-Lauf zu warten oder den Produktions-Delta-Zustand zu
  gefährden.
- Neue Sektion "Noch nicht produktiv verifiziert": TL;DR-Block,
  Titel-Frontloading, Retention-Rückkopplung, Sprecherwechsel und die
  komplette Shorts-Pipeline liefen bisher nur in Unit-/Sichttests der
  einzelnen Worktree-Agents, noch in keinem echten Cron-Durchlauf (der
  20:35/21:15-Lauf vom 20.08. selbst wurde vom Marker des alten
  Morgenlaufs übersprungen). Erster echter Volltest: heute Abend
  21.08.2026 — konkrete Prüfpunkte für den nächsten Check dokumentiert.
- Betriebswerte aktualisiert (TTS-Kontingent 17.3 %, Stimme en-US-Studio-O,
  Testanzahl 194, Shorts-Upload-Kontingent).
- Zwei vorbestehende (nicht neue) mypy-Fehler in `tests/test_upload_metadaten.py`
  und `tests/test_schlussbild.py` dokumentiert statt übersehen.

**Warum:** Nutzerauftrag "prüfe die letzten Implementationen" — vollständiger
Checklisten-Durchlauf über acht Commits (sieben Features + Skill-Ergänzungen),
die seit dem letzten Overseer-Abgleich gelandet sind, plus Pflege des
Skill-Dokuments mit den Befunden.

**Auswirkung:** Keine Code-Änderung. `ruff check` sauber, `mypy` sauber
(ausser den zwei dokumentierten Alt-Fehlern), `pytest` 194/194 grün, lokal
und hp-ubuntu auf demselben Commit (`36006fe`), Crontab passt zur
dokumentierten Zeit. Die beiden BMAD-Skill-Commits (`1c478ff`/`c581ea5`)
wurden geprüft, aber bewusst nicht ins Skill-Dokument aufgenommen — reine
Claude-Code-Skill-Ergänzungen ohne Pipeline-Bezug.

**Offen:** Ergebnis des heutigen Abendlaufs (21.08., 20:35/21:15/23:30)
morgen anhand der in SKILL.md gelisteten konkreten Prüfpunkte kontrollieren.
