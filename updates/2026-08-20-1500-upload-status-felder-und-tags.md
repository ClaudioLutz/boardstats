# Upload verlor embeddable und publicStatsViewable — Ursache und Fix

## Was kaputt war

Die Videos vom 19. und 20.08.2026 standen auf `embeddable: false` und
`publicStatsViewable: false` — sie liessen sich nirgends einbetten und die
Aufrufzahl war öffentlich ausgeblendet. Alle Uploads davor waren sauber.

Es war kein Content-ID-Claim und kein Handgriff in YouTube Studio, sondern
unser eigener Code. Seit `8c6287d` (19.08., "Upload erst privat, öffentlich
erst nach Thumbnail/Untertitel/Playlist") schaltet `status_setzen()` das Video
per `videos.update` frei — und schickte dabei nur `privacyStatus`. YouTube
ersetzt bei einem Update aber **den ganzen angegebenen part**: jedes Feld, das
im Body fehlt, fällt auf den API-Default zurück. Für die beiden Booleans heisst
das `false`.

Beide Videos wurden am 20.08. per `videos.update` mit vollständigem
status-Block repariert und nachgeprüft.

## Was geändert wurde

**`youtube_auth.py`**

- `status_lesen()` neu: liest den status-Block eines Videos.
- `status_setzen()` arbeitet jetzt als Read-Modify-Write — der vorhandene
  Block wird gelesen und mitsamt allen beschreibbaren Feldern
  (`STATUS_FELDER`) zurückgeschrieben, nur `privacyStatus` wird ersetzt.
  Fehlen die Felder in der Antwort, greift der Kanalwunsch: einbettbar,
  Aufrufzahl sichtbar.
- `hochladen()` setzt `embeddable` und `publicStatsViewable` ausdrücklich,
  damit der Update-Pfad später garantiert Werte zum Zurücklesen hat.

**`video_report.py` — Tag-Qualität**

Die Tags schöpften 108 von 450 erlaubten Zeichen aus, und was durchkam, war
teils Rauschen (`impossible`, `crashes`, `klarna crashes $120k`). Grund: als
Titel-Kandidat diente `_thumb_aus_titel()` — das ist der auf drei Wörter
gekappte Text fürs Vorschaubild, keine Suchanfrage.

- `_titel_schlagworte()` neu: nimmt die grossgeschriebenen Wörter des Titels
  einzeln (`klarna`, `nvidia`, `monero`), ohne Schlagzeilen-Zahlen wie `120K`.
- `STOPP_TAGS`: Schlagzeilenverben und mehrdeutige Kürzel (`crashes`, `pumps`,
  `impossible`, `cusip`, `app`, `link` …) fliegen aus jeder Quelle raus.
- `tags_bauen()` nimmt zusätzlich den Berichtstext und zieht daraus die Ticker
  in Klammern — `Klarna (KLAR)` → `klar`. Das sind die präzisesten
  Suchbegriffe des Tages.

Gemessen an den Berichten vom 16.–19.08. ergibt das statt
`['klarna crashes $120k']` nun `['klarna', 'klar', 'nlst']` bzw.
`['nvidia', 'spac rights', 'macro', 'meme stocks']`.

**`tests/test_upload_metadaten.py`** neu: fünf Tests — Status-Felder überleben
das Update, Fallback auf einbettbar, Eigennamen statt Phrase, Ticker aus dem
Bericht, Zeichenlimit.

## Nachträglich an den Videos

- `66TVSAMrUSw` (19.08.) und `LGhGnj75rEg` (20.08.): `embeddable` und
  `publicStatsViewable` zurück auf `true`.
- `od-AKhvWzIA` (15.08., vor dem Metadaten-Commit hochgeladen): Tags und
  Hashtag-Zeile nachgetragen, Kopfzeile gross. Kapitelmarken fehlen dort
  weiterhin — die Zeitstempel gibt es nachträglich nicht mehr.

## Validierung

`ruff check` sauber, `mypy` sauber, 140 Tests grün.
