"""Zitat-Standzeit und Schluss-Ausklang.

Beide Fehler stammen aus dem Video vom 19.08.2026: die Zitatkarte stand
starre 12 Sekunden und ragte in das naechste Thema hinein, und das
Schlussbild verschwand am letzten gesprochenen Wort, weil die Tonspur dort
endete und -shortest das Video mitkappte.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report as vr  # noqa: E402


def worte(paare: list[tuple[str, float, float]]) -> list[vr.Wort]:
    return [vr.Wort(t, a, b) for t, a, b in paare]


class TestSatzEnde(unittest.TestCase):
    def setUp(self) -> None:
        self.w = worte([
            ("Idiots", 0.0, 0.4), ("want", 0.4, 0.7), ("the", 0.7, 0.9),
            ("security", 0.9, 1.4), ("blanket", 1.4, 1.9), ("of", 1.9, 2.0),
            ("an", 2.0, 2.1), ("American", 2.1, 2.7),
            ("company", 2.7, 3.2), ("like", 3.2, 3.5), ("XOM.", 3.5, 4.0),
            ("The", 4.3, 4.5), ("thread", 4.5, 5.0), ("moves", 5.0, 5.4),
            ("on.", 5.4, 5.8),
        ])

    def test_findet_das_satzende(self) -> None:
        self.assertAlmostEqual(vr._satz_ende(self.w, 1.0), 4.0)

    def test_ab_zeit_hinter_dem_ersten_satz(self) -> None:
        self.assertAlmostEqual(vr._satz_ende(self.w, 4.4), 5.8)

    def test_ohne_satzzeichen_none(self) -> None:
        self.assertIsNone(vr._satz_ende(worte([("hello", 0.0, 0.5)]), 0.0))

    def test_abkuerzung_beendet_den_satz_nicht(self) -> None:
        w = worte([("The", 0.0, 0.2), ("U.S.", 0.2, 0.8),
                   ("market", 0.8, 1.3), ("crashed.", 1.3, 1.9)])
        self.assertAlmostEqual(vr._satz_ende(w, 0.0), 1.9)

    def test_initiale_beendet_den_satz_nicht(self) -> None:
        w = worte([("Warren", 0.0, 0.4), ("E.", 0.4, 0.6),
                   ("Buffett", 0.6, 1.1), ("bought.", 1.1, 1.6)])
        self.assertAlmostEqual(vr._satz_ende(w, 0.0), 1.6)


class TestAnkerSpanne(unittest.TestCase):
    def setUp(self) -> None:
        self.w = worte([("one", 0.0, 0.3), ("two", 0.3, 0.6),
                        ("three", 0.6, 1.1), ("four", 1.1, 1.5)])

    def test_start_und_ende(self) -> None:
        self.assertEqual(vr._anker_spanne("two three", self.w), (0.3, 1.1))

    def test_einzelwort(self) -> None:
        self.assertEqual(vr._anker_spanne("four", self.w), (1.1, 1.5))

    def test_nicht_gefunden(self) -> None:
        self.assertIsNone(vr._anker_spanne("five", self.w))

    def test_leerer_anker(self) -> None:
        self.assertIsNone(vr._anker_spanne("   ", self.w))

    def test_anker_zeit_bleibt_der_start(self) -> None:
        self.assertAlmostEqual(vr._anker_zeit("two three", self.w), 0.3)


class TestZitatDauer(unittest.TestCase):
    """Rechnung aus szenen_bauen, hier direkt nachgestellt."""

    @staticmethod
    def bis(sp: tuple[float, float], w: list[vr.Wort],
            naechster: float) -> float:
        natur = (vr._satz_ende(w, sp[1]) or sp[1]) + vr.ZITAT_NACHLAUF
        natur = max(natur, sp[0] + vr.ZITAT_MIN)
        return min(sp[0] + vr.ZITAT_MAX, naechster - 0.5, natur)

    def test_karte_geht_mit_ihrem_satz(self) -> None:
        w = worte([("Idiots", 0.0, 0.4), ("want", 0.4, 3.5),
                   ("XOM.", 3.5, 4.0), ("Next", 6.0, 6.4),
                   ("topic.", 6.4, 7.0)])
        # 4.0s Satzende + 1.5s Nachlauf - nicht die vollen 12s.
        self.assertAlmostEqual(self.bis((0.0, 4.0), w, 60.0), 5.5)

    def test_kurzes_zitat_behaelt_lesezeit(self) -> None:
        w = worte([("Kek.", 0.0, 0.8), ("Next", 5.0, 5.4)])
        self.assertAlmostEqual(self.bis((0.0, 0.8), w, 60.0), vr.ZITAT_MIN)

    def test_hoechstdauer_bleibt_die_obergrenze(self) -> None:
        # Ein Satz, der ewig laeuft: ZITAT_MAX deckelt weiterhin.
        w = worte([("und", 0.0, 40.0), ("Ende.", 40.0, 41.0)])
        self.assertAlmostEqual(self.bis((0.0, 40.0), w, 90.0), vr.ZITAT_MAX)

    def test_kapitelwechsel_deckelt(self) -> None:
        w = worte([("Zitat", 0.0, 2.0), ("Ende.", 2.0, 3.0)])
        self.assertAlmostEqual(self.bis((0.0, 3.0), w, 4.0), 3.5)


class TestAusklang(unittest.TestCase):
    def test_fade_passt_in_den_ausklang(self) -> None:
        self.assertLess(vr.SCHLUSS_FADE, vr.AUSKLANG)

    def test_tonkette_reicht_bis_zum_ende(self) -> None:
        _, teile, quelle = vr._ton_kette(1, 100.0)
        kette = ";".join(teile)
        self.assertEqual(quelle, "[mix]")
        # Gepolstert wird immer die Sprache - mit Bett zusaetzlich gesplittet,
        # weil sidechaincompress denselben Strom als Trigger braucht.
        self.assertIn("apad=whole_dur=100.000", kette)
        if vr.BETT.exists():
            self.assertIn("asplit=2[sp][sck]", kette)
            self.assertIn("[bettg][sck]sidechaincompress", kette)
            self.assertIn("[sp][bett]amix", kette)

    def test_ohne_bett_wird_gepolstert(self) -> None:
        echt = vr.BETT
        try:
            vr.BETT = Path("gibt-es-nicht.opus")
            ein, teile, quelle = vr._ton_kette(1, 42.5)
            self.assertEqual(ein, [])
            self.assertEqual(quelle, "[mix]")
            self.assertEqual(teile, ["[1:a]apad=whole_dur=42.500[mix]"])
        finally:
            vr.BETT = echt


if __name__ == "__main__":
    unittest.main()
