"""Abdeckung des Drehbuchs: kein Absatz des Berichts darf ohne Stichwort
bleiben. Bleibt einer leer, laeuft im Video eine Redestrecke ohne neuen Text
im Bild - der Renderer fuellt sie zwar mit Fallback-Bullets, die tragen aber
per Konstruktion keine Stichwort-Fragmente (Nutzerbefund 19.08.2026: von
7:59 bis 9:19 kein einziges Fragment, alle sechs Absaetze des laengsten
Kapitels bis auf den ersten ohne Anker)."""
import unittest

import run_report
import szenen
import thumbnail

ABSATZ_A = (
    "An 8-year day trader answering questions is the fastest-moving thread "
    "on the board (https://boards.4chan.org/biz/thread/62605073). He says "
    "Fidelity banned him for volume, claims $1.2 million in five to six "
    "years, and now frames his edge as 0.32 percent per day compounding.")
ABSATZ_B = (
    "The most usable numbers of the day are in a timeshare argument: $35k "
    "upfront, $700 maintenance, $500 booking, $200 interval registration, "
    "working out to a claimed $2,400 a week. The skeptic's counter is the "
    "practical one - secondhand contracts go for pennies on the dollar.")
BERICHT = f"## SELF-REPORTED TRACK RECORDS\n\n{ABSATZ_A}\n\n{ABSATZ_B}\n"


def drehbuch(anker: list[str], ueber: str = "SELF-REPORTED TRACK RECORDS"
             ) -> dict:
    return {"abschnitte": [{"ueberschrift": ueber, "titel": "Track records",
                            "stichworte": [{"text": "X", "anker": a}
                                           for a in anker]}]}


class Absaetze(unittest.TestCase):
    def test_kurze_absaetze_zaehlen_nicht(self):
        """Eine Ueberleitung von zwei Zeilen ist keine eigene Geschichte und
        braucht keinen eigenen Anker."""
        md = f"## A\n\nAlso new today.\n\n{ABSATZ_A}\n"
        self.assertEqual(len(run_report._absaetze(md)["A"]), 1)

    def test_markdown_link_stoert_den_anker_nicht(self):
        """Der Anker steht verbatim im Bericht - aber im Fliesstext liegt
        eine URL dazwischen, die nicht vorgelesen wird."""
        md = f"## A\n\n{ABSATZ_A}\n"
        absatz = run_report._absaetze(md)["A"][0]
        self.assertIn("fastest-moving thread on the board", absatz)
        self.assertNotIn("http", absatz)

    def test_anker_ueber_zeilengrenze(self):
        """Der Bericht ist umgebrochen, der Anker nicht - sonst faende die
        Pruefung ihn nie und forderte bei jedem Lauf nach."""
        md = "## A\n\n" + ABSATZ_A.replace(" thread ", "\nthread ") + "\n"
        luecken = run_report._abdeckung_luecken(
            md, drehbuch(["fastest-moving thread on the"], "A"))
        self.assertEqual(luecken, [])


class Luecken(unittest.TestCase):
    def test_leerer_absatz_wird_gefunden(self):
        luecken = run_report._abdeckung_luecken(
            BERICHT, drehbuch(["Fidelity banned him for volume"]))
        self.assertEqual(len(luecken), 1)
        self.assertIn("timeshare argument", luecken[0][1])

    def test_jeder_absatz_gedeckt_ist_keine_luecke(self):
        self.assertEqual(run_report._abdeckung_luecken(
            BERICHT, drehbuch(["Fidelity banned him for volume",
                               "in a timeshare argument"])), [])

    def test_unchanged_abschnitt_ist_ausgenommen(self):
        """Dieser Abschnitt bekommt laut Prompt bewusst nur zwei Stichworte;
        ihn zu flaggen kostete jeden Tag einen Nachforder-Aufruf."""
        md = BERICHT.replace("SELF-REPORTED TRACK RECORDS",
                             "UNCHANGED SINCE YESTERDAY")
        self.assertEqual(run_report._abdeckung_luecken(
            md, drehbuch(["Fidelity banned him for volume"],
                         "UNCHANGED SINCE YESTERDAY")), [])

    def test_nachtrag_nennt_die_absaetze(self):
        luecken = run_report._abdeckung_luecken(
            BERICHT, drehbuch(["Fidelity banned him for volume"]))
        text = run_report._abdeckung_nachtrag(luecken)
        self.assertIn("SELF-REPORTED TRACK RECORDS", text)
        self.assertIn("the most usable numbers", text)


class FragmentFarbe(unittest.TestCase):
    """Die Fragmente sind weiss gefuellt wie der Bulletpoint - im Grau der
    geparkten Punkte lasen sie sich als ausgegraut, obwohl sie genau das
    zeigen, was gerade gesprochen wird."""

    def test_fragmentzeile_ist_weiss(self):
        teile = szenen.detail_teile("NOG YIELD CUT: 10% TO 7%",
                                    ["Still unsourced"])
        assert teile is not None
        _, zeilen = teile
        farben = [f for f in zeilen[0].getcolors(200000) or []
                  if f[1][3] > 200]
        hellster = max(farben, key=lambda f: sum(f[1][:3]))[1][:3]
        self.assertEqual(hellster, thumbnail.TEXT_HELL[:3])

    def test_geparkte_punkte_bleiben_gedimmt(self):
        """Nur das Fragment wurde aufgehellt: in der Themen-Karte steht der
        geparkte Punkt weiterhin im gedimmten Grau."""
        self.assertNotEqual(szenen.KARTE_ALT[:3], thumbnail.TEXT_HELL[:3])
