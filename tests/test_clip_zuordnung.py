"""Clip-Ernte und Clip-Zuordnung: kommt genug Bewegtbild zusammen, und
landet es im Video?

Beide Seiten waren am 22.08.2026 unterversorgt. Ernte: von 18 Clip-Anhaengen
im Snapshot lagen nur 5 in den ausgewerteten Threads, und alle fuenf standen
schon im Katalog - null neue Kandidaten. Zuordnung: ein Abschnitt bekam
hoechstens einen Clip, und der trug nur die erste Szene seines Kapitels, also
3 von 50 Szenen. Mehr Bewegung ueber laengere Standzeit desselben Clips ist
ausgeschlossen (Nutzerbefund 18.08.2026), deshalb: mehr VERSCHIEDENE."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import klip_katalog            # noqa: E402
import video_report            # noqa: E402


def post(tim: int, ext: str = ".webm", **rest) -> dict:
    d = {"tim": tim, "ext": ext, "w": 640, "h": 480, "fsize": 500_000,
         "md5": f"md5-{tim}", "resto": 1}
    d.update(rest)
    return d


class ErnteAusDemGanzenSnapshot(unittest.TestCase):
    """Die Kopplung an die ausgewerteten Threads war wirkungslos - ein Clip
    wird spaeter per Beschreibung zugeordnet, nicht ueber seine Herkunft -
    und liess den Katalog verhungern."""

    MANIFEST = {"buendel": [{"thread": "111"}]}
    POSTS = {"111": [post(1)], "222": [post(2)], "333": [post(3)]}

    def kandidaten(self) -> list[dict]:
        with mock.patch.object(klip_katalog.rr, "_snapshot_posts",
                               return_value=self.POSTS) as gelesen:
            aus = klip_katalog.klip_kandidaten(self.MANIFEST)
        # None heisst "alle Threads" - genau das ist der Fix
        gelesen.assert_called_once_with(None)
        return aus

    def test_auch_threads_ausserhalb_der_auswertung(self):
        threads = [k["thread"] for k in self.kandidaten()]
        self.assertEqual(sorted(threads), ["111", "222", "333"])

    def test_ausgewertete_threads_kommen_zuerst(self):
        """Unter KLIP_MAX duerfen die Threads des Berichts nicht vom Rest
        des Boards verdraengt werden."""
        self.assertEqual(self.kandidaten()[0]["thread"], "111")

    def test_je_thread_bleibt_gedeckelt(self):
        viele = {"111": [post(i) for i in range(10)]}
        with mock.patch.object(klip_katalog.rr, "_snapshot_posts",
                               return_value=viele):
            aus = klip_katalog.klip_kandidaten({"buendel": []})
        self.assertEqual(len(aus), klip_katalog.KLIP_JE_THREAD)


class MehrereClipsJeAbschnitt(unittest.TestCase):
    """Ein Abschnitt darf bis zu KLIP_JE_ABSCHNITT verschiedene Clips
    bekommen; kein Clip zweimal, weder im selben noch in einem anderen."""

    KATALOG = {"clips": {f"m{i}": {"status": "frei", "beschreibung": f"clip {i}"}
                         for i in range(6)}}

    def zuordnen(self, antwort: str) -> dict:
        # list[Abschnitt] ist invariant; die Attrappe braucht nur .threads
        abschnitte: list = [mock.Mock(threads=["t0"]),
                            mock.Mock(threads=["t1"])]
        with mock.patch.object(klip_katalog, "katalog_laden",
                               return_value=self.KATALOG), \
             mock.patch.object(klip_katalog, "katalog_speichern"), \
             mock.patch.object(klip_katalog, "klip_datei",
                               side_effect=lambda md5, k, z: Path(f"{md5}.webm")), \
             mock.patch.object(video_report.rr, "claude_ruf",
                               return_value=antwort):
            return video_report._klip_zuordnung(
                "2026-08-22", abschnitte, {}, nur_video=True)

    def test_liste_je_abschnitt(self):
        aus = self.zuordnen('{"zuordnung": {"0": ["m0","m1"], "1": ["m2"]}}')
        self.assertEqual([p.name for p in aus[0]], ["m0.webm", "m1.webm"])
        self.assertEqual([p.name for p in aus[1]], ["m2.webm"])

    def test_deckel_je_abschnitt(self):
        aus = self.zuordnen(
            '{"zuordnung": {"0": ["m0","m1","m2","m3","m4"]}}')
        self.assertEqual(len(aus[0]), video_report.KLIP_JE_ABSCHNITT)

    def test_kein_clip_zweimal(self):
        """Dieselbe bewegte Kulisse ein zweites Mal faellt sofort auf."""
        aus = self.zuordnen('{"zuordnung": {"0": ["m0","m0"], "1": ["m0"]}}')
        self.assertEqual([p.name for p in aus[0]], ["m0.webm"])
        self.assertNotIn(1, aus)

    def test_einzelner_string_bleibt_gueltig(self):
        """Bei effort=low faellt das Modell gelegentlich auf die alte
        Antwortform zurueck - die darf nicht durchfallen."""
        aus = self.zuordnen('{"zuordnung": {"0": "m0"}}')
        self.assertEqual([p.name for p in aus[0]], ["m0.webm"])

    def test_intro_bleibt_eine_liste(self):
        aus = self.zuordnen('{"zuordnung": {}, "intro": "m5"}')
        self.assertEqual([p.name for p in aus[video_report.INTRO_KLIP_KEY]],
                         ["m5.webm"])

    def test_prompt_nennt_den_deckel(self):
        self.assertIn(str(video_report.KLIP_JE_ABSCHNITT),
                      video_report.KLIP_PROMPT_ZUORDNUNG
                      % video_report.KLIP_JE_ABSCHNITT)


if __name__ == "__main__":
    unittest.main()
