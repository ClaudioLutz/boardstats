"""Ein halb geschriebener Crawl-Snapshot darf den Bericht nicht still entwerten.

Am 19.08.2026 20:23 ueberlappte ein Testlauf mit dem 20:20-Crawl und las
raw/2026-08-19T1820.jsonl.gz mitten im Schreiben: gzip.BadGzipFile, abgefangen
von einem try/except weiter oben - kein Absturz, aber kein einziges frisches
Motiv, keine Kulisse, keine Clips fuer den ganzen Tag, ohne eine Zeile im Log.

Zwei Seiten sind hier festgenagelt: dass der Crawl waehrend des Schreibens
unsichtbar bleibt (crawl_biz.py) und dass ein Torso beim Lesen auffaellt
(run_report._snapshot_posts).
"""
import gzip
import json
import logging
import tempfile
import unittest
from pathlib import Path

import crawl_biz
import run_report


def snapshot_schreiben(pfad: Path, threads: dict[int, list[dict]]) -> None:
    with gzip.open(pfad, "wt", encoding="utf-8") as f:
        for no, posts in threads.items():
            f.write(json.dumps({"thread": no, "posts": posts}) + "\n")


class TmpName(unittest.TestCase):
    """Die Endung entscheidet: .jsonl.gz.tmp faellt aus dem glob der Leser
    heraus, ein Praefix-Schema wie .tmp-<stamp>.jsonl.gz waere sichtbar und
    wuerde als 'juengster Snapshot' sogar gewinnen."""

    def test_tmp_ist_fuer_die_leser_unsichtbar(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d)
            (raw / "2026-08-20T0520.jsonl.gz").touch()
            (raw / "2026-08-20T1120.jsonl.gz.tmp").touch()
            gefunden = sorted(p.name for p in raw.glob("*.jsonl.gz"))
            self.assertEqual(gefunden, ["2026-08-20T0520.jsonl.gz"])

    def test_crawl_schreibt_ueberhaupt_in_tmp(self):
        quelle = Path(crawl_biz.__file__).read_text(encoding="utf-8")
        self.assertIn('.jsonl.gz.tmp', quelle)
        self.assertIn('tmp.replace(target)', quelle)
        # Der Rename muss vor die Groessenmessung, sonst stat auf eine Datei,
        # die es nicht mehr gibt.
        self.assertLess(quelle.index("tmp.replace(target)"),
                        quelle.index("target.stat().st_size"))


class SnapshotLesen(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.raw = Path(self._tmpdir.name) / "raw"
        self.raw.mkdir()
        self._alt = run_report.BASE
        run_report.BASE = Path(self._tmpdir.name)
        self.addCleanup(self._aufraeumen)

    def _aufraeumen(self):
        run_report.BASE = self._alt
        self._tmpdir.cleanup()

    def test_ohne_snapshot_leer(self):
        self.assertEqual(run_report._snapshot_posts({"1"}), {})

    def test_heiler_snapshot_wird_gelesen(self):
        snapshot_schreiben(self.raw / "2026-08-20T0520.jsonl.gz",
                           {1: [{"no": 11}], 2: [{"no": 22}]})
        posts = run_report._snapshot_posts({"1"})
        self.assertEqual(posts, {"1": [{"no": 11}]})

    def test_torso_faellt_auf_den_vorherigen_zurueck(self):
        snapshot_schreiben(self.raw / "2026-08-20T0520.jsonl.gz",
                           {1: [{"no": 11}]})
        torso = self.raw / "2026-08-20T1120.jsonl.gz"
        snapshot_schreiben(torso, {1: [{"no": 99}]})
        torso.write_bytes(torso.read_bytes()[:-8])  # mitten im Schreiben

        with self.assertLogs(run_report.log, level=logging.WARNING) as protokoll:
            posts = run_report._snapshot_posts({"1"})
        self.assertEqual(posts, {"1": [{"no": 11}]})
        self.assertIn("unvollstaendig", "\n".join(protokoll.output))
        self.assertIn("2026-08-20T1120", "\n".join(protokoll.output))

    def test_einziger_snapshot_kaputt_bleibt_leer_aber_laut(self):
        torso = self.raw / "2026-08-20T1120.jsonl.gz"
        snapshot_schreiben(torso, {1: [{"no": 99}]})
        torso.write_bytes(torso.read_bytes()[:-8])

        with self.assertLogs(run_report.log, level=logging.WARNING):
            self.assertEqual(run_report._snapshot_posts({"1"}), {})


if __name__ == "__main__":
    unittest.main()
