# boardstats — /biz/ Situation Report

Täglicher Lagebericht aus dem 4chan-Board /biz/ (Business & Finance),
veröffentlicht als Markdown-Archiv und YouTube-Video: was diskutiert wird,
welche Titel und Coins genannt werden, welche konkreten Zahlen fallen,
welche Thesen mit welcher Begründung vertreten werden — samt der Stimme des
Boards (Memes und Einzeiler als wörtliche Zitate). Diskurs-Dokumentation,
keine Anlageberatung. Seit 16.08.2026 läuft die gesamte Pipeline auf
Englisch, der Sprache des Boards: jede Übersetzung ins Deutsche verlor
Jargon und Boardhumor. Der frühere E-Mail-Versand ist abgebaut.

## Architektur

Dreistufige Pipeline (`run_report.py`), läuft per Cron auf hp-ubuntu:

1. **Bündeln** — `bundle_biz.py` wählt die Top-15-Threads nach Substanzdichte
   aus dem jüngsten Crawl-Snapshot (`crawl_biz.py`, 3x täglich) und schneidet
   Volltext-Bündel. Threads mit bekanntem Extrakt bekommen nur das Delta.
2. **Extrahieren** — Sonnet liest je Thread parallel und schreibt einen
   strukturierten Extrakt auf Englisch (Topic, Hard Numbers, Claims,
   Sources, ... und «Mood and Memes»: die wörtlichen Einzeiler und Memes,
   die den Ton des Threads tragen). Liegt ein
   Extrakt vom Vortag vor, wird er fortgeschrieben statt neu erstellt
   (inkrementeller Extrakt-Cache); nach 5 Fortschreibungen oder >50 % neuen
   Posts seit der letzten Voll-Extraktion wird neu verankert.
3. **Synthetisieren** — Opus schreibt aus den Extrakten den englischen
   Bericht (700–1000 Wörter): faktenorientiert, aber mit der Stimme des
   Boards als Würze (die stärksten Mood-and-Memes-Zitate wandern in die
   passenden Themen; Slurs und Streit bleiben draussen). Die Extrakte gehen
   in Sandwich-Reihenfolge hinein
   (stärkster zuerst, zweitstärkster zuletzt, gegen den "lost in the
   middle"-Positionsbias), und die Synthese legt je Thread Rechenschaft ab
   (verwendet oder ausgelassen mit Grund). Das Glossar entsteht
   deterministisch in Python aus den Extrakt-Glossaren. Ein
   kleiner Sonnet-Aufruf erzeugt aus dem Bericht einen
   reisserischen YouTube-Titel (`titel.json`, Hook + Serien-Suffix); die
   Titel der letzten 14 Tage gehen als Sperrliste mit, damit sich der
   Aufhänger auch bei Dauerthemen nicht wiederholt. Derselbe Aufruf liefert
   ein kurzes Schlagwort für das Vorschaubild. Ein weiterer
   Sonnet-Aufruf verdichtet den Bericht zu Folieninhalten für die
   Video-Präsentation (`folien.json`: je Abschnitt Folientitel, Stichpunkte
   mit wörtlichen Anker-Phrasen fürs Timing, optionale Kennzahl, dazu vier
   «Numbers of the day»). Danach sucht der
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
   ungesehene Urteile bleibt dasselbe). Jedes freigegebene Bild bekommt
   dabei zwei Bewertungen von 1 bis 5 (Unterhaltungswert als Kulisse,
   Themennähe zu Finanzen/Märkten), nach denen der Video-Lauf die
   Bildauswahl sortiert. Die freigegebenen Bilder liegen mit
   Thread-Zuordnung und Bewertungen unter `arbeit/motive/<datum>/`.

