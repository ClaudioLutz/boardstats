# boardstats — /biz/ Lagebericht

Täglicher Lagebericht aus dem 4chan-Board /biz/ (Business & Finance) als
E-Mail: was diskutiert wird, welche Titel und Coins genannt werden, welche
konkreten Zahlen fallen, welche Thesen mit welcher Begründung vertreten
werden. Diskurs-Dokumentation, keine Anlageberatung.

## Architektur

Dreistufige Pipeline (`run_report.py`), läuft per Cron auf hp-ubuntu:

1. **Bündeln** — `bundle_biz.py` wählt die Top-15-Threads nach Substanzdichte
   aus dem jüngsten Crawl-Snapshot (`crawl_biz.py`, 3x täglich) und schneidet
   Volltext-Bündel. Threads mit bekanntem Extrakt bekommen nur das Delta.
2. **Extrahieren** — Sonnet liest je Thread parallel und schreibt einen
   strukturierten Extrakt (Thema, Zahlen, Thesen, Quellen, ...). Liegt ein
   Extrakt vom Vortag vor, wird er fortgeschrieben statt neu erstellt
   (inkrementeller Extrakt-Cache); nach 5 Fortschreibungen oder >50 % neuen
   Posts seit der letzten Voll-Extraktion wird neu verankert.
3. **Synthetisieren** — Opus schreibt aus den Extrakten den Bericht
   (700–1000 Wörter). Die Extrakte gehen in Sandwich-Reihenfolge hinein
   (stärkster zuerst, zweitstärkster zuletzt, gegen den "lost in the
   middle"-Positionsbias), und die Synthese legt je Thread Rechenschaft ab
   (verwendet oder ausgelassen mit Grund). Das Glossar entsteht
   deterministisch in Python aus den Extrakt-Glossaren.

Versand als multipart/alternative (Klartext + HTML, `bericht_html.py`) über
SMTP mit XOAUTH2 (`send_mail.py`); Zugangsdaten liegen ausserhalb des Repos.

4. **Vertonen & Veröffentlichen auf YouTube** (`video_report.py`, eigener
   Cron-Eintrag via `video.sh`, entkoppelt von den ersten drei Schritten) —
   liest das bereits veröffentlichte `extrakte/<datum>/bericht.md`,
   bereinigt es für die Vertonung (`bloecke_erzeugen()`: Quell-/Beleg-Zeilen,
   nackte Thread-URLs und das GLOSSAR raus; die Blockstruktur — Absätze,
   ##-Überschriften, Aufzählungspunkte — bleibt erhalten), vertont per
   `edge-tts` (Stimme `de-DE-KatjaNeural`) und baut mit `ffmpeg`/`libass`
   ein Video, in dem der Bericht als dichter, formatierter Fliesstext
   (Absatzabstände, farbige Überschriften, Aufzählungszeichen) kontinuierlich
   durchs Bild scrollt und das jeweils gesprochene Wort farblich hervorgehoben
   wird (generiertes `.ass`, pro Wort ein deckungsgleiches Overlay statt
   nativem ASS-Karaoke; der Text läuft als starrer Block entlang einer
   global verankerten Scroll-Funktion, die sich dem Sprechtempo anpasst). Upload als **unlisted** über die YouTube Data API v3
   (`youtube_auth.py`, rohes Resumable-Upload per `urllib`, kein
   `google-api-python-client`). OAuth-Zugangsdaten liegen wie beim
   Mailversand ausserhalb des Repos
   (`~/.config/boardstats/youtube_client.json`/`youtube_token.json`,
   einmalig per `youtube_auth_setup.py` interaktiv eingerichtet). Ein
   Marker (`extrakte/<datum>/video.json`) verhindert Doppel-Uploads.

## Öffentliches Archiv

Unter [`extrakte/<datum>/`](extrakte/) liegt pro Tag sowohl der versandte
**Bericht** (`bericht.md`, `bericht_zu_markdown()`) als auch je Thread eine
**Extrakt**-Seite (Thema, Zahlen, Thesen, Quellen, Fachbegriffe, ...) plus
eine Tages-Übersicht. Das passiert automatisch bei jedem Lauf — Extrakte
gleich nach Stufe 2 (`markdown_tag_schreiben()`), der Bericht nach Stufe 3
(`bericht_veroeffentlichen()`) —, jeweils mit eigenem Commit + Push
(`git_veroeffentlichen()`; mit `--kein-github` abschaltbar). Anders als der
versandte Bericht behalten die Extrakt-Seiten auch das Glossar und die
offenen Fragen je Thread.

## Dateien

| Datei | Zweck |
|---|---|
| `run_report.py` | Orchestrierung der drei Stufen, Cache-Pflege, Versand |
| `bundle_biz.py` | Thread-Auswahl, Substanz-Scoring, Bündel-Schnitt |
| `crawl_biz.py` | Board-Crawl über die JSON-API (1 req/s) |
| `aggregate_biz.py` | Tages-Aggregation der Snapshots |
| `extract_prompt.txt` | Prompt Stufe 2, Voll-Extraktion |
| `update_prompt.txt` | Prompt Stufe 2, Delta-Fortschreibung |
| `bericht_html.py` | Klartext-Bericht → HTML-Mail (Inline-Styles) |
| `send_mail.py` | SMTP-Versand (OAuth-Refresh oder App-Passwort) |
| `video_report.py` | Bericht → TTS → Video, Upload zu YouTube |
| `youtube_auth.py` | YouTube-OAuth-Refresh + Resumable-Upload |
| `youtube_auth_setup.py` | Einmaliges interaktives YouTube-OAuth-Setup |
| `report.sh` / `run.sh` / `video.sh` | Cron-Wrapper für Bericht, Crawl bzw. Video |

Laufzeitdaten (`arbeit/`, `berichte/`, `cache/`, `logs/`) sind bewusst
nicht versioniert — sie enthalten Board-Rohinhalte.
