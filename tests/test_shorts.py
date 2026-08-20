"""Tages-Shorts (shorts.py): Segmentgrenzen, Kappung, Titel und Marker.

Hintergrund (20.08.2026): pro ##-Story des Berichts entsteht ein eigenes
9:16-Short, geschnitten aus der fertigen Tages-Tonspur. Die Schnittgrenzen
werden ueber die Ueberschrift-Phrasen direkt im Wortstrom lokalisiert -
bewusst nicht ueber worte_zu_bloecken, weil die Tonspur des Tages von einem
aelteren Codestand (andere Rahmen-Reihenfolge) stammen kann.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

import shorts
import video_report as vr


def _worte(text: str, ab: float = 0.0, dt: float = 0.4) -> list[vr.Wort]:
    aus = []
    t = ab
    for tok in text.split():
        aus.append(vr.Wort(tok, t, t + dt))
        t += dt
    return aus


def _bloecke() -> list[vr.Block]:
    return [
        vr.Block("absatz", "Welcome to the report.", 0, rolle="intro"),
        vr.Block("ueberschrift", "STOCKS: ALPHA RUNS HOT", 1),
        vr.Block("absatz", "Alpha ran hot all day long.", 1),
        vr.Block("punkt", "One poster disagreed loudly.", 1),
        vr.Block("ueberschrift", "MACRO: YIELDS GRIND UP", 2),
        vr.Block("absatz", "Yields ground higher again.", 2),
        vr.Block("absatz", vr.PRAES_OUTRO, 0, rolle="outro"),
    ]


# ----------------------------------------------------------- Segmentgrenzen

def test_story_grenzen_schneiden_an_ueberschrift_und_rahmen() -> None:
    grenzen = shorts.story_grenzen(_bloecke())
    assert grenzen == [(1, 4, 1), (4, 6, 2)]


def test_story_grenzen_ohne_ueberschrift_leer() -> None:
    bloecke = [vr.Block("absatz", "Nur Fliesstext.", 0)]
    assert shorts.story_grenzen(bloecke) == []


def test_stories_finden_lokalisiert_im_wortstrom() -> None:
    bloecke = _bloecke()
    worte = _worte(" ".join(b.text for b in bloecke))
    stories = shorts.stories_finden(bloecke, worte)
    assert [s.nr for s in stories] == [1, 2]
    # Story 1 beginnt mit ihrer Ueberschrift und endet vor der naechsten.
    assert stories[0].worte[0].text == "STOCKS:"
    assert stories[0].worte[-1].text == "loudly."
    # Story 2 endet vor dem Outro-Rahmensatz.
    assert stories[1].worte[-1].text == "again."


def test_stories_finden_uebersteht_fremde_rahmen_reihenfolge() -> None:
    """Die Tonspur darf einen anderen Vorspann tragen als der aktuelle
    Codestand rekonstruiert (Morgen-Audio mit Agenda, Abend-Code mit TL;DR) -
    die Storys liegen trotzdem an den Ueberschrift-Phrasen."""
    bloecke = _bloecke()
    gesprochen = ("Coming up: Alpha runs. Yields grind. "
                  "STOCKS: ALPHA RUNS HOT Alpha ran hot all day long. "
                  "One poster disagreed loudly. "
                  "MACRO: YIELDS GRIND UP Yields ground higher again. "
                  "Before we wrap up, the numbers of the day. "
                  "Alpha gained ten percent today. " + vr.PRAES_OUTRO)
    stories = shorts.stories_finden(bloecke, _worte(gesprochen))
    assert [s.nr for s in stories] == [1, 2]
    # die Zahlen-Strecke am Ende gehoert NICHT mehr zur letzten Story
    assert stories[1].worte[-1].text == "again."


def test_stories_finden_fehlende_ueberschrift_wird_uebersprungen() -> None:
    bloecke = _bloecke()
    gesprochen = ("STOCKS: ALPHA RUNS HOT Alpha ran hot all day long. "
                  "One poster disagreed loudly. " + vr.PRAES_OUTRO)
    stories = shorts.stories_finden(bloecke, _worte(gesprochen))
    assert [s.nr for s in stories] == [1]


# ----------------------------------------------------------- Aehnlichkeits-Guard

def test_text_aehnlichkeit_erkennt_fremde_tonspur() -> None:
    bloecke = _bloecke()
    passend = _worte(" ".join(b.text for b in bloecke))
    fremd = _worte("Something entirely different was spoken here today " * 20)
    assert shorts.text_aehnlichkeit(passend, bloecke) > 0.95
    assert shorts.text_aehnlichkeit(fremd, bloecke) < shorts.AEHNLICHKEIT_MIN
    assert shorts.text_aehnlichkeit([], bloecke) == 0.0


# ----------------------------------------------------------- SRT-Naeherung

def test_srt_worte_liest_cues_und_verteilt_zeiten(tmp_path: Path) -> None:
    srt = tmp_path / "u.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello brave new\nworld today\n\n"
        "2\n00:01:00,500 --> 00:01:02,000\nSecond cue\n",
        encoding="utf-8")
    worte = shorts.srt_worte(srt)
    assert [w.text for w in worte] == ["Hello", "brave", "new", "world",
                                       "today", "Second", "cue"]
    assert worte[0].start == 1.0
    assert worte[4].end <= 3.0 + 1e-6
    assert worte[5].start == 60.5
    # monoton und innerhalb der Cue-Fenster
    assert all(a.start <= a.end for a in worte)
    assert all(worte[i].start <= worte[i + 1].start
               for i in range(len(worte) - 1))


# ----------------------------------------------------------- Kappung/Titel

def test_dauer_grenzen() -> None:
    assert shorts.MIN_DAUER == 20.0
    assert shorts.MAX_DAUER <= 180.0 - 3.0   # unter dem 3-Minuten-Limit


def test_short_titel_haelt_100_zeichen() -> None:
    lang = "A" * 44  # laengster Kapiteltitel aus folien.json
    t = shorts.short_titel(lang, "MRNA", "2026-08-20")
    assert len(t) <= 100
    assert t.endswith(" | /biz/ 2026-08-20")
    assert "(MRNA)" in t
    # Ticker schon im Titel -> nicht doppeln
    t2 = shorts.short_titel("MRNA melts up", "MRNA", "2026-08-20")
    assert t2.count("MRNA") == 1
    # absurd langer Titel wird gekappt statt das Limit zu reissen
    t3 = shorts.short_titel("B" * 140, None, "2026-08-20")
    assert len(t3) <= 100


def test_short_titel_entschaerft_derbes() -> None:
    t = shorts.short_titel("Fucking chaos everywhere", None, "2026-08-20")
    assert "Fucking" not in t and "Freaking" in t


def test_ticker_finden_filtert_stopp_kuerzel() -> None:
    assert shorts.ticker_finden("Klarna (KLAR) is down") == "KLAR"
    assert shorts.ticker_finden("the identifier (CUSIP) is not one") is None
    assert shorts.ticker_finden("no ticker here") is None


def test_story_hashtag() -> None:
    assert shorts.story_hashtag("Moderna melts up", "MRNA") == "mrna"
    assert shorts.story_hashtag("Moderna melts up", None) == "moderna"
    assert shorts.story_hashtag("", None) == "biz"


def test_short_tags_story_vor_serie_und_im_budget() -> None:
    tags = shorts.short_tags(
        "Moderna melts up, everyone bickers",
        "STOCKS: MODERNA IS THE DAY'S PUMP",
        "Moderna (MRNA) ran hard. A poster compared it to Pfizer (PFE).")
    assert tags[-len(shorts.SHORT_SERIEN_TAGS):] == shorts.SHORT_SERIEN_TAGS
    assert "mrna" in tags and "moderna" in tags
    gesamt = sum(len(t) + 2 for t in tags)
    assert gesamt <= vr.TAGS_MAX_ZEICHEN + 2 * len(tags)


# ----------------------------------------------------------- Einblendungen

def test_einblendungen_start_ohne_stichworte_und_min_abstand() -> None:
    folge = shorts.einblendungen([5.0, 5.1, None, 40.0], 20.0, 60.0)
    assert folge[0].zeit == 0.0 and folge[0].stichworte == 0
    assert not folge[0].karte          # Frame 1 = Titelkarte pur
    # Abstaende mindestens MIN_STAND
    for a, b in zip(folge, folge[1:]):
        assert b.zeit - a.zeit >= shorts.MIN_STAND - 1e-9
    # am Ende sind alle 4 Stichworte und die Karte sichtbar
    assert folge[-1].stichworte == 4
    assert any(e.karte for e in folge)


def test_einblendungen_anker_ohne_fund_folgt_vorgaenger() -> None:
    folge = shorts.einblendungen([None, None], None, 30.0)
    assert folge[-1].stichworte == 2
    assert all(e.zeit < 30.0 for e in folge)


# ----------------------------------------------------------- Motiv-Hintergrund

DATUM = "2026-08-20"


def _motiv_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
               threads: dict[str, list[str]],
               werte: dict | None = None,
               typ: dict | None = None) -> Path:
    """Fake-Tag unter arbeit/motive/<datum>/ mit echten Mini-Bildern."""
    tag = tmp_path / "motive" / DATUM
    tag.mkdir(parents=True)
    for namen in threads.values():
        for n in namen:
            Image.new("RGB", (40, 30), (180, 60, 60)).save(tag / n)
    (tag / "motive.json").write_text(json.dumps(
        {"threads": threads, "werte": werte or {}, "typ": typ or {}}),
        encoding="utf-8")
    monkeypatch.setattr(vr, "HINTERGRUND_DIR", tmp_path / "motive")
    monkeypatch.setattr(vr, "MOTIV_DIR", tmp_path / "thumbs")  # leer
    return tag


def test_story_motive_folgt_kapitel_zuordnung(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story i traegt das eigene Thread-Bild ihres Abschnitts - dieselbe
    Reservierung, mit der das Hauptvideo (vr.MotivWahl) seine Kapitel belegt."""
    tag = _motiv_tag(tmp_path, monkeypatch,
                     {"111": ["a.png"], "222": ["b.png"]})
    abschnitte = [vr.Abschnitt([]), vr.Abschnitt(["111"]),
                  vr.Abschnitt(["222"])]
    motive = shorts.story_motive(DATUM, _bloecke(), abschnitte)
    assert motive == {1: tag / "a.png", 2: tag / "b.png"}
    # und identisch zur direkten Kapitel-Reservierung des Hauptvideos
    _, kapitel = vr.MotivWahl(DATUM).kapitel_reservieren(abschnitte, [1, 2])
    assert kapitel == [motive[1], motive[2]]


