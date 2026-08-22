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


class AnkerNachtrag(unittest.TestCase):
    """Der Nachtrag ergaenzt fehlende Stichworte, statt das Drehbuch neu
    schreiben zu lassen. Der alte Weg forderte das GANZE Drehbuch erneut an
    und verlor dabei die Abdeckung anderswo - am 22.08.2026 produktiv
    gemessen: 3 Luecken rein, 12 raus, Ergebnis verworfen."""

    def nachtrag(self, anker: list[str],
                 ueber: str = "SELF-REPORTED TRACK RECORDS") -> list:
        return [{"ueberschrift": ueber,
                 "stichworte": [{"text": "neu", "anker": a} for a in anker]}]

    def test_luecke_wird_geschlossen(self):
        d = drehbuch(["fastest-moving thread on"])
        self.assertEqual(len(run_report._abdeckung_luecken(BERICHT, d)), 1)
        ergaenzt = run_report._nachtrag_mergen(
            d, self.nachtrag(["$35k upfront, $700 maintenance"]), BERICHT)
        self.assertEqual(ergaenzt, 1)
        self.assertEqual(run_report._abdeckung_luecken(BERICHT, d), [])

    def test_nachtrag_sitzt_an_der_ankerstelle(self):
        """Die Reihenfolge traegt die Zeit - angehaengt statt einsortiert
        wuerde der Punkt am Kapitelende aufpoppen, obwohl sein Satz laengst
        gesprochen ist."""
        d = drehbuch(["An 8-year day trader", "secondhand contracts go for"])
        run_report._nachtrag_mergen(
            d, self.nachtrag(["Fidelity banned him for"]), BERICHT)
        anker = [p["anker"] for p in d["abschnitte"][0]["stichworte"]]
        self.assertEqual(anker, ["An 8-year day trader",
                                 "Fidelity banned him for",
                                 "secondhand contracts go for"])

    def test_erfundener_anker_wird_verworfen(self):
        """Ohne Fundstelle im Abschnitt gibt es keinen Zeitpunkt, an dem das
        Stichwort aufleuchten koennte."""
        d = drehbuch(["An 8-year day trader"])
        ergaenzt = run_report._nachtrag_mergen(
            d, self.nachtrag(["this phrase does not exist"]), BERICHT)
        self.assertEqual(ergaenzt, 0)
        self.assertEqual(len(d["abschnitte"][0]["stichworte"]), 1)

    def test_unbekannter_abschnitt_bleibt_folgenlos(self):
        d = drehbuch(["An 8-year day trader"])
        ergaenzt = run_report._nachtrag_mergen(
            d, self.nachtrag(["$35k upfront, $700 maintenance"],
                             ueber="EIN GANZ ANDERER ABSCHNITT"), BERICHT)
        self.assertEqual(ergaenzt, 0)
        self.assertEqual(len(d["abschnitte"][0]["stichworte"]), 1)

    def test_alte_reihenfolge_bleibt_bei_unauffindbarem_anker(self):
        """Ein bestehendes Stichwort, dessen Anker sich nicht wiederfinden
        laesst, erbt die Stelle seines Vorgaengers - es darf durch den
        Nachtrag nicht ans Kapitelende rutschen."""
        d = drehbuch(["An 8-year day trader", "nicht im Bericht",
                      "secondhand contracts go for"])
        run_report._nachtrag_mergen(
            d, self.nachtrag(["Fidelity banned him for"]), BERICHT)
        anker = [p["anker"] for p in d["abschnitte"][0]["stichworte"]]
        self.assertEqual(anker[:2], ["An 8-year day trader",
                                     "nicht im Bericht"])
        self.assertEqual(anker[-1], "secondhand contracts go for")

    def test_merge_ist_rein_additiv(self):
        """Der Kern des Umbaus: bestehende Stichworte koennen nicht
        verlorengehen, weil nur ergaenzt wird."""
        d = drehbuch(["An 8-year day trader", "secondhand contracts go for"])
        vorher = [dict(p) for p in d["abschnitte"][0]["stichworte"]]
        run_report._nachtrag_mergen(
            d, self.nachtrag(["Fidelity banned him for"]), BERICHT)
        for p in vorher:
            self.assertIn(p, d["abschnitte"][0]["stichworte"])
