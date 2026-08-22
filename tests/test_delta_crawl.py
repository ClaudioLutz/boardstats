"""Der Delta-Crawl darf nur Requests sparen, nie Threads verlieren.

Kern der Zusage von crawl_biz.py: die geschriebene Datei ist ein VOLLSTAENDIGER
Snapshot, egal wie viele Threads aus dem Vorgaenger uebernommen wurden -
aggregate_biz.py und bundle_biz.py lesen sie, ohne von Deltas zu wissen.
"""
import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crawl_biz


def schreib_snapshot(pfad: Path, threads: dict[int, int]) -> None:
    """Snapshot mit je einem OP pro Thread; der int-Wert wird Post-Nummer."""
    with gzip.open(pfad, "wt", encoding="utf-8") as fh:
        for tno, letzte in threads.items():
            posts = [{"no": tno, "resto": 0, "time": letzte, "com": f"OP {tno}"}]
            fh.write(json.dumps({"thread": tno, "posts": posts}) + "\n")


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    """crawl_biz auf ein leeres raw/ umbiegen und das Netz stilllegen."""
    raw = tmp_path / "raw"
    raw.mkdir()
    monkeypatch.setattr(crawl_biz, "RAW", raw)
    monkeypatch.setattr(crawl_biz, "STAND", raw / "stand.json")
    monkeypatch.setattr(crawl_biz.time, "sleep", lambda _s: None)
    return raw


def netz(monkeypatch, threads_json, geholt: list[int]):
    """fetch() durch eine Attrappe ersetzen; protokolliert die Thread-Abrufe."""
    def fake(url: str):
        if url.endswith("/threads.json"):
            return threads_json
        tno = int(url.rsplit("/", 1)[1].removesuffix(".json"))
        geholt.append(tno)
        return {"posts": [{"no": tno, "resto": 0, "time": 1, "com": f"neu {tno}"}]}
    monkeypatch.setattr(crawl_biz, "fetch", fake)


def threads_seite(paare: dict[int, int]):
    return [{"threads": [{"no": no, "last_modified": lm} for no, lm in paare.items()]}]


def gelesen(raw: Path) -> dict[int, dict]:
    pfad = sorted(raw.glob("*.jsonl.gz"))[-1]
    with gzip.open(pfad, "rt", encoding="utf-8") as fh:
        return {json.loads(z)["thread"]: json.loads(z) for z in fh if z.strip()}


def test_erstlauf_holt_alles(umgebung, monkeypatch):
    """Ohne Vorgaenger und ohne stand.json gibt es nichts zu uebernehmen."""
    geholt: list[int] = []
    netz(monkeypatch, threads_seite({1: 100, 2: 200}), geholt)
    assert crawl_biz.main() == 0
    assert sorted(geholt) == [1, 2]
    assert set(gelesen(umgebung)) == {1, 2}


def test_unveraenderte_threads_werden_uebernommen(umgebung, monkeypatch):
    """Gleicher last_modified + Zeile im Vorgaenger = kein Request."""
    schreib_snapshot(umgebung / "2026-08-22T1000.jsonl.gz", {1: 111, 2: 222})
    (umgebung / "stand.json").write_text(json.dumps({"1": 100, "2": 200}))
    geholt: list[int] = []
    netz(monkeypatch, threads_seite({1: 100, 2: 999}), geholt)

    assert crawl_biz.main() == 0
    assert geholt == [2], "nur der veraenderte Thread darf geholt werden"

    inhalt = gelesen(umgebung)
    assert set(inhalt) == {1, 2}, "der Snapshot muss trotzdem beide Threads enthalten"
    assert inhalt[1]["posts"][0]["com"] == "OP 1", "Thread 1 kommt unveraendert aus dem Vorgaenger"
    assert inhalt[2]["posts"][0]["com"] == "neu 2"


def test_fehlende_zeile_im_vorgaenger_wird_geholt(umgebung, monkeypatch):
    """Steht ein Thread im Stand, aber nicht im Snapshot, darf er nicht fehlen.

    Das passiert real, wenn sein Abruf im letzten Lauf fehlschlug.
    """
    schreib_snapshot(umgebung / "2026-08-22T1000.jsonl.gz", {1: 111})
    (umgebung / "stand.json").write_text(json.dumps({"1": 100, "2": 200}))
    geholt: list[int] = []
    netz(monkeypatch, threads_seite({1: 100, 2: 200}), geholt)

    assert crawl_biz.main() == 0
    assert geholt == [2]
    assert set(gelesen(umgebung)) == {1, 2}


def test_verschwundener_thread_faellt_aus_dem_stand(umgebung, monkeypatch):
    """Geprunte Threads duerfen den Stand nicht unbegrenzt wachsen lassen."""
    schreib_snapshot(umgebung / "2026-08-22T1000.jsonl.gz", {1: 111, 2: 222})
    (umgebung / "stand.json").write_text(json.dumps({"1": 100, "2": 200}))
    netz(monkeypatch, threads_seite({1: 100}), [])

    assert crawl_biz.main() == 0
    stand = json.loads((umgebung / "stand.json").read_text())
    assert set(stand) == {"1"}
    assert set(gelesen(umgebung)) == {1}, "der geprunte Thread darf nicht mitgeschleppt werden"


def test_fehlgeschlagener_abruf_bleibt_ausserhalb_des_stands(umgebung, monkeypatch):
    """Ein Fehlschlag muss im naechsten Lauf wieder als 'zu holen' gelten."""
    def fake(url: str):
        if url.endswith("/threads.json"):
            return threads_seite({1: 100})
        raise OSError("Netz weg")
    monkeypatch.setattr(crawl_biz, "fetch", fake)

    assert crawl_biz.main() == 1, "ohne einen einzigen Thread ist der Lauf fehlgeschlagen"
    assert json.loads((umgebung / "stand.json").read_text()) == {}
    meta = json.loads(sorted(umgebung.glob("*.meta.json"))[-1].read_text())
    assert meta["failed"] == [1]


def test_retention_verschont_den_stand(umgebung, monkeypatch):
    """stand.json ist Laufzeitzustand und darf der Retention nie zum Opfer fallen."""
    import os
    import time
    alt = umgebung / "2026-07-01T1000.jsonl.gz"
    schreib_snapshot(alt, {9: 999})
    stand = umgebung / "stand.json"
    stand.write_text(json.dumps({"9": 900}))
    vergangen = time.time() - (crawl_biz.RETENTION_DAYS + 5) * 86400
    for f in (alt, stand):
        os.utime(f, (vergangen, vergangen))

    netz(monkeypatch, threads_seite({1: 100}), [])
    assert crawl_biz.main() == 0
    assert stand.exists(), "stand.json wurde von der Retention entfernt"
    assert not alt.exists(), "der alte Snapshot haette entfernt werden muessen"
