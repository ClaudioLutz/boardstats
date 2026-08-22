"""Serientitel BIZ-NEWS (C5, 22.08.2026).

Der Serientitel im Bild ist von der 4chan-Board-Notation geloest: kein
"4CHAN", keine Slash-Schreibweise. Einzige Ausnahme ist die
Zitat-Post-Karte, wo "/biz/" die Herkunftsangabe eines echten Board-Posts
ist. Die YouTube-Metadaten (Tags, Beschreibung) ziehen bewusst nicht mit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import folien
import shorts
import szenen


def test_bug_text_ist_biz_news():
    assert szenen.BUG_TEXT == "BIZ-NEWS"
    assert folien.KOPF_TEXT == "BIZ-NEWS"
    assert folien.OUTRO_TITEL == "BIZ-NEWS"
    assert shorts.KOPF_TEXT == "BIZ-NEWS"


def test_kein_4chan_label_mehr_im_bild():
    for wert in (szenen.BUG_TEXT, folien.KOPF_TEXT, folien.OUTRO_TITEL,
                 shorts.KOPF_TEXT):
        assert "4chan" not in wert.lower()
        assert "/biz/" not in wert


def test_zitat_post_behaelt_boardherkunft():
    # In der Post-Karte ist "/biz/" Herkunftsangabe, kein Serientitel -
    # der Quelltext der Funktion muss sie weiterhin setzen.
    import inspect
    quelle = inspect.getsource(szenen.zitat_post)
    assert "/biz/" in quelle


def test_metadaten_bleiben_bei_4chan():
    # Reichweitenentscheid ist getrennt: Beschreibung/Tags nennen 4chan.
    import video_report as vr
    assert "#4chan" in vr.HASHTAG_ZEILE
    assert "4chan" in vr.FESTE_TAGS["en"]
