---
datum: 2026-08-19
agent: worktree-trockenlauf
typ: feature
commit: <Hash, sobald bekannt>
---

# Einheitliches Dry-Run-Flag --trockenlauf für die ganze Pipeline

**Was:** Neues Flag `--trockenlauf` in allen drei Pipeline-Einstiegen:

- `run_report.py`: `git_veroeffentlichen()` bekommt einen
  `trockenlauf`-Parameter und loggt statt zu committen/pushen
  (`[Trockenlauf] wuerde committen und pushen: ...`) — auch `git add`
  wird übersprungen. `bericht_veroeffentlichen()` reicht das Flag durch.
  Alle Generierungsschritte (Extrakte, Bericht, Titel, `folien.json`,
  Motive, Hintergründe, Clip-Ernte) laufen unverändert und schreiben
  lokale Dateien.
- `video_report.py`: `--trockenlauf` ist gleichbedeutend mit
  `--nur-video` (kein Upload, kein Marker) — gleiche Mechanik wie die
  bestehende `--vorschau`-Implikation.
- `klip_katalog.py`: `klip_bereinigen()` bekommt einen
  `trockenlauf`-Parameter; beide `unlink()`-Stellen (Rohclips und
  `abgelehnt/`) loggen dann nur, was fällig wäre. Der Standalone-Aufruf
  hat jetzt ein argparse mit `--trockenlauf` plus `logging.basicConfig`,
  damit die Zeilen auch aus `video.sh` sichtbar wären. `katalog.json`
  bleibt in beiden Modi unberührt.
- `.claude/skills/pipeline-overseer/SKILL.md`: Falle-Abschnitt zu
  `--kein-github` um das neue Flag ergänzt.

**Warum:** `--kein-github` ist kein reines Dry-Run-Flag (es unterdrückt
die komplette `bericht_veroeffentlichen()`-Stufe, dokumentierte Falle im
Overseer-Skill), und die Clip-Retention hatte gar keinen Löschschutz.
Ein "alles erzeugen, nichts veröffentlichen"-Lauf war bisher unmöglich.

**Auswirkung:** `run_report.py --trockenlauf` erzeugt alles wie im
Cron-Betrieb, nur der Git-Push entfällt. Bewusst *nicht* geändert:
`--kein-github`, `--nur-video` und `--vorschau` verhalten sich exakt wie
bisher (Cron-Skripte run.sh/report.sh/video.sh und Tests unberührt);
bei `--kein-github --trockenlauf` gewinnt `--kein-github`.

Verifiziert ohne API-Kosten je Kontrollpunkt einzeln:
`klip_katalog.py --trockenlauf` gegen präparierte Alt-Clips (Dateien
blieben, ohne Flag gelöscht), `git_veroeffentlichen(trockenlauf=True)`
real aufgerufen (HEAD und Status unverändert, Logzeile erschien),
`video_report.py --trockenlauf` in-process mit Stolperdraht (Marker wird
wie bei `--nur-video` ignoriert). Voller End-to-End-Trockenlauf wegen
Kostenverbots ausgelassen — auf hp-ubuntu jederzeit nachholbar.
ruff/mypy sauber, 71 Tests grün.

**Offen:** —
