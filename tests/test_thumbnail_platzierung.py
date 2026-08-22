"""Meme-Vorschaubild: Textplatzierung und der Weg dahin.

Seit dem Umbau vom 22.08.2026 steht der Aufhaenger frei ueber dem Motiv,
ohne dunkle Abdeckung. Damit haengt die Lesbarkeit daran, WO er steht -
entschieden wird das vom Modell (video_report._thumb_platzierung) mit einer
deterministischen Messung als Netz. Diese Tests halten fest, dass das Netz
traegt und die Geometrie in jeder Zone im Bild bleibt."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from PIL import Image

import thumbnail
import video_report as vr


def _bild(pfad: Path, oben: tuple[int, int, int],
          unten: tuple[int, int, int], streifen: int = 8) -> Path:
    """Testmotiv: ruhige Flaeche oben ODER unten, im Rest ein hartes
    Streifenmuster - das erzeugt genau den Kantenkontrast, an dem sich
    platzierung_messen() orientiert."""
    bild = Image.new("RGB", (thumbnail.BREITE, thumbnail.HOEHE), oben)
    for y in range(thumbnail.HOEHE // 2, thumbnail.HOEHE, streifen):
        for x in range(0, thumbnail.BREITE, streifen):
            farbe = unten if (x // streifen + y // streifen) % 2 else oben
            bild.paste(Image.new("RGB", (streifen, streifen), farbe), (x, y))
    bild.save(pfad, "JPEG", quality=90)
    return pfad


class Messung(unittest.TestCase):
    def test_ruhige_haelfte_gewinnt(self):
        """Liegt das Gewimmel unten, wandert der Text nach oben."""
        with TemporaryDirectory() as d:
            p = _bild(Path(d) / "m.jpg", (20, 20, 30), (240, 240, 250))
            zone, ausrichtung = thumbnail.platzierung_messen(p)
        self.assertEqual(zone, "oben")
        self.assertIn(ausrichtung, thumbnail.AUSRICHTUNGEN)

    def test_ohne_motiv_standard(self):
        self.assertEqual(thumbnail.platzierung_messen(None),
                         (thumbnail.ZONE_STANDARD,
                          thumbnail.AUSRICHTUNG_STANDARD))

    def test_kaputtes_motiv_standard(self):
        """Eine unlesbare Datei darf die Messung nicht werfen - das
        Vorschaubild entsteht trotzdem."""
        with TemporaryDirectory() as d:
            p = Path(d) / "kaputt.jpg"
            p.write_bytes(b"kein Bild")
            self.assertEqual(thumbnail.platzierung_messen(p),
                             (thumbnail.ZONE_STANDARD,
                              thumbnail.AUSRICHTUNG_STANDARD))


class Geometrie(unittest.TestCase):
    def test_block_bleibt_im_bild(self):
        for zone in thumbnail.ZONEN:
            for hoehe in (80, 260, 400):
                y = thumbnail._block_oben(zone, hoehe)
                self.assertGreaterEqual(y, thumbnail.TEXT_OBEN, zone)
                self.assertLessEqual(y + hoehe, thumbnail.HOEHE, zone)

    def test_zone_unten_laesst_den_chip_frei(self):
        y = thumbnail._block_oben("unten", 200)
        self.assertLessEqual(y + 200, thumbnail.CHIP_Y)

    def test_ausrichtung_haelt_die_raender(self):
        breit = thumbnail.TEXT_BREITE
        for ausrichtung in thumbnail.AUSRICHTUNGEN:
            x = thumbnail._zeile_links(ausrichtung, breit)
            self.assertGreaterEqual(x, thumbnail.MARGIN, ausrichtung)
            self.assertLessEqual(x + breit, thumbnail.BREITE, ausrichtung)

    def test_ausrichtung_rechts_setzt_rechts_an(self):
        x = thumbnail._zeile_links("rechts", 400)
        self.assertEqual(x, thumbnail.BREITE - thumbnail.MARGIN - 400)


class BauenMitZone(unittest.TestCase):
    def test_zone_wirkt_auf_die_textlage(self):
        """Derselbe Text in Zone oben und unten darf nicht dasselbe Bild
        ergeben - sonst wird die Platzierung nur gemeldet, nicht gebaut."""
        with TemporaryDirectory() as d:
            motiv = _bild(Path(d) / "m.jpg", (30, 30, 40), (200, 200, 210))
            a = thumbnail.bauen("50% TARIFFS", motiv, Path(d) / "a.jpg",
                                zone="oben", ausrichtung="mitte")
            b = thumbnail.bauen("50% TARIFFS", motiv, Path(d) / "b.jpg",
                                zone="unten", ausrichtung="mitte")
            self.assertNotEqual(a.read_bytes(), b.read_bytes())

    def test_unbekannte_zone_faellt_auf_die_messung(self):
        with TemporaryDirectory() as d:
            motiv = _bild(Path(d) / "m.jpg", (30, 30, 40), (200, 200, 210))
            ziel = thumbnail.bauen("50% TARIFFS", motiv, Path(d) / "z.jpg",
                                   zone="quatsch", ausrichtung="")
            self.assertTrue(ziel.exists())
            self.assertLessEqual(ziel.stat().st_size, thumbnail.MAX_BYTES)


class Platzierungsurteil(unittest.TestCase):
    """_thumb_platzierung(): das Urteil zaehlt nur mit Beleg."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.motiv = _bild(Path(self.tmp.name) / "m.jpg", (30, 30, 40),
                           (200, 200, 210))

    def tearDown(self):
        self.tmp.cleanup()

    def test_urteil_wird_uebernommen(self):
        antwort = ('{"beschreibung": "pinkes Wojak-Gesicht vor dunklem '
                   'Gitter, Mund unten offen", "zone": "unten", '
                   '"ausrichtung": "links", "grund": "Gesicht oben frei '
                   'halten"}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "50% TARIFFS"),
                             ("unten", "links"))

    def test_ohne_beschreibung_greift_die_messung(self):
        """Ein Urteil ohne eigene Beschreibung heisst: nicht hingesehen."""
        antwort = '{"beschreibung": "ok", "zone": "unten", "ausrichtung": "rechts"}'
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "X"),
                             thumbnail.platzierung_messen(self.motiv))

    def test_muell_antwort_greift_die_messung(self):
        with mock.patch.object(vr.rr, "claude_ruf", return_value="kein JSON"):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "X"),
                             thumbnail.platzierung_messen(self.motiv))

    def test_aufruf_faellt_aus(self):
        with mock.patch.object(vr.rr, "claude_ruf",
                               side_effect=RuntimeError("timeout")):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "X"),
                             thumbnail.platzierung_messen(self.motiv))

    def test_unsinnige_zone_wird_ersetzt(self):
        antwort = ('{"beschreibung": "ein Chart-Screenshot mit roter '
                   'Kerzenreihe", "zone": "diagonal", "ausrichtung": "mitte"}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            zone, ausrichtung = vr._thumb_platzierung(self.motiv, "X")
        self.assertIn(zone, thumbnail.ZONEN)
        self.assertEqual(ausrichtung, "mitte")

    def test_ohne_motiv_kein_aufruf(self):
        """Ohne Motiv gibt es nichts anzusehen - der Aufruf muss entfallen,
        er kostet sonst jeden Lauf ein Modell-Token fuer nichts."""
        with mock.patch.object(vr.rr, "claude_ruf") as ruf:
            self.assertEqual(vr._thumb_platzierung(None, "X"),
                             (thumbnail.ZONE_STANDARD,
                              thumbnail.AUSRICHTUNG_STANDARD))
        ruf.assert_not_called()


if __name__ == "__main__":
    unittest.main()