4. **Vertonen & Veröffentlichen auf YouTube** (`video_report.py`, eigener
   Cron-Eintrag via `video.sh`, entkoppelt von den ersten drei Schritten) —
   vertont `bericht.md` mit der Stimme `en-US-Neural2-J`. Der Lauf
   bereinigt den Bericht für die Vertonung (`bloecke_erzeugen()`:
   Quell-/Beleg-Zeilen, nackte Thread-URLs und das GLOSSAR raus), ergänzt
   gesprochene Rahmen-Sätze (Begrüssung, Kapitel-Aufzählung, Tageszahlen,
   Abspann), vertont per
   Google Cloud TTS (Neural2-Stimme; Wort-Zeitstempel über SSML-`<mark>`-
   Timepoints, absatzweise gestückelt wegen des 5000-Byte-API-Limits; der
   API-Key liegt ausserhalb des Repos unter
   `~/.config/boardstats/google_tts_key.txt`, ohne Key fällt der Lauf auf
   `edge-tts` mit `en-US-GuyNeural` zurück) und baut mit `ffmpeg` eine
   **Folien-Präsentation** (`folien.py`, Design wie das Vorschaubild):
   Intro-Folie mit dem Tages-Aufhänger, Agenda, je Berichtsabschnitt eine
   Themen-Folie mit verdichteten Stichpunkten und optionaler Zahlen-Karte,
   zum Schluss «Numbers of the day» und ein Abspann. Die Folieninhalte
   verdichtet ein Sonnet-Aufruf im Report-Lauf (`folien.json`: Folientitel,
   Stichpunkte mit wörtlichen Anker-Phrasen, Kennzahlen). Beim
   Kapitelwechsel erscheint das Board-Bild des Abschnitts zuerst
   vollflächig und unverdunkelt mit der Überschrift (solange sie gesprochen
   wird) und blendet dann weich zur Folie über; die Stichpunkte leuchten
   auf, sobald die Vorlesestimme ihre Anker-Phrase erreicht. Alle Zustände
   sind PIL-Standbilder, zeitgesteuert über eine ffconcat-Liste — Text wird
   auf diesem Pfad nicht mehr per ASS eingebrannt. Die Bilder kommen aus
   den freigegebenen Anhängen der besprochenen Threads
   (`arbeit/motive/<datum>/`, Zuordnung über die Quell-URLs unter jedem
   Berichtsabschnitt, je Thread die bestbewerteten zuerst); jede Folie
   bekommt ein frisches, noch nicht gezeigtes Bild — zuerst aus dem eigenen
   Thread, dann aus dem Pool der übrigen Tagesbilder (die unterhaltsamsten
   zuerst), erst wenn alle durch sind wiederholt sich eines. Auch innerhalb
   einer Themen-Folie wechselt das Motiv: mit jedem aufleuchtenden
   Stichpunkt kommt ein weiteres Bild, bevorzugt aus dem eigenen Thread
   (notfalls rotieren dessen Bilder), und die Agenda zeigt beim Aufleuchten
   eines Eintrags das Motiv des zugehörigen Kapitels als Vorschau. Die
   Fusszeile der Themen-Folie nennt den Original-Betreff des Quell-Threads
   (aus dem H1 der Extrakt-Seite; nur wenn der fehlt, die Thread-Nummer).
   Ein Tag ganz ohne Bilder läuft auf der dunklen Grundfläche. Fehlt `folien.json` oder scheitert der
   Folien-Aufbau, entsteht das Video im bisherigen Text-Layout
   (Text-Happen unten, Titelkarten oben, Wort-Karaoke per `libass`) — die
   Präsentation darf den Upload nie verhindern.
   Upload als **öffentliches** Video über die YouTube
   Data API v3 (`youtube_auth.py`, rohes Resumable-Upload per `urllib`, kein
   `google-api-python-client`); mitgegeben werden Sprach-Metadaten
   (`defaultLanguage`/`defaultAudioLanguage`), Tags (feste Serien-Tags plus
   Tagesthemen aus den Überschriften), Hashtags am Beschreibungsanfang und
   automatische Kapitelmarken aus den Abschnitts-Startzeiten der Vertonung.
   Nach dem Upload wird eine **eigene Untertitel-Spur** (SRT) angehängt,
   gebaut aus den Wort-Zeitstempeln der TTS: satzweise Cues mit maximal zwei
   Zeilen, gebrochen an Satzenden und hörbaren Pausen — präziser als die
   YouTube-Automatik. `captions.insert` braucht den Scope
   `youtube.force-ssl`; fehlt er im Token, bleibt es bei den
   Auto-Untertiteln, der Upload ist davon unberührt. Das Vorschaubild baut `thumbnail.py` je
   Sprache neu: fester Serienrahmen (dunkler Grund, Amber-Akzent, Kopf- und
   Fusszeile) mit dem Schlagwort des Tages in grosser Schrift, als Motiv
   rechts das geprüfte Board-Bild aus `arbeit/thumbs/` und ersatzweise das
   statische `assets/thumbnail.jpg`; gesetzt wird es über `thumbnails/set`,
   das einen verifizierten Kanal braucht.
   OAuth-Zugangsdaten liegen ausserhalb des Repos
   (`~/.config/boardstats/youtube_client.json`/`youtube_token.json`,
   einmalig per `youtube_auth_setup.py` interaktiv eingerichtet). Ein
   Marker (`extrakte/<datum>/video_en.json`)
   verhindert Doppel-Uploads. Der Video-Titel kommt aus der vom Report-Lauf
   erzeugten `titel.json` (dynamischer Tages-Hook); fehlt sie oder ist sie
   unbrauchbar, fällt der Upload auf den statischen Serientitel
   «/biz/ Situation Report {datum}» zurück. Die Videobeschreibung enthält den
   Berichtstext selbst (Markdown-Auszeichnung entfernt) und darunter die
   Quell-Threads; da YouTube nur 5000 Zeichen zulässt, wird an einer
   Abschnittsgrenze gekappt, wobei die Thread-Links ihr Budget vorab
   bekommen. Auf das eigene Repo wird dort nicht verlinkt.

