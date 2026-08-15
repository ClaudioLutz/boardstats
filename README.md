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
   deterministisch in Python aus den Extrakt-Glossaren. Der fertige Bericht
   wird anschliessend in einem einzigen Sonnet-Aufruf ins Englische
   rückübersetzt (`bericht_en.md`) — Rückübersetzung deshalb, weil die
   Quelle englischsprachig ist und der /biz/-Jargon in seiner originalen
   Form rekonstruiert werden muss, nicht wörtlich übersetzt. Ein weiterer
   kleiner Sonnet-Aufruf erzeugt aus dem Bericht je Sprache einen
   reisserischen YouTube-Titel (`titel.json`, Hook + Serien-Suffix); die
   Titel der letzten 14 Tage gehen als Sperrliste mit, damit sich der
   Aufhänger auch bei Dauerthemen nicht wiederholt. Derselbe Aufruf liefert
   je Sprache ein kurzes Schlagwort für das Vorschaubild. Danach sucht der
   Lauf ein Bildmotiv für dieses Vorschaubild: die Kandidaten kommen aus den
   Anhängen der ausgewerteten Threads im Crawl-Snapshot (OP-Bilder zuerst,
   gespoilerte, gelöschte, zu kleine und Bannerformate fallen raus), Sonnet
   sieht sie mit dem Read-Werkzeug an und wählt höchstens eines aus. Der
   Standard ist Ablehnung: ohne eigene Bildbeschreibung je Kandidat gilt die
   Antwort als ungesehen und wird verworfen, und gewählt werden darf nur
   eine tatsächlich heruntergeladene Datei. Das Motiv landet unter
   `arbeit/thumbs/` und damit ausserhalb des Repos — fremdes Bildmaterial
   gehört nicht ins öffentliche Archiv. Nach demselben Muster, aber mit
   bewusst lockerer Messlatte, prüft der Lauf zusätzlich Hintergrundbilder
   fürs Video: je ausgewertetem Thread bis zu vier Bild-Anhänge, abgelehnt
   wird nur, was gegen die YouTube-Richtlinien verstösst (das Netz gegen
   ungesehene Urteile bleibt dasselbe). Die freigegebenen Bilder liegen mit
   Thread-Zuordnung unter `arbeit/motive/<datum>/`.

Versand als multipart/alternative (Klartext + HTML, `bericht_html.py`) über
SMTP mit XOAUTH2 (`send_mail.py`); Zugangsdaten liegen ausserhalb des Repos.

4. **Vertonen & Veröffentlichen auf YouTube** (`video_report.py`, eigener
   Cron-Eintrag via `video.sh`, entkoppelt von den ersten drei Schritten) —
   läuft zweisprachig (deutsch aus `bericht.md` mit `de-DE-KatjaNeural`,
   englisch aus `bericht_en.md` mit `en-US-JennyNeural`, Parameter
   `--sprache`), liest das bereits veröffentlichte `extrakte/<datum>/bericht.md`,
   bereinigt es für die Vertonung (`bloecke_erzeugen()`: Quell-/Beleg-Zeilen,
   nackte Thread-URLs und das GLOSSAR raus; die Blockstruktur — Absätze,
   ##-Überschriften, Aufzählungspunkte — bleibt erhalten), vertont per
   `edge-tts` (Stimme `de-DE-KatjaNeural`) und baut mit `ffmpeg`/`libass`
   ein Video: der Text erscheint synchron zum Gesprochenen in Happen von
   höchstens drei Zeilen am unteren Bildrand (linksbündig, Fliesstext mit
   Satzzeichen, Aufzählungen mit hängendem Einzug), ##-Überschriften stehen
   während ihrer Sprechzeit als grosse Titelkarte weiter oben, und das
   jeweils gesprochene Wort wird farblich hervorgehoben. Gerendert werden
   die Quell-Tokens des Berichts (edge-tts-WordBoundary-Texte sind
   satzzeichenlos und liefern nur die Zeitfenster); die Hervorhebung ist
   derselbe Zeilenstring mit per `\alpha` maskierten Nachbarwörtern und
   dadurch pixelgenau deckungsgleich. Als Hintergrund laufen — entsättigt,
   stark abgedunkelt und leicht unscharf — die freigegebenen Bild-Anhänge
   der gerade besprochenen Threads (`arbeit/motive/<datum>/`, Zuordnung
   über die Quell-URLs unter jedem Berichtsabschnitt); Abschnitte ohne
   freigegebenes Bild bekommen das Vorschaubild des Tages, und scheitert
   der Hintergrund-Aufbau ganz, bleibt die einfarbige Fläche.
   Upload als **öffentliches** Video über die YouTube
   Data API v3 (`youtube_auth.py`, rohes Resumable-Upload per `urllib`, kein
   `google-api-python-client`). Das Vorschaubild baut `thumbnail.py` je
   Sprache neu: fester Serienrahmen (dunkler Grund, Amber-Akzent, Kopf- und
   Fusszeile) mit dem Schlagwort des Tages in grosser Schrift, als Motiv
   rechts das geprüfte Board-Bild aus `arbeit/thumbs/` und ersatzweise das
   statische `assets/thumbnail.jpg`; gesetzt wird es über `thumbnails/set`,
   das einen verifizierten Kanal braucht.
   OAuth-Zugangsdaten liegen wie beim Mailversand ausserhalb des Repos
   (`~/.config/boardstats/youtube_client.json`/`youtube_token.json`,
   einmalig per `youtube_auth_setup.py` interaktiv eingerichtet). Ein
   Marker je Sprache (`extrakte/<datum>/video.json` bzw. `video_en.json`)
   verhindert Doppel-Uploads. Der Video-Titel kommt aus der vom Report-Lauf
   erzeugten `titel.json` (dynamischer Tages-Hook); fehlt sie oder ist sie
   unbrauchbar, fällt der Upload auf den statischen Serientitel
   «/biz/-Lagebericht {datum}» zurück. Die Videobeschreibung enthält den
   Berichtstext selbst (Markdown-Auszeichnung entfernt) und darunter die
   Quell-Threads; da YouTube nur 5000 Zeichen zulässt, wird an einer
   Abschnittsgrenze gekappt, wobei die Thread-Links ihr Budget vorab
   bekommen. Auf das eigene Repo wird dort nicht verlinkt.

## Öffentliches Archiv

Unter [`extrakte/<datum>/`](extrakte/) liegt pro Tag sowohl der versandte
**Bericht** (`bericht.md`, `bericht_zu_markdown()`; dazu die englische
Fassung `bericht_en.md`) als auch je Thread eine
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
| `thumbnail.py` | Vorschaubild: Serienrahmen + Tages-Schlagwort + Motiv |
| `youtube_auth.py` | YouTube-OAuth-Refresh + Resumable-Upload |
| `youtube_auth_setup.py` | Einmaliges interaktives YouTube-OAuth-Setup |
| `report.sh` / `run.sh` / `video.sh` | Cron-Wrapper für Bericht, Crawl bzw. Video |

Laufzeitdaten (`arbeit/`, `berichte/`, `cache/`, `logs/`) sind bewusst
nicht versioniert — sie enthalten Board-Rohinhalte.
