---
datum: 2026-08-22
agent: claude/delta-crawl-stuendlich (Worktree)
typ: infra
commit: <Hash, sobald bekannt>
---

# Delta-Crawl: stuendliche Snapshots zum Preis eines Viertel-Vollcrawls

**Was:** `crawl_biz.py` holt nicht mehr blind alle Threads des Katalogs.
Statt `catalog.json` fragt es `threads.json` (ein Request, liefert `no`,
`replies`, `last_modified` pro Thread) und holt einzeln nur die Threads, deren
`last_modified` gegenueber dem letzten Lauf gestiegen ist oder die neu sind.
Alle uebrigen werden als Rohzeile aus dem Vorgaenger-Snapshot uebernommen. Der
letzte bekannte Stand liegt in `raw/stand.json` (von der Retention ausgenommen).
`run.sh` bekommt den Modus `crawl-only` (nur Crawl, eigenes Log `logs/crawl.log`);
ohne Argument laeuft es unveraendert als Crawl + Verdichtung.
Neu: `tests/test_delta_crawl.py` (6 Tests).

**Warum:** Vorarbeit fuer einen Trigger auf schnell wachsende Threads. Die
Messung in `research/messung-wachstums-trigger-2026-08-22.md` zeigte als
groesste Schwaeche die Abtastrate: bei 3 Crawls pro Tag und 1-h-Fenster ist ein
Thread, der um 15:00 explodiert, um 20:20 schon wieder kalt und faellt durch.
Gemessen: 201 Katalog-Threads, Vollcrawl 4:10 min, 0.6 MB pro Snapshot — aber
pro Stunde sind nur 23–52 Threads aktiv, also rund ein Viertel. Ein stuendlicher
Delta-Lauf kostet damit weniger Requests als der bisherige 3x-taegliche
Vollcrawl und bleibt weit unter dem API-Limit von 1 Request/Sekunde.

**Auswirkung:** Die geschriebene Datei bleibt ein **vollstaendiger** Snapshot —
`aggregate_biz.py` und `bundle_biz.py` lesen sie unveraendert weiter und wissen
nichts von Deltas. Genau das sichern die neuen Tests ab, inklusive der Faelle
"Thread stand im Stand, fehlt aber im Vorgaenger" (Fetch war fehlgeschlagen) und
"Thread geprunt" (faellt aus dem Stand, wird nicht mitgeschleppt).
`raw/` waechst bei stuendlichem Takt auf rund 430 MB bei 30 Tagen Retention
(heute 46 MB); auf hp-ubuntu sind 60 GB frei.
Bewusst **nicht** geaendert: `aggregate_biz.py` laeuft weiter nur 3x taeglich.
Es fuehrt mit `seen.json` einen Novelty-Zustand ueber die Laeufe und speist
`reports/latest.json`, das in den Tagesbericht eingeht — stuendlich verdichten
wuerde diesen Zustand 8x schneller fortschreiben und den Berichtspfad
veraendern. Der Crawl selbst ist zustandslos und darf beliebig oft laufen.

**Offen:** Der eigentliche Wachstums-Trigger. Die Schwelle ist gemessen
(Beschleunigung x3 gegen den eigenen Schnitt, mindestens 8 verschiedene Poster
im Fenster, Anteil des haeufigsten Posters unter 40 %, kein General-Format
≈ ein Treffer alle 5 Tage), das Ausgabeformat (eigenes Sondervideo / Short /
Pflichtkapitel im Tagesvideo) ist noch offen. Ein Themenfilter ist Pflicht: ein
Treffer der Messreihe war ein reiner Beleidigungs-Thread.
