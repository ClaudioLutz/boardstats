"""Metadaten des Uploads: Status-Felder und Tag-Qualitaet.

Hintergrund: Am 19./20.08.2026 gingen embeddable und publicStatsViewable
verloren, weil videos.update den ganzen status-part ersetzt und der Aufruf
nur privacyStatus schickte.
"""
from __future__ import annotations

import json
from unittest import mock

import video_report as v
import youtube_auth


class _Antwort:
    def read(self) -> bytes:
        return b"{}"

    def __enter__(self) -> "_Antwort":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _block(text: str) -> v.Block:
    return v.Block(art="ueberschrift", text=text)


def _status_geschrieben(vorher: dict[str, object]) -> dict[str, object]:
    """Ruft status_setzen mit gemocktem Netz auf und gibt den Body zurueck."""
    gesendet: dict[str, object] = {}

    def fake_open(req, timeout=None):  # type: ignore[no-untyped-def]
        if req.data:
            gesendet.update(json.loads(req.data.decode()))
        return _Antwort()

    with mock.patch.object(youtube_auth, "access_token", return_value="t"), \
         mock.patch.object(youtube_auth, "status_lesen", return_value=vorher), \
         mock.patch("urllib.request.urlopen", fake_open):
        youtube_auth.status_setzen("abc", "public")
    return dict(gesendet["status"])  # type: ignore[arg-type]


def test_status_setzen_erhaelt_die_uebrigen_felder() -> None:
    status = _status_geschrieben({
        "uploadStatus": "processed", "privacyStatus": "private",
        "license": "youtube", "embeddable": True,
        "publicStatsViewable": True, "madeForKids": False,
        "selfDeclaredMadeForKids": False})
    assert status["privacyStatus"] == "public"
    assert status["embeddable"] is True
    assert status["publicStatsViewable"] is True
    assert status["selfDeclaredMadeForKids"] is False
    # Nur lesbare Felder duerfen nicht mitgeschickt werden
    assert "uploadStatus" not in status
    assert "madeForKids" not in status


def test_status_setzen_faellt_auf_einbettbar_zurueck() -> None:
    """Gibt YouTube die Felder nicht zurueck, gewinnt der Kanalwunsch."""
    status = _status_geschrieben({"privacyStatus": "private"})
    assert status["embeddable"] is True
    assert status["publicStatsViewable"] is True


def test_tags_nehmen_eigennamen_statt_schlagzeilenfragment() -> None:
    titel = "KLARNA CRASHES 22%: Dip Buyers Watch $120K Vanish | /biz/ 2026-08-19"
    tags = v.tags_bauen("en", titel, [_block("STOCKS: KLARNA IS THE BODY COUNT")])
    assert "klarna" in tags
    # Die gekappte Vorschaubild-Phrase und die Schlagzeilen-Zahl taugen nicht
    assert "klarna crashes $120k" not in tags
    assert "crashes" not in tags
    assert "120k" not in tags


def test_tags_nehmen_ticker_aus_dem_bericht() -> None:
    markdown = "## STOCKS: MEMORY\n\nKlarna (KLAR) fiel, Netlist (NLST) stieg.\n"
    tags = v.tags_bauen("en", "Something Happened | /biz/ 2026-08-19", [], markdown)
    assert "klar" in tags and "nlst" in tags


def test_tags_bleiben_unter_dem_zeichenlimit() -> None:
    markdown = "\n".join(f"Firma{i} (AB{i})" for i in range(200))
    tags = v.tags_bauen("en", "AAAA BBBB CCCC | /biz/ 2026-08-19", [], markdown)
    assert sum(len(t) + 2 for t in tags) <= v.TAGS_MAX_ZEICHEN
    # Die Serien-Tags haben ein reserviertes Budget und ueberleben auch
    # einen Bericht voller Ticker
    for fest in v.FESTE_TAGS["en"]:
        assert fest in tags


def test_tags_nehmen_die_themenphrase_nach_dem_doppelpunkt() -> None:
    bloecke = [_block("STOCKS: MODERNA IS THE DAY'S PUMP"),
               _block("FILLING FAST")]
    tags = v.tags_bauen("en", "X | /biz/ 2026-08-20", bloecke)
    # Volle Phrase, Apostroph ersatzlos entfernt (kein "day s"-Fragment)
    assert "moderna is the days pump" in tags
    assert not any(" s " in t or t.endswith(" s") for t in tags)


def test_tags_nehmen_kapiteltitel_aus_folien_json() -> None:
    fdaten = {"abschnitte": [
        {"ueberschrift": "MACRO: SOVEREIGN YIELDS AT MULTI-DECADE HIGHS",
         "titel": "Yields hit multi-decade highs"},
        {"ueberschrift": "FILLING FAST",
         "titel": "Threads filling faster than usual"}]}
    tags = v.tags_bauen("en", "X | /biz/ 2026-08-20", [], "", fdaten)
    assert "yields hit multi-decade highs" in tags
    # Serienrubriken ohne Doppelpunkt-Thema bleiben draussen
    assert "threads filling faster than usual" not in tags


def test_tags_nehmen_firmennamen_vor_dem_ticker() -> None:
    markdown = "Klarna (KLAR) fiel weiter.\n"
    tags = v.tags_bauen("en", "X | /biz/ 2026-08-19", [], markdown)
    assert "klarna" in tags and "klar" in tags


def test_hook_gesprochen_laesst_klammer_ticker_weg() -> None:
    satz = v._hook_gesprochen("Moderna (MRNA) PUMPS 200%: Cancer Vaccine Hype")
    assert "(" not in satz and "MRNA" not in satz
    assert satz == "Moderna PUMPS 200%, Cancer Vaccine Hype."
