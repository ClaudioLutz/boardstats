#!/usr/bin/env python3
"""Wandelt den Klartext-Lagebericht in eine lesbare HTML-Mail.

Warum die Trennung: Das Modell soll Inhalt liefern, nicht Layout. Es schreibt
weiter Klartext (der so auch in berichte/<datum>.txt archiviert wird), und
dieses Modul macht daraus die Darstellung. Damit aendert sich das Layout, ohne
dass am Prompt geschraubt werden muss - und ein Modell, das sich im Layout
vertut, kann die Mail nicht zerstoeren.

Warum durchgehend Inline-Styles: Gmail entfernt <style>-Bloecke im Kopf
zuverlaessig, aber respektiert style-Attribute an den Elementen. Alles andere
wuerde in Gmail als unformatierter Text ankommen.
"""
from __future__ import annotations

import html
import re

URL = re.compile(r"https?://[^\s<>\"')\]]+")
THREAD_URL = re.compile(r"https?://boards\.4chan\.org/biz/thread/(\d+)")

# Eine Ueberschrift ist eine kurze Zeile ohne Satzzeichen am Ende, die keine
# Kleinbuchstaben enthaelt. Ziffern, Umlaute, Schraegstriche und Doppelpunkte
# sind erlaubt, damit "AKTIEN: SANDISK" und "/SMG/ - LAGE" erkannt werden.
def _ist_ueberschrift(z: str) -> bool:
    if not (2 < len(z) <= 90):
        return False
    if re.search(r"[a-zäöüß]", z):
        return False
    return bool(re.search(r"[A-ZÄÖÜ]{3}", z)) and not z.endswith((".", "!", "?"))


FARBE_TEXT = "#1a1a1a"
FARBE_LEISE = "#666666"
FARBE_LINIE = "#e0e0e0"
FARBE_AKZENT = "#0b5394"
SCHRIFT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
           "'Helvetica Neue',Arial,sans-serif")

P = (f"margin:0 0 14px 0;font-size:15px;line-height:1.62;color:{FARBE_TEXT};")
H2 = (f"margin:34px 0 12px 0;font-size:13px;line-height:1.4;letter-spacing:.09em;"
      f"text-transform:uppercase;color:{FARBE_AKZENT};font-weight:700;"
      f"border-bottom:2px solid {FARBE_LINIE};padding-bottom:7px;")
LI = (f"margin:0 0 8px 0;font-size:15px;line-height:1.62;color:{FARBE_TEXT};")
A = f"color:{FARBE_AKZENT};text-decoration:underline;"


def _links(text: str) -> str:
    """Setzt Links und kuerzt die langen 4chan-Adressen auf etwas Lesbares."""
    def ersetze(m: re.Match) -> str:
        u = m.group(0).rstrip(".,;:")
        schwanz = m.group(0)[len(u):]
        t = THREAD_URL.match(u)
        anzeige = f"Thread {t.group(1)}" if t else re.sub(r"^https?://(www\.)?", "", u)
        if len(anzeige) > 60:
            anzeige = anzeige[:57] + "..."
        return (f'<a href="{html.escape(u, quote=True)}" style="{A}">'
                f'{html.escape(anzeige)}</a>{html.escape(schwanz)}')

    stuecke, pos = [], 0
    for m in URL.finditer(text):
        stuecke.append(html.escape(text[pos:m.start()]))
        stuecke.append(ersetze(m))
        pos = m.end()
    stuecke.append(html.escape(text[pos:]))
    return "".join(stuecke)


def _glossar(zeilen: list[str]) -> str:
    """Das Glossar als zweispaltige Tabelle - Begriff links, Erklaerung rechts.
    Deutlich schneller zu ueberfliegen als eine Folge von Bindestrich-Zeilen."""
    reihen = []
    for z in zeilen:
        z = z.strip().lstrip("-").strip()
        if not z:
            continue
        m = re.match(r"^(.{1,45}?)\s+[-–:]\s+(.+)$", z)
        begriff, erklaerung = (m.group(1), m.group(2)) if m else ("", z)
        reihen.append(
            f'<tr>'
            f'<td style="padding:9px 14px 9px 0;vertical-align:top;font-size:14px;'
            f'font-weight:600;color:{FARBE_TEXT};white-space:nowrap;">'
            f'{html.escape(begriff)}</td>'
            f'<td style="padding:9px 0;vertical-align:top;font-size:14px;'
            f'line-height:1.55;color:{FARBE_TEXT};border-bottom:1px solid {FARBE_LINIE};">'
            f'{_links(erklaerung)}</td>'
            f'</tr>')
    if not reihen:
        return ""
    return ('<table cellpadding="0" cellspacing="0" border="0" '
            'style="width:100%;border-collapse:collapse;margin:0 0 14px 0;">'
            + "".join(reihen) + "</table>")


