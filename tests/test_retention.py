"""Retention-Rueckkopplung: Kennwerte aus Abbruchkurven und der No-Op-Pfad.

Der Befund aus arbeit/analytics/<datum>.json wird an Synthese- und
Drehbuch-Prompt angehaengt. Zwei Eigenschaften sind hier abgesichert:
die Kennwert-Ableitung ist deterministisch nachrechenbar (synthetische
Kurven), und jeder Stoerfall (Datei fehlt, Messung zu alt, keine Kurven,
Video ohne Laufzeit) liefert exakt "" - dann bleibt der Prompt per
Konstruktion (prompt += "") byte-gleich zum bisherigen Stand."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import run_report


def kurve(f, punkte: int = 100) -> list[dict]:
    """Synthetische Kurve: f(x) liefert die Bindung am Laufzeitanteil x."""
    return [{"elapsedVideoTimeRatio": i / punkte,
             "audienceWatchRatio": f(i / punkte)} for i in range(punkte)]


def video(f, laufzeit_s: int = 600, **extra) -> dict:
    return {"video_id": "v", "titel": "T", "veroeffentlicht": "2026-08-18",
            "laufzeit_s": laufzeit_s, "kurve": kurve(f), **extra}


class Kennwerte(unittest.TestCase):
    def test_linearer_abfall(self):
        """Bindung 1-x: unter 50 % ab x=0.51, unter 30 % ab x=0.71."""
        k = run_report._retention_kennwerte(video(lambda x: 1 - x))
        assert k is not None
        self.assertEqual(k["laufzeit_s"], 600)
        self.assertAlmostEqual(k["unter_05"], 0.51)
        self.assertAlmostEqual(k["unter_03"], 0.71)
        self.assertAlmostEqual(k["mittel"], 0.505, places=3)

    def test_nie_unter_der_schwelle(self):
        """Haelt die Kurve ueber 50 %, gibt es keinen Schwellen-Zeitpunkt."""
        k = run_report._retention_kennwerte(video(lambda x: 0.8))
        assert k is not None
        self.assertIsNone(k["unter_05"])
        self.assertIsNone(k["unter_03"])

    def test_steilste_zone(self):
        """Sturz von 1.0 auf 0.2 zwischen x=0.4 und x=0.5 wird geortet."""
        def f(x):
            if x < 0.4:
                return 1.0
            if x < 0.5:
                return 1.0 - 8 * (x - 0.4)
            return 0.2
        k = run_report._retention_kennwerte(video(f))
        assert k is not None
        self.assertAlmostEqual(k["steil_von"], 0.4, delta=0.02)
        self.assertAlmostEqual(k["steil_bis"], 0.5, delta=0.02)
        self.assertAlmostEqual(k["steil_verlust"], 0.8, delta=0.1)

    def test_unauswertbar(self):
        """Ohne Laufzeit, ohne Kurve oder mit zu wenigen Stuetzpunkten: None."""
        self.assertIsNone(run_report._retention_kennwerte(
            video(lambda x: 1 - x, laufzeit_s=0)))
        self.assertIsNone(run_report._retention_kennwerte(
            {"laufzeit_s": 600, "kurve": []}))
        self.assertIsNone(run_report._retention_kennwerte(
            {"laufzeit_s": 600, "kurve": kurve(lambda x: 1 - x, punkte=5)}))


class Block(unittest.TestCase):
    def test_zieldauer_und_wortbudget(self):
        """Median-Abbruch unter 30 % bei x=0.71 von 600 s -> Ziel ~7.1 min,
        Wortziel = 700..1000 skaliert mit 0.71 (auf Zehner gerundet)."""
        k = run_report._retention_kennwerte(video(lambda x: 1 - x))
        block = run_report._retention_block([k])
        self.assertTrue(block.startswith("\n"))
        self.assertIn("target a total runtime of about 7.1 minutes", block)
        self.assertIn("500 to 710 words", block)     # 700*0.71=497, 1000*0.71=710
        self.assertIn("half the audience is gone by 5:06", block)  # 0.51*600
        self.assertIn("front-load", block)

    def test_intro_kollaps_wird_gedaempft(self):
        """Bricht die Bindung schon im Intro ein (wie am 20.08.2026 gemessen:
        unter 30 % nach 0:45 von 10:54), misst t30 das Opening-Problem, nicht
        die richtige Laenge. Das Ziel faellt deshalb nie unter die halbe
        Median-Laufzeit - sonst draengt der Loop den Bericht gegen null."""
        def kollaps(x):
            return max(0.2, 1.0 - 20 * x)
        k = run_report._retention_kennwerte(video(kollaps))
        assert k is not None
        self.assertAlmostEqual(k["unter_03"], 0.04)   # t30 bei 24 s
        block = run_report._retention_block([k])
        # Ziel = max(24 s, 600/2 s) = 300 s = 5.0 min, nie 0.4 min
        self.assertIn("fewer than 30% of viewers are left after 0:24", block)
        self.assertIn("target a total runtime of about 5.0 minutes", block)
        self.assertIn("350 to 500 words", block)      # 700*0.5, 1000*0.5

    def test_stichprobengroesse_in_der_kopfzeile(self):
        """Bei einer Handvoll Views ist die Kurve Richtungssignal - das
        sagt der Block dazu, samt Spannweite der Stichprobe."""
        k1 = run_report._retention_kennwerte(video(lambda x: 1 - x, views=12))
        k2 = run_report._retention_kennwerte(video(lambda x: 1 - x, views=25))
        block = run_report._retention_block([k1, k2])
        self.assertIn("only 12-25 views each, treat as directional", block)


class Befund(unittest.TestCase):
    """retention_befund() gegen eine Ablage auf Platte: die vier
    No-Op-Faelle liefern "", der Gutfall den Block."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ablage = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def schreiben(self, erstellt: str, kurven: list) -> None:
        (self.ablage / f"{erstellt}.json").write_text(json.dumps(
            {"erstellt": erstellt, "tage": [], "videos": [], "kurve": [],
             "kurven": kurven}), encoding="utf-8")

    def test_ablage_fehlt_oder_leer(self):
        self.assertEqual(run_report.retention_befund(self.ablage / "nix"), "")
        self.assertEqual(run_report.retention_befund(self.ablage), "")

    def test_messung_zu_alt(self):
        alt = (date.today() - timedelta(days=4)).isoformat()
        self.schreiben(alt, [video(lambda x: 1 - x)])
        self.assertEqual(run_report.retention_befund(self.ablage), "")

    def test_ohne_kurven_feld(self):
        """Der reale Ist-Zustand: 2026-08-19.json traegt noch kein kurven."""
        (self.ablage / "heute.json").write_text(json.dumps(
            {"erstellt": date.today().isoformat(), "tage": [],
             "videos": [], "kurve": []}), encoding="utf-8")
        self.assertEqual(run_report.retention_befund(self.ablage), "")

    def test_video_ohne_laufzeit(self):
        self.schreiben(date.today().isoformat(),
                       [video(lambda x: 1 - x, laufzeit_s=0)])
        self.assertEqual(run_report.retention_befund(self.ablage), "")

    def test_kaputtes_json_ist_stiller_noop(self):
        (self.ablage / "kaputt.json").write_text("{", encoding="utf-8")
        self.assertEqual(run_report.retention_befund(self.ablage), "")

    def test_kurvenloser_messtag_faellt_auf_aeltere_messung_zurueck(self):
        """Ein transienter API-Fehler kann die juengste Datei ohne Kurven
        hinterlassen (beobachtet 20.08.2026) - dann traegt die naechstaeltere
        brauchbare Messung im Frischefenster."""
        gestern = (date.today() - timedelta(days=1)).isoformat()
        self.schreiben(gestern, [video(lambda x: 1 - x)])
        self.schreiben(date.today().isoformat(), [])
        self.assertIn("RETENTION FEEDBACK",
                      run_report.retention_befund(self.ablage))

    def test_gutfall(self):
        self.schreiben(date.today().isoformat(), [video(lambda x: 1 - x)])
        block = run_report.retention_befund(self.ablage)
        self.assertIn("RETENTION FEEDBACK", block)
        # Der Block beginnt mit einem Umbruch, damit er beim Anhaengen an
        # einen Prompt (der auf einer eigenen Zeile endet) sauber ansetzt.
        self.assertTrue(block.startswith("\n"))
        self.assertFalse(block.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
