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
   die den Ton des Threads tragen — getrennt nach Tageszitat und
   «Canon:», den festen Wendungen, die das Board über Threads und Tage
   hinweg wiederverwendet; dazu erklärt «Terms and Slang» neben Fach- und
   Board-Jargon auch die Mechanik des Boards selbst, an der ein
   Aussenstehender hängenbleibt: General, OP, QRD, 1pbtid, jannies).
   Zitiert wird ausschliesslich wörtlich: eine halb gesagte Wendung darf
   nicht zur bekannten Form vervollständigt werden — gemessen am 17.08.
   war genau das passiert. Liegt ein
   Extrakt vom Vortag vor, wird er fortgeschrieben statt neu erstellt
   (inkrementeller Extrakt-Cache); nach 5 Fortschreibungen oder >50 % neuen
   Posts seit der letzten Voll-Extraktion wird neu verankert.
3. **Synthetisieren** — Opus schreibt aus den Extrakten den englischen
   Bericht (700–1000 Wörter): faktenorientiert, aber die Stimme des
   Boards zählt als Material, nicht als Würze — jedes Thema mit brauchbarer
   Zeile trägt mindestens ein wörtliches Zitat, Canon-Wendungen haben
   Vorrang vor dem Einfall von heute Morgen, und die Generals gelten als
   Institution: die laufende Nummer eines Threads (z. B. `/XSG/ #2555`)
   ist selbst ein Befund. Slurs und Streit bleiben draussen. Die Extrakte gehen
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
   Sonnet-Aufruf schreibt das Szenen-Drehbuch für das Video
   (`folien.json`, Version 2): je Abschnitt ein Kapiteltitel, die
   Bildseite der Stichpunkt-Karte (bewusste Platzierung durch das
   Modell), Stichpunkte als laufender Kommentar (möglichst einer je
   gesprochenem Satz), optionale Zwischenthemen, das beste wörtliche
   Board-Zitat und die markanteste Kennzahl — alles mit wörtlichen
   Anker-Phrasen fürs Timing, dazu vier «Numbers of the day». Welche
   Elemente ein Abschnitt bekommt, entscheidet das Modell nach Material,
   der Aufbau variiert also von Tag zu Tag. Danach sucht der
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
   `edge-tts` mit `en-US-GuyNeural` zurück) und baut mit `ffmpeg` ein
   **Szenen-Video** (Overlays aus `szenen.py`, Design-Vokabular wie das
   Vorschaubild): jede Szene zeigt ein Board-Bild vollflächig mit langsamem
   Zoom-Drift (`zoompan`), mild weichgezeichnet und leicht abgedunkelt,
   damit die Feinstruktur der Board-Bilder nicht mit der Schrift
   konkurriert; darüber liegen transparente Text-Overlays, die
   zeitgesteuert ein- und ausblenden — Kapitel-Opener als Lower Third,
   der Titel des laufenden Themas oben, darunter die persistente Liste
   der bereits geparkten Stichpunkte, die stehen bleibt, bis das Thema
   oder Zwischenthema wechselt, und daneben der Stichpunkt, über den
   gerade gesprochen wird: er erscheint synchron zum Gesprochenen groß in
   der freien Bildhälfte, steht dort, bis der nächste ihn ablöst, und
   fliegt dann in die Liste, wo er parkt (damit läuft keine
   Sprechsekunde ohne Text im Bild und die freie Bildhälfte bleibt
   belebt); nach dem letzten Stichpunkt eines Themas hält das Bild rund
   zweieinhalb Sekunden auf der vollständigen Liste, wofür die
   Vertonung an Kapitelgrenzen eine entsprechend lange Pause setzt.
   Dazu Zwischenthemen als eigene Mini-Opener, Board-Zitate als
   4chan-Post-Karte und Kennzahlen als bildschirmfüllende Zahl mit
   Count-up. Das Drehbuch dazu stammt aus dem
   Report-Lauf (`folien.json`, Version 2); wann ein Element erscheint,
   steuert der Fundort seiner Anker-Phrase in den Wort-Zeitstempeln. Jede
   Szene wird als eigener kurzer ffmpeg-Clip gerendert und am Ende auf dem
   25-fps-Frame-Raster nahtlos zusammengefügt (kein Drift zur Tonspur).
   Die Bilder kommen aus den freigegebenen Anhängen der besprochenen
   Threads (`arbeit/motive/<datum>/`, Zuordnung über die Quell-URLs unter
   jedem Berichtsabschnitt, je Thread die bestbewerteten zuerst); jede
   Szene bekommt ein frisches, noch nicht gezeigtes Bild — zuerst aus dem
   eigenen Thread, dann aus dem Pool der übrigen Tagesbilder (die
   stärksten Motive zuerst), erst wenn alle durch sind wiederholt sich
   eines. Die Reihenfolge richtet sich nach der Sichtprüfung des
   Report-Laufs, die jedes Bild danach bewertet, wie viel echtes Motiv
   statt Text darauf zu sehen ist: Bilder, die praktisch nur eine Textwand
   sind (Screenshot einer Artikel- oder Suchergebnisseite, Chatverlauf,
   Kurstabelle), verlieren auch den Vorrang im eigenen Thread und kommen
   nur dran, wenn der Tag kein frisches Motiv mehr hergibt. Lange Sprechstrecken wechseln spätestens alle zwanzig Sekunden
   die Szene, das «Coming up» zeigt zu jedem Kapitel das Motiv als
   Vorschau, und der Kapitel-Opener nennt den Original-Betreff des
   Quell-Threads (aus dem H1 der Extrakt-Seite). Ein Tag ganz ohne Bilder
   läuft auf der dunklen Grundfläche. Eine `folien.json` im alten Format
   (ohne Version) rendert weiter die v6-Folien-Präsentation (`folien.py`);
   fehlt sie ganz oder scheitert der Szenen-Aufbau, entsteht das Video im
   Text-Layout (Text-Happen unten, Titelkarten oben, Wort-Karaoke per
   `libass`) — kein Layout-Problem darf den Upload verhindern.
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
   «/biz/ Situation Report {datum}» zurück. Derselbe Hook eröffnet auch die
   **Vertonung** («Today's top story: …» vor dem Serien-Satz), damit die
   ersten Sekunden einlösen, wofür der Titel den Klick geholt hat, statt mit
   Datum und Inhaltsverzeichnis zu beginnen; beim statischen Serientitel
   bleibt die Eröffnung wie bisher. Nach dem Upload hängt der Lauf das Video
   in die Serien-Playlist des Kanals (`playlistItems.insert`, Playlist-ID in
   `SPRACHEN`) und macht es zum Kanal-Trailer, den die Kanalseite Besuchern
   ohne Abo oben zeigt (`channels.update`, `brandingSettings.unsubscribedTrailer`);
   scheitert eines von beidem, bleibt der Upload gültig. Die
   Videobeschreibung enthält den
   Berichtstext selbst (Markdown-Auszeichnung entfernt) und darunter die
   Quell-Threads; da YouTube nur 5000 Zeichen zulässt, wird an einer
   Abschnittsgrenze gekappt, wobei die Thread-Links ihr Budget vorab
   bekommen. Auf das eigene Repo wird dort nicht verlinkt.

## Öffentliches Archiv

Unter [`extrakte/<datum>/`](extrakte/) liegt pro Tag sowohl der
**Bericht** (`bericht.md`, `bericht_zu_markdown()`) als auch je Thread eine
**Extrakt**-Seite (Topic, Hard Numbers, Claims, Sources, Slang, ...) plus
eine Tages-Übersicht. Tage bis zum 15.08.2026 sind deutsch (damals mit
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
| `video_report.py` | Bericht → TTS → Szenen-Video, Upload zu YouTube |
| `szenen.py` | Text-Overlays des Szenen-Videos (PIL, transparente PNGs) |
| `folien.py` | v6-Präsentations-Folien — nur noch Fallback für alte `folien.json` |
| `thumbnail.py` | Vorschaubild: Serienrahmen + Tages-Schlagwort + Motiv |
| `youtube_auth.py` | YouTube-OAuth-Refresh + Resumable-Upload |
| `youtube_auth_setup.py` | Einmaliges interaktives YouTube-OAuth-Setup |
| `report.sh` / `run.sh` / `video.sh` | Cron-Wrapper für Bericht, Crawl bzw. Video |

Laufzeitdaten (`arbeit/`, `berichte/`, `cache/`, `logs/`) sind bewusst
nicht versioniert — sie enthalten Board-Rohinhalte.
