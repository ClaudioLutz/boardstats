#!/usr/bin/env python3
"""Tests fuer die Stichwort-Fragmente unter dem Fokus-Punkt (19.08.2026).

Der Fokus-Punkt zeigte bisher nur den 34-Zeichen-Bulletpoint; darunter steht
jetzt ein Kasten mit zwei bis drei Telegramm-Fragmenten, der wieder
verschwindet, bevor der Punkt in die Themen-Karte parkt. Geprueft wird die
Geometrie, denn sie traegt zwei Zusagen, die man dem fertigen Video nicht
mehr ansieht:

- ohne Fragmente sitzt der Fokus-Punkt exakt wie vorher (keine Regression
  fuer Drehbuecher ohne das neue Feld),
- mit Fragmenten ueberlaeuft der Stapel nie den Themen-Titel oben - lieber
  fallen Fragmente weg als dass der Kapiteltitel verdeckt wird.

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_report            # noqa: E402
import szenen                # noqa: E402
import video_report          # noqa: E402

PUNKT = "BTC BACK AT 61K"
FRAGMENTE = ["bounce from 58.2K overnight",
             "one poster: shorts liquidated at 60K",
             "unsourced, mood flips to greed"]


def _kasten(bild) -> tuple[int, int, int, int]:
    """Sichtbarer Bereich eines Overlays im 1280x720-Raster."""
    k = bild.getbbox()
    assert k is not None, "Overlay ist leer"
    return k


class FokusOhneDetail(unittest.TestCase):
    """Ohne Fragmente darf sich an der bisherigen Lage nichts aendern."""

    def test_zentriert_wie_bisher(self) -> None:
        leer: list[str] = []
        for detail in (None, leer):
            with self.subTest(detail=detail):
                bild, _, _ = szenen.fokus_punkt(PUNKT, "left", detail)
                oben, unten = _kasten(bild)[1], _kasten(bild)[3]
                # Der Kasten ist auf FOKUS_MITTE zentriert (1 px Toleranz
                # fuer die Ganzzahl-Halbierung der Hoehe).
                self.assertAlmostEqual((oben + unten) / 2,
                                       szenen.FOKUS_MITTE, delta=1.5)

    def test_kein_detail_kasten(self) -> None:
        self.assertIsNone(szenen.detail_karte(PUNKT, [], "left"))
        self.assertIsNone(szenen.detail_karte(PUNKT, ["   "], "left"))


class StapelGeometrie(unittest.TestCase):
    """Fokus-Kasten und Detail-Kasten sind zwei Overlays und muessen ohne
    Ueberlappung uebereinander sitzen - sie werden getrennt gerendert, also
    kann das nur eine gemeinsame Rechnung sichern."""

    def test_detail_sitzt_unter_dem_punkt(self) -> None:
        fk, _, _ = szenen.fokus_punkt(PUNKT, "left", FRAGMENTE)
        dk = szenen.detail_karte(PUNKT, FRAGMENTE, "left")
        assert dk is not None
        f_links, _, f_rechts, f_unten = _kasten(fk)
        d_links, d_oben, d_rechts, _ = _kasten(dk)
        self.assertGreaterEqual(d_oben, f_unten,
                                "Detail-Kasten ueberlappt den Fokus-Punkt")
        self.assertEqual((f_links, f_rechts), (d_links, d_rechts),
                         "Kaesten stehen nicht buendig uebereinander")

    def test_beide_seiten(self) -> None:
        """lage steuert die Bildseite; beide Kaesten muessen dieselbe waehlen."""
        for lage, erwartet_links in (("right", szenen.MARGIN),
                                     ("left", szenen.B - szenen.MARGIN
                                      - szenen.FOKUS_BREITE)):
            with self.subTest(lage=lage):
                fk, _, _ = szenen.fokus_punkt(PUNKT, lage, FRAGMENTE)
                dk = szenen.detail_karte(PUNKT, FRAGMENTE, lage)
                assert dk is not None
                self.assertEqual(_kasten(fk)[0], erwartet_links)
                self.assertEqual(_kasten(dk)[0], erwartet_links)

    def test_titel_wird_nie_ueberlaufen(self) -> None:
        """oben_min ist die Unterkante des Themen-Titels: der Stapel beginnt
        nie darueber, egal wie viel Text er traegt."""
        oben_min = szenen.titel_unterkante("Memory stocks") + 14
        langer_punkt = szenen.karte_text(
            "MEMORY STOCKS RIP ON SUPPLY DEAL NEWS")
        lange_fragmente = [
            "SK Hynix up 8% premarket on the news",
            "contract terms not public anywhere yet",
            "board calls it priced in already today"]
        fk, _, _ = szenen.fokus_punkt(langer_punkt, "right", lange_fragmente,
                                      oben_min)
        dk = szenen.detail_karte(langer_punkt, lange_fragmente, "right",
                                 oben_min)
        assert dk is not None
        self.assertGreaterEqual(_kasten(fk)[1], oben_min)
        self.assertLessEqual(_kasten(dk)[3], szenen.STAPEL_UNTEN_MAX)

    def test_fragmente_fallen_weg_statt_zu_ueberlaufen(self) -> None:
        """Passt der Stapel nicht mehr zwischen Titel und Unterkante, kuerzt
        er sich von hinten - er waechst nicht in den Titel hinein."""
        # kaum Platz unter dem Titel (200 im 720p-Layoutmass, nativ skaliert)
        eng = szenen.STAPEL_UNTEN_MAX - szenen._s(200)
        dk = szenen.detail_karte(PUNKT, FRAGMENTE, "left", eng)
        if dk is not None:
            self.assertLessEqual(_kasten(dk)[3], szenen.STAPEL_UNTEN_MAX)
        fk, _, _ = szenen.fokus_punkt(PUNKT, "left", FRAGMENTE, eng)
        self.assertGreaterEqual(_kasten(fk)[1], eng)

    def test_hoechstens_drei_fragmente(self) -> None:
        """Sechs Fragmente ergeben denselben Kasten wie die ersten drei -
        der Rest wird nicht kleiner gesetzt, sondern gar nicht gezeigt."""
        viele = [f"fragment nummer {i}" for i in range(6)]
        voll = szenen.detail_karte(PUNKT, viele, "left")
        drei = szenen.detail_karte(PUNKT, viele[:szenen.DETAIL_MAX], "left")
        assert voll is not None and drei is not None
        self.assertEqual(_kasten(voll), _kasten(drei))


class DetailFelder(unittest.TestCase):
    """Das Drehbuch-Feld ist optional und kommt vom Modell - beide Seiten
    muessen mit fehlendem, leerem und falsch getipptem Inhalt umgehen."""

    def test_leseseite_vertraegt_alles(self) -> None:
        for roh, erwartet in (
                ({}, []),
                ({"detail": None}, []),
                ({"detail": []}, []),
                ({"detail": "einzelnes fragment"}, ["einzelnes fragment"]),
                ({"detail": ["  a  ", "", "b"]}, ["a", "b"]),
                ({"detail": 42}, [])):
            with self.subTest(roh=roh):
                self.assertEqual(video_report._detail_liste(roh), erwartet)

    def test_schreibseite_kappt(self) -> None:
        p = {"text": "BTC BACK AT 61K", "anker": "the price of",
             "detail": ["x" * 80, "zweites fragment.", "drittes", "viertes"]}
        aus = run_report._stichwort(p)
        self.assertEqual(len(aus["detail"]), run_report.DETAIL_MAX_FRAGMENTE)
        self.assertEqual(len(aus["detail"][0]),
                         run_report.DETAIL_MAX_ZEICHEN)
        self.assertFalse(aus["detail"][1].endswith("."),
                         "Schlusspunkt gehoert nicht ins Fragment")

    def test_ohne_detail_kein_feld(self) -> None:
        aus = run_report._stichwort({"text": "SHORTS WIPED", "anker": "a b c"})
        self.assertNotIn("detail", aus)


class FragmentlaengePasstInsFenster(unittest.TestCase):
    """Die Kappung muss an der Zeit im Bild gemessen werden, nicht an der
    Kartenbreite. Bei DETAIL_MAX_ZEICHEN=40 brauchten zwei Fragmente 8.7s -
    weit ueber jedem real gemessenen Fenster (Median 4.93s am 21.08.2026),
    weshalb die zweite Zeile bei 13 von 24 Punkten wegfiel."""

    #: Oberes Drittel der am 22.08.2026 gemessenen freien Fenster. Wer
    #: DETAIL_MAX_ZEICHEN wieder anhebt, laesst diesen Test fallen und sieht
    #: an ihm, was er der zweiten Fragmentzeile damit nimmt.
    FENSTER_GUT = 6.0

    def test_zwei_maximale_fragmente_passen_in_ein_gutes_fenster(self) -> None:
        lang = "x" * run_report.DETAIL_MAX_ZEICHEN
        noetig = (video_report.detail_boden([lang, lang])
                  + video_report.DETAIL_BLENDEN)
        self.assertLessEqual(
            noetig, self.FENSTER_GUT,
            f"zwei Fragmente à {run_report.DETAIL_MAX_ZEICHEN} Zeichen "
            f"brauchen {noetig:.2f}s - mehr als ein gutes Fenster hergibt")

    def test_kurzes_fragmentpaar_liegt_auf_dem_boden(self) -> None:
        """Unter 20 Zeichen bringt Kuerzen nichts mehr: dort greift
        DETAIL_FRAG_MIN, zwei Fragmente kosten immer 4.0s. Das ist die
        Grenze, an der die Messung ausgelaufen ist (17 vollstaendig bei
        Kappung 22 wie bei 20)."""
        self.assertEqual(video_report.detail_frag_boden("x" * 12),
                         video_report.DETAIL_FRAG_MIN)
        self.assertEqual(video_report.detail_boden(["x" * 12] * 2),
                         2 * video_report.DETAIL_FRAG_MIN)

    def test_prompt_nennt_das_kuerzere_ziel(self) -> None:
        """Das Sicherheitsnetz kappt, den Text schreibt der Prompt - steht
        die Zielmarke nicht darin, kappt die Grenze nur mitten im Wort."""
        self.assertIn("22 characters or less", run_report.FOLIEN_PROMPT)


if __name__ == "__main__":
    unittest.main()
