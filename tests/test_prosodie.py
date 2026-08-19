#!/usr/bin/env python3
"""Tests fuer die Prosodie des Studio-Pfads.

Was en-US-Studio-Q an SSML annimmt, ist am 19.08.2026 gegen die Live-API
gemessen: <prosody rate>, <prosody volume>, <break>, <say-as> und <s> gehen,
<prosody pitch> und <emphasis> antworten mit HTTP 400. Betonung gibt es also
nicht - der Ersatz ist Verlangsamung.

Die Tests sichern drei Eigenschaften, die dabei nicht verloren gehen duerfen:
der Klartext bleibt unberuehrt (an ihm haengen Zeitachse und Untertitel), die
Grossenordnung wird nicht zerschnitten ("$303 million" darf nicht als
"$303 m" plus "illion" herauskommen), und SSML entsteht nur dort, wo es etwas
traegt - sonst zahlt jeder Satz die Tags in der Abrechnung mit.

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report as V  # noqa: E402


class TestZahlenHervorheben(unittest.TestCase):
    def _treffer(self, satz: str) -> list[str]:
        return [m.group() for m in V.ZAHL_HART.finditer(satz)]

    def test_groessenordnung_bleibt_ganz(self):
        # Der Fehler, der den Test veranlasst hat: eine Alternative "m" vor
        # "million" matchte "$303 m", die Stimme sprach danach "illion".
        self.assertEqual(self._treffer("owes about $303 million in damages"),
                         ["$303 million"])

    def test_prozent_in_beiden_schreibweisen(self):
        self.assertEqual(self._treffer("dropped 22 percent"), ["22 percent"])
        self.assertEqual(self._treffer("2% of my port"), ["2%"])
        self.assertEqual(self._treffer("gained 30 percentage points"),
                         ["30 percentage points"])

    def test_geld_und_groessen(self):
        self.assertEqual(self._treffer("a $200 order"), ["$200"])
        self.assertEqual(self._treffer("$1.2bn wiped out"), ["$1.2bn"])
        self.assertEqual(self._treffer("worth 50k a year"), ["50k"])
        self.assertEqual(self._treffer("a 2.4x acceleration"), ["2.4x"])

    def test_datum_und_aktenzeichen_bleiben_unberuehrt(self):
        self.assertEqual(self._treffer("on 8-17-2026 the court ruled"), [])
        self.assertEqual(self._treffer("order 24-2203 as evidence"), [])
        self.assertEqual(self._treffer("Bitcoin is 17 years old"), [])

    def test_kein_treffer_erzeugt_kein_ssml(self):
        ssml, gew = V._zahlen_hervorheben("Nothing quantitative here at all.")
        self.assertIsNone(ssml)
        self.assertEqual(gew, ())

    def test_gewichte_passen_zur_tokenzahl(self):
        satz = "Klarna dropped 22 percent in one session."
        ssml, gew = V._zahlen_hervorheben(satz)
        self.assertIsNotNone(ssml)
        self.assertEqual(len(gew), len(satz.split()))
        # Genau die beiden Tokens der Zahl sind gestreckt.
        self.assertEqual([g > 1.0 for g in gew],
                         [False, False, True, True, False, False, False])

    def test_sonderzeichen_werden_maskiert(self):
        ssml, _ = V._zahlen_hervorheben('He said "R&D costs 50k" yesterday.')
        self.assertNotIn("&D", ssml)
        self.assertIn("&amp;", ssml)


class TestStudioStuecke(unittest.TestCase):
    # Die Saetze sind bewusst laenger als STUDIO_SATZ_MIN (45 Zeichen) -
    # kuerzere Fragmente haengt _saetze_teilen an den Vorgaenger, und der
    # Absatz haette dann nur einen einzigen Satz.
    # Vier Umbrueche = Kapitelgrenze, drei = Agenda-Eintrag, zwei = Absatz
    # (siehe V._pause_fuer_trenner).
    TEXT = ("An introductory line that is long enough to stand alone.\n\n\n\n"
            "CRYPTO\n\n"
            "Monero fell 12 percent overnight and nobody explained why. "
            "A second sentence follows it and carries the argument along. "
            "And a third one closes the paragraph with the actual point.\n\n"
            "A trailing paragraph that carries no numbers whatsoever.")

    def setUp(self):
        self.stuecke = V._studio_stuecke(self.TEXT)

    def test_klartext_enthaelt_kein_markup(self):
        for s in self.stuecke:
            self.assertNotIn("<", s.text)

    def test_ueberschrift_und_folgesatz_laufen_langsamer(self):
        langsam = [s.text for s in self.stuecke
                   if s.ssml and V.STUDIO_KAPITEL_RATE in s.ssml]
        self.assertIn("CRYPTO", langsam)
        self.assertTrue(any(t.startswith("Monero fell") for t in langsam))

    def test_pointe_bekommt_die_laengere_pause(self):
        pointen = [s.text for s in self.stuecke
                   if abs(s.pause - V.STUDIO_POINTE_PAUSE) < 1e-9]
        self.assertEqual(len(pointen), 1)
        self.assertTrue(pointen[0].startswith("And a third one"))

    def test_kurzer_absatz_bekommt_keine_pointen_pause(self):
        # Zwei Saetze sind kein Aufbau - erst ab STUDIO_POINTE_AB.
        kurz = V._studio_stuecke("One sentence here that is plenty long enough. "
                                 "And a second one that is also long enough.")
        self.assertTrue(all(abs(s.pause - V.STUDIO_POINTE_PAUSE) > 1e-9
                            for s in kurz))

    def test_saetze_ohne_anlass_bleiben_klartext(self):
        ohne = [s for s in self.stuecke if s.ssml is None]
        self.assertTrue(ohne, "mindestens ein Satz muss ohne SSML durchgehen")
        self.assertIn("A trailing paragraph that carries no numbers whatsoever.",
                      [s.text for s in ohne])


class TestWorteVerteilen(unittest.TestCase):
    def test_gestreckte_tokens_bekommen_mehr_zeit(self):
        satz = "up 22 percent today"
        ohne = V._worte_verteilen(satz, 0.0, 4.0)
        mit = V._worte_verteilen(satz, 0.0, 4.0, (1.0, 1.5, 1.5, 1.0))
        d_ohne = ohne[1].end - ohne[1].start
        d_mit = mit[1].end - mit[1].start
        self.assertGreater(d_mit, d_ohne)

    def test_satzgrenzen_bleiben_exakt(self):
        worte = V._worte_verteilen("up 22 percent today", 1.0, 4.0,
                                   (1.0, 1.5, 1.5, 1.0))
        self.assertAlmostEqual(worte[0].start, 1.0)
        self.assertAlmostEqual(worte[-1].end, 4.0)

    def test_falsche_gewichtslaenge_wird_ignoriert(self):
        worte = V._worte_verteilen("up 22 percent today", 0.0, 4.0, (1.0, 2.0))
        self.assertEqual(len(worte), 4)
        self.assertAlmostEqual(worte[-1].end, 4.0)


if __name__ == "__main__":
    unittest.main()
