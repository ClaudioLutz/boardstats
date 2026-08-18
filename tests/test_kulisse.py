#!/usr/bin/env python3
"""Tests fuer die Kulisse des Videos - Sichtpruefung und Bildpool.

Anlass ist der Ausfall am 16.08.2026 abends und am 18.08.2026 morgens: die
Sichtpruefung pruefte alle 36 Hintergrundbilder in einem Aufruf und verwarf
die komplette Freigabe, sobald zwei Urteile dieselbe Beschreibung trugen.
Damit entstand kein motive.json, der Bildpool des Video-Laufs war leer, und
alle 70 Szenen liefen mit demselben Vorschaubild-Motiv - ein zehnminuetiges
Video aus einem einzigen Bild.

Geprueft werden beide Schichten des Fixes und die Sicherheitseigenschaft, die
dabei nicht verloren gehen darf: ein Urteil ohne Beleg fuers Hinsehen fuehrt
nie zu einer Freigabe.

Lauf:  python -m unittest discover -s tests
       (stdlib statt pytest - hp-ubuntu hat kein pytest, und die Tests sollen
       auf beiden Systemen laufen)
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_report            # noqa: E402
import video_report          # noqa: E402


def _urteil(name: str, beschreibung: str, ok: bool = True) -> dict:
    return {"datei": name, "beschreibung": beschreibung, "ok": ok,
            "grund": "", "bildlich": 4, "unterhaltung": 4, "themen": 3}


def _antwort(urteile: list[dict]) -> str:
    return json.dumps({"bilder": urteile})


class SichtAntwort(unittest.TestCase):
    """Das Netz gegen ungesehene Urteile (_sicht_antwort)."""

    def _pruefe(self, urteile: list[dict], anzahl: int, duldung: float = 0.0):
        bilder = [Path(f"b{i}.jpg") for i in range(anzahl)]
        with mock.patch.object(run_report, "claude_ruf",
                               return_value=_antwort(urteile)):
            return run_report._sicht_antwort("p", bilder, "e", 10, duldung)

    def test_strikt_verwirft_doppelte_beschreibung(self):
        """Vorschaubild: alles-oder-nichts bleibt, ein ungepruefter
        Kanalanstrich kostet im schlimmsten Fall den Kanal."""
        urteile = [_urteil("b0.jpg", "ein gruener Frosch am Handelsschirm"),
                   _urteil("b1.jpg", "ein gruener Frosch am Handelsschirm")]
        with self.assertRaises(RuntimeError):
            self._pruefe(urteile, 2)

    def test_strikt_verwirft_leere_beschreibung(self):
        urteile = [_urteil("b0.jpg", "ein gruener Frosch am Handelsschirm"),
                   _urteil("b1.jpg", "kurz")]
        with self.assertRaises(RuntimeError):
            self._pruefe(urteile, 2)

    def test_duldung_haelt_die_uebrigen_urteile(self):
        """Der eigentliche Fix: ein doppeltes Paar kostet zwei Bilder,
        nicht den ganzen Stapel."""
        urteile = [_urteil(f"b{i}.jpg", f"Bild Nummer {i} mit viel Beschreibung")
                   for i in range(12)]
        urteile[3]["beschreibung"] = urteile[7]["beschreibung"]
        daten = self._pruefe(urteile, 12, duldung=0.34)
        verdacht = [u["datei"] for u in daten["bilder"] if u.get("_verdacht")]
        self.assertEqual(sorted(verdacht), ["b3.jpg", "b7.jpg"])
        self.assertEqual(len([u for u in daten["bilder"]
                              if not u.get("_verdacht")]), 10)

    def test_duldung_kippt_bei_flaechendeckendem_verdacht(self):
        """Zehn gleiche Beschreibungen sind kein Ausrutscher, sondern eine
        Antwort, die nichts gesehen hat - die bleibt ein Fehler."""
        urteile = [_urteil(f"b{i}.jpg", "irgendein Bild mit langem Text")
                   for i in range(10)]
        urteile += [_urteil(f"b{i}.jpg", f"eigenes Bild Nummer {i} hier")
                    for i in (10, 11)]
        with self.assertRaises(RuntimeError):
            self._pruefe(urteile, 12, duldung=0.34)

    def test_unvollstaendige_antwort_bleibt_fehler(self):
        urteile = [_urteil("b0.jpg", "ein gruener Frosch am Handelsschirm")]
        with self.assertRaises(RuntimeError):
            self._pruefe(urteile, 3, duldung=0.34)


class HintergrundPruefen(unittest.TestCase):
    """Die Stapel-Pruefung der Hintergrundbilder."""

    def setUp(self):
        self.bilder = [Path(f"6250{i // 4}-{i}.jpg") for i in range(25)]
        self.aufrufe = 0

    def _antworten(self, kaputter_stapel: int | None = None):
        """Antwortet je Aufruf passend zu den Bildern des Stapels; der
        genannte Stapel (1-basiert) liefert eine unbrauchbare Antwort."""
        def ruf(prompt, eingabe, modell, timeout, **kw):
            self.aufrufe += 1
            namen = [z.split(":")[0].lstrip("- ").strip()
                     for z in eingabe.splitlines()[1:]]
            if self.aufrufe == kaputter_stapel:
                return _antwort([_urteil(n, "immer dieselbe Beschreibung hier")
                                 for n in namen])
            return _antwort([_urteil(n, f"Bild {n} zeigt einen Chart mit Zahlen")
                             for n in namen])
        return ruf

    def test_stapelgroesse(self):
        with mock.patch.object(run_report, "claude_ruf",
                               side_effect=self._antworten()):
            frei, gruende = run_report.hintergrund_pruefen(self.bilder)
        self.assertEqual(self.aufrufe, 3)       # 12 + 12 + 1
        self.assertEqual(len(frei), 25)

    def test_kaputter_stapel_kostet_nur_seine_bilder(self):
        """Die Regression vom 18.08.2026: vorher war die ganze Freigabe weg,
        jetzt ueberleben die anderen Stapel."""
        with mock.patch.object(run_report, "claude_ruf",
                               side_effect=self._antworten(kaputter_stapel=1)):
            frei, gruende = run_report.hintergrund_pruefen(self.bilder)
        self.assertEqual(len(frei), 13)
        self.assertNotIn(self.bilder[0], frei)
        self.assertIn(self.bilder[12], frei)
        # Auch ein verworfener Stapel muss einen Grund je Bild hinterlassen,
        # sonst stehen zwoelf Bilder ohne Erklaerung im Ablehnungsordner.
        self.assertEqual(len(gruende), 12)
        self.assertIn("Stapel verworfen", gruende[self.bilder[0]])

    def test_verdaechtiges_urteil_wird_nie_freigegeben(self):
        """Sicherheitseigenschaft: ohne Beleg fuers Hinsehen keine Freigabe -
        auch wenn das Urteil selbst 'ok' sagt."""
        bilder = [Path(f"1-{i}.jpg") for i in range(8)]
        urteile = [_urteil(p.name, f"Bild {p.name} zeigt einen Frosch am Chart")
                   for p in bilder]
        urteile[0]["beschreibung"] = urteile[1]["beschreibung"]
        with mock.patch.object(run_report, "claude_ruf",
                               return_value=_antwort(urteile)):
            frei, gruende = run_report.hintergrund_pruefen(bilder)
        self.assertEqual(set(frei), set(bilder[2:]))
        self.assertEqual(set(gruende), {bilder[0], bilder[1]})
        self.assertIn("doppelt", gruende[bilder[0]])

    def test_alle_stapel_tot_ist_ein_fehler(self):
        """Kein leeres Ergebnis zurueckgeben: hintergruende_waehlen wuerde
        sonst ein leeres motive.json schreiben, der Tag gaelte als versorgt
        und der Rueckgriff im Video-Lauf wuerde nicht greifen."""
        with mock.patch.object(run_report, "claude_ruf",
                               return_value="kein JSON"):
            with self.assertRaises(RuntimeError):
                run_report.hintergrund_pruefen(self.bilder)

    def test_ablehnung_bleibt_ablehnung(self):
        bilder = [Path(f"1-{i}.jpg") for i in range(3)]
        urteile = [_urteil(p.name, f"Bild {p.name} zeigt einen Frosch am Chart")
                   for p in bilder]
        urteile[1]["ok"] = False
        urteile[1]["grund"] = "Slur im Bildtext"
        with mock.patch.object(run_report, "claude_ruf",
                               return_value=_antwort(urteile)):
            frei, gruende = run_report.hintergrund_pruefen(bilder)
        self.assertEqual(set(frei), {bilder[0], bilder[2]})
        self.assertEqual(gruende[bilder[1]], "Slur im Bildtext")


class AblehnungAblegen(unittest.TestCase):
    """Abgelehnte Bilder bleiben mit Grund im Dateinamen liegen, damit die
    Sichtpruefung gegengeprueft werden kann (Nutzerwunsch 18.08.2026)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.arbeit = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(run_report, "ARBEIT", self.arbeit),
            mock.patch.object(run_report, "VERWENDET_DATEI",
                              self.arbeit / "motive" / "verwendet.json"),
        ]
        for pa in self.patches:
            pa.start()

    def tearDown(self):
        for pa in self.patches:
            pa.stop()
        self.tmp.cleanup()

    def _lauf(self, urteile_bauen):
        """hintergruende_waehlen mit erfundenen Kandidaten laufen lassen:
        der Download wird ersetzt, die Sichtpruefung antwortet gemockt."""
        namen = ["11-a.jpg", "11-b.png", "22-c.jpg"]
        kandidaten = [{"thread": n.split("-")[0], "datei": n,
                       "url": f"http://x/{n}", "md5": f"md5{i}"}
                      for i, n in enumerate(namen)]

        def laden(kand, ziel_dir):
            ziel_dir.mkdir(parents=True, exist_ok=True)
            pfade = []
            for k in kand:
                ziel = ziel_dir / k["datei"]
                ziel.write_bytes(b"bild")
                pfade.append(ziel)
            return pfade

        with mock.patch.object(run_report, "hintergrund_kandidaten",
                              return_value=kandidaten),              mock.patch.object(run_report, "motiv_laden", side_effect=laden),              mock.patch.object(run_report, "claude_ruf",
                               return_value=_antwort(urteile_bauen(namen))):
            frei = run_report.hintergruende_waehlen({}, "2026-08-18")
        ordner = self.arbeit / "motive" / "2026-08-18"
        daten = json.loads((ordner / "motive.json").read_text(encoding="utf-8"))
        return frei, ordner, daten

    def test_abgelehntes_bild_liegt_mit_grund_im_ordner(self):
        def bauen(namen):
            urteile = [_urteil(n, f"Bild {n} zeigt einen Frosch am Chart")
                       for n in namen]
            urteile[1]["ok"] = False
            urteile[1]["grund"] = "Slur im Bildtext gross sichtbar"
            return urteile
        frei, ordner, daten = self._lauf(bauen)
        self.assertEqual(frei, 2)
        self.assertEqual(list((ordner / "abgelehnt").iterdir()),
                         [ordner / "abgelehnt"
                          / "11-b__slur-im-bildtext-gross-sichtbar.png"])
        self.assertEqual(daten["abgelehnt"],
                         {"11-b.png": "Slur im Bildtext gross sichtbar"})
        # Das freigegebene Bild bleibt, wo der Video-Lauf es erwartet.
        self.assertTrue((ordner / "11-a.jpg").exists())
        self.assertEqual(sorted(daten["threads"]), ["11", "22"])

    def test_kein_ablehnungsordner_wenn_alles_durchgeht(self):
        def bauen(namen):
            return [_urteil(n, f"Bild {n} zeigt einen Frosch am Chart")
                    for n in namen]
        frei, ordner, daten = self._lauf(bauen)
        self.assertEqual(frei, 3)
        self.assertFalse((ordner / "abgelehnt").exists())
        self.assertEqual(daten["abgelehnt"], {})


