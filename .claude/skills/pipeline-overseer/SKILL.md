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
| 7:35 | `report.sh` | `run_report.py --top 15` → `extrakte/<datum>/bericht.md`, Folien, Bilder, GitHub-Publish |
| 8:10 | `video.sh` | `video_report.py --sprache en` (Vertonung+Render+Upload) + `klip_katalog.py` (Retention) |
| 21:30 | (inline) | `analytics_bericht.py --tage 45 --speichern` — Abbruchkurven als Erfolgskontrolle |

Jedes der drei Haupt-Skripte startet mit `git pull --ff-only || echo WARNUNG`
(fault-tolerant, damit hp-ubuntu bei jedem Lauf synchron zu `main` bleibt,
ohne den Lauf bei Konflikt abzubrechen). `report.sh` läuft **vor** `video.sh`
(7:35 vs 8:10), damit `bericht.md` sicher fertig ist, bevor die Vertonung
draufzugreift.

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
verbrauchen (Stand 19.08.2026: 12 % von 1'000'000 Zeichen/Monat, geteilt mit
hp-ubuntu — ein voller Testlauf kostet ca. 8'700 Zeichen). Nie einen Lauf
ohne Test-Flag lokal starten.

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
- Auf hp-ubuntu lässt sich derselbe Testlauf per SSH beobachten (nützlich,
  wenn der reale Cron-Lauf gerade läuft oder ein Produktions-spezifisches
  Problem vermutet wird — z.B. venv-Paketstand, Speicher, Rechenzeit):
  ```bash
  ssh hp-ubuntu "cd ~/boardstats && nohup ~/.venvs/boardstats-video/bin/python3 -u video_report.py --sprache en --nur-video > video/\$(date +%F)/build_test.log 2>&1 & disown"
  ```
  `-u` (unbuffered) ist Pflicht, sonst bleibt das Log bis Prozessende leer
  (bestätigter Fehlermodus, siehe Memory `feedback_logs_live_schreiben`).

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
3. **Tests laufen lassen** (`tests/`: `test_auswahl.py`, `test_kulisse.py`,
   `test_prosodie.py`, `test_tonmischung.py` — Stand 19.08.2026: 61 Tests):
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

## Bekannte Betriebswerte (Referenz, bei Bedarf hier aktualisieren)

- Google Studio-TTS-Kontingent: 1'000'000 Zeichen/Monat, geteilt zwischen
  hp-ubuntu-Produktion und jedem lokalen Testlauf ohne `--nur-video`/
  `--vorschau`. Realer Tagesbericht ≈ 8'700 Zeichen/~590 s Video.
  Stand 19.08.2026: 12 % verbraucht.
- Intro-Länge bis Kapitel 1: 29.6 s (Boden 10 s wegen YouTube-Kapitelregel).
  Tonwerte Sprachspur: −19.5 LUFS, Pausen −84 dBFS, 85 % Energie < 700 Hz →
  Musikbett bei −22 LU, kein Ducking (nur sidechaincompress am Bett selbst).
- Wiederverwendungssperre für Bilder/Clips: 5 Tage (seit `ece2f82`,
  vorher 14 Tage).
- Clip-Katalog-Retention (`klip_katalog.py`, via `video.sh` nach jedem
  Video-Lauf): Rohdatei löscht sich nach Verwendung oder 48 h Alter,
  Katalog-Eintrag (MD5, Bewertung) bleibt erhalten.
- Reuse-Ausnahme in `_klip_zuordnung()`: `zuletzt_verwendet == heute` zählt
  weiterhin als frei — ein Rebuild/Testlauf am selben Tag sperrt sich damit
  nicht selbst alle Clips.

## Geklärte Fälle (Root-Cause gefunden, nicht mehr aktiv verfolgen)

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
- **`aktivitaet.py` (Balkengrafik "Board-Aktivität", nutzt dieselben Fonts)
  ist laut eigenem Docstring noch NICHT in `video_report.py` verdrahtet** —
  Fonts sind bereit, der Chart läuft im produktiven Video noch nicht mit.
  Aktiv genutzt werden die Fonts bisher nur über `thumbnail.py`-Karten.

## Offene/unklare Punkte (nicht aktiv verfolgen, ausser Nutzer spricht sie an)

- Ungeklärter Mechanismus, wie Video `Q5Mbsfmkvnc` bereits vor einem
  expliziten Löschversuch auf YouTube als "Deleted video" markiert war.

## Wartung dieses Skills

Dieses Dokument nach jeder Overseer-relevanten Erkenntnis erweitern:
neue Cron-Zeiten/-Skripte, neue Test-Flags, neue Fehlerklassen bei der
Update-Prüfung, aktualisierte Betriebswerte. Nicht dupliziert in `MEMORY.md`
pflegen — dort nur ein kurzer Verweis, Details hier.
