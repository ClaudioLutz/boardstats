"""Einblendzeit der Stichwort-Fragmente: jedes erscheint, wenn sein Inhalt
gesprochen wird - nicht alle zusammen mit dem Bulletpoint. Zwei Dinge duerfen
dabei nie kaputtgehen: die Reihenfolge im Kasten und die Lage des Stapels."""
import unittest

import szenen
import video_report as vr

PUNKT = "META/GOOGLE $200B RISK"
FRAGMENTE = ["addictive-algorithm suits", "claim is unsourced",
             "$200B at stake"]


def worte(text: str, ab: float = 0.0, takt: float = 0.5) -> list[vr.Wort]:
    """Wortstrom mit gleichmaessigem Takt - so ist jede erwartete Zeit im
    Test eine einfache Rechnung statt einer Zahl aus dem Nichts."""
    return [vr.Wort(w, ab + i * takt, ab + (i + 1) * takt)
            for i, w in enumerate(text.split())]


SATZ = worte(
    "Meta and Google face a two hundred billion dollar risk if the "
    "addictive-algorithm suits land. The claim is unsourced. Cerebras "
    "says its chip is thirty times more efficient than anything else.")


class Fundort(unittest.TestCase):
    def test_findet_die_sprechstelle(self):
        t = vr._detail_fundort("addictive-algorithm suits", SATZ)
        self.assertIsNotNone(t)
        i = next(i for i, w in enumerate(SATZ)
                 if w.text == "addictive-algorithm")
        self.assertAlmostEqual(t, SATZ[i].start)

    def test_wortinterne_tokens_zaehlen(self):
        """"$12.50" ist EIN gesprochenes Wort, das zu zwei Tokens
        normalisiert - ein Stringvergleich fande seine Zahl nie wieder."""
        strom = worte("I sold at $12.50 yesterday")
        self.assertIsNotNone(vr._detail_fundort("bought $14, now $12.50",
                                                strom))

    def test_einzelnes_haeufiges_wort_traegt_nicht(self):
        """Ein Treffer auf einem Wort, das im Fenster staendig faellt, zeigt
        das Fragment irgendwo - dann lieber interpolieren."""
        strom = worte("chip and chip and chip and chip again")
        self.assertIsNone(vr._detail_fundort("chip demand rising", strom))

    def test_seltenes_einzelwort_traegt(self):
        strom = worte("nothing here except cerebras in this stretch")
        self.assertIsNotNone(vr._detail_fundort("cerebras claim", strom))

    def test_ohne_treffer_none(self):
        self.assertIsNone(vr._detail_fundort("völlig anderer Inhalt", SATZ))
        self.assertIsNone(vr._detail_fundort("the and of", SATZ))


class Zeiten(unittest.TestCase):
    def test_nicht_von_anfang_an(self):
        """Der Kern der Aenderung: das Fragment steht nicht schon da, wenn
        der Bulletpoint erscheint."""
        z = vr._detail_zeiten(["addictive-algorithm suits"], SATZ, 0.0, 20.0)
        self.assertGreater(z[0], 1.0)

    def test_reihenfolge_bleibt(self):
        """Der Kasten baut sich von oben nach unten auf - ein spaeteres
        Fragment darf nie vor einem frueheren erscheinen, auch wenn sein
        Fundort frueher liegt."""
        z = vr._detail_zeiten(["chip is efficient", "Google faces risk"],
                              SATZ, 0.0, 20.0)
        self.assertGreaterEqual(z[1], z[0] + vr.DETAIL_VERSATZ)

    def test_lesezeit_vor_dem_ende(self):
        """Das letzte Fragment darf nicht aufblitzen: es braucht seine
        Lesezeit, bevor der Punkt in die Karte fliegt."""
        z = vr._detail_zeiten(FRAGMENTE, SATZ, 0.0, 12.0)
        rest = 0.0
        for i in range(len(FRAGMENTE) - 1, -1, -1):
            rest += vr.detail_frag_boden(FRAGMENTE[i])
            self.assertLessEqual(z[i], 12.0 - rest + 1e-6)

    def test_enges_fenster_bleibt_im_rahmen(self):
        z = vr._detail_zeiten(FRAGMENTE, SATZ, 5.0, 6.0)
        self.assertTrue(all(5.0 <= t <= 6.0 for t in z), z)

    def test_ohne_fundort_gleichmaessig(self):
        """Fragmente ohne Fundstelle verteilen sich ueber das Fenster,
        statt alle am Anfang zu kleben."""
        z = vr._detail_zeiten(["erstes fremdwort", "zweites fremdwort"],
                              SATZ, 0.0, 30.0)
        self.assertGreater(z[0], 0.0)
        self.assertGreater(z[1], z[0])

    def test_leere_liste(self):
        self.assertEqual(vr._detail_zeiten([], SATZ, 0.0, 10.0), [])


class Stapel(unittest.TestCase):
    def test_letzte_stufe_ergibt_die_karte(self):
        teile = szenen.detail_teile(PUNKT, FRAGMENTE)
        self.assertIsNotNone(teile)
        kaesten, zeilen = teile
        self.assertEqual(len(kaesten), len(FRAGMENTE))
        self.assertEqual(len(zeilen), len(FRAGMENTE))
        bild = kaesten[-1].copy()
        for zeile in zeilen:
            bild.alpha_composite(zeile)
        self.assertEqual(bild.tobytes(),
                         szenen.detail_karte(PUNKT, FRAGMENTE).tobytes())

    def test_kasten_waechst_nur_nach_unten(self):
        """Der Fokus-Punkt darueber steht fest, waehrend der Kasten sich
        fuellt - nach oben darf er deshalb keinen Millimeter wandern, und
        jede Stufe muss die vorige vollstaendig ueberdecken (sonst blitzt
        an der Naht das Motiv durch)."""
        kaesten, zeilen = szenen.detail_teile(PUNKT, FRAGMENTE)
        for i in range(1, len(kaesten)):
            with self.subTest(stufe=i):
                x0, y0, x1, y1 = kaesten[i - 1].getbbox()
                nx0, ny0, nx1, ny1 = kaesten[i].getbbox()
                self.assertEqual((nx0, ny0, nx1), (x0, y0, x1))
                self.assertGreater(ny1, y1)

    def test_jede_zeile_liegt_in_ihrer_stufe(self):
        """Eine Zeile darf nie ausserhalb des Kastens stehen, der zu ihrer
        Zeit gilt - sonst haengt Kleintext auf dem rohen Board-Motiv."""
        kaesten, zeilen = szenen.detail_teile(PUNKT, FRAGMENTE)
        for i, (kasten, zeile) in enumerate(zip(kaesten, zeilen)):
            with self.subTest(stufe=i):
                kx = kasten.getbbox()
                zx = zeile.getbbox()
                self.assertGreaterEqual(zx[0], kx[0])
                self.assertGreaterEqual(zx[1], kx[1])
                self.assertLessEqual(zx[2], kx[2])
                self.assertLessEqual(zx[3], kx[3])

    def test_kein_detail_keine_teile(self):
        self.assertIsNone(szenen.detail_teile(PUNKT, []))
        self.assertIsNone(szenen.detail_teile(PUNKT, ["   "]))


if __name__ == "__main__":
    unittest.main()
