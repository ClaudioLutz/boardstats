"""Sound-Design (Intent B5) und Kapitel-Knall/Bett-Senke (A#80/69, #137)."""
import sys
import unittest
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sounds
import video_report as vr


class TestKlaenge(unittest.TestCase):
    def test_klaenge_sind_deterministisch(self) -> None:
        self.assertEqual(sounds.whoosh(), sounds.whoosh())
        self.assertEqual(sounds.impact_zahl(), sounds.impact_zahl())

    def test_klaenge_bleiben_im_wertebereich(self) -> None:
        for name, bauer in sounds._BAUER.items():
            probe = bauer()
            self.assertTrue(probe, name)
            self.assertLessEqual(max(abs(s) for s in probe), 3.0, name)

    def test_effekt_spur_schreibt_wav(self) -> None:
        with TemporaryDirectory() as d:
            ziel = sounds.effekt_spur(
                [(0.5, "kapitel"), (2.0, "whoosh"), (2.35, "klick"),
                 (4.0, "zahl")], 6.0, Path(d) / "sfx.wav")
            assert ziel is not None
            with wave.open(str(ziel), "rb") as w:
                self.assertEqual(w.getframerate(), sounds.SR)
                self.assertEqual(w.getnchannels(), 1)
                # 6s Ereignisfenster + 1s Reserve
                self.assertEqual(w.getnframes(), 7 * sounds.SR)

    def test_ereignisse_ausserhalb_fallen_weg(self) -> None:
        with TemporaryDirectory() as d:
            self.assertIsNone(sounds.effekt_spur(
                [(99.0, "zahl"), (-1.0, "klick")], 10.0, Path(d) / "s.wav"))


class TestTonKette(unittest.TestCase):
    def test_zahl_senke_baut_ausdruck(self) -> None:
        expr = vr._zahl_senke(30.0)
        self.assertIn("volume=", expr)
        self.assertIn("29.50", expr)   # 30.0 - ZAHL_SENKE_VORLAUF

    def test_zahl_senke_ohne_moment_bleibt_leer(self) -> None:
        self.assertEqual(vr._zahl_senke(0.0), "")

    def test_effektspur_wird_gemischt(self) -> None:
        # Ohne Bett-Datei ist es der Zwei-Kanal-Mix Sprache+Effekte.
        ein, teile, quelle = vr._ton_kette(0, 10.0,
                                           effekte=Path("sfx.wav"))
        if not vr.BETT.exists():
            self.assertIn("-i", ein)
            self.assertTrue(any("amix=inputs=2" in t for t in teile))
        else:
            self.assertTrue(any("amix=inputs=3" in t for t in teile))
        self.assertEqual(quelle, "[mix]")

    def test_schwarzblende_liegt_im_retention_fenster(self) -> None:
        # Intent A#80/69: wenige Frames (0.1-0.25 s), nicht Sekunden.
        self.assertGreaterEqual(vr.SCHWARZ_BLENDE, 0.1)
        self.assertLessEqual(vr.SCHWARZ_BLENDE, 0.25)


if __name__ == "__main__":
    unittest.main()