def zu_html(bericht: str, betreff: str = "/biz/ Lagebericht") -> str:
    zeilen = bericht.replace("\r\n", "\n").split("\n")

    kopf = ""
    if zeilen and zeilen[0].lower().startswith("datenstand"):
        kopf = zeilen[0].strip()
        zeilen = zeilen[1:]

    teile: list[str] = []
    absatz: list[str] = []
    liste: list[str] = []
    glossar: list[str] = []
    im_glossar = False

    def absatz_schliessen() -> None:
        if absatz:
            teile.append(f'<p style="{P}">{_links(" ".join(absatz))}</p>')
            absatz.clear()

    def liste_schliessen() -> None:
        if liste:
            punkte = "".join(f'<li style="{LI}">{_links(x)}</li>' for x in liste)
            teile.append(f'<ul style="margin:0 0 16px 0;padding-left:22px;">{punkte}</ul>')
            liste.clear()

    for z in zeilen:
        roh = z.rstrip()
        z = roh.strip()
        if not z:
            absatz_schliessen()
            liste_schliessen()
            continue
        if _ist_ueberschrift(z):
            absatz_schliessen()
            liste_schliessen()
            im_glossar = z.startswith("GLOSSAR")
            teile.append(f'<h2 style="{H2}">{html.escape(z)}</h2>')
            continue
        if im_glossar:
            glossar.append(z)
            continue
        if re.match(r"^[-•*]\s+", z) or re.match(r"^\d{1,2}[.)]\s+", z):
            absatz_schliessen()
            liste.append(re.sub(r"^([-•*]|\d{1,2}[.)])\s+", "", z))
            continue
        liste_schliessen()
        absatz.append(z)

    absatz_schliessen()
    liste_schliessen()
    if glossar:
        teile.append(_glossar(glossar))

    kopfblock = ""
    if kopf:
        kopfblock = (
            f'<div style="margin:0 0 26px 0;padding:13px 16px;background:#f5f7fa;'
            f'border-left:3px solid {FARBE_AKZENT};font-size:13px;line-height:1.5;'
            f'color:{FARBE_LEISE};">{html.escape(kopf)}</div>')

    return (
        f'<div style="margin:0;padding:0;background:#ffffff;">'
        f'<div style="max-width:680px;margin:0 auto;padding:26px 22px 34px 22px;'
        f'font-family:{SCHRIFT};">'
        f'<div style="font-size:19px;font-weight:700;color:{FARBE_TEXT};'
        f'margin:0 0 4px 0;">{html.escape(betreff)}</div>'
        f'<div style="height:3px;width:46px;background:{FARBE_AKZENT};'
        f'margin:0 0 20px 0;"></div>'
        f'{kopfblock}{"".join(teile)}'
        f'<div style="margin-top:34px;padding-top:13px;border-top:1px solid {FARBE_LINIE};'
        f'font-size:12px;line-height:1.5;color:{FARBE_LEISE};">'
        f'Automatisch erstellt aus oeffentlichen Beitraegen des Boards /biz/. '
        f'Aussagen von Postern sind Behauptungen, keine Anlageberatung.'
        f'</div></div></div>')


if __name__ == "__main__":
    import sys
    from pathlib import Path
    if len(sys.argv) < 2:
        raise SystemExit("Aufruf: bericht_html.py <berichtsdatei> [ausgabe.html]")
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    ziel = Path(sys.argv[2] if len(sys.argv) > 2 else "vorschau.html")
    ziel.write_text(zu_html(text), encoding="utf-8")
    print(f"{ziel} geschrieben ({ziel.stat().st_size} Bytes)")
