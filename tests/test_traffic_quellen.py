"""Traffic-Aufschluesselung in analytics_bericht: Pivot und Vorwaertskompatibilitaet.

Die drei Abfragen selbst (traffic_quellen, suchbegriffe, landeszahlen) sind
duenne API-Wrapper und werden nicht gemockt - was an ihnen schiefgehen kann,
faengt der weiche Fehlerpfad in main() ab. Getestet wird, was eigene Logik
ist: die Pivotierung fuer die Anzeige und die Zusicherung, dass die
zusaetzlichen Schluessel in der Ablage die Retention-Rueckkopplung nicht
veraendern.
"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import analytics_bericht as ab
import run_report


class Pivot(unittest.TestCase):
    def test_quellen_nach_aufkommen_sortiert(self):
        """Die staerkste Quelle steht links, nicht die alphabetisch erste."""
        zeilen = [
            {"day": "2026-08-18", "insightTrafficSourceType": "YT_SEARCH", "views": 3},
            {"day": "2026-08-18", "insightTrafficSourceType": "RELATED_VIDEO", "views": 11},
            {"day": "2026-08-19", "insightTrafficSourceType": "YT_SEARCH", "views": 2},
        ]
        quellen, je_tag = ab.traffic_pivot(zeilen)
        self.assertEqual(quellen, ["RELATED_VIDEO", "YT_SEARCH"])
        self.assertEqual(je_tag["2026-08-18"]["RELATED_VIDEO"], 11)
        self.assertEqual(je_tag["2026-08-19"], {"YT_SEARCH": 2})

    def test_leere_eingabe(self):
        self.assertEqual(ab.traffic_pivot([]), ([], {}))

    def test_fehlende_felder_kippen_nicht(self):
        """Unvollstaendige Zeilen duerfen die Anzeige nicht sprengen."""
        quellen, je_tag = ab.traffic_pivot([{"views": None}, {}])
        self.assertEqual(quellen, ["?"])
        self.assertEqual(je_tag[""]["?"], 0)

    def test_tag_ohne_quelle_bleibt_luecke(self):
        """Der Nachlauf laesst juengste Tage fehlen - kein Tag wird erfunden."""
        _, je_tag = ab.traffic_pivot(
            [{"day": "2026-08-14", "insightTrafficSourceType": "YT_SEARCH", "views": 2}])
        self.assertEqual(list(je_tag), ["2026-08-14"])


class AblageVorwaertskompatibel(unittest.TestCase):
    """Die neuen Top-Level-Schluessel duerfen retention_befund() nicht stoeren."""

    def _befund(self, extra: dict) -> str:
        kurve = [{"elapsedVideoTimeRatio": i / 100,
                  "audienceWatchRatio": 1.0 - i / 100} for i in range(100)]
        daten = {"erstellt": date.today().isoformat(), "tage": [], "videos": [],
                 "kurve": [], "kurven": [
                     {"video_id": "v", "titel": "T",
                      "veroeffentlicht": date.today().isoformat(),
                      "laufzeit_s": 600, "views": 30, "kurve": kurve}],
                 **extra}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / f"{date.today().isoformat()}.json"
            p.write_text(json.dumps(daten), encoding="utf-8")
            return run_report.retention_befund(Path(d))

    def test_befund_byte_gleich_mit_und_ohne_traffic(self):
        ohne = self._befund({})
        mit = self._befund({
            "traffic": [{"day": "2026-08-18",
                         "insightTrafficSourceType": "YT_SEARCH", "views": 12}],
            "suchbegriffe": [{"insightTrafficSourceDetail": "monero", "views": 11}],
            "land": "CH",
            "land_tage": [{"day": "2026-08-18", "views": 0}]})
        self.assertTrue(ohne, "Vorbedingung: der Befund darf nicht leer sein")
        self.assertEqual(ohne, mit)


class Konstanten(unittest.TestCase):
    def test_suchbegriff_grenze_im_api_maximum(self):
        """25 ist das Maximum dieser Dimension - hoehere Werte quittiert die
        API mit 400, was der weiche Pfad zwar auffinge, aber als stillen
        Datenverlust."""
        self.assertLessEqual(ab.SUCH_BEGRIFFE_MAX, 25)


if __name__ == "__main__":
    unittest.main()
