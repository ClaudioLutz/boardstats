---
datum: 2026-08-22
agent: main
typ: feature
commit: <Hash, sobald bekannt>
---

# Analytics: Traffic-Quellen fest in der Erfolgskontrolle

**Was:** `analytics_bericht.py` erhebt und speichert jetzt zusaetzlich, **woher**
die Aufrufe kommen. Drei neue Abfragen, eine reine Anzeigefunktion, ein Flag:

- `traffic_quellen()` — Aufrufe je Tag und Quelle (`day,insightTrafficSourceType`)
- `suchbegriffe()` — die Begriffe hinter `YT_SEARCH`, nach Aufrufen sortiert
- `landeszahlen(land="CH")` — Tagesreihe eines Landes als Eigensichtungs-Detektor
- `traffic_pivot()` — pure Pivotierung fuer die Anzeige, getestet
- `--land ISO` — Kontrollreihe umstellbar

Unter `--speichern` wandern die **Rohzeilen** als `traffic`, `suchbegriffe`,
`land`, `land_tage` in `arbeit/analytics/<datum>.json`; pivotiert wird erst
beim Lesen.

**Warum:** Anlass war die Frage, ob YouTube die aktuellen Videos "abgeschrieben"
hat (3 / 8 / 8 Aufrufe gegen 30 am 18.08.). Die Antwort stand nicht in den
Aufrufzahlen, sondern in ihrer Herkunft — und die musste ad hoc erhoben werden,
weil das Skript sie nicht kannte. Ohne die Aufschluesselung liest man jeden
Rueckgang als Strafe des Empfehlungs-Algorithmus. Tatsaechlich zeigte die
Messung (`research/messung-reichweite-einbruch-2026-08-22.md`):

- **kein `YT_BROWSE`** im ganzen Zeitraum 14.-19.08. — der Empfehlungs-Feed hat
  den Kanal nie ausgespielt
- die Suchbegriffe sind tagesaktuell (`monero` 11, `grrr stock` 4), kein
  einziger Kanal-/Markenbegriff
- die CH-Aufrufe fallen nach dem 16.08. auf **exakt null** — das sind die
  weggefallenen eigenen Kontrollblicke, nicht verlorenes Publikum

Genau diese drei Groessen stehen ab jetzt in jedem 23:30-Lauf.

**Auswirkung:** Die Erfolgskontrolle beantwortet kuenftig ohne Handarbeit, ob
ein Rueckgang Verteilung, Suchglueck oder Eigensichtung ist. Die Ausgabe sagt
explizit, ob `YT_BROWSE` vorhanden ist — der Tag, an dem der Feed erstmals
anspringt, ist damit datierbar.

**Robustheit:** Jede der drei Abfragen laeuft einzeln in `try/except RuntimeError`
mit Logzeile und leerer Liste. Grund: der 23:30-Cron liefert vor allem die
Abbruchkurven an `run_report.retention_befund()`; eine gescheiterte
Traffic-Abfrage darf diese Rueckkopplung nicht mitreissen. Heute Nacht ist der
erste produktive Lauf des neuen Codes.

**Vorwaertskompatibilitaet geprueft, nicht angenommen:** `retention_befund()`
greift gezielt auf `kurven` und `erstellt` zu (`run_report.py:2368ff`), neue
Schluessel sind unschaedlich. `tests/test_traffic_quellen.py` sichert das mit
einem Byte-Vergleich des Befunds mit und ohne die neuen Felder ab.

**Fallen als Kommentar hinterlegt:** Nicht jede Dimensionskombination ist
zulaessig, und die API meldet das nur als HTTP 400 "query is not supported".
Empirisch geprueft: `day,insightTrafficSourceType` geht,
`video,insightTrafficSourceType` und `day,country` nicht — Landeszahlen muessen
deshalb ueber `filters=` laufen.

Ebenfalls nachgeprueft und im Modul-Docstring festgehalten: **Impressionen und
Klickrate gibt die Analytics-API nicht her** (`impressions` und
`impressionClickThroughRate` → HTTP 400 "Unknown identifier"; `adImpressions`
ist Werbung und 401). Die bisherige Aussage im Docstring stimmt also, ist jetzt
aber mit dem Gegentest belegt. Damit kann dieses Skript die Frage "zu wenig
angeboten oder zu selten geklickt" prinzipiell nicht beantworten — dafuer
bleibt YouTube Studio, Reiter *Reichweite*, noetig.

**Validierung:** `ruff check` und `mypy` sauber, 238 Tests gruen (6 neu),
echter Lauf gegen die Produktions-API ohne `--speichern` geprueft.

**Offen:** Traffic-Quellen **je Video** (braucht eine Filter-Schleife ueber alle
Videos, `video,insightTrafficSourceType` ist unzulaessig) — bewusst nicht
gebaut, bis ein Bedarf da ist.
