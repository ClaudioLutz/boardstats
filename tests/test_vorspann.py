#!/usr/bin/env python3
"""Tests fuer den Vorspann-Deckel und den TL;DR-Zahlenblock (21.08.2026).

Der Vorspann kannte bis dahin nur einen BODEN (INTRO_BODEN, wegen der
YouTube-Kapitelregel) und keine Decke. Gemessen wuchs er von 29.6 s ueber
37.0 s auf 48.9 s im produktiven Lauf vom 21.08. - gegen eine Abbruchkurve,
die 50 % der Zuschauer nach 1:08 verliert. Hier sind die drei Regeln
gesichert, die ihn seither begrenzen:

- der Hook eroeffnet, ohne Ansage davor,
- hoechstens ZAHLEN_GESPROCHEN der vier Tageszahlen werden vorgelesen,
- ein zu langer Vorspann verliert weitere Zahlensaetze, bis er unter
  INTRO_DECKEL liegt (die Karten bleiben im Bild).

Lauf:  python -m unittest discover -s tests
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_report as V  # noqa: E402

DATUM = "2026-08-21"


def karte(nr: int, satz: str) -> dict:
    return {"wert": f"{nr}00%", "titel": f"Titel {nr}", "sub": "sub",
            "satz": satz}


def bloecke_bauen(saetze: list[str], hook: str = "SILVER HITS 70") -> list:
    fdaten = {"zahlen": [karte(i + 1, s) for i, s in enumerate(saetze)]}
    return V.praesentations_bloecke([], {}, fdaten, DATUM, hook)


def rollen(bloecke: list, rolle: str) -> list:
    return [b for b in bloecke if b.rolle == rolle]


class ZahlSatz(unittest.TestCase):
    def test_erster_satz_und_wortgrenze(self):
        """Mehrsaetzige Modelltexte werden auf den ersten Satz und dann auf
        ZAHL_SATZ_WORTE Woerter gekappt - die Zahl selbst steht am
        Satzanfang und bleibt dabei unberuehrt."""
        lang = ("Silver touched seventy dollars an ounce today after a one "
                "dollar and fifty three cents overnight gain. It then "
                "bounced off three times.")
        aus = V._zahl_satz({"wert": "70", "satz": lang})
        self.assertLessEqual(len(aus.split()), V.ZAHL_SATZ_WORTE)
        self.assertTrue(aus.startswith("Silver touched seventy"))
        self.assertNotIn("bounced", aus)
        self.assertTrue(aus.endswith("."))

    def test_kurzer_satz_bleibt_unveraendert(self):
        aus = V._zahl_satz({"wert": "70", "satz": "Silver hit seventy."})
        self.assertEqual(aus, "Silver hit seventy.")

    def test_fallback_ohne_satz(self):
        """Ohne "satz" bilden Titel und Wert die Ansage."""
        aus = V._zahl_satz({"wert": "70", "titel": "Silver"})
        self.assertEqual(aus, "Silver: 70.")


class Vorspann(unittest.TestCase):
    def test_hook_eroeffnet_ohne_ansage(self):
        """Der erste gesprochene Block ist der Hook selbst - keine
        Ansage ("Today's top story") und kein Serienname davor."""
        bloecke = bloecke_bauen(["Eins.", "Zwei.", "Drei.", "Vier."])
        intro = rollen(bloecke, "intro")[0]
        self.assertTrue(intro.text.startswith("SILVER HITS 70"))

    def test_nur_zwei_zahlen_werden_gesprochen(self):
        """Vier Karten im Drehbuch, aber hoechstens ZAHLEN_GESPROCHEN
        gesprochene Zahl-Bloecke."""
        bloecke = bloecke_bauen(["Eins.", "Zwei.", "Drei.", "Vier."])
        self.assertLessEqual(len(rollen(bloecke, "zahl")),
                             V.ZAHLEN_GESPROCHEN)
        self.assertEqual(len(rollen(bloecke, "zahl_kopf")), 1)

    def test_langer_vorspann_verliert_zahlensaetze(self):
        """Bleibt der Vorspann ueber INTRO_DECKEL, faellt der letzte
        gesprochene Zahlensatz weg - einer bleibt immer stehen, sonst
        waere der Zahlen-Kopf eine Ansage ohne Inhalt."""
        lang = " ".join(["wort"] * V.ZAHL_SATZ_WORTE) + "."
        bloecke = bloecke_bauen([lang] * 4, hook=" ".join(["hook"] * 12))
        self.assertEqual(len(rollen(bloecke, "zahl")), 1)

    def test_deckel_wird_eingehalten(self):
        """Die geschaetzte Vorspanndauer liegt unter INTRO_DECKEL, solange
        der Hook selbst nicht laenger ist als die Decke."""
        bloecke = bloecke_bauen(["Silver hit seventy today.",
                                 "Gold added two percent.",
                                 "Bitcoin lost four percent.",
                                 "Uranium gained nine percent."])
        vorspann = [b for b in bloecke
                    if b.rolle in ("intro", "zahl_kopf", "zahl")]
        worte = sum(len(b.text.split()) for b in vorspann)
        dauer = (worte / V.TOKENS_PRO_S
                 + V._pause_sekunden(V.GOOGLE_ABSATZ_PAUSE)
                 * (1 + len(rollen(bloecke, "zahl")))
                 + V._pause_sekunden(V.GOOGLE_KAPITEL_PAUSE))
        self.assertLessEqual(dauer, V.INTRO_DECKEL)

    def test_kurzer_vorspann_behaelt_den_serien_satz(self):
        """Unter INTRO_BODEN wird der Serien-Satz angehaengt, damit
        Kapitel 1 nicht unter die 10-Sekunden-Regel rutscht - er steht
        dabei HINTER dem Hook, nie davor."""
        bloecke = bloecke_bauen(["A."], hook="GOLD")
        intro = rollen(bloecke, "intro")[0]
        self.assertTrue(intro.text.startswith("GOLD"))
        self.assertIn("4chan business board report", intro.text)


if __name__ == "__main__":
    unittest.main()
