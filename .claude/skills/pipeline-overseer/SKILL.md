---
name: pipeline-overseer
description: Definiert die stehende Overseer-Rolle für boardstats — Testvideos generieren, jedes auf main eingespielte Update prüfen (ruff/mypy/pytest, Story, Activity-Log, hp-ubuntu-Deploy) und den Gesamtüberblick über die Crawl→Bericht→Video-Pipeline halten. Auto-relevant bei "prüfe was gebaut/deployed wurde", "generiere ein Testvideo", "Overseer", "Pipeline-Status", nach jedem Commit auf main in diesem Repo.
---

# Overseer-Rolle boardstats

Stehender Auftrag (vom Nutzer bestätigt): Testvideos generieren, jedes auf
`main` eingespielte Update prüfen, Gesamtüberblick über die Pipeline halten
und für deren Funktionsfähigkeit einstehen. Dieses Dokument selbst pflegen —
neue Erkenntnisse hier nachtragen, nicht nur ins Gedächtnis.

**Stehende Ermächtigung (19.08.2026):** Wenn Glieder der Kette (Crawl →
Bericht → Video → Upload, inkl. der getrennten Umgebungen lokal/hp-ubuntu)
nicht sauber zusammenspielen, selbständig fixen und überwachen — dazu
gehört ausdrücklich auch, sich dafür passende Diagnose-/Test-Werkzeuge zu
bauen (Skripte, Monitor-Läufe, Log-Auswertungen), statt nur zu melden.
Grenzen bleiben trotzdem in Kraft: kein Push auf `main` ohne Rückfrage bei
riskanten/destruktiven Aktionen, kein produktiver Upload/keine echten
Kosten ohne Test-Flags (siehe Credentials-Hinweis oben).

## Pipeline-Architektur

Drei entkoppelte Cron-Jobs auf **hp-ubuntu** (`crontab -l`), bewusst getrennt,
damit ein Fehler in einem Schritt die anderen nicht mitreisst:

| Zeit (täglich) | Skript | Tut |
|---|---|---|
| 7:20 / 13:20 / 20:20 | `run.sh` | `crawl_biz.py` + `aggregate_biz.py` → Snapshot, `reports/latest.json` |
| 20:35 | `report.sh` | `run_report.py --top 15` → `extrakte/<datum>/bericht.md`, Folien, Bilder, GitHub-Publish |
| 21:15 | `video.sh` | `video_report.py --sprache en` (Vertonung+Render+Upload) + `shorts.py` (Tages-Shorts je Story) + `klip_katalog.py` (Retention) |
| 23:30 | (inline) | `analytics_bericht.py --tage 45 --speichern` — Abbruchkurven als Erfolgskontrolle, seit `2e2d63a` zugleich Datenquelle für die Retention-Rückkopplung in den nächsten Bericht |