## Öffentliches Archiv

Unter [`extrakte/<datum>/`](extrakte/) liegt pro Tag sowohl der
**Bericht** (`bericht.md`, `bericht_zu_markdown()`) als auch je Thread eine
**Extrakt**-Seite (Topic, Hard Numbers, Claims, Sources, Slang, ...) plus
eine Tages-Übersicht. Tage bis zum 16.08.2026 sind deutsch (damals mit
englischer Zweitfassung `bericht_en.md`), spätere englisch. Das passiert
automatisch bei jedem Lauf — Extrakte
gleich nach Stufe 2 (`markdown_tag_schreiben()`), der Bericht nach Stufe 3
(`bericht_veroeffentlichen()`) —, jeweils mit eigenem Commit + Push
(`git_veroeffentlichen()`; mit `--kein-github` abschaltbar). Anders als der
Bericht behalten die Extrakt-Seiten auch das Glossar und die
offenen Fragen je Thread.

## Dateien

| Datei | Zweck |
|---|---|
| `run_report.py` | Orchestrierung der drei Stufen, Cache-Pflege, Veröffentlichung |
| `bundle_biz.py` | Thread-Auswahl, Substanz-Scoring, Bündel-Schnitt |
| `crawl_biz.py` | Board-Crawl über die JSON-API (1 req/s) |
| `aggregate_biz.py` | Tages-Aggregation der Snapshots |
| `extract_prompt.txt` | Prompt Stufe 2, Voll-Extraktion |
| `update_prompt.txt` | Prompt Stufe 2, Delta-Fortschreibung |
| `bericht_html.py` | Überschrift-Erkennung fürs Markdown (Rest aus der Mail-Zeit) |
| `send_mail.py` | SMTP-Versand — seit 16.08.2026 ungenutzt (Mail abgebaut) |
| `video_report.py` | Bericht → TTS → Video, Upload zu YouTube |
| `folien.py` | Präsentations-Folien des Videos (PIL, Design wie Vorschaubild) |
| `thumbnail.py` | Vorschaubild: Serienrahmen + Tages-Schlagwort + Motiv |
| `youtube_auth.py` | YouTube-OAuth-Refresh + Resumable-Upload |
| `youtube_auth_setup.py` | Einmaliges interaktives YouTube-OAuth-Setup |
| `report.sh` / `run.sh` / `video.sh` | Cron-Wrapper für Bericht, Crawl bzw. Video |

Laufzeitdaten (`arbeit/`, `berichte/`, `cache/`, `logs/`) sind bewusst
nicht versioniert — sie enthalten Board-Rohinhalte.
