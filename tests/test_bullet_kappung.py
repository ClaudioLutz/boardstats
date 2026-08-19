"""Kappung der Stichpunkte: was im Bild steht, darf nie wie ein Fehler
aussehen - kein Schnitt mitten im Wort, kein haengendes Fuellwort, und nichts,
was beim Parken in der Themen-Karte verloren geht."""
import unittest

from PIL import ImageDraw

import folien
import run_report
import szenen
import video_report as vr

# Saetze aus einem echten Bericht, jeweils so, wie ein Satz-Cue sie liefert.
KORPUS = [
    'liquid investable USD in millions" - net worth including your house '
    'does not count on those lists.',
    "The mechanical explanation for the semi sell-off, attributed to a "
    "single desk, is not sourced.",
    "Coca-Cola got its own thread on the \"why is it mooning\" question.",
    "A CAFC order dated 8-17-2026 is cited for ~$303 million owed.",
    "Practical tip: check the university's withdrawal-fee schedule first.",
    "FUD - \"fear, uncertainty, and doubt,\" discouraging rhetoric.",
    "$15.5 average entry, 2% of my port.",
    "Premarket today: 0.07%, i.e.",
    "Bagholder - a term for an investor stuck holding a losing position.",
]


class LueckenBullet(unittest.TestCase):
    def test_letztes_wort_bleibt_wenn_es_passt(self):
        """Der gemeldete Fehler: das schliessende Anfuehrungszeichen frass
        genau ein Zeichen des Budgets, und die Kappung am letzten vollen Wort
        warf daraufhin MILLIONS weg."""
        self.assertEqual(vr._luecken_bullet(KORPUS[0]),
                         "LIQUID INVESTABLE USD IN MILLIONS")

    def test_nie_auf_einem_fuellwort(self):
        for satz in KORPUS:
            with self.subTest(satz=satz):
                letzt = vr._luecken_bullet(satz).split()[-1].rstrip("…").strip()
                self.assertNotIn(letzt, vr.BULLET_FUELLWORT)

    def test_parken_verliert_nichts(self):
        """Die Invariante aus dem Docstring von karte_text: was die
        Fokus-Karte zeigt, muss die Themen-Karte ungekuerzt aufnehmen."""
        for satz in KORPUS:
            with self.subTest(satz=satz):
                b = vr._luecken_bullet(satz)
                self.assertEqual(szenen.karte_text(b), b)

    def test_kein_schnitt_im_wort(self):
        for satz in KORPUS:
            with self.subTest(satz=satz):
                b = vr._luecken_bullet(satz).rstrip(" …")
                quelle = satz.upper().replace('"', "")
                for wort in b.split():
                    self.assertIn(wort.strip(",;:"), quelle)

    def test_laengenziel_gehalten(self):
        """Zwei volle Kartenzeilen fassen rund 80 Zeichen - so lang darf ein
        Fallback nicht werden, sonst steht der gesprochene Satz im Bild."""
        for satz in KORPUS:
            with self.subTest(satz=satz):
                self.assertLessEqual(len(vr._luecken_bullet(satz)),
                                     vr.BULLET_MAX + 2)

    def test_auslassung_nur_wenn_gekappt(self):
        self.assertNotIn("…", vr._luecken_bullet("Short enough already."))
        self.assertTrue(vr._luecken_bullet(
            "The mechanical explanation for the semiconductor sell-off was "
            "attributed to a single desk").endswith("…"))

    def test_leer_und_ueberlanges_wort(self):
        self.assertEqual(vr._luecken_bullet("  -- ,  "), "")
        lang = "Donaudampfschifffahrtsgesellschaftskapitaensmuetze" * 2
        self.assertTrue(vr._luecken_bullet(lang))


class KartenBreite(unittest.TestCase):
    def test_umbruchbreite_ist_die_echte_textbreite(self):
        """Umbrochen wurde frueher gegen die Kante des Marker-Quadrats statt
        gegen den Texteinzug - 22 px zu breit, lange Zeilen liefen aus dem
        Kasten heraus."""
        self.assertEqual(szenen.KARTE_INNEN,
                         szenen.KARTE_BREITE - szenen.KARTE_TEXT_X
                         - szenen.KARTE_PAD_R)

    def test_keine_zeile_laeuft_aus_dem_kasten(self):
        d = ImageDraw.Draw(szenen._leer())
        f = folien._font_medium(szenen.KARTE_PUNKT_FONT)
        platz = szenen.KARTE_BREITE - szenen.KARTE_TEXT_X - szenen.KARTE_PAD_R
        for satz in KORPUS:
            punkt = szenen.karte_text(vr._luecken_bullet(satz))
            for zeile in folien._umbrechen(d, punkt.upper(), f,
                                           szenen.KARTE_INNEN):
                with self.subTest(zeile=zeile):
                    self.assertLessEqual(d.textlength(zeile, font=f), platz)

    def test_karte_passt_misst_zwei_zeilen(self):
        self.assertTrue(szenen.karte_passt("SHORT ONE"))
        self.assertFalse(szenen.karte_passt("WORD " * 40))
        self.assertFalse(szenen.karte_passt("   "))


class Wortgrenze(unittest.TestCase):
    def test_kappt_am_wort_nicht_im_wort(self):
        self.assertEqual(run_report._wortgrenze("alpha beta gammagamma", 14),
                         "alpha beta")

    def test_kurzes_bleibt_unberuehrt(self):
        self.assertEqual(run_report._wortgrenze("alpha beta", 20),
                         "alpha beta")

    def test_ueberlanges_einzelwort_wird_hart_gekappt(self):
        self.assertEqual(run_report._wortgrenze("gammagammagamma", 5), "gamma")

    def test_stichwort_nutzt_die_wortgrenze(self):
        p = run_report._stichwort({
            "text": "alpha beta gamma delta epsilon zeta eta theta iota",
            "detail": ["one two three four five six seven eight nine ten."]})
        self.assertFalse(p["text"].endswith("IOT"))
        self.assertTrue(all(w in p["text"].split()
                            for w in p["text"].split()))
        self.assertLessEqual(len(p["text"]), 38)
        self.assertLessEqual(len(p["detail"][0]),
                             run_report.DETAIL_MAX_ZEICHEN)


if __name__ == "__main__":
    unittest.main()
