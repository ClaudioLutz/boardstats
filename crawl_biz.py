#!/usr/bin/env python3
"""Crawlt /biz/ ueber die 4chan-JSON-API und legt einen Snapshot pro Lauf ab.

Ein Lauf = eine gzip-komprimierte JSON-Lines-Datei, eine Zeile pro Thread.
Rate-Limit laut 4chan-API-Regeln: max. 1 Request/Sekunde.
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
RETENTION_DAYS = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; boardstats/1.0)"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S")


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
    target = RAW / f"{stamp}.jsonl.gz"

    catalog = fetch(f"{BASE}/catalog.json")
    thread_nos = [t["no"] for page in catalog for t in page["threads"]]
    logging.info("Katalog: %d Threads", len(thread_nos))

    ok, failed = 0, []
    with gzip.open(target, "wt", encoding="utf-8") as out:
        for i, no in enumerate(thread_nos, 1):
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
            ok += 1
            if i % 50 == 0:
                logging.info("%d/%d", i, len(thread_nos))

    meta = {
        "stamp": stamp,
        "board": BOARD,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_threads": len(thread_nos),
        "fetched": ok,
        "failed": failed,
        "bytes": target.stat().st_size,
    }
    (RAW / f"{stamp}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logging.info("Snapshot %s: %d/%d Threads, %.1f MB", stamp, ok, len(thread_nos),
                 target.stat().st_size / 1e6)

    # Retention: alte Snapshots entfernen
    cutoff = time.time() - RETENTION_DAYS * 86400
    entfernt = 0
    for f in RAW.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            entfernt += 1
    if entfernt:
        logging.info("Retention: %d alte Dateien entfernt", entfernt)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
