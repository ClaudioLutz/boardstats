#!/usr/bin/env python3
"""Crawlt /biz/ ueber die 4chan-JSON-API und legt einen Snapshot pro Lauf ab.

Ein Lauf = eine gzip-komprimierte JSON-Lines-Datei, eine Zeile pro Thread.
Rate-Limit laut 4chan-API-Regeln: max. 1 Request/Sekunde.

Delta-Abruf (seit 22.08.2026): threads.json liefert in EINEM Request
`last_modified` pro Thread. Nur Threads, deren Wert gegenueber dem letzten Lauf
gestiegen ist (oder die neu sind), werden einzeln geholt; die uebrigen werden
Zeile fuer Zeile aus dem Vorgaenger-Snapshot uebernommen. Die geschriebene Datei
bleibt damit ein VOLLSTAENDIGER Snapshot - aggregate_biz.py und bundle_biz.py
lesen sie unveraendert weiter, ohne von Deltas zu wissen.

Gemessen am 22.08.2026: von 201 Katalog-Threads sind pro Stunde nur 23-52 aktiv,
also rund ein Viertel. Ein stuendlicher Delta-Lauf kostet damit weniger
Requests als der frueheren 3x-taegliche Vollcrawl (201 Requests, 4:10 min).
"""
import gzip
import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BOARD = "biz"
BASE = f"https://a.4cdn.org/{BOARD}"
ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
STAND = RAW / "stand.json"   # Thread -> last_modified des letzten Abrufs
RETENTION_DAYS = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; boardstats/1.0)"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def vorgaenger() -> Path | None:
    """Neuester fertiger Snapshot, aus dem unveraenderte Threads kommen koennen."""
    kandidaten = sorted(RAW.glob("*.jsonl.gz"))
    return kandidaten[-1] if kandidaten else None


def alte_zeilen(snapshot: Path) -> dict[int, str]:
    """Rohzeilen des Vorgaenger-Snapshots je Thread - unveraendert wiederverwendbar.

    Bewusst als Rohtext (nicht geparst): die Zeile wandert unveraendert in den
    neuen Snapshot, ein Round-Trip durch json.loads/dumps waere nur Rechenzeit.
    """
    zeilen: dict[int, str] = {}
    with gzip.open(snapshot, "rt", encoding="utf-8") as fh:
        for zeile in fh:
            zeile = zeile.rstrip("\n")
            if not zeile:
                continue
            try:
                tno = json.loads(zeile)["thread"]
            except (ValueError, KeyError):
                continue
            zeilen[tno] = zeile
    return zeilen


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    target = RAW / f"{stamp}.jsonl.gz"
    # Waehrend des Crawls traegt die Datei die Endung .tmp und faellt damit aus
    # dem glob("*.jsonl.gz") der Leser heraus. Erst der Rename am Schluss macht
    # sie sichtbar - wer parallel liest (run_report.py, bundle_biz.py), sieht
    # entweder den fertigen Snapshot oder den vorherigen, nie einen Torso.
    # Bricht der Crawl ab, bleibt gar kein Snapshot zurueck.
    tmp = RAW / f"{stamp}.jsonl.gz.tmp"
    for rest in RAW.glob("*.jsonl.gz.tmp"):  # Reste abgebrochener Laeufe
        rest.unlink()

    # threads.json statt catalog.json: gleiche Threadliste, dazu last_modified,
    # und ein Bruchteil der Uebertragung (kein OP-Text, keine Bildmetadaten).
    seiten = fetch(f"{BASE}/threads.json")
    aktuell = {t["no"]: t.get("last_modified", 0) for page in seiten for t in page["threads"]}
    logging.info("Katalog: %d Threads", len(aktuell))

    stand: dict[str, int] = {}
    if STAND.exists():
        try:
            stand = json.loads(STAND.read_text(encoding="utf-8"))
        except ValueError:
            logging.warning("stand.json unlesbar - Vollcrawl")

    vor = vorgaenger()
    uebernehmbar = alte_zeilen(vor) if vor else {}
    if vor:
        logging.info("Vorgaenger %s mit %d Threads", vor.name, len(uebernehmbar))

    # Ein Thread darf nur uebernommen werden, wenn sein last_modified unveraendert
    # ist UND seine Zeile im Vorgaenger wirklich vorliegt (dort kann ein Fetch
    # fehlgeschlagen sein). Sonst wird er neu geholt.
    zu_holen, zu_uebernehmen = [], []
    for no, lm in aktuell.items():
        if stand.get(str(no)) == lm and no in uebernehmbar:
            zu_uebernehmen.append(no)
        else:
            zu_holen.append(no)
    logging.info("Delta: %d holen, %d uebernehmen", len(zu_holen), len(zu_uebernehmen))

    ok, failed = 0, []
    neuer_stand: dict[str, int] = {}
    with gzip.open(tmp, "wt", encoding="utf-8") as out:
        for no in zu_uebernehmen:
            out.write(uebernehmbar[no] + "\n")
            neuer_stand[str(no)] = aktuell[no]
            ok += 1
        for i, no in enumerate(zu_holen, 1):
            time.sleep(1.0)
            data = None
            for versuch in (1, 2):
                try:
                    data = fetch(f"{BASE}/thread/{no}.json")
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code == 404:  # Thread zwischenzeitlich geprunt
                        break
                    logging.warning("Thread %d HTTP %s (Versuch %d)", no, exc.code, versuch)
                    time.sleep(3)
                except Exception as exc:
                    logging.warning("Thread %d Fehler: %s (Versuch %d)", no, exc, versuch)
                    time.sleep(3)
            if data is None:
                failed.append(no)
                continue
            out.write(json.dumps({"thread": no, "posts": data["posts"]}, ensure_ascii=False) + "\n")
            # Erst nach erfolgreichem Abruf in den Stand - ein fehlgeschlagener
            # Thread muss beim naechsten Lauf wieder als "zu holen" gelten.
            neuer_stand[str(no)] = aktuell[no]
            ok += 1
            if i % 50 == 0:
                logging.info("%d/%d geholt", i, len(zu_holen))

    tmp.replace(target)
    STAND.write_text(json.dumps(neuer_stand, indent=0), encoding="utf-8")

    meta = {
        "stamp": stamp,
        "board": BOARD,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_threads": len(aktuell),
        "fetched": ok,
        "delta_geholt": len(zu_holen) - len(failed),
        "delta_uebernommen": len(zu_uebernehmen),
        "failed": failed,
        "bytes": target.stat().st_size,
    }
    (RAW / f"{stamp}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logging.info("Snapshot %s: %d/%d Threads (%d geholt, %d uebernommen), %.1f MB",
                 stamp, ok, len(aktuell), len(zu_holen) - len(failed), len(zu_uebernehmen),
                 target.stat().st_size / 1e6)

    # Retention: alte Snapshots entfernen. stand.json ist Laufzeitzustand und
    # darf nie wegfallen, auch wenn sie zwischen zwei Laeufen alt aussieht.
    cutoff = time.time() - RETENTION_DAYS * 86400
    entfernt = 0
    for f in RAW.iterdir():
        if f.is_file() and f != STAND and f.stat().st_mtime < cutoff:
            f.unlink()
            entfernt += 1
    if entfernt:
        logging.info("Retention: %d alte Dateien entfernt", entfernt)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
