#!/usr/bin/env python3
"""YouTube-Analytics abfragen: Tageszahlen, Video-Rangliste, Abbruchkurve.

Zweck ist die Erfolgskontrolle der Video-Aenderungen. Ohne Messung bleibt jede
Priorisierung Gefuehlssache: ob die Intro-Kuerzung wirkt, ob das Musikbett den
frueher Absprung verschiebt, ob ein Kapitelwechsel Zuschauer kostet, steht in
der Abbruchkurve und sonst nirgends.

Braucht den Scope yt-analytics.readonly im gespeicherten Token (siehe
youtube_auth.SCOPE) - nach dessen Erweiterung muss youtube_auth_setup.py
einmalig neu durchlaufen sein.

Bewusst ohne Marker-Dateien aus den Tageslaeufen: die Video-Liste kommt aus der
Analytics-API selbst, Titel und Veroeffentlichungsdatum aus der Data API. So
laeuft die Auswertung auf jedem Rechner, nicht nur auf dem Render-Rechner.

Nicht per API verfuegbar: Thumbnail-Impressionen und die Klickrate (CTR). Die
zeigt nur YouTube Studio in der Oberflaeche - fuer Thumbnail-Vergleiche bleibt
ein gelegentlicher Blick dorthin noetig.

Aufrufe:
    python3 analytics_bericht.py                  # Tageszahlen + Video-Rangliste
    python3 analytics_bericht.py --tage 60
    python3 analytics_bericht.py --kurve VIDEO_ID # Abbruchkurve eines Videos
    python3 analytics_bericht.py --kurve neuestes
    python3 analytics_bericht.py --speichern      # zusaetzlich als JSON ablegen
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import youtube_auth

log = logging.getLogger("analytics")

BERICHT_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
ABLAGE = Path(__file__).parent / "arbeit" / "analytics"

# Analytics-Daten laufen ein bis zwei Tage nach; ohne diesen Abstand steht der
# letzte Tag mit halben Zahlen in der Auswertung und sieht nach Einbruch aus.
NACHLAUF_TAGE = 2

# So weit zurueck werden bei --speichern die Abbruchkurven der juengsten
# Uploads miterhoben. Die Kurven fliessen als Rueckkopplung in die naechste
# Bericht-/Drehbuch-Generierung ein (run_report.retention_befund).
KURVEN_TAGE = 10


def _abfrage(token: str, params: dict[str, str]) -> dict:
    """Ein Analytics-Report. Fehler werden mit Klartext aus der API gemeldet."""
    req = urllib.request.Request(
        BERICHT_URL + "?" + urllib.parse.urlencode(params),
        headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        if e.code == 403 and "insufficient" in detail.lower():
            raise RuntimeError(
                "Analytics-Zugriff verweigert - traegt das Token den Scope "
                "yt-analytics.readonly? Notfalls youtube_auth_setup.py neu "
                f"ausfuehren. Antwort: {detail}") from e
        raise RuntimeError(f"Analytics-Abfrage fehlgeschlagen ({e.code}): {detail}") from e


def _zeilen(antwort: dict) -> list[dict]:
    """Macht aus columnHeaders/rows eine Liste benannter Zeilen."""
    namen = [c["name"] for c in antwort.get("columnHeaders", [])]
    return [dict(zip(namen, z)) for z in antwort.get("rows", [])]


def zeitraum(tage: int) -> tuple[str, str]:
    ende = date.today() - timedelta(days=NACHLAUF_TAGE)
    return str(ende - timedelta(days=tage)), str(ende)


def tageszahlen(token: str, tage: int = 30) -> list[dict]:
    """Aufrufe und Wiedergabedauer je Tag, aelteste zuerst."""
    von, bis = zeitraum(tage)
    antwort = _abfrage(token, {
        "ids": "channel==MINE", "startDate": von, "endDate": bis,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,"
                   "averageViewPercentage,subscribersGained",
        "dimensions": "day", "sort": "day",
    })
    return _zeilen(antwort)


def je_video(token: str, tage: int = 90, grenze: int = 50) -> list[dict]:
    """Rangliste der Videos im Zeitraum, nach Aufrufen absteigend."""
    von, bis = zeitraum(tage)
    antwort = _abfrage(token, {
        "ids": "channel==MINE", "startDate": von, "endDate": bis,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,"
                   "averageViewPercentage",
        "dimensions": "video", "sort": "-views", "maxResults": str(grenze),
    })
    zeilen = _zeilen(antwort)
    for z, meta in zip(zeilen, _video_meta(token, [z["video"] for z in zeilen])):
        z.update(meta)
    return zeilen


def _video_meta(token: str, ids: list[str]) -> list[dict]:
    """Titel, Veroeffentlichung und Laufzeit je Video-ID (Data API, 50er-Bloecke).

    Die Reihenfolge der Antwort folgt nicht der Anfrage, deshalb wird ueber die
    ID zurueckgeordnet - sonst haengen Titel am falschen Video.
    """
    gefunden: dict[str, dict] = {}
    for start in range(0, len(ids), 50):
        block = ids[start:start + 50]
        req = urllib.request.Request(
            VIDEOS_URL + "?" + urllib.parse.urlencode({
                "part": "snippet,contentDetails", "id": ",".join(block)}),
            headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            log.warning("Video-Metadaten nicht abrufbar (%s) - nur IDs", e.code)
            continue
        for eintrag in d.get("items", []):
            gefunden[eintrag["id"]] = {
                "titel": eintrag["snippet"]["title"],
                "veroeffentlicht": eintrag["snippet"]["publishedAt"][:10],
                "laufzeit": eintrag.get("contentDetails", {}).get("duration", ""),
                # Die Kapitelmarken stehen in der Beschreibung, die der
                # snippet-Part ohnehin mitliefert - sie sind die einzige
                # Quelle, gegen die sich die Abbruchkurve KAPITELWEISE lesen
                # laesst (siehe kapitel_aus_beschreibung).
                "kapitel": kapitel_aus_beschreibung(
                    eintrag["snippet"].get("description", "")),
            }
    return [gefunden.get(i, {}) for i in ids]


# Eine Kapitelzeile der YouTube-Beschreibung: "00:00 TL;DR", "07:07 Silver
# hits 70". Stunden sind zugelassen, kommen bei diesem Format aber nicht vor.
_KAPITEL_ZEILE = re.compile(r"^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s+(\S.*)$")


def kapitel_aus_beschreibung(text: str) -> list[dict]:
    """Kapitelmarken einer Videobeschreibung als [{"zeit_s", "titel"}, ...].

    YouTube verlangt fuer gueltige Kapitel eine erste Marke bei 00:00,
    mindestens drei Marken und 10 s Mindestabstand - genau das erzeugt
    video_report.kapitel_bauen(). Hier wird dieselbe Liste wieder
    eingelesen, damit die Abbruchkurve kapitelweise ausgewertet werden
    kann. Eine Beschreibung ohne solchen Block liefert [] - der Konsument
    faellt dann auf die Gesamtkurve zurueck."""
    marken: list[dict] = []
    for zeile in text.splitlines():
        m = _KAPITEL_ZEILE.match(zeile.strip())
        if not m:
            continue
        std, minute, sek, titel = m.groups()
        marken.append({"zeit_s": int(std or 0) * 3600 + int(minute) * 60
                       + int(sek), "titel": titel.strip()})
    # Erst ab der Marke bei 0 s ist es ein Kapitelblock und keine zufaellige
    # Zeitangabe im Fliesstext; die Reihenfolge muss aufsteigend sein.
    if not marken or marken[0]["zeit_s"] != 0:
        return []
    for a, b in zip(marken, marken[1:]):
        if b["zeit_s"] <= a["zeit_s"]:
            return []
    return marken if len(marken) >= 3 else []


def abbruchkurve(token: str, video_id: str, tage: int = 90) -> list[dict]:
    """Zuschauerbindung ueber die Videolaenge: 100 Stuetzpunkte, 0.0 bis 1.0.

    audienceWatchRatio ist der Anteil der Zuschauer, der diesen Punkt noch
    sieht (relativ zum Start), relativeRetentionPerformance vergleicht das mit
    aehnlich langen YouTube-Videos.
    """
    von, bis = zeitraum(tage)
    antwort = _abfrage(token, {
        "ids": "channel==MINE", "startDate": von, "endDate": bis,
        "metrics": "audienceWatchRatio,relativeRetentionPerformance",
        "dimensions": "elapsedVideoTimeRatio",
        "filters": f"video=={video_id}", "sort": "elapsedVideoTimeRatio",
    })
    return _zeilen(antwort)


def kurven_erheben(token: str, tage: int = KURVEN_TAGE) -> list[dict]:
    """Abbruchkurven aller Uploads der letzten `tage` Tage.

    Eigene je_video-Abfrage mit kurzem Fenster statt der grossen Rangliste:
    die ist Top-50 nach Aufrufen, und genau die juengsten Uploads haben die
    wenigsten Aufrufe - sie wuerden dort als erste rausfallen. zeitraum()
    endet ohnehin NACHLAUF_TAGE vor heute, juengere Videos ohne belastbare
    Kurve tauchen also gar nicht erst auf.

    Fehler je Video (geloescht, keine Bindungsdaten) kosten nur dieses eine
    Video, nie die ganze Erhebung.
    """
    heute = date.today()
    aus: list[dict] = []
    for v in sorted(je_video(token, tage=tage),
                    key=lambda v: v.get("veroeffentlicht", ""), reverse=True):
        try:
            alter = (heute - date.fromisoformat(v.get("veroeffentlicht", ""))).days
        except ValueError:
            continue    # Meta fehlt (z.B. geloeschtes Video) - keine Kurve
        if alter > tage or alter < NACHLAUF_TAGE:
            continue
        try:
            kurve = abbruchkurve(token, v["video"], tage)
        except RuntimeError as e:
            log.warning("Abbruchkurve %s nicht abrufbar: %s", v["video"], e)
            continue
        if not kurve:
            log.info("Abbruchkurve %s leer - zu wenige Aufrufe", v["video"])
            continue
        aus.append({"video_id": v["video"], "titel": v.get("titel", ""),
                    "veroeffentlicht": v.get("veroeffentlicht", ""),
                    "laufzeit_s": _sekunden(v.get("laufzeit", "")),
                    # Kapitelmarken aus der Beschreibung: erst mit ihnen
                    # laesst sich der Verlust einzelnen Kapiteln zuordnen
                    # statt nur der Laufzeit insgesamt (run_report.
                    # _kapitel_verluste). Leer, wenn das Video keine hat.
                    "kapitel": v.get("kapitel") or [],
                    # Stichprobengroesse gehoert zum Befund: bei einer
                    # Handvoll Aufrufen ist die Kurve Richtungs-, kein
                    # Praezisionssignal - der Konsument sagt das dazu.
                    "views": int(v.get("views", 0)),
                    "kurve": kurve})
    return aus


def _sekunden(iso_dauer: str) -> int:
    """ISO-8601-Dauer der Data API (PT11M4S) in Sekunden."""
    zahl, gesamt = "", 0
    for zeichen in iso_dauer.removeprefix("PT"):
        if zeichen.isdigit():
            zahl += zeichen
        elif zeichen in "HMS" and zahl:
            gesamt += int(zahl) * {"H": 3600, "M": 60, "S": 1}[zeichen]
            zahl = ""
    return gesamt


def kurve_zeigen(kurve: list[dict], laufzeit_s: int = 0) -> None:
    """Abbruchkurve als Textbalken, mit Sekundenangabe wenn die Laenge bekannt."""
    if not kurve:
        print("keine Bindungsdaten - zu wenige Aufrufe fuer dieses Video")
        return
    print(f"{'Zeit':>8}  {'Bindung':>8}  Verlauf")
    for punkt in kurve:
        anteil = punkt.get("elapsedVideoTimeRatio", 0.0)
        wert = punkt.get("audienceWatchRatio", 0.0)
        marke = (f"{int(anteil * laufzeit_s) // 60}:"
                 f"{int(anteil * laufzeit_s) % 60:02d}" if laufzeit_s
                 else f"{anteil * 100:.0f}%")
        print(f"{marke:>8}  {wert * 100:7.1f}%  {'#' * max(0, round(wert * 40))}")


def _ausgeben(tage: list[dict], videos: list[dict]) -> None:
    print("\n=== Tageszahlen ===")
    print(f"{'Tag':<12}{'Aufrufe':>9}{'Minuten':>9}{'Ø Dauer':>9}{'Ø Anteil':>10}{'Abos':>6}")
    for z in tage:
        print(f"{z.get('day',''):<12}{z.get('views',0):>9.0f}"
              f"{z.get('estimatedMinutesWatched',0):>9.0f}"
              f"{z.get('averageViewDuration',0):>8.0f}s"
              f"{z.get('averageViewPercentage',0):>9.1f}%"
              f"{z.get('subscribersGained',0):>6.0f}")
    summe = sum(z.get("views", 0) for z in tage)
    if summe:
        # Nach Aufrufen gewichtet und nur ueber Tage mit Daten: ein einfacher
        # Mittelwert ueber alle Tage zieht jeder Null-Tag nach unten und meldet
        # 3 % statt der tatsaechlichen ~27 %.
        minuten = sum(z.get("estimatedMinutesWatched", 0) for z in tage)
        schnitt = sum(z.get("averageViewPercentage", 0) * z.get("views", 0)
                      for z in tage) / summe
        print(f"{'Summe/Mittel':<12}{summe:>9.0f}{minuten:>9.0f}{'':>9}{schnitt:>9.1f}%")

    print("\n=== Videos (nach Aufrufen) ===")
    print(f"{'Datum':<12}{'Aufrufe':>8}{'Ø Anteil':>10}  {'ID':<13}Titel")
    for v in videos:
        print(f"{v.get('veroeffentlicht','?'):<12}{v.get('views',0):>8.0f}"
              f"{v.get('averageViewPercentage',0):>9.1f}%  "
              f"{v.get('video',''):<13}{v.get('titel','')[:52]}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tage", type=int, default=30, help="Zeitraum der Tageszahlen")
    p.add_argument("--video-tage", type=int, default=90, help="Zeitraum der Video-Rangliste")
    p.add_argument("--kurve", metavar="VIDEO_ID",
                   help="Abbruchkurve eines Videos ('neuestes' fuer das juengste)")
    p.add_argument("--speichern", action="store_true",
                   help=f"Ergebnis zusaetzlich unter {ABLAGE} ablegen")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    token = youtube_auth.access_token()
    tage = tageszahlen(token, args.tage)
    videos = je_video(token, args.video_tage)
    _ausgeben(tage, videos)

    kurve: list[dict] = []
    if args.kurve:
        ziel = args.kurve
        laufzeit = 0
        if ziel == "neuestes":
            nach_datum = sorted(videos, key=lambda v: v.get("veroeffentlicht", ""))
            if not nach_datum:
                raise SystemExit("keine Videos im Zeitraum")
            ziel = nach_datum[-1]["video"]
            laufzeit = _sekunden(nach_datum[-1].get("laufzeit", ""))
            print(f"\njuengstes Video: {ziel} ({nach_datum[-1].get('titel','')})")
        else:
            treffer = [v for v in videos if v.get("video") == ziel]
            laufzeit = _sekunden(treffer[0].get("laufzeit", "")) if treffer else 0
        kurve = abbruchkurve(token, ziel, args.video_tage)
        print(f"\n=== Zuschauerbindung {ziel} ===")
        kurve_zeigen(kurve, laufzeit)

    if args.speichern:
        # Kurven der juengsten Uploads immer miterheben: sie sind die
        # Rueckkopplung an run_report.py (retention_befund) und duerfen nicht
        # davon abhaengen, dass der Cron-Aufruf --kurve mitgibt.
        try:
            kurven = kurven_erheben(token)
        except RuntimeError as e:
            log.warning("Kurven-Erhebung fehlgeschlagen: %s", e)
            kurven = []
        ABLAGE.mkdir(parents=True, exist_ok=True)
        ziel_datei = ABLAGE / f"{date.today().isoformat()}.json"
        ziel_datei.write_text(json.dumps(
            {"erstellt": date.today().isoformat(), "tage": tage,
             "videos": videos, "kurve": kurve, "kurven": kurven},
            indent=2), encoding="utf-8")
        print(f"\ngespeichert: {ziel_datei} ({len(kurven)} Abbruchkurven)")


if __name__ == "__main__":
    main()
