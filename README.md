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

## Extrakt-Archiv

Die strukturierten Thread-Extrakte aus Stufe 2 werden zusätzlich als Markdown
unter [`extrakte/<datum>/`](extrakte/) abgelegt — je Thread eine Seite (Thema,
Zahlen, Thesen, Quellen, Fachbegriffe, ...) und eine Tages-Übersicht. Das
passiert automatisch bei jedem Lauf (`markdown_tag_schreiben()` in
`run_report.py`, Commit + Push per `git_veroeffentlichen()`; mit
`--kein-github` abschaltbar). Anders als der versandte Bericht bleiben hier
auch das Glossar und die offenen Fragen je Thread erhalten.

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
| `report.sh` / `run.sh` | Cron-Wrapper für Bericht bzw. Crawl |

Laufzeitdaten (`arbeit/`, `berichte/`, `cache/`, `logs/`) sind bewusst
nicht versioniert — sie enthalten Board-Rohinhalte.
