"""Ein Testlauf darf den produktiven Zustand nicht anfassen.

Am 19.08.2026 haben drei Testlaeufe den Delta-Stand von 07:19 auf 20:27
vorgeschoben; zwoelf Stunden Board-Aktivitaet mussten von Hand
zurueckgerollt werden. Die Guards dagegen sind ueber run_report.py verstreut,
darum hier die Stellen, die sich still wieder loesen koennten.
"""
import re
import unittest

import run_report


class AusgabeTag(unittest.TestCase):
    """Bilder des produktiven Laufs muessen den Testlauf ueberleben:
    video_report.py liest arbeit/thumbs/<datum>.* und arbeit/motive/<datum>/
    erst um 08:10, der Bericht ist um 07:50 fertig."""

    def test_produktiv_bleibt_das_nackte_datum(self):
        self.assertEqual(run_report.ausgabe_tag("2026-08-20", False),
                         "2026-08-20")

    def test_trockenlauf_weicht_aus(self):
        self.assertEqual(run_report.ausgabe_tag("2026-08-20", True),
                         "2026-08-20-test")

    def test_die_beiden_kollidieren_nie(self):
        self.assertNotEqual(run_report.ausgabe_tag("2026-08-20", False),
                            run_report.ausgabe_tag("2026-08-20", True))


class LaufMuster(unittest.TestCase):
    """Das Aufraeumen am Ende von main() zaehlt Laufverzeichnisse. Vor dem
    20.08.2026 suchte es nach '2026-08-20', die Ordner heissen aber
    '20260820-073501' - es raeumte gar nichts, und die Verzeichnisse wuchsen
    unbegrenzt. Umgekehrt darf es die dauerhaften Ordner unter arbeit/ nie
    erwischen (clips/ traegt den kumulativen Katalog)."""

    MUSTER = re.compile(
        r"^\d{8}-\d{6}(" + re.escape(run_report.TEST_SUFFIX) + r")?$")

    def test_trifft_produktives_laufverzeichnis(self):
        self.assertTrue(self.MUSTER.match("20260820-073501"))

    def test_trifft_testlaufverzeichnis(self):
        self.assertTrue(self.MUSTER.match("20260820-141500-test"))

    def test_verschont_dauerhafte_ordner(self):
        for name in ("clips", "motive", "thumbs", "srt_nachzug", "analytics"):
            with self.subTest(name=name):
                self.assertIsNone(self.MUSTER.match(name))

    def test_verschont_datumsordner(self):
        # arbeit/motive/<datum>/ liegt eine Ebene tiefer, aber das alte
        # Muster kam von hier - es soll nicht versehentlich zurueckkehren.
        self.assertIsNone(self.MUSTER.match("2026-08-20"))

    def test_test_und_produktiv_sind_trennbar(self):
        namen = ["20260820-073501", "20260820-141500-test"]
        test = [n for n in namen if n.endswith(run_report.TEST_SUFFIX)]
        produktiv = [n for n in namen
                     if not n.endswith(run_report.TEST_SUFFIX)]
        self.assertEqual(test, ["20260820-141500-test"])
        self.assertEqual(produktiv, ["20260820-073501"])


class MarkdownZiel(unittest.TestCase):
    """extrakte/<datum>/ ist die oeffentliche Fassung zum hochgeladenen Video
    und der einzige getrackte Pfad, den ein Testlauf sonst anfasst."""

    def test_ziel_ist_ueberschreibbar(self):
        # Signatur-Vertrag: ohne ziel bleibt es beim Repo-Pfad, mit ziel
        # schreibt der Trockenlauf in sein Laufverzeichnis.
        import inspect
        sig = inspect.signature(run_report.markdown_tag_schreiben)
        self.assertIn("ziel", sig.parameters)
        self.assertIsNone(sig.parameters["ziel"].default)


if __name__ == "__main__":
    unittest.main()
