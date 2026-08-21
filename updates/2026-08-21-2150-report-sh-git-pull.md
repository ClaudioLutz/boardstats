---
datum: 2026-08-21
agent: main
typ: bugfix
commit: <Folgecommit, siehe Story-Hash-Korrektur>
---

# `report.sh` zieht jetzt `git pull --ff-only` wie die anderen zwei Cron-Skripte

**Was:** In `report.sh` die fehlende Zeile
`git pull --ff-only || echo "WARNUNG: …"` eingebaut, wortgleich zum seit je
erprobten Muster in `run.sh:24` und `video.sh:51`, mit Kommentar zum Vorfall.
`bash -n` sauber. Der Workaround-Absatz in
`.claude/skills/pipeline-overseer/SKILL.md` ist entsprechend von
„Dauerzustand" auf „behoben, Diagnosemuster bleibt nützlich" umgeschrieben.

**Warum:** Am 21.08.2026 als einziges der drei Cron-Skripte ohne Pull
identifiziert (per `grep -n 'git pull' run.sh report.sh video.sh` auf
hp-ubuntu belegt). Real eingetreten: ein Push nach `main` um 20:21 erreichte
hp-ubuntu nie, der 20:35-Bericht lief auf altem Code — und weil
`run_report.py` Extrakte und Bericht selbst committet und pusht, prallten
beide Pushes an `origin` ab („Veroeffentlichung auf GitHub fehlgeschlagen"),
das Repo divergierte (lokal 2 Commits voraus, origin 1) und der
`--ff-only`-Pull von `video.sh` um 21:15 wäre ebenfalls gescheitert. Heute
blieb der Schaden aus, weil der betroffene Commit reine Dokumentation war;
mit Pipeline-Code hätte der Abendbericht unbemerkt auf altem Stand
gerendert. Ein dokumentierter manueller Workaround für einen Ein-Zeilen-Fix
ist der falsche Endzustand.

**Auswirkung:** Ein Push nach `main` genügt wieder für alle drei Läufe. Das
Fehlerverhalten bleibt fault-tolerant: `--ff-only` verweigert bei
schmutzigem Arbeitsverzeichnis, statt etwas zu überschreiben, und ein
Fehlschlag stoppt den Lauf nicht — lieber ein Bericht auf altem Stand als
gar keiner. Kein Python berührt, `ruff`/`mypy` nicht einschlägig.

**Offen:** Nichts an diesem Fix. Der Fix greift erstmals beim Lauf am
22.08. 20:35 — hp-ubuntu wurde von Hand nachgezogen, weil `report.sh` sich
den eigenen Pull naturgemäss nicht selbst holen kann.
