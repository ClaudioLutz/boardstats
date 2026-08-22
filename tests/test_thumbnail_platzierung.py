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

from PIL import Image, ImageDraw

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

    def _messung(self):
        zone, ausrichtung = thumbnail.platzierung_messen(self.motiv)
        return {"zone": zone, "ausrichtung": ausrichtung,
                "block_breite": thumbnail.BREITE_STANDARD, "umbruch": None}

    def test_urteil_wird_uebernommen(self):
        antwort = ('{"beschreibung": "pinkes Wojak-Gesicht vor dunklem '
                   'Gitter, Mund unten offen", "zone": "unten", '
                   '"ausrichtung": "rechts", "breite": "drittel", '
                   '"umbruch": ["50%", "TARIFFS"], "grund": "dunkle Spalte '
                   'rechts nutzen"}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            urteil = vr._thumb_platzierung(self.motiv, "50% TARIFFS")
        self.assertEqual(urteil, {"zone": "unten", "ausrichtung": "rechts",
                                  "block_breite": "drittel",
                                  "umbruch": ["50%", "TARIFFS"]})

    def test_umbruch_der_den_text_aendert_wird_verworfen(self):
        """Das Modell darf Zeilen teilen, nicht die Schlagzeile umschreiben -
        sonst stuende ein erfundener Text als Kanalanstrich im Netz."""
        antwort = ('{"beschreibung": "ein Chart mit roter Kerzenreihe und '
                   'Gitternetz", "zone": "oben", "ausrichtung": "mitte", '
                   '"breite": "halb", "umbruch": ["100%", "TARIFFS", "NOW"]}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            urteil = vr._thumb_platzierung(self.motiv, "50% TARIFFS")
        self.assertIsNone(urteil["umbruch"])
        self.assertEqual(urteil["block_breite"], "halb")

    def test_unbekannte_breite_faellt_auf_voll(self):
        antwort = ('{"beschreibung": "ein Chart mit roter Kerzenreihe und '
                   'Gitternetz", "zone": "oben", "ausrichtung": "mitte", '
                   '"breite": "schmal"}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            urteil = vr._thumb_platzierung(self.motiv, "50% TARIFFS")
        self.assertEqual(urteil["block_breite"], thumbnail.BREITE_STANDARD)

    def test_ohne_beschreibung_greift_die_messung(self):
        """Ein Urteil ohne eigene Beschreibung heisst: nicht hingesehen."""
        antwort = ('{"beschreibung": "ok", "zone": "unten", '
                   '"ausrichtung": "rechts", "breite": "drittel"}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "X"),
                             self._messung())

    def test_muell_antwort_greift_die_messung(self):
        with mock.patch.object(vr.rr, "claude_ruf", return_value="kein JSON"):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "X"),
                             self._messung())

    def test_aufruf_faellt_aus(self):
        with mock.patch.object(vr.rr, "claude_ruf",
                               side_effect=RuntimeError("timeout")):
            self.assertEqual(vr._thumb_platzierung(self.motiv, "X"),
                             self._messung())

    def test_unsinnige_zone_wird_ersetzt(self):
        antwort = ('{"beschreibung": "ein Chart-Screenshot mit roter '
                   'Kerzenreihe", "zone": "diagonal", "ausrichtung": "mitte"}')
        with mock.patch.object(vr.rr, "claude_ruf", return_value=antwort):
            urteil = vr._thumb_platzierung(self.motiv, "X")
        self.assertIn(urteil["zone"], thumbnail.ZONEN)
        self.assertEqual(urteil["ausrichtung"], "mitte")

    def test_ohne_motiv_kein_aufruf(self):
        """Ohne Motiv gibt es nichts anzusehen - der Aufruf muss entfallen,
        er kostet sonst jeden Lauf ein Modell-Token fuer nichts."""
        with mock.patch.object(vr.rr, "claude_ruf") as ruf:
            urteil = vr._thumb_platzierung(None, "X")
        ruf.assert_not_called()
        self.assertEqual(urteil["zone"], thumbnail.ZONE_STANDARD)
        self.assertEqual(urteil["ausrichtung"], thumbnail.AUSRICHTUNG_STANDARD)


class Umbruchriegel(unittest.TestCase):
    """umbruch_pruefen(): dieselben Woerter in derselben Reihenfolge."""

    def test_gleiche_woerter_gehen_durch(self):
        self.assertEqual(
            thumbnail.umbruch_pruefen("50% TARIFFS", ["50%", "tariffs"]),
            ["50%", "TARIFFS"])

    def test_mehrwort_zeilen_gehen_durch(self):
        self.assertEqual(
            thumbnail.umbruch_pruefen("CANADA HITS BACK HARD",
                                      ["CANADA HITS", "BACK HARD"]),
            ["CANADA HITS", "BACK HARD"])

    def test_wort_weggelassen(self):
        self.assertIsNone(
            thumbnail.umbruch_pruefen("50% TARIFFS", ["TARIFFS"]))

    def test_wort_dazu(self):
        self.assertIsNone(thumbnail.umbruch_pruefen(
            "50% TARIFFS", ["50%", "TARIFFS", "NOW"]))

    def test_reihenfolge_gedreht(self):
        self.assertIsNone(thumbnail.umbruch_pruefen(
            "50% TARIFFS", ["TARIFFS", "50%"]))

    def test_zu_viele_zeilen(self):
        self.assertIsNone(thumbnail.umbruch_pruefen(
            "A B C D", ["A", "B", "C", "D"]))

    def test_leere_zeile(self):
        self.assertIsNone(thumbnail.umbruch_pruefen(
            "50% TARIFFS", ["50% TARIFFS", ""]))

    def test_keine_liste(self):
        self.assertIsNone(thumbnail.umbruch_pruefen("50% TARIFFS", "50%"))
        self.assertIsNone(thumbnail.umbruch_pruefen("50% TARIFFS", None))


class SpalteUndUmbruch(unittest.TestCase):
    """Die schmale Spalte ist der Zweck der Uebung: der Text muss dann
    wirklich in die Spaltenbreite passen, nicht quer ueber das Bild."""

    def test_umbruch_wird_gezeichnet(self):
        with TemporaryDirectory() as d:
            motiv = _bild(Path(d) / "m.jpg", (30, 30, 40), (200, 200, 210))
            eng = thumbnail.bauen("50% TARIFFS", motiv, Path(d) / "eng.jpg",
                                  zone="unten", ausrichtung="rechts",
                                  block_breite="drittel",
                                  umbruch=["50%", "TARIFFS"])
            voll = thumbnail.bauen("50% TARIFFS", motiv, Path(d) / "voll.jpg",
                                   zone="unten", ausrichtung="rechts",
                                   block_breite="voll")
            self.assertNotEqual(eng.read_bytes(), voll.read_bytes())

    def test_schmale_spalte_zwingt_kleinere_schrift(self):
        zeichnen = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        breit = int(thumbnail.TEXT_BREITE * thumbnail.BLOCK_BREITEN["voll"])
        schmal = int(thumbnail.TEXT_BREITE
                     * thumbnail.BLOCK_BREITEN["drittel"])
        f_breit, _ = thumbnail._passende_schrift(
            "50% TARIFFS", breit, thumbnail.TEXT_HOEHE, zeichnen)
        f_schmal, zeilen = thumbnail._passende_schrift(
            "50% TARIFFS", schmal, thumbnail.TEXT_HOEHE, zeichnen,
            ["50%", "TARIFFS"])
        self.assertLess(f_schmal.size, f_breit.size)
        self.assertEqual(zeilen, ["50%", "TARIFFS"])
        for zeile in zeilen:
            self.assertLessEqual(zeichnen.textlength(zeile, font=f_schmal),
                                 schmal)

    def test_unpassende_vorgabe_wird_neu_umgebrochen(self):
        """Passt die Vorgabe selbst in der kleinsten Schrift nicht in die
        Spalte, bricht der Code wieder selbst um - kein Text aus dem Bild."""
        zeichnen = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        text = "MASSIVE UNBELIEVABLE LIQUIDATION"
        schmal = int(thumbnail.TEXT_BREITE
                     * thumbnail.BLOCK_BREITEN["drittel"])
        _, zeilen = thumbnail._passende_schrift(
            text, schmal, thumbnail.TEXT_HOEHE, zeichnen, [text])
        self.assertNotEqual(zeilen, [text])


if __name__ == "__main__":
    unittest.main()
