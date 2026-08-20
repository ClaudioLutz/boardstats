---
datum: 2026-08-20
agent: main
typ: infra
commit: <Hash, sobald bekannt>
---

# Bericht und Video auf den Abendrhythmus umgestellt (20:35 / 21:15 CEST)

**Was:** Crontab auf hp-ubuntu umgestellt (liegt nicht im Git, Sicherung unter
`~/crontab.bak-20260820`):

| Job | vorher | nachher |
|---|---|---|
| `run.sh` (Crawl) | 20 7,13,20 | **unverändert** |
| `report.sh` | 35 7 | 35 20 |
| `video.sh` | 10 8 | 15 21 |
| `analytics_bericht.py` | 30 21 | 30 23 |

Im Repo dazu: README.md nennt den neuen Tagesrhythmus im Architektur-Abschnitt
und die korrigierte Analytics-Uhrzeit (23:30).

**Warum:** Messung vom 20.08.2026
(`research/recherche-upload-zeitpunkt-2026-08-20.md`). /biz/ folgt dem
US-Handelstag — 13–21 UTC tragen 52.5 % aller Posts, 06–11 UTC nur 14.1 %. Der
bisherige Redaktionsschluss 05:20 UTC lag im Aktivitätstief, die
Veröffentlichung um 02:30–07:49 ET in der Nacht der Zielgruppe. Der
Abend-Crawl (20:20 CEST) als Schluss hebt die junge Substanz von 38 auf 47 %
und deckt 72 % des laufenden US-Handelstages ab; die Veröffentlichung gegen
21:35 CEST trifft 20:35 London und 15:35 ET.

**Auswirkung:**

- Das Crawl-Raster bleibt unangetastet — der 20:20-Crawl war schon da und hat
  denselben 15-Minuten-Vorlauf zum Bericht wie bisher der Morgen-Crawl.
- Laufzeitbudget aus den Logs: Crawl 4:14 min, Bericht 15–24 min (Ende ~21:00),
  Video 2–20 min. 16 Minuten Puffer zwischen Bericht und Video.
- Datumslogik bleibt korrekt: `run_report.py:2372` und `video_report.py:4329`
  nehmen die Lokalzeit, 20:35/21:15 CEST liegen sicher vor Mitternacht.
- Übergang heute: der Abendlauf am 20.08. aktualisiert `extrakte/2026-08-20/`
  und `berichte/2026-08-20.txt` (Backup automatisch), lädt aber **kein**
  zweites Video hoch — `markdown_tag_schreiben()` (`run_report.py:628`) löscht
  nichts, der Marker `extrakte/2026-08-20/video_en.json` bleibt stehen und
  `video_report.py:4337` bricht ab. Das erste Abend-Delta ist einmalig nur
  ~13 h statt 24 h.
- Bewusst **nicht** geändert: die Crawl-Häufigkeit (Messung Punkt 8 des
  Befunds — zusätzliche Crawls bringen nur die ~4 % Threads, die zwischen zwei
  Läufen entstehen und vergehen) und der Mittags-Crawl 13:20 CEST, der im
  Tagestief liegt.

**Offen:** Kontrolle am 21.08. abends (Logs auf die neuen Zeiten,
`publishedAt` gegen 21:35 CEST). Optional später: Mittags-Crawl auf 15:20 CEST
und `If-Modified-Since` in `crawl_biz.py`, das häufigeres Crawlen erst
vertretbar macht.
