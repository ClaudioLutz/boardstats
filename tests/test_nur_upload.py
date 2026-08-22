"""--nur-upload laedt ein bereits gebautes Video hoch, ohne neu zu rendern.

Der Riegel davor ist wichtiger als das Flag selbst: die Kapitelmarken
entstehen aus den Wort-Zeitstempeln der Vertonung. Kommt die Tonspur nicht
aus dem Cache, gehoeren ihre Zeitstempel zu einer anderen Aufnahme als der,
gegen die das Bild gerendert wurde - die Marken laegen dann daneben, auf
einem oeffentlichen Video.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report            # noqa: E402


class NurUploadRiegel(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        d = Path(self.tmp.name)
        self.mp3 = d / "audio_en.mp3"
        self.mp4 = d / "video_en.mp4"
        self.mp3.write_bytes(b"ton")
        self.mp4.write_bytes(b"bild")
        # Video nach der Tonspur gebaut - der Normalfall
        import os
        alt = self.mp3.stat().st_mtime
        os.utime(self.mp4, (alt + 100, alt + 100))
        self.stand = self.mp3.stat().st_mtime

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_cache_getroffen_video_da(self):
        """Tonspur unveraendert (Cache griff), Video juenger: darf hoch."""
        self.assertIsNone(video_report.nur_upload_hindernis(
            self.mp4, self.mp3, self.stand, self.stand))

    def test_video_fehlt(self):
        self.mp4.unlink()
        h = video_report.nur_upload_hindernis(
            self.mp4, self.mp3, self.stand, self.stand)
        self.assertIsNotNone(h)
        self.assertIn("fehlt", h or "")

    def test_neu_vertont_bricht_ab(self):
        """Der teuerste Fehler: mtime der MP3 hat sich bewegt, die
        Kapitelmarken gehoeren zu einer anderen Tonspur."""
        h = video_report.nur_upload_hindernis(
            self.mp4, self.mp3, self.stand, self.stand + 5)
        self.assertIsNotNone(h)
        self.assertIn("Kapitelmarken", h or "")

    def test_ohne_vorherige_tonspur_bricht_ab(self):
        """Gab es vor dem Lauf gar keine MP3, wurde zwingend neu vertont."""
        h = video_report.nur_upload_hindernis(
            self.mp4, self.mp3, None, self.stand)
        self.assertIsNotNone(h)

    def test_video_aelter_als_tonspur(self):
        import os
        neu = self.mp3.stat().st_mtime + 500
        os.utime(self.mp3, (neu, neu))
        h = video_report.nur_upload_hindernis(
            self.mp4, self.mp3, neu, neu)
        self.assertIsNotNone(h)
        self.assertIn("aelter", h or "")

    def test_flag_impliziert_nicht_nur_video(self):
        """Wuerde --nur-upload nur_video setzen, kaeme main() vor dem Upload
        zurueck - das Flag waere wirkungslos."""
        quelle = Path(video_report.__file__).read_text("utf-8")
        self.assertIn("if args.vorschau is not None or args.trockenlauf:",
                      quelle)
        zeile = next(z for z in quelle.splitlines()
                     if "args.vorschau is not None or" in z)
        self.assertNotIn("nur_upload", zeile)


if __name__ == "__main__":
    unittest.main()
