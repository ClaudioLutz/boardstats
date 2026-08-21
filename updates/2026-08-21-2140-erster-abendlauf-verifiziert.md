---
datum: 2026-08-21
agent: main
typ: docs
commit: 95d6e8c
---

# Erster produktiver Abendlauf verifiziert, `report.sh`-Pull-Lücke gefunden

**Was:** Der erste echte Abendlauf der 20.08.-Feature-Serie (Report
20:35–20:55, Video+Shorts 21:15–21:33) beobachtet und die Upload-Seite an
den tatsächlich hochgeladenen YouTube-Metadaten geprüft (`videos.list`,
read-only), nicht nur am Log. Befunde in
`.claude/skills/pipeline-overseer/SKILL.md` nachgetragen:

- Neuer Abschnitt „Erster produktiver Abendlauf verifiziert" — Kapitelmarken,
  Tags, Sichtbarkeit, Thumbnail, Untertitel, Playlist, Kanal-Trailer,
  Shorts-Rückverweise und beide Marker sind belegt.
- **Korrektur einer falschen Aussage im Skill-Dokument:** `report.sh` macht
  **kein** `git pull` — nur `run.sh` und `video.sh` tun das. Die frühere
  Behauptung „jedes der drei Haupt-Skripte startet mit `git pull --ff-only`"
  war falsch, verifiziert am Skript selbst.
- Betriebswert Vorspann als offener Kritikpunkt umgeschrieben: 29.6 → 37.0
  (Trockenlauf) → **48.9 s** (produktiv), mit gemessener Ursache.

**Warum:** Fortsetzung des Nutzerauftrags — der Testlauf sollte belegen, dass
der Delta unversehrt bleibt und der Abendlauf mit der richtigen Periode
läuft. Beides ist jetzt am realen Lauf bestätigt statt nur am Trockenlauf
plausibilisiert.

**Auswirkung:** Keine Code-Änderung, nur Dokumentation — plus eine
Reparatur am Repo-Zustand von hp-ubuntu (siehe unten). Delta bestätigt:
`17 Threads (3× delta, 14× voll), Datenstand 21.08. 20:19` — volle
Tagesperiode seit dem Lauf vom 20.08., vom Trockenlauf nachweislich
unangetastet. Sichtprüfung produktiv schärfer als im Test (5 Ablehnungen:
Hakenkreuz, homophober Slur, Galgenstrick-Symbolik, sexualisierte Pose,
Beschimpfung). Ähnlichkeits-Guard der Shorts produktiv 1.000.

Die fehlende `git pull`-Zeile in `report.sh` ist heute real eingetreten: ein
Docs-Push um 20:21 erreichte hp-ubuntu nie, `run_report.py` committete
Extrakte und Bericht lokal, beide Pushes prallten an `origin` ab
(„Veroeffentlichung auf GitHub fehlgeschlagen"), das Repo divergierte
(lokal 2 voraus, origin 1). Der Bericht selbst blieb unberührt, aber das
GitHub-Archiv wäre leer geblieben und der `--ff-only`-Pull von `video.sh`
um 21:15 ebenfalls gescheitert. Repariert per
`git pull --rebase origin main && git push origin main` auf hp-ubuntu
(working tree war sauber); danach lief `video.sh` mit „Already up to date."
sauber durch. Inhaltlich hat der Vorfall nichts verdorben, weil der Commit
reine Dokumentation war — mit Pipeline-Code hätte der Abendbericht
unbemerkt auf altem Stand gerendert.

**Offen:**

- **Vorspann wächst unkontrolliert** (29.6 → 37.0 → 48.9 s). Ursache ist
  nicht die Anzahl der TL;DR-Zahlen (beide Läufe: exakt 4), sondern die
  unbegrenzte Länge des Feldes `satz` je Zahl in `folien.json`. Gegen die
  gemessene Abbruchkurve (50 % weg nach 1:08) verbrennt das rund drei
  Viertel der mittleren Verweildauer vor dem ersten Kapitelinhalt — der
  Vorspann arbeitet damit direkt gegen die Retention-Rückkopplung, die ihn
  kürzen soll. Eine Decke fehlt; der Boden von 10 s existiert.
- **14 von 63 Stichwort-Fragmenten fielen wegen zu enger Fenster weg**
  (Trockenlauf: 1 von 54) — ein Fünftel der geplanten Bildtexte erscheint
  nicht.
- Wortzahl-Ableitung in `_retention_block()` (`run_report.py:2101`) bleibt
  falsch kalibriert, unverändert seit der Vor-Story.
- Tag-Qualität: ganze Kapitelüberschriften landen als Tags
  (`drs ledger and a $10 wish`) und verschenken Tag-Plätze.
- Anime-Motive mit betonter Körperlichkeit passieren die Sichtprüfung
  weiterhin — Positionierungsfrage für den Kanal.