def test_story_motive_ohne_bilder_leer_und_ohne_tagesmotiv(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ohne freigegebene Bilder KEIN Rueckfall auf das Vorschaubild-Motiv -
    die Shorts rendern dann wie bisher auf dem Farbtheme."""
    monkeypatch.setattr(vr, "HINTERGRUND_DIR", tmp_path / "motive")
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    Image.new("RGB", (40, 30)).save(thumbs / f"{DATUM}.jpg")
    monkeypatch.setattr(vr, "MOTIV_DIR", thumbs)
    assert shorts.story_motive(DATUM, _bloecke(), [vr.Abschnitt([])] * 3) == {}


def test_story_motive_animiert_nur_mit_poster(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Animierte Motive laufen ueber ihr Posterframe; ohne Poster faellt die
    Story aufs Farbtheme zurueck (Standbild-Pipeline, kein Absturz)."""
    tag = _motiv_tag(tmp_path, monkeypatch,
                     {"111": ["a.gif"], "222": ["b.gif"]},
                     typ={"a.gif": "animiert", "b.gif": "animiert"})
    Image.new("RGB", (40, 30)).save(tag / "a_poster.png")
    (tag / "motive.json").write_text(json.dumps(
        {"threads": {"111": ["a.gif"], "222": ["b.gif"]},
         "typ": {"a.gif": "animiert", "b.gif": "animiert"},
         "poster": {"a.gif": "a_poster.png"}}), encoding="utf-8")
    abschnitte = [vr.Abschnitt([]), vr.Abschnitt(["111"]),
                  vr.Abschnitt(["222"])]
    motive = shorts.story_motive(DATUM, _bloecke(), abschnitte)
    assert motive == {1: tag / "a_poster.png"}


def test_hintergrund_bauen_croppt_formatfuellend(tmp_path: Path) -> None:
    quer = tmp_path / "quer.png"
    Image.new("RGB", (400, 100), (250, 250, 250)).save(quer)
    bild = shorts.hintergrund_bauen(quer)
    assert bild is not None and bild.size == (shorts.B, shorts.H)
    # Scrim drueckt helle Motivpartien deutlich Richtung GRUND
    px = bild.getpixel((540, 1900))
    assert isinstance(px, tuple) and max(px[:3]) < 200


def test_hintergrund_bauen_unlesbar_gibt_none(tmp_path: Path) -> None:
    kaputt = tmp_path / "kaputt.webm"
    kaputt.write_bytes(b"kein bild")
    assert shorts.hintergrund_bauen(kaputt) is None


# ----------------------------------------------------------- Marker

def test_marker_roundtrip_und_unbrauchbar(tmp_path: Path) -> None:
    pfad = tmp_path / "shorts_en.json"
    assert shorts.marker_laden(pfad) == []
    eintraege = [{"story_index": 1, "titel": "T", "video_id": "x",
                  "url": "https://youtu.be/x"}]
    shorts.marker_schreiben(pfad, eintraege)
    assert shorts.marker_laden(pfad) == eintraege
    pfad.write_text("kein json", encoding="utf-8")
    assert shorts.marker_laden(pfad) == []
