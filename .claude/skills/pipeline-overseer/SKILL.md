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
Morgenlauf-Marker übersprungen (siehe „Noch nicht produktiv verifiziert"
unten). `report.sh` läuft weiterhin **vor** `video.sh` (20:35 vs 21:15),
damit `bericht.md` sicher fertig ist, bevor die Vertonung draufzugreift.

Jedes der Haupt-Skripte startet mit `git pull --ff-only || echo WARNUNG`
(fault-tolerant, damit hp-ubuntu bei jedem Lauf synchron zu `main` bleibt,
ohne den Lauf bei Konflikt abzubrechen).

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
- **Seit `7191699`/`c33885c` ist der Ketten-Test Report→Video nicht mehr
  ohne Weiteres möglich:** `video_report.py` liest hart `extrakte/<heutiges
  Datum>/bericht.md` (Lokalzeit, kein `--datum`-Flag). Ein `--trockenlauf`
  von `run_report.py` schreibt Bericht/Markdown aber bewusst NICHT mehr
  dorthin, sondern nach `arbeit/<stamp>-test/` (Zustandsschutz, siehe unten)
  — `video_report.py` findet also nichts und bricht mit "kein Bericht für
  ... nichts zu tun" ab. Ein echter (nicht-trockener) `run_report.py`-Lauf
  nur zum Testen würde dagegen den Delta-Zustand für den echten Abendlauf
  vorwegnehmen (derselbe Fehler wie beim Vorfall vom 19.08., nur über den
  ungeschützten Produktivpfad). Für einen echten Report→Video-Kettentest
  bleibt daher nur: auf den nächsten realen Cron-Lauf warten und dessen
  Logs prüfen, oder `testumgebung.py --kopieren` in einen Worktree spiegeln
  und dort risikofrei experimentieren. `shorts.py` hat dagegen ein eigenes
  `--datum`-Flag und lässt sich unabhängig gegen einen beliebigen
  vorhandenen `extrakte/<datum>/`-Stand testen.

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
  eines Tagesberichts, weil der Vertonungs-Cache dabei nicht greift.
- `videos.insert` (Uploads, inkl. Shorts) hat ein eigenes Kontingent von
  100 Uploads/Tag seit 2026 — 8 Shorts/Tag zusätzlich zum Hauptvideo sind
  unkritisch (siehe Memory `youtube-quota-2026-eigene-upload-buckets.md`).
- Intro-Länge bis Kapitel 1: 29.6 s (Boden 10 s wegen YouTube-Kapitelregel).
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

## Noch nicht produktiv verifiziert (Stand 21.08.2026 09:10 CEST)

Die gesamte Serie vom 20.08. an Synthese-/Render-/Upload-Logik — TL;DR-
Zahlenblock (`6509099`), Titel-Frontloading + Tag-Phrasen (`7f90c51`),
Retention-Rückkopplung (`2e2d63a`), Sprecherwechsel (`cb52e17`) und die
komplette Shorts-Pipeline (`4d4b34e`/`6a26128`) — läuft nur in
Unit-Tests/Sichttests der einzelnen Worktree-Agents (siehe deren Stories) und
in `pytest` auf dem gemergten `main` (194 grün). Ein echter End-to-End-Lauf
war zum Zeitpunkt dieser Prüfung nicht möglich, weil einerseits
`video_report.py` zwingend `extrakte/<heutiges Datum>/` braucht (siehe oben)
und andererseits ein echter, nicht-trockener `run_report.py`-Testlauf den
Delta-Zustand vor dem realen Abendlauf verschoben hätte (derselbe
Fehlermodus wie beim Vorfall vom 19.08.). Der erste vollständige Auto-Lauf
im neuen Abendrhythmus ist heute Abend, 21.08.2026 (Bericht 20:35, Video
21:15, Analytics 23:30, Shorts danach). **Beim nächsten Check konkret
prüfen:**
- `video_cron.log`: TL;DR-Kapitelmarke "TL;DR" bei ~00:00, Kapitel 1 ab
  ~40 s statt ~30 s, Video-Titel mit Suchbegriff vorne und Hook ≤55 Zeichen.
- `report_cron.log`: Zeile "Retention: ..." mit echtem Kennwerteblock
  (nicht "keine auswertbare Messung") — die Datengrundlage
  (`arbeit/analytics/2026-08-20.json`, 4 Kurven) steht bereits.
- Stimme im hochgeladenen Video: weiblich (Studio-O).
- `extrakte/<datum>/shorts_en.json`: mehrere Storys hochgeladen, Guard nicht
  gegriffen (Ähnlichkeit ≥0.90).

## Wartung dieses Skills

Dieses Dokument nach jeder Overseer-relevanten Erkenntnis erweitern:
neue Cron-Zeiten/-Skripte, neue Test-Flags, neue Fehlerklassen bei der
Update-Prüfung, aktualisierte Betriebswerte. Nicht dupliziert in `MEMORY.md`
pflegen — dort nur ein kurzer Verweis, Details hier.