class MotivQuelle(unittest.TestCase):
    """Der Bildpool des Video-Laufs samt Rueckgriff auf die Vortage."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.patch = mock.patch.object(video_report, "HINTERGRUND_DIR",
                                       self.dir)
        self.patch.start()
        video_report._quelle_gemeldet.clear()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _tag(self, datum: str, threads: dict[str, list[str]],
             dateien: bool = True, werte: dict | None = None) -> Path:
        ordner = self.dir / datum
        ordner.mkdir(parents=True, exist_ok=True)
        if dateien:
            for namen in threads.values():
                for n in namen:
                    (ordner / n).write_bytes(b"bild")
        (ordner / "motive.json").write_text(json.dumps(
            {"threads": threads, "werte": werte or {}}), encoding="utf-8")
        return ordner

    def test_eigener_tag_hat_vorrang(self):
        self._tag("2026-08-17", {"1": ["1-a.jpg"]})
        self._tag("2026-08-18", {"2": ["2-b.jpg"]})
        zu = video_report.motiv_zuordnung("2026-08-18")
        self.assertEqual(list(zu), ["2"])
        self.assertEqual(zu["2"][0].parent.name, "2026-08-18")

    def test_fehlendes_motive_json_greift_auf_vortag_zurueck(self):
        """Die Regression vom 18.08.2026: die Sichtpruefung des Tages
        scheiterte, der Ordner blieb ohne motive.json - vorher war der Pool
        leer und jede Szene nahm dasselbe Tagesmotiv."""
        self._tag("2026-08-17", {"1": ["1-a.jpg", "1-b.jpg"]})
        (self.dir / "2026-08-18").mkdir()
        zu = video_report.motiv_zuordnung("2026-08-18")
        self.assertTrue(zu, "Rueckgriff auf den Vortag hat nicht gegriffen")
        pfade = [p for liste in zu.values() for p in liste]
        self.assertEqual(len(pfade), 2)
        self.assertTrue(all(p.parent.name == "2026-08-17" for p in pfade))

    def test_leeres_motive_json_gilt_nicht_als_versorgt(self):
        self._tag("2026-08-16", {"1": ["1-a.jpg"]})
        self._tag("2026-08-18", {})
        zu = video_report.motiv_zuordnung("2026-08-18")
        self.assertEqual([p.parent.name for liste in zu.values()
                          for p in liste], ["2026-08-16"])

    def test_verwaistes_motive_json_gilt_nicht_als_versorgt(self):
        """motive.json nennt Dateien, die nicht (mehr) da sind."""
        self._tag("2026-08-16", {"1": ["1-a.jpg"]})
        self._tag("2026-08-18", {"9": ["9-weg.jpg"]}, dateien=False)
        zu = video_report.motiv_zuordnung("2026-08-18")
        self.assertEqual([p.parent.name for liste in zu.values()
                          for p in liste], ["2026-08-16"])

    def test_rueckgriff_endet_nach_sieben_tagen(self):
        self._tag("2026-08-01", {"1": ["1-a.jpg"]})
        (self.dir / "2026-08-18").mkdir()
        self.assertEqual(video_report.motiv_zuordnung("2026-08-18"), {})

    def test_werte_und_bilder_kommen_vom_selben_tag(self):
        """Sonst sortiert der Video-Lauf die Bilder von gestern nach den
        Bewertungen von heute - und haelt Motive fuer Textwaende."""
        self._tag("2026-08-17", {"1": ["1-a.jpg"]},
                  werte={"1-a.jpg": {"bildlich": 5, "unterhaltung": 5,
                                     "themen": 3}})
        (self.dir / "2026-08-18").mkdir()
        werte = video_report.motiv_werte("2026-08-18")
        self.assertEqual(werte["1-a.jpg"]["bildlich"], 5)
        quelle = video_report.motiv_quelle("2026-08-18")
        assert quelle is not None
        self.assertEqual(quelle[0].name, "2026-08-17")

    def test_bildrang_sortiert_motive_vor_textwaenden(self):
        """Innerhalb eines Threads steht das echte Motiv vor dem
        Text-Screenshot - das ist die Reihenfolge, in der der Szenenbau
        zugreift."""
        self._tag("2026-08-18", {"1": ["1-textwand.jpg", "1-frosch.jpg"]},
                  werte={"1-textwand.jpg": {"bildlich": 1, "unterhaltung": 1,
                                            "themen": 5},
                         "1-frosch.jpg": {"bildlich": 5, "unterhaltung": 5,
                                          "themen": 1}})
        zu = video_report.motiv_zuordnung("2026-08-18")
        self.assertEqual([p.name for p in zu["1"]],
                         ["1-frosch.jpg", "1-textwand.jpg"])


if __name__ == "__main__":
    unittest.main()
