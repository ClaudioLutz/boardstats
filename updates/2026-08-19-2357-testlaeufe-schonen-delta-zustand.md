---
datum: 2026-08-19
agent: worktree-agent-a54b71351aef8bdf5
typ: bugfix
commit: <Hash, sobald bekannt>
---

# Testlaeufe schreiben den Delta-Zustand nicht mehr fort

**Was:** Guards fuer die drei Zustands-Schreiber, die bisher auch unter den
Test-Flags liefen:

- `run_report.py`: `cache_pflegen()` (schreibt `cache/status.json` und kopiert
  Extrakte nach `cache/<thread>.txt`) laeuft mit `--trockenlauf` nicht mehr —
  Guard direkt am Aufruf in `main()`.
- `run_report.py`: `motiv_waehlen()` und `hintergruende_waehlen()` bekommen
  einen `trockenlauf`-Parameter (durchgereicht aus
  `bericht_veroeffentlichen()`, das ihn schon hatte) und lassen damit die
  Aufrufe von `verwendete_merken()` aus — `arbeit/motive/verwendet.json`
  bekommt im Testlauf keine neuen Bildsperren.
- `video_report.py`: `_klip_zuordnung()` bekommt einen `nur_video`-Parameter
  (durchgereicht ueber `szenen_bauen()` aus `main()`) und ruft damit
  `klip_katalog.katalog_speichern()` nicht mehr auf — die
  `zuletzt_verwendet`-Stempel bleiben im Speicher und
  `arbeit/clips/katalog.json` auf der Platte unberuehrt.
- Beim Sweep zusaetzlich gefunden: `--kein-cache` loeschte `cache/status.json`
  auch im Trockenlauf. Die Kombination `--kein-cache --trockenlauf` ignoriert
  das Loeschen jetzt (mit Logzeile) — ein Testlauf darf den Delta-Zustand
  auch nicht per Loeschung anfassen.

Jeder uebersprungene Schreiber loggt eine Zeile ("Trockenlauf - ... bleibt
unberuehrt"), damit spaeter niemand raetselt, warum der Cache nicht waechst.
Die `--help`-Texte von `--trockenlauf` (run_report) und
`--nur-video`/`--trockenlauf` (video_report) benennen das neue Verhalten.

**Warum:** Die Testlaeufe vom 19.08.2026 (14:49, 20:12, 20:25) haben den
Delta-Stand der Pipeline um rund zwoelf Stunden nach vorne geschoben; der
Cron-Lauf am Folgetag haette nur noch das Delta seit 20:27 statt seit dem
letzten Upload gesehen. Musste von Hand zurueckgerollt werden — siehe
[2026-08-19-2340-delta-nach-testlaeufen-zurueckgerollt.md](2026-08-19-2340-delta-nach-testlaeufen-zurueckgerollt.md),
dort als "Offen: Wurzelursache" angekuendigt.

**Auswirkung:** `run_report.py --trockenlauf` und
`video_report.py --nur-video`/`--trockenlauf`/`--vorschau` lassen
`cache/status.json`, `cache/<thread>.txt`, `arbeit/motive/verwendet.json` und
die `zuletzt_verwendet`-Stempel in `arbeit/clips/katalog.json` unberuehrt.
Bewusst *nicht* geaendert:

- Der produktive Pfad ohne Test-Flags verhaelt sich exakt wie bisher (alle
  neuen Parameter haben `False` als Default, die Guards greifen nur unter den
  Flags).
- Die Freigabe-Ergebnisse laufen auch im Testlauf weiter: `motive.json` und
  die kumulativen Katalog-Eintraege aus `klip_katalog.klips_ernten()`
  (`status`/`beschreibung`) werden weiterhin geschrieben — die Sichtpruefung
  soll nicht taeglich neu bezahlt werden.
- `seen.json` (`aggregate_biz.py`/`crawl_biz.py`, Cron-Crawl) ist nicht
  betroffen und unangetastet.
- Akzeptierte Divergenz: ohne `verwendete_merken()` sieht
  `hintergruende_waehlen()` im selben Testlauf die frische Thumbnail-Sperre
  von `motiv_waehlen()` nicht — harmlos, betrifft nur Testlaeufe.

**Offen:** Ein Trockenlauf schreibt weiterhin Testlauf-Extrakte nach
`extrakte/<datum>/` (ohne Commit, Working Tree wird dirty) — ausserhalb des
Auftrags, `--kein-github` deckt es ab; bei Bedarf separat angehen.
