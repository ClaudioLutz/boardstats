# Der Crawl-Snapshot wird erst sichtbar, wenn er fertig ist

**Was:** `crawl_biz.py` schreibt den Snapshot jetzt nach `<stamp>.jsonl.gz.tmp`
und benennt ihn erst nach dem letzten Thread in `<stamp>.jsonl.gz` um. Waehrend
der rund vier Minuten Crawl faellt die Datei damit aus dem `glob("*.jsonl.gz")`
aller Leser heraus. Zusaetzlich meldet `run_report._snapshot_posts()` einen
unlesbaren Snapshot jetzt im Log und weicht auf den vorherigen aus, statt still
leer zurueckzukommen.

**Warum:** Am 19.08.2026 20:23 ueberlappte ein Testlauf mit dem 20:20-Crawl und
las `raw/2026-08-19T1820.jsonl.gz` mitten im Schreibvorgang —
`gzip.BadGzipFile`. Der Fehler lief in ein try/except weiter oben: kein
Absturz, aber kein einziges frisches Motiv, keine Kulisse, keine Clips fuer den
ganzen Tag, und keine Zeile im Log, die das erklaert haette.

Der Rename loest das an der Quelle und deckt damit alle drei Leser ab
(`run_report.py`, `bundle_biz.py`, `aggregate_biz.py`). Das ist der Punkt: Eine
reine Fehlerbehandlung beim Lesen haette den *technisch* kaputten Snapshot
erkannt, nicht aber den technisch heilen, inhaltlich halben — `bundle_biz.py`
haette daraus ein lueckenhaftes Buendel gebaut, ohne dass irgendwo etwas
auffaellt. Die Fehlerbehandlung bleibt trotzdem drin, fuer Torsi aus der Zeit
vor dieser Aenderung und fuer Snapshots, die per `--host` von einem anderen
Rechner kommen.

**Auswirkung:** Im Normalbetrieb (report.sh 15 Min nach run.sh) aendert sich
nichts. Verzoegert sich ein Crawl oder wird zu einem unguenstigen Zeitpunkt von
Hand gestartet, sieht der Leser jetzt den vorherigen vollstaendigen Snapshot
statt eines Torsos. Nebengewinn: Ein abgebrochener Crawl hinterlaesst keinen
halben Snapshot mehr, der bis zum naechsten Lauf als "juengster" gelten wuerde;
Reste raeumt der naechste Crawl-Start weg.

**Offen:** `bundle_biz.lade()` faengt weiterhin nichts ab. Mit dem Rename kann
der Fall dort nicht mehr entstehen, und ein harter Abbruch in `report.sh` waere
laut genug — bewusst so gelassen.