**Seit 20.08.2026 (`231c51a`) Abendrhythmus statt Morgenlauf:** Messung
zeigte, dass /biz/ dem US-Handelstag folgt (13–21 UTC = 52.5 % aller Posts,
06–11 UTC nur 14.1 %) — der alte Redaktionsschluss 05:20 UTC lag im
Aktivitätstief. Crawl-Raster (7:20/13:20/20:20) bleibt unverändert, nur
Bericht/Video/Analytics rückten auf den Abend. Erster echter Voll-Zyklus im
neuen Rhythmus: heute Abend 21.08.2026 — der Abendlauf vom 20.08. selbst
lieferte zwar Bericht/Extrakte neu, das Hauptvideo wurde aber vom
Morgenlauf-Marker übersprungen (siehe „Serie vom 20.08. im Kettentest
verifiziert" unten). `report.sh` läuft weiterhin **vor** `video.sh` (20:35 vs 21:15),
damit `bericht.md` sicher fertig ist, bevor die Vertonung draufzugreift.

Alle drei Haupt-Skripte starten mit `git pull --ff-only || echo WARNUNG`
(fault-tolerant: lieber mit altem Stand laufen als gar nicht) — **in
`report.sh` allerdings erst seit `481724f`, 21.08.2026.** Bis dahin war es
das einzige der drei ohne Pull, was die frühere Behauptung „jedes der drei
Haupt-Skripte startet mit `git pull`" zu einer unbemerkten Falle machte.

Die zwei Folgen, beide am 21.08. real eingetreten, bevor der Pull eingebaut
war (als Diagnosemuster weiterhin nützlich, falls der Pull mal fehlschlägt):

- Ein Push auf `main` zwischen dem letzten `video.sh` und dem nächsten
  `report.sh` erreicht den 20:35-Lauf **nicht**. Wer Code testet, das Ergebnis
  pusht und annimmt, der Abendbericht laufe damit, irrt.
- Schlimmer: `run_report.py` committet Extrakte/Bericht selbst und pusht.
  Liegt auf `origin` ein Commit, den hp-ubuntu nicht hat, wird der Push
  **zweimal abgelehnt** („Veroeffentlichung auf GitHub fehlgeschlagen") und
  das Repo divergiert (lokal 2 Commits voraus, origin 1). Der Bericht selbst
  ist davon unberührt, aber das GitHub-Archiv bleibt leer und der `--ff-only`
  -Pull von `video.sh` scheitert danach ebenfalls.

Reparatur (working tree ist nach dem Lauf sauber, also unkritisch):

```bash
ssh hp-ubuntu "cd ~/boardstats && git pull --rebase origin main && git push origin main"
```

**Konsequenz für eigene Pushes:** seit `481724f` reicht ein Push nach `main`
wieder für alle drei Läufe. Solange der Pull noch fehlte, war der Workaround
„vor 20:35 pushen *und* von Hand nachziehen" nötig — er ist jetzt Geschichte,
bleibt aber die richtige Reaktion, falls ein `git pull` im Log als WARNUNG
auftaucht (dann liegt ein schmutziges Arbeitsverzeichnis auf hp-ubuntu vor).

**Getrennte Umgebungen:**
- hp-ubuntu Produktions-venv: `~/.venvs/boardstats-video/bin/python3` — hat
  `edge-tts`, `pillow`, `matplotlib`, `pytest`, aber **kein** `mypy`/`ruff`
  (Validierung läuft lokal, nicht auf dem Renderserver).
  `run.sh`/`report.sh` nutzen dagegen System-`python3` (kein venv nötig,
  keine der genannten Extra-Bibliotheken).
- Lokal (dieser Windows-Rechner): Python
  `C:\Users\claud\AppData\Local\Programs\Python\Python313\python.exe` hat
  ebenfalls `edge-tts`, `pillow`, `matplotlib`, `pytest`, **und** `mypy`+`ruff`
  — hier läuft die Pflicht-Validierung nach jeder Python-Änderung.
  `ffmpeg`/`ffprobe` liegen unter `C:\Users\claud\bin\` (im PATH).
- Kein `requirements.txt`/`pyproject.toml` im Repo — neue Pakete werden per
  `pip install` direkt in beide Umgebungen installiert, ohne Dateiänderung.
  Bei neuen Third-Party-Imports: prüfen, ob das Paket in **beiden**
  Umgebungen (lokal UND hp-ubuntu-venv) vorhanden ist, sonst bricht nur der
  Cron-Lauf auf hp-ubuntu.

**Wichtig — geteilte Ressourcen, auch lokal:**
`~/.config/boardstats/` existiert auch auf diesem Windows-Rechner mit
**echten** Produktions-Credentials (`youtube_client.json`,
`youtube_token.json`, `google_tts_key.txt`, `bett.opus`/`bett_quelle.mp3`).
Ein lokaler Lauf ohne `--nur-video`/`--vorschau` würde also **wirklich**
auf den Produktionskanal hochladen und den echten Google-Studio-TTS-Kontingent
verbrauchen (Stand 20.08.2026 08:10: 17.3 % von 1'000'000 Zeichen/Monat,
geteilt mit hp-ubuntu — ein voller Testlauf kostet ca. 8'700-13'000 Zeichen).
Nie einen Lauf ohne Test-Flag lokal starten. Seit `cb52e17` (20.08.) spricht
Sprache `en` mit **en-US-Studio-O** (weiblich, vorher Studio-Q) —
Hörvergleich aller en-US-Klassen, Ersatzkette (Neural2-G/AriaNeural) an
Grundfrequenz mitgezogen. Der Vertonungs-Cache greift beim ersten Lauf mit
der neuen Stimme nicht (Cache-Schlüssel enthält den Stimmennamen) — erster
Lauf nach dem Wechsel vertont komplett neu und kostet volles Kontingent.

## Testvideos generieren (meine Verantwortung)

Immer mit Test-Flag, nie ein blanker Lauf lokal:

```bash
python video_report.py --sprache en --vorschau 20
```

- `--vorschau SEKUNDEN` — baut nur die ersten N Sekunden des Szenen-Layouts,
  volle Auflösung, impliziert `--nur-video`. Erste Wahl für schnelle
  Sicht-/Hörprüfung nach einer Render-Änderung (Kulisse, Overlay, Musikbett).
- `--nur-video` — voller Bau, aber kein Upload, kein Marker (`video_en.json`
  wird nicht geschrieben) → wiederholbar, ohne den Cron-Lauf des Tages zu
  blockieren. Nötig, wenn ein Fehler erst spät im Video auftritt (z.B.
  Outro/Aktivitätsgrafik) und `--vorschau` ihn nicht erreicht.
- `--bett-bauen` — synthetisiert nur das Musikbett (`BETT`) neu und beendet;
  eigener Aufruf, kein Automatismus beim fehlenden File (bewusst, s. Kommentar
  im Code: ein Cron-Lauf soll keine ungehörte Tonspur erzeugen).
- Voraussetzung: `extrakte/<heutiges Datum>/bericht.md` muss existieren
  (kommt aus `report.sh`/`run_report.py`, wird von `git pull` mitgebracht,
  liegt bereits lokal unter `extrakte/`). Ohne aktuellen Bericht bricht der
  Lauf sauber mit "kein Bericht für ... - nichts zu tun" ab (kein Fehler).
- Nach dem Lauf: Ergebnis unter `video/<datum>/video_en.mp4` (lokal,
  gitignored) ansehen/anhören, bevor eine Änderung als verifiziert gilt —
  reines `ruff`/`mypy`/`pytest`-Grün beweist nur Typ-/Syntaxkorrektheit,
  nicht dass die Szene tatsächlich wie beabsichtigt aussieht/klingt.
- **Seit 20.08.2026 (`c33885c`) sind Testlauf-Ausgaben vom produktiven Zustand
  getrennt:** `run_report.py --trockenlauf` schreibt Thumbnail/Motive/Bericht/
  Markdown-Extrakte nicht mehr nach `arbeit/thumbs/<datum>.*`,
  `arbeit/motive/<datum>/`, `berichte/<datum>.txt` bzw. `extrakte/<datum>/`,
  sondern gebündelt unter `arbeit/<stamp>-test/` (Laufverzeichnis, per Regex
  auf den echten Zeitstempel `\d{8}-\d{6}` aufgeräumt, Test- und
  Produktivläufe zählen getrennt gegen `LAEUFE_BEHALTEN`). Ein Testlauf ist
  damit für den produktiven Pfad folgenlos, bleibt aber unter diesem Ordner
  vollständig inspizierbar. Für einen worktree-lokalen Testlauf bringt
  `testumgebung.py --kopieren` `cache/`, `berichte/`, `verwendet.json` und
  `katalog.json` aus dem Haupt-Checkout mit (nur in diese Richtung).
- **Seit 19./20.08.2026 (`2bb3bf6`, `43d3fac`) schreiben Testflags den
  Delta-Zustand nicht mehr fort:** `cache_pflegen()` (`cache/status.json`,
  `cache/<thread>.txt`), `verwendete_merken()`
  (`arbeit/motive/verwendet.json`) und das Stempeln von `zuletzt_verwendet`
  in `arbeit/clips/katalog.json` laufen unter `--trockenlauf`/`--nur-video`/
  `--vorschau` nicht mehr — jeder übersprungene Schreiber loggt eine
  "Trockenlauf - ... bleibt unberührt"-Zeile. `--kein-cache` löscht
  `cache/status.json` in Kombination mit `--trockenlauf` ebenfalls nicht mehr.
  Bewusst weiterhin geschrieben (gewollt kumulativ bzw. echtes Kontingent):
  `arbeit/tts_verbrauch.json`, die Freigabe-Ergebnisse
  (`status`/`beschreibung`) aus `motive.json` und `klip_katalog.klips_ernten()`.
  **Hintergrund:** genau das Fehlen dieser Guards hat am 19.08.2026 durch
  meine eigenen drei Testläufe (14:49/20:12/20:25) den Delta-Stand der
  Pipeline ca. zwölf Stunden nach vorne geschoben und musste von Hand
  zurückgerollt werden (`258506a`) — siehe Geklärte Fälle unten. Der Guard
  war Stand 20.08.2026 im Feld noch nicht bestätigt: bei einem echten
  Testlauf die mtimes von `cache/status.json`, `arbeit/motive/verwendet.json`
  und `arbeit/clips/katalog.json` vor/nach dem Lauf vergleichen — bleiben sie
  stehen, greift der Guard.
- Auf hp-ubuntu lässt sich derselbe Testlauf per SSH beobachten (nützlich,
  wenn der reale Cron-Lauf gerade läuft oder ein Produktions-spezifisches
  Problem vermutet wird — z.B. venv-Paketstand, Speicher, Rechenzeit):
  ```bash
  ssh hp-ubuntu "cd ~/boardstats && nohup ~/.venvs/boardstats-video/bin/python3 -u video_report.py --sprache en --nur-video > video/\$(date +%F)/build_test.log 2>&1 & disown"
  ```
  `-u` (unbuffered) ist Pflicht, sonst bleibt das Log bis Prozessende leer
  (bestätigter Fehlermodus, siehe Memory `feedback_logs_live_schreiben`).
### Voller Kettentest Report→Video→Shorts (erprobtes Rezept, 21.08.2026)

Der Kettentest ist möglich, **lokal auf diesem Windows-Rechner**, ohne den
Produktions-Delta anfassen zu können. Der frühere Eintrag hier ("nicht mehr
ohne Weiteres möglich") galt nur für einen Test *auf hp-ubuntu*. Der Trick:
lokal gibt es keinen produktiven Zustand, den man verderben könnte — die
Produktion lebt komplett auf hp-ubuntu. Alles, was lokal fabriziert wird,
ist folgenlos, solange nichts committet/gepusht wird.

Ausgangsproblem bleibt: `video_report.py` liest hart
`extrakte/<heutiges Datum>/` (Lokalzeit, kein `--datum`-Flag), ein
`--trockenlauf` von `run_report.py` schreibt aber bewusst nach
`arbeit/<stamp>-test/`. Die Kettennaht wird darum von Hand gelegt.

```bash
# 1. Prod-Zustand LESEND spiegeln, damit der Test den echten Delta-Pfad rechnet
#    (ohne das liest der lokale Lauf alle Threads voll = falscher Codepfad)
mv cache <scratchpad>/cache-alt && mkdir cache
scp hp-ubuntu:boardstats/cache/status.json cache/
scp "hp-ubuntu:boardstats/cache/*.txt" cache/
# 2. Analytics-Messung spiegeln, sonst bleibt retention_befund() leer
mkdir -p arbeit/analytics && scp hp-ubuntu:boardstats/arbeit/analytics/*.json arbeit/analytics/
# 3. Rohsnapshot spiegeln - OHNE ihn gibt es lokal NULL Bildkandidaten
#    (_snapshot_posts() liest raw/*.jsonl.gz; mit --host liegt raw/ nur remote)
mkdir -p raw && scp hp-ubuntu:boardstats/raw/<juengster>.jsonl.gz raw/
# 4. Report (Remote-Anteil dauert nur ~5 s, danach laeuft alles lokal)
python -u run_report.py --host hp-ubuntu --top 15 --trockenlauf
# 5. Kettennaht legen
cp -r arbeit/<stamp>-test/extrakte-md/. extrakte/<datum>/
cp -r arbeit/motive/<datum>-test arbeit/motive/<datum>
cp arbeit/thumbs/<datum>-test.jpg arbeit/thumbs/<datum>.jpg
# 6. Video und Shorts
python -u video_report.py --sprache en --trockenlauf
python -u shorts.py --sprache en --trockenlauf --datum <datum>
```

**Aufräumen ist Pflicht**, sonst kollidiert das fabrizierte
`extrakte/<datum>/` (untracked) beim nächsten `git pull` mit dem echten
Produktions-Commit desselben Tages:
```bash
rm -rf extrakte/<datum> arbeit/motive/<datum> arbeit/thumbs/<datum>.jpg raw
```
`video/<datum>/` darf bleiben (gitignored) — das ist das Prüfergebnis.
Danach `git status --short` gegenprüfen: muss leer sein.

**Fallen, real erlebt:**
- Ein `cd` im Bash-Tool wirkt in Folgeaufrufen weiter. Beim Aufräumen
  **absolute Pfade** verwenden, sonst löscht das `rm -rf` relativ zum
  letzten `cd` ins Leere (oder Schlimmeres).
- Zeitfenster beachten: der `--host`-Schritt schreibt `bundles/` und
  `cache_status.json` auf hp-ubuntu. Vor ~20:10 unkritisch, danach
  kollidiert er mit dem 20:20-Crawl / 20:35-Report.
- Der lokale Video-Render darf problemlos über 20:35 hinauslaufen —
  getrennte Maschine.

**Gegenprobe, dass die Produktion unberührt blieb** (die drei Delta-Dateien
müssen den Stempel des letzten produktiven Laufs behalten):
```bash
ssh hp-ubuntu "cd ~/boardstats && stat -c '%y %n' cache/status.json arbeit/motive/verwendet.json arbeit/clips/katalog.json"
```

`shorts.py` hat zusätzlich ein eigenes `--datum`-Flag und lässt sich auch
unabhängig gegen einen beliebigen vorhandenen `extrakte/<datum>/`-Stand
testen.

## Updates auf main prüfen (Checkliste pro Commit/Commit-Serie)

1. **`git log`/`git diff` lokal vs. hp-ubuntu vergleichen** — beide müssen
   auf demselben Hash stehen, sonst per `git pull --ff-only` auf hp-ubuntu
   nachziehen (`ssh hp-ubuntu "cd ~/boardstats && git pull --ff-only"`).
2. **Validierungspflicht nachvollziehen** (CLAUDE.md: nach Python-Änderungen
   `ruff check` + `mypy` — kein Config-File im Repo, Default-Settings):
   ```bash
   "C:\Users\claud\AppData\Local\Programs\Python\Python313\python.exe" -m ruff check .
   "C:\Users\claud\AppData\Local\Programs\Python\Python313\python.exe" -m mypy .
   ```
   Wenn ein Commit das übersprungen hat und Fehler auftauchen: `git blame`
   bzw. `git log -L <start>,<end>:<datei>` nutzen, um den genauen
   verursachenden Commit zu bestimmen, statt pauschal zu vermuten.
3. **Tests laufen lassen** (`tests/` — Stand 21.08.2026: 194 Tests, u.a.
   `test_shorts.py` (16) und `test_retention.py` (15) neu dazugekommen;
   Dateiliste wächst, im Zweifel `ls tests/*.py` statt hier genannten Namen
   vertrauen):
   ```bash
   "C:\Users\claud\AppData\Local\Programs\Python\Python313\python.exe" -m pytest
   ```
   **Nicht nur lokal** — auch auf hp-ubuntu tatsächlich ausführen lassen
   (`ssh hp-ubuntu "cd ~/boardstats && ~/.venvs/boardstats-video/bin/python3 -m pytest"`),
   bevor ich behaupte "Tests laufen auf hp-ubuntu". Eine unbelegte Behauptung
   dazu hat sich am 19.08. als falsch herausgestellt (pytest war dort gar
   nicht installiert) — nie eine Testaussage über eine Umgebung treffen, die
   nicht tatsächlich geprüft wurde.
4. **Story vorhanden?** Jede Änderung braucht `updates/YYYY-MM-DD-HHMM-*.md`
   im selben Commit (Format: `updates/README.md`). Fehlt sie bei einem fremden
   Commit, selbst keine nachträglich unterschieben, sondern dem Nutzer melden
   bzw. bei eigenen Fixes selbst nachtragen.
5. **Activity-Log-Eintrag** (`mcp__activity-log__log_activity`,
   project=`boardstats`) pro Commit; bei `compaction_due` die `to_compact`
   -Einträge per `compress_activity` verdichten.
6. **Inhaltlich verifizieren, nicht nur grün abhaken:** bei Änderungen an
   Render-/Ton-/Auswahl-Logik zusätzlich ein Testvideo bauen (siehe oben) und
   das Ergebnis stichprobenartig ansehen/anhören — grüne Tests decken nicht
   ab, ob z.B. ein Ken-Burns-Zoom optisch glatt bleibt oder ein Musikbett
   hörbar richtig gemischt ist.
7. **Kontrollieren, ob die Anpassung seit dem letzten Stand tatsächlich
   greift** (Nutzeranweisung, wörtlich: "auch deine Aufgabe ist zu
   kontrollieren ob die neuen Anpassungen welche seit dem letzten gemacht
   wurden greifen") — pro Änderung konkret nachweisen, nicht nur annehmen:
   z.B. Coverage-Gegenprobe (`13a5970`) am Log ablesen ("Abdeckung: N Threads
   ausgelassen/teilweise, mit Begründung"), Themenverlauf-Tiefe (`d275488`)
   an der Log-Zeile "Themenverlauf: N Berichte" zählen, Stichwort-Fragmente
   (`4cd6c64`) in `folien.json`/Szenen-Overlays suchen, Lautheitsänderungen
   (z.B. `de84ef1`, +7 dB Intro-Bett) per ffmpeg/loudnorm am fertigen Video
   messen statt nur zu hören. Bei jeder Serie "substantieller Anpassungen"
   (mehrere Commits an einem Tag an Synthese/Render-Logik) einen echten
   End-to-End-Testlauf machen (Bericht **und** Video), nicht nur Unit-Tests.

**Wichtige Falle: `run_report.py --kein-github` ist kein reines
Dry-Run-Flag.** Es schaltet nicht nur den Git-Push ab, sondern die
komplette `bericht_veroeffentlichen()`-Stufe (Titel, Drehbuch/`folien.json`,
Motiv-/Hintergrundauswahl **und Clip-Ernte** `klip_katalog.klips_ernten`) -
siehe `run_report.py:2208-2209`. Ein lokaler Testlauf mit `--kein-github`
erzeugt also nie ein `bericht.md`/`folien.json`/frische Clip-Kandidaten,
mit denen `video_report.py` etwas anfangen kann. Für einen echten
End-to-End-Test (inkl. Clip-Zuordnung) muss der Lauf **ohne**
`--kein-github` erfolgen (Nutzerentscheidung 19.08.2026: GitHub-Publish
der Extrakte/Berichte ist unkritisch, darf jederzeit überschrieben werden -
kein Rückfragebedarf mehr dafür).

Seit 19.08.2026 gibt es dafür ein echtes, einheitliches Dry-Run-Flag:
`--trockenlauf`. `run_report.py --trockenlauf` erzeugt alles wie im
Normalbetrieb (Extrakte, Bericht, Titel, `folien.json`, Motive,
Hintergründe, Clip-Ernte) und überspringt nur `git add/commit/push` in
`git_veroeffentlichen()` (geloggt als `[Trockenlauf] würde committen`).
`video_report.py --trockenlauf` entspricht `--nur-video` (kein Upload,
kein Marker); `klip_katalog.py --trockenlauf` loggt die fällige
Retention, löscht aber nichts. `--kein-github` behält sein bisheriges
Verhalten (ganze Markdown-Stufe aus) und hat bei Kombination Vorrang.

## Neue Pipeline-Stufe seit 20.08.2026: Tages-Shorts (`shorts.py`)

Läuft in `video.sh` **nach** dem Hauptvideo. Pro `##`-Story des Tagesberichts
ein YouTube-Short (1080×1920, 20–175 s), geschnitten aus dem bereits
vorhandenen `video/<datum>/audio_en.mp3` an Wort-Zeitstempeln — **keine**
eigene Vertonung, kostet also kein zusätzliches TTS-Kontingent. Seit
`6a26128`/`36006fe` trägt jedes Short zusätzlich das Kapitel-Motiv des
Hauptvideos als Hintergrund (`MotivWahl`-Klasse aus `szenen_bauen()`
extrahiert, `shorts.story_motive()` rechnet exakt dieselbe Zuordnung).

- **Marker:** `extrakte/<datum>/shorts_en.json`, inkrementell nach jedem
  Upload fortgeschrieben (Wiederanlauf überspringt bereits hochgeladene
  Storys), analog `video_en.json` bewusst **nicht** committet.
- **Ähnlichkeits-Guard (Schwelle 0.90):** vor dem Schnitt vergleicht
  `shorts.py` den Wortstrom aus `video/<datum>/audio_en.mp3` mit den
  Blocktexten des **aktuellen** `extrakte/<datum>/`-Stands. Passt die
  Tonspur nicht zum Bericht (z.B. weil `report.sh` den Bericht neu
  geschrieben hat, aber `video.sh` das zugehörige Video wegen bestehendem
  Marker übersprungen hat — Morgen-Audio vs. Abend-Bericht), bricht der Lauf
  sauber mit Logzeile ab statt an falschen Grenzen zu schneiden. Genau das
  ist am 20.08. 21:15 passiert (Ähnlichkeit 0.040) — kein Fehler, erwartetes
  Verhalten beim ersten (unvollständigen) Abendlauf.
- **Testen:** `shorts.py --sprache en --trockenlauf --datum YYYY-MM-DD
  [--nur STORY_INDEX] [--status unlisted]` — unabhängig von der
  Report→Video-Ketten-Einschränkung oben nutzbar, solange für das
  angegebene Datum ein vollständiger `extrakte/<datum>/`-Stand samt
  `video/<datum>/audio_en.mp3` existiert.
- Test-Upload vom 20.08. (unlisted): https://youtu.be/Q7biXzouGos.

## Bekannte Betriebswerte (Referenz, bei Bedarf hier aktualisieren)

- Google Studio-TTS-Kontingent: 1'000'000 Zeichen/Monat, geteilt zwischen
  hp-ubuntu-Produktion und jedem lokalen Testlauf ohne `--nur-video`/
  `--vorschau`. Realer Tagesbericht ≈ 8'700-13'000 Zeichen/~590-700 s Video.
  Stand 20.08.2026 08:10: 17.3 % verbraucht (173'378 Zeichen) — der erste
  Lauf mit der neuen Stimme (`cb52e17`) kostet nochmal das volle Kontingent
  eines Tagesberichts, weil der Vertonungs-Cache dabei nicht greift
  (bestätigt 21.08.: 9'191 Zeichen für 65 Sätze, kein einziger Cache-Treffer).
- **Der TTS-Verbrauchszähler ist pro Maschine, nicht global.**
  `arbeit/tts_verbrauch.json` zählt nur die Läufe der jeweiligen Maschine;
  der lokale Testlauf meldete "Studio-Kontingent 2026-08: 15'668 von
  1'000'000 (1.6%)", während hp-ubuntu bei 173'378 Zeichen steht. Das echte
  Google-Kontingent ist die **Summe beider** (~19 % Ende August). Die
  Prozentanzeige eines lokalen Laufs nie als Kontingentstand lesen.
- `videos.insert` (Uploads, inkl. Shorts) hat ein eigenes Kontingent von
  100 Uploads/Tag seit 2026 — 8 Shorts/Tag zusätzlich zum Hauptvideo sind
  unkritisch (siehe Memory `youtube-quota-2026-eigene-upload-buckets.md`).
- Intro-Länge bis Kapitel 1 — **wächst und ist der offene Kritikpunkt**:
  29.6 s (vor `6509099`) → 37.0 s (Trockenlauf 21.08.) → **48.9 s im
  produktiven Lauf 21.08.** Boden 10 s wegen YouTube-Kapitelregel — liegt
  Kapitel 1 darunter, schiebt `kapitelmarken()` die Marke auf 10 s; eine
  **Decke gibt es nicht**. Ursache ist nicht die Anzahl der Zahlen (beide
  Läufe hatten exakt 4), sondern die unbegrenzte Länge des Feldes `satz` je
  Zahl in `folien.json` — produktiv voll ausgeschriebene Fliesssätze
  („one dollar and fifty three cents"). Gegen die gemessene Abbruchkurve
  (50 % weg nach 1:08) verbrennt der Vorspann damit rund drei Viertel der
  mittleren Verweildauer, bevor der erste Kapitelinhalt beginnt — er
  arbeitet direkt gegen die Retention-Rückkopplung, die ihn kürzen soll.
  Laufzeit des Tagesvideos 21.08.: produktiv 483 s (8:03), Trockenlauf
  513.8 s (8:34), vorher Median 11:39.
  Tonwerte Sprachspur: −19.5 LUFS, Pausen −84 dBFS, 85 % Energie < 700 Hz →
  Musikbett bei −22 LU, kein Ducking (nur sidechaincompress am Bett selbst).
- Kaltstart-Schlagwort (erster Titel, z.B. "$120K GONE"): seit `50621da`
  Wunschdauer 3.5 s (Boden `KALTSTART_MIN` 2.0 s), adaptiv gegen die
  Hook-Lesezeit (`HOOK_CPS`=17 + `HOOK_VORLAUF`=0.5s) verkürzt, vorher starr
  2.0 s. Stichwort-Fragmente: Lesezeit-Boden `DETAIL_FRAG_MIN` 1.4→2.0 s,
  `DETAIL_CPS` 12→10 (mehr Lesezeit pro Zeichen). `szenen_bauen()` loggt seither
  die Zahl gezeigter vs. wegen zu engem Fenster gekürzter Fragmente.
- Wiederverwendungssperre für Bilder/Clips: 5 Tage (seit `ece2f82`,
  vorher 14 Tage).
- Clip-Katalog-Retention (`klip_katalog.py`, via `video.sh` nach jedem
  Video-Lauf): Rohdatei löscht sich nach Verwendung oder 48 h Alter,
  Katalog-Eintrag (MD5, Bewertung) bleibt erhalten.
- Reuse-Ausnahme in `_klip_zuordnung()`: `zuletzt_verwendet == heute` zählt
  weiterhin als frei — ein Rebuild/Testlauf am selben Tag sperrt sich damit
  nicht selbst alle Clips.

## Geklärte Fälle (Root-Cause gefunden, nicht mehr aktiv verfolgen)

- **Eigene Testläufe haben am 19.08.2026 den Delta-Zustand der Produktion
  verschoben, seit 20.08.2026 durch Guards behoben:** Meine drei
  Overseer-Testläufe (14:49, 20:12, 20:25) liefen mit `--trockenlauf`/
  `--nur-video`, das damals nur Git/Upload übersprang — `cache_pflegen()`,
  `verwendete_merken()` und das Clip-Katalog-Stempeln liefen trotzdem mit und
  schrieben denselben Zustand fort wie ein echter Produktivlauf. Ergebnis:
  der Cron-Lauf am Folgetag hätte nur noch das Delta seit 20:27 statt seit
  dem letzten YouTube-Upload gesehen, rund zwölf Stunden Board-Aktivität
  wären im Video nie aufgetaucht. Musste von Hand zurückgerollt werden
  (`258506a`: `cache/status.json`, `cache/<thread>.txt`,
  `arbeit/motive/verwendet.json`, `arbeit/clips/katalog.json` und
  `extrakte/2026-08-19/` auf den Stand nach dem Morgen-Upload zurückgesetzt).
  Danach zwei Fixes: `2bb3bf6`/`43d3fac` stoppen das Fortschreiben des
  Delta-Zustands unter Testflags, `c33885c` verlegt zusätzlich alle
  Testlauf-**Ausgaben** nach `arbeit/<stamp>-test/` (Details oben unter
  "Testvideos generieren"). **Lehre:** Ein Dry-Run-Flag, das nur Git/Upload
  abschaltet, schützt nicht automatisch den Zustand, den der nächste Lauf
  als Referenz liest — bei jedem neuen Test-Flag prüfen, welche
  Zustandsschreiber (Cache, Sperrlisten, Katalog-Stempel) ausserhalb von
  Git/Upload existieren und ob sie mitgemeint sind.

- **YouTube-Uploads vom 19./20.08.2026 verloren `embeddable` und
  `publicStatsViewable` (behoben in `e0cad36`/`57763f8`):** Seit `8c6287d`
  (Upload erst privat, Freischaltung erst nach Thumbnail/Untertitel/Playlist)
  schaltet `status_setzen()` das Video per `videos.update` frei und schickte
  dabei nur `privacyStatus` im `status`-Part. YouTube ersetzt bei einem
  Update aber den **ganzen** angegebenen Part — jedes fehlende Feld fällt auf
  den API-Default zurück, für beide Booleans `false`. Fix:
  `status_setzen()` liest zuerst den vorhandenen Block
  (`status_lesen()`) und schreibt ihn inkl. aller `STATUS_FELDER` zurück, nur
  `privacyStatus` wird ersetzt (Read-Modify-Write); `hochladen()` setzt beide
  Felder zusätzlich explizit beim Upload. Nachträglich repariert:
  `66TVSAMrUSw` (19.08.) und `LGhGnj75rEg` (20.08.). **Lehre, verallgemeinert
  über `status_setzen()` hinaus:** Ein `videos.update`/`*.update`-Aufruf mit
  einem `part`-Parameter der YouTube-Data-API ersetzt den ganzen Part —
  jeder eigene Schreibzugriff auf einen Teilbereich zuerst lesen, dann
  vollständig zurückschreiben (vgl. bereits bekannt aus
  Memory `youtube-update-ersetzt-part.md`, hier jetzt auch code-seitig
  durchgesetzt). Im selben Commit wurde nebenbei die Tag-Qualität gefixt
  (`_titel_schlagworte()`/`STOPP_TAGS`/Ticker aus dem Bericht statt der
  gekappten Thumbnail-Phrase als Tag-Quelle).

- **`arbeit/clips/`-Verschwinden (19.08.2026, behoben in `034ae86`):** Die
  Aufräum-Logik am Ende von `run_report.py main()` sortierte alle Einträge
  unter `arbeit/` alphabetisch absteigend und behielt nur die ersten
  `LAEUFE_BEHALTEN` (5) — Namen wie `thumbs`/`srt_nachzug`/`motive`/`clips`
  stehen alphabetisch vor jedem Datumsordner, `clips` fiel exakt auf den
  Schnitt und wurde bei **jedem** Lauf mitsamt `katalog.json` gelöscht,
  kurz nachdem `klips_ernten()` sie neu geschrieben hatte. Fix filtert
  jetzt per Regex nur echte `YYYY-MM-DD`-Ordner vor der Sortierung. Lehre:
  bei jeder neuen dauerhaften Unterordner-Struktur unter `arbeit/`
  (Vorbild `clips/`, `motive/`, `thumbs/`) prüfen, ob generische
  "Alte-Läufe-aufräumen"-Logik davon betroffen ist.

- **Eigene Schriften (`assets/fonts/`) sind Repo-Dateien, keine System-Fonts:**
  `SpaceGrotesk-Bold.ttf`/`Inter-Regular.ttf`/`Inter-Medium.ttf`/
  `IBMPlexMono-Bold.ttf` liegen git-tracked im Repo, `thumbnail.FONT_DIR`
  löst sie repo-relativ auf (`Path(__file__).resolve().parent / "assets" /
  "fonts"`), PIL lädt per Dateipfad — kein `fc-list`/Font-Installation auf
  hp-ubuntu nötig, kommen automatisch mit `git pull` mit. Fallback auf
  System-`DejaVuSans*` in derselben Kandidatenliste, falls eine Datei fehlt.
  Verifiziert 19.08.2026 auf hp-ubuntu: alle vier Dateien vorhanden (Commit
  `556aef9`), laden fehlerfrei via `PIL.ImageFont.truetype()`, Pixelvergleich
  bestätigt sichtbaren Gewichtsunterschied Inter-Regular vs. Inter-Medium
  (1'922 vs. 2'251 belichtete Pixel bei identischem Text/Grösse) trotz
  irreführender interner Namenstabelle (`getname()` meldet bei beiden
  fälschlich "Regular" bzw. bei SpaceGrotesk-Bold fälschlich "Light" —
  kosmetisches Metadaten-Artefakt aus dem Variable-Font-Export, betrifft
  nicht das tatsächliche Glyphen-Rendering).
- **Lange Strecken ohne Stichworte im Video vom 19.08. (behoben in
  `4810739`):** Ein Kapitel lief 124.7 s, hatte aber nur 6 Stichworte, alle
  in den ersten 32 s — danach 93 s Rede ohne ein einziges Drehbuch-Stichwort.
  Ursache: der Abschnitt bestand aus mehreren Absätzen (mehreren Threads),
  das Modell schrieb trotz Prompt-Regel ("one bullet for roughly EVERY
  sentence of the WHOLE section") alle Stichworte nur für den ersten Absatz;
  der Renderer füllte den Rest mit `detail`-losen Fallback-Bullets aus
  `_luecken_fuellen()` — kein Renderer-Fehler, das Modell hatte die Lücke
  schon im Drehbuch. Fix: neue Prüfung `_abdeckung_luecken()` zählt nach
  jedem Drehbuch-Lauf, ob jeder substanzielle Absatz (≥200 Zeichen)
  mindestens eine Anker-Phrase trägt; bei Lücken geht ein zweiter,
  gezielter Sonnet-Nachtrag-Aufruf raus (max. 1 zusätzlicher Call/Tag,
  scheitert er, gilt der erste Versuch). Nebenbei: Stichwort-Fragmente
  rendern seither weiss (`HELL`) statt im Grau der geparkten Punkte.
  Kalibrierung an echten Drehbüchern: 17.08. 0 Lücken, 18.08. 2, 19.08. 5.

- **`aktivitaet.py` (Balkengrafik "Board-Aktivität", nutzt dieselben Fonts)
  ist laut eigenem Docstring noch NICHT in `video_report.py` verdrahtet** —
  Fonts sind bereit, der Chart läuft im produktiven Video noch nicht mit.
  Aktiv genutzt werden die Fonts bisher nur über `thumbnail.py`-Karten.

- **Race Condition beim Lesen frischer Crawl-Snapshots (behoben in
  `3b3f4d5`):** selbst geflaggter Befund vom 20.08. — ein Testlauf um 20:23
  überlappte mit dem 20:20-Crawl und las `raw/2026-08-19T1820.jsonl.gz`
  mitten im Schreibvorgang (`gzip.BadGzipFile`), lief in ein vorhandenes
  try/except und hinterliess **keine** erklärende Logzeile, nur einen Tag
  ganz ohne frische Motive/Kulisse/Clips. Fix an der Quelle statt nur beim
  Lesen: `crawl_biz.py` schreibt jetzt nach `<stamp>.jsonl.gz.tmp` und
  benennt erst nach dem letzten Thread um — ein unfertiger Snapshot fällt
  damit aus jedem `glob("*.jsonl.gz")` heraus, deckt alle drei Leser ab
  (`run_report.py`, `bundle_biz.py`, `aggregate_biz.py`). Zusätzlich loggt
  `_snapshot_posts()` einen unlesbaren Snapshot jetzt statt still leer
  zurückzukommen. Damit hinfällig: der zuvor als Task geflaggte Vorschlag
  "Race Condition beim Lesen frischer Crawl-Snapshots absichern".

## Offene/unklare Punkte (nicht aktiv verfolgen, ausser Nutzer spricht sie an)

- Ungeklärter Mechanismus, wie Video `Q5Mbsfmkvnc` bereits vor einem
  expliziten Löschversuch auf YouTube als "Deleted video" markiert war.
- Zwei vorbestehende mypy-Fehler in `tests/` (nicht Teil der 20.08.-Serie,
  seit `e0cad36` bzw. `c288868` unbemerkt liegengeblieben): falscher
  `type: ignore`-Fehlercode in `test_upload_metadaten.py:44`
  (`call-overload` statt `arg-type`) und `float | None` gegen
  `assertAlmostEqual` in `test_schlussbild.py` (5 Stellen). `ruff` und
  `pytest` bleiben davon unberührt (grün) — beim nächsten Anfassen einer
  der beiden Dateien mitkorrigieren.

## Serie vom 20.08. im Kettentest verifiziert (21.08.2026, 19:04–20:16 CEST)

Voller lokaler Kettentest Report→Video→Shorts nach dem Rezept oben, mit
gespiegeltem Prod-Cache (Delta-Pfad: 6× delta / 12× voll) und gespiegelter
Analytics-Messung. **Alle fünf offenen Prüfpunkte der 20.08.-Serie sind
damit an echter Ausgabe belegt, nicht nur durch grüne Tests:**

| Feature | Nachweis im Testlauf |
|---|---|
| Retention-Rückkopplung `2e2d63a` | "Retention: Befund aus 2026-08-20.json eingespeist (4 Videos, Median-Laufzeit 11:39)"; Block wirkt: 1801 Wörter (19.08.) → 878 Wörter, Laufzeit 11:39 → **8:34** |
| Titel-Frontloading `7f90c51` | `BBBYQ NOL Theory: $3BN Claim Meets 'Backend Glitch'` — Ticker vorn, Hook 50 Zeichen (≤55) |
| TL;DR-Zahlenblock `6509099` | 4 Tageszahlen in `folien.json` mit gesprochenem Satz; Frame bei 0:15 zeigt Zahlkarte; Vorspann bis **37.0 s** (vorher 29.6 s) |
| Stimme `cb52e17` | "Vertonung: Google TTS satzweise (en-US-Studio-O)" |
| Shorts `4d4b34e`/`6a26128` | Ähnlichkeits-Guard **1.000** (20.08. noch 0.040 → korrekter Abbruch); 7 Storys, 7 **verschiedene** Kapitel-Motive als Hintergrund; Frame-Sichtprüfung: Titel/Stichworte/Kennzahlkarte lesbar, UI-Zonen frei |

Zustandsschutz im selben Lauf mitbelegt: die drei Delta-Dateien auf
hp-ubuntu (`cache/status.json`, `arbeit/motive/verwendet.json`,
`arbeit/clips/katalog.json`) trugen vor **und nach** dem Test unverändert
den Stempel des Laufs vom 20.08. Die Trockenlauf-Guards melden das auch
selbst ("Bildsperre nicht vermerkt", "Clip-Katalog nicht gestempelt",
"Cache-Fortschritt nicht fortgeschrieben").

Was der Test nicht abdeckte, ist am produktiven Abendlauf desselben Tages
nachgeholt (siehe nächster Abschnitt).

## Erster produktiver Abendlauf verifiziert (21.08.2026, 20:35–21:33 CEST)

Report 20:35–20:55 (`5196b1f`), Video+Shorts 21:15–21:33. Die Upload-Seite,
die der Trockenlauf prinzipiell nicht bauen kann, ist damit belegt — per
`videos.list` an den **tatsächlich hochgeladenen** Metadaten gelesen, nicht
am Log:

- **Kapitelmarken** in der Beschreibung vorhanden und korrekt: `00:00 TL;DR`,
  `00:48 SILVER HITS 70…` bis `07:07 UNCHANGED FROM YESTERDAY`.
- **Tags**: 17 Stück, Sichtbarkeit `public`, Kategorie 25, `defaultLanguage=en`,
  Thumbnail gesetzt, Untertitel hochgeladen, Playlist `PLE-UMRGn6d6g`,
  Kanal-Trailer gesetzt.
- Beschreibung enthält Datenstand, Disclaimer, Hashtags, den 5000-Zeichen-
  Abschneidehinweis und die Quell-Threads.
- **Shorts**: 6 Storys, alle `public`, Rückverweis aufs Hauptvideo in der
  Beschreibung, Dauer 1:33 (< 3 min + 9:16 → YouTube erkennt sie als Shorts,
  auch ohne `#Shorts`-Hashtag). Marker `shorts_en.json` und `video_en.json`
  beide geschrieben. Ähnlichkeits-Guard produktiv **1.000**.
- **Delta korrekt**: `17 Threads (3× delta, 14× voll), Datenstand 20:19` —
  volle Tagesperiode seit dem Lauf vom 20.08., vom Trockenlauf unangetastet.
- **Sichtprüfung schärfer als im Test**: 5 Bilder abgelehnt (Hakenkreuz,
  homophober Slur, Galgenstrick-Symbolik, sexualisierte Pose, Beschimpfung),
  31 freigegeben, 8 Clips.

Zwei Auffälligkeiten, die den Lauf nicht gefährdet haben, aber offen sind:

- **Vorspann 48.9 s** statt 37.0 s im Test — Betriebswert oben, ernstester
  Punkt gegen die Retention.
- **14 von 63 Stichwort-Fragmenten fielen wegen zu enger Fenster weg**
  (Trockenlauf: 1 von 54). Bei dichterem Text kollabieren die Lesezeit-Böden
  `DETAIL_FRAG_MIN`/`DETAIL_CPS` reihenweise; wenn ein Fünftel der geplanten
  Bildtexte verschwindet, ist die Zwischenstufen-Idee halb wirksam.
- Randfall sauber abgefangen: `Clip … Frame bei 0.39s fehlgeschlagen:
  ffmpeg lieferte Exit 0, aber keine Datei (EOF-Randfall)` → Clip abgelehnt,
  Lauf lief weiter.
- Tag-Qualität: neben echten Suchbegriffen stehen ganze Kapitelüberschriften
  als Tags (`drs ledger and a $10 wish`, `short squeeze with a number on it`).
  Unschädlich, aber verschenkt Tag-Plätze.

**Neuer Befund: Wortzahl-Ableitung im Retention-Block ist falsch
kalibriert** (`run_report.py:2101`, `_retention_block()`). Die Formel
skaliert das **Soll**-Budget `WORTBUDGET = (700, 1000)` mit der
**Ist**-Laufzeit der Messung (699 s) — die aber zu Berichten mit ~1800
Wörtern gehört, weil das Budget nie eingehalten wurde. Soll und Ist werden
vermischt, das Wortziel fällt dadurch rund um Faktor 2 zu niedrig aus:
heute "target 5.8 minutes … roughly 350 to 500 words", während 350–500
Wörter beim gemessenen Tempo (878 Wörter = 8:34) nur **3:25–4:50 min**
ergäben — deutlich unter dem eigenen Laufzeitziel. Dass das Modell die
Vorgabe ignorierte und 878 Wörter schrieb, war Zufall, nicht Regelwerk.
Sauber wäre, mit der Ist-Wortzahl des zur Messung gehörenden Berichts zu
skalieren statt mit `WORTBUDGET`. Kein Blocker — die Richtung stimmt.

**Inhaltliche Beobachtung zur Kulisse (Nutzerentscheidung, kein Bug):** die
Sichtprüfung filtert zuverlässig Hass/Extremismus (2 Bilder abgelehnt:
antisemitischer Bildtext, Hakenkreuz), lässt aber Anime-Motive mit betonter
Körperlichkeit als Kapitelhintergrund durch (Short 3, Treasury-Buyback).
Themenbezug fehlt dort, und für einen Finanzkanal ist das eine
Positionierungsfrage. Falls unerwünscht, gehört ein Kriterium in
`HINTERGRUND_PROMPT`, nicht in den Szenenbau.

## Wartung dieses Skills

Dieses Dokument nach jeder Overseer-relevanten Erkenntnis erweitern:
neue Cron-Zeiten/-Skripte, neue Test-Flags, neue Fehlerklassen bei der
Update-Prüfung, aktualisierte Betriebswerte. Nicht dupliziert in `MEMORY.md`
pflegen — dort nur ein kurzer Verweis, Details hier.
