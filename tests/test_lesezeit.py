"""Lesezeit-Verifikation im Lauf (Leitplanke 3, 22.08.2026).

Die effektive Lesezeit eines Textelements ist seine Standzeit minus
Einblendphase (Einflug/Aufblende), minus Ausblende, minus Zeit ab
Flugbeginn. Die Verifikation laeuft am fertigen Szenenplan und warnt bei
jedem Element unter seinem Boden - sie ist das Sicherheitsnetz, das
anschlagen muss, wenn ein kuenftiger Animations-Beat die Planungs-Boeden
umgeht.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report as vr


def szene(*overlays: vr.Overlay, start: float = 0.0) -> vr.Szene:
    return vr.Szene(None, start, overlays=list(overlays))


class TestLesezeitVerifizieren(unittest.TestCase):
    def test_element_mit_genug_zeit_besteht(self) -> None:
        o = vr.Overlay(Path("a.png"), 1.0, 8.0, 0.35, einflug="unten",
                       lese_text="BTC BREAKS $120K", lese_boden=2.0)
        self.assertEqual(vr.lesezeit_verifizieren([szene(o)], 60.0), [])

    def test_zu_kurzes_element_wird_gemeldet(self) -> None:
        # 1.5s Standzeit minus 0.4 Einflug minus 0.35 Ausblende = 0.75s
        o = vr.Overlay(Path("a.png"), 1.0, 2.5, 0.35, einflug="unten",
                       lese_text="ZU KURZ", lese_boden=2.0)
        v = vr.lesezeit_verifizieren([szene(o)], 60.0)
        self.assertEqual(len(v), 1)
        self.assertAlmostEqual(v[0].effektiv, 0.75)
        self.assertEqual(v[0].text, "ZU KURZ")

    def test_flug_beendet_die_lesezeit(self) -> None:
        # Steht 1.0-9.0, fliegt aber ab 3.0: effektiv 3.0-1.0-0.4 = 1.6s.
        o = vr.Overlay(Path("a.png"), 1.0, 9.0, 0.35, einflug="unten",
                       flug_ab=3.0, flug_x=10, flug_y=10,
                       lese_text="FLIEGT FRUEH", lese_boden=2.0)
        v = vr.lesezeit_verifizieren([szene(o)], 60.0)
        self.assertEqual(len(v), 1)
        self.assertAlmostEqual(v[0].effektiv, 1.6)

    def test_stuecke_ueber_szenengrenzen_zaehlen_zusammen(self) -> None:
        # Dasselbe PNG in zwei Szenen: 1.0-5.0 und 5.0-9.0 = ein Fenster.
        a = vr.Overlay(Path("a.png"), 1.0, 5.0, 0.35, einflug="unten",
                       weiter=True, lese_text="LAEUFT WEITER",
                       lese_boden=3.0)
        b = vr.Overlay(Path("a.png"), 5.0, 9.0, 0.35,
                       lese_text="LAEUFT WEITER", lese_boden=3.0)
        self.assertEqual(
            vr.lesezeit_verifizieren([szene(a), szene(b, start=5.0)], 60.0),
            [])

    def test_elemente_ohne_boden_bleiben_aussen_vor(self) -> None:
        o = vr.Overlay(Path("stufe.png"), 1.0, 1.2, 0.0)  # Count-up-Stufe
        self.assertEqual(vr.lesezeit_verifizieren([szene(o)], 60.0), [])

    def test_boeden_gelten_gegen_effektive_zeit_in_der_planung(self) -> None:
        # Die Planung rechnet den Einblendverlust auf ihre Boeden drauf.
        self.assertGreater(vr.EINBLEND_VERLUST, 0.0)
        self.assertGreaterEqual(vr.EINBLEND_VERLUST, vr.EINFLUG_DAUER)


if __name__ == "__main__":
    unittest.main()
