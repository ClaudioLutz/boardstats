#!/usr/bin/env python3
"""WebM/MP4-Clip-Katalog fuer die Video-Kulisse (Schritt 2 aus
research/recherche-biz-videos-2026-08-18.md, GIF war Schritt 1).

Anders als arbeit/motive/<datum>/motive.json (pro Tag neu geschrieben) ist
arbeit/clips/katalog.json KUMULATIV: einmal per Sichtpruefung bewertete
Clips (per MD5 des 4chan-Posts) behalten ihr Urteil ueber Tage hinweg, auch
wenn die Rohdatei laengst von klip_bereinigen() geloescht wurde - ein
wiederkehrender Clip aus einem langlebigen Thread muss dann nicht erneut
sichtgeprueft werden. Fehlt die Rohdatei bei tatsaechlichem Bedarf, laedt
klip_datei() sie ueber die im Katalog gemerkte URL erneut nach.

Wiederverwendet aus run_report.py statt dupliziert: _sicht_antwort() (das
Netz gegen ungesehene Urteile), _snapshot_posts(), _grund_slug(),
BILD_BASIS/BILD_HEADERS, ARBEIT, log."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import run_report as rr

KLIP_ENDUNGEN = (".webm", ".mp4")
KLIP_MAGIC_WEBM = b"\x1a\x45\xdf\xa3"
KLIP_MIN_BREITE = 300   # Videoanhaenge sind oft kleiner als Bild-Motive -
KLIP_MIN_HOEHE = 200    # lockerer als MOTIV_MIN_BREITE/HOEHE
KLIP_MAX_BYTES = 16_000_000
KLIP_MAX_SEKUNDEN = 30.0   # laenger wird verworfen statt gekuerzt - klein
                           # gehalten, damit KLIP_FRAMES_MAX das Sekunden-
                           # raster nicht ausduennt (siehe unten) UND ein
                           # Sichtpruefungs-Stapel nicht so gross wird, dass
                           # die Antwort unvollstaendig zurueckkommt
                           # (beobachtet 18.08.2026 bei laengeren Clips)
KLIP_JE_THREAD = 3
KLIP_MAX = 24              # Gesamtdeckel NEUER Kandidaten je Lauf
KLIP_FRAME_ABSTAND = 5.0   # Sicherheitsauflage der Recherche 18.08.2026:
                           # "frameweise (Sekundenraster, nicht Stichprobe)"
                           # - hoechstens so viele Sekunden bleiben zwischen
                           # zwei Pruefpunkten ungesehen, statt bei jedem
                           # Clip nur Start/Mitte/Ende zu zeigen
KLIP_FRAMES_MIN = 3
KLIP_FRAMES_MAX = 8        # Deckel gegen einen einzelnen ueberlangen Clip,
                           # der einen ganzen Sichtpruefungs-Stapel fuellt
KLIP_STAPEL = 8            # Frames je Sichtpruefungs-Aufruf - bewusst klein:
                           # ein groesserer Testlauf zeigte, dass die
                           # Antwort bei zu vielen Frames auf einmal
                           # unvollstaendig zurueckkommt (faellt sicher auf
                           # Ablehnung, kostet aber Ausbeute). Faktisch
                           # meist ein Clip je Aufruf statt mehrerer.
KLIP_DULDUNG = 0.34        # wie HG_DULDUNG - siehe run_report._sicht_antwort
TIMEOUT_KLIP = 300

KLIP_DIR = rr.ARBEIT / "clips"
KLIP_KATALOG_DATEI = KLIP_DIR / "katalog.json"

KLIP_PROMPT = """\
Du prüfst Standbilder aus kurzen, TONLOSEN Videoclips (WebM/MP4) fürs den
Videohintergrund eines Nachrichtenvideos über das 4chan-Board /biz/. Das ist
ein "blue board", auf dem die Moderation nicht jugendfreies Material
entfernt; grob Anstössiges ist dort die Ausnahme. Die Clips laufen als
bewegte Kulisse HINTER dem Untertiteltext. Es geht darum, ob ein Clip
öffentlich gezeigt werden darf - nicht darum, ob er schön ist oder zum
Thema passt.

Sieh dir JEDES unten genannte Bild mit dem Read-Werkzeug an. Urteile nur
nach dem, was du wirklich siehst, und rate nichts.

Jede Datei ist ein einzelnes extrahiertes Standbild aus einem Clip zu einem
bestimmten Zeitpunkt. Dateien mit demselben Namen vor "__f" (z. B.
"123-456__f0.png", "123-456__f1.png") stammen aus DEMSELBEN Clip - kein
eigenstaendiges Bild je Frame. Eine wortgleiche Beschreibung mehrerer Frames
desselben Clips ist in Ordnung, wortgleiche Beschreibungen über
VERSCHIEDENE Clips hinweg sind es nicht.

Ein Clip ist NUR dann ungeeignet, wenn er gegen die YouTube-Richtlinien
verstösst: Nacktheit oder Sexualisiertes, Gewalt oder Blut, Hass- oder
Extremismus-Symbolik, Drogen, grobe Beschimpfungen oder Slurs im Bildtext,
eine reale Person in kompromittierender Lage. Nur bei dieser Frage gilt im
Zweifel Ablehnung. ALLES andere ist geeignet.

Gib NUR ein JSON-Objekt aus, ohne Vor- oder Nachbemerkungen und ohne
Code-Zaun. Die Beschreibung ist Pflicht, sachlich und kurz (max. 20 Woerter)
- sie dient spaeter dazu, den Clip inhaltlich einem Berichtsabschnitt
zuzuordnen, nicht nur der Sichtpruefung:
{"bilder": [{"datei": "...", "beschreibung": "...", "ok": true,
"grund": "..."}]}
"""


def klip_kandidaten(manifest: dict) -> list[dict]:
    """WebM/MP4-Anhaenge des GANZEN Snapshots, je Thread bis zu
    KLIP_JE_THREAD Stueck (OP-Anhaenge zuerst). Dieselben mechanischen
    Filter wie bei Hintergrundbildern (siehe hintergrund_kandidaten), nur
    mit eigenen Format-/Groessen-Grenzen.

    Bis zum 22.08.2026 wurden nur die ausgewerteten Threads geerntet - und
    daran verhungerte der Katalog. Messung an jenem Tag: 18 Clip-Anhaenge im
    Snapshot, davon lagen **5** in den 16 ausgewerteten Threads, und alle
    fuenf standen schon im Katalog; neue Kandidaten also null. Der Verbrauch
    liegt bei bis zu 9 Clips taeglich (Kapitel plus Intro), die Sperre
    (rr.VERWENDET_TAGE) haelt sie 5 Tage fest - noetig waere ein Pool von
    rund 45, vorhanden waren 29 freie, davon 11 nicht gesperrt.

    Die Kopplung an die ausgewerteten Threads war ohnehin ohne Wirkung: ein
    Clip wird nicht ueber seine Herkunft eingesetzt, sondern spaeter per
    LLM ueber seine Beschreibung einem Abschnitt zugeordnet
    (video_report._klip_zuordnung). Die ausgewerteten Threads kommen
    trotzdem zuerst, damit sie unter KLIP_MAX nicht verdraengt werden."""
    bevorzugt = [str(b["thread"]) for b in manifest.get("buendel", [])]
    posts = rr._snapshot_posts(None)
    threads = bevorzugt + [no for no in posts if no not in set(bevorzugt)]
    gesehen: set[str] = set()
    aus: list[dict] = []
    for no in threads:
        sortiert = sorted(posts.get(no, []),
                          key=lambda p: (p.get("resto") or 0) != 0)
        gefunden = 0
        for post in sortiert:
            if gefunden >= KLIP_JE_THREAD:
                break
            tim, ext = post.get("tim"), str(post.get("ext") or "").lower()
            if not tim or ext not in KLIP_ENDUNGEN:
                continue
            if post.get("spoiler") or post.get("filedeleted"):
                continue
            breite, hoehe = post.get("w") or 0, post.get("h") or 0
            if (breite < KLIP_MIN_BREITE or hoehe < KLIP_MIN_HOEHE
                    or (post.get("fsize") or 0) > KLIP_MAX_BYTES):
                continue
            md5 = str(post.get("md5") or tim)
            if md5 in gesehen:
                continue
            gesehen.add(md5)
            aus.append({"thread": no, "datei": f"{no}-{tim}{ext}",
                        "url": f"{rr.BILD_BASIS}/{tim}{ext}", "md5": md5})
            gefunden += 1
    return aus[:KLIP_MAX]


def _klip_laden(kandidaten: list[dict], ziel_dir: Path) -> list[Path]:
    """Download analog run_report.motiv_laden, mit Magic-Bytes-Pruefung
    fuer WebM (EBML-Header) und MP4 (ftyp-Box ab Offset 4) statt
    MOTIV_MAGIC."""
    ziel_dir.mkdir(parents=True, exist_ok=True)
    geladen: list[Path] = []
    for k in kandidaten:
        try:
            req = urllib.request.Request(k["url"], headers=rr.BILD_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                daten = resp.read(KLIP_MAX_BYTES + 1)
        except Exception as e:
            rr.log.info("Clip %s nicht geladen: %s", k["datei"], e)
            continue
        finally:
            time.sleep(1.0)
        if len(daten) > KLIP_MAX_BYTES:
            continue
        if not (daten.startswith(KLIP_MAGIC_WEBM) or daten[4:8] == b"ftyp"):
            continue
        ziel = ziel_dir / k["datei"]
        ziel.write_bytes(daten)
        geladen.append(ziel)
    return geladen


def _klip_metadaten(pfad: Path) -> dict | None:
    """Dauer/Aufloesung/Framerate per ffprobe - None bei kaputten Dateien
    oder wenn ffprobe fehlt. Einziger ffprobe-Aufruf im Projekt bisher war
    video_report._mp3_dauer() (reine Audiodauer); dieser hier liest
    zusaetzlich den ersten Videostream."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "format=duration:stream=width,height,"
                              "avg_frame_rate",
             "-of", "json", str(pfad)],
            check=True, timeout=30, capture_output=True, text=True).stdout
        daten = json.loads(out)
        dauer = float((daten.get("format") or {}).get("duration") or 0.0)
        streams = daten.get("streams") or [{}]
        s0 = streams[0] if streams else {}
        breite = int(s0.get("width") or 0)
        hoehe = int(s0.get("height") or 0)
        num, _, den = str(s0.get("avg_frame_rate") or "0/1").partition("/")
        fps = (float(num) / float(den)) if den and float(den) else 0.0
        if dauer <= 0 or breite <= 0 or hoehe <= 0:
            return None
        return {"dauer_s": dauer, "breite": breite, "hoehe": hoehe, "fps": fps}
    except Exception as e:
        rr.log.info("Clip %s: ffprobe fehlgeschlagen: %s", pfad.name, e)
        return None


def _klip_frames_fuer_pruefung(pfad: Path, dauer: float, ziel_dir: Path,
                               stem: str) -> list[Path]:
    """Pruefframes im echten Sekundenraster statt einer Drei-Punkte-
    Stichprobe: die Anzahl waechst mit der Clipdauer (ein Frame je
    KLIP_FRAME_ABSTAND Sekunden), gedeckelt bei KLIP_FRAMES_MAX. Ohne diese
    Skalierung bliebe bei KLIP_MAX_SEKUNDEN=60 und nur 3 Frames bis zu 28s
    am Stueck ungesehen - genau das verbietet die Sicherheitsauflage der
    Recherche vom 18.08.2026 ("frameweise, nicht Stichprobe")."""
    ziel_dir.mkdir(parents=True, exist_ok=True)
    n = max(KLIP_FRAMES_MIN,
           min(KLIP_FRAMES_MAX, math.ceil(dauer / KLIP_FRAME_ABSTAND) + 1))
    if n <= 1 or dauer <= 0:
        punkte = [0.0]
    else:
        # Der letzte Punkt liegt sonst exakt auf der von ffprobe gemeldeten
        # Dauer - dort liefert ffmpeg -ss haeufig Exit-Code 0, aber gar
        # keine Datei (EOF-Randfall, kein decodierbares Frame mehr). Ein
        # kleiner Sicherheitsabstand vor dem Ende umgeht das.
        ende = max(0.0, dauer - min(0.1, dauer * 0.02))
        punkte = sorted({round(ende * i / (n - 1), 2) for i in range(n)})
    aus: list[Path] = []
    for i, t in enumerate(punkte):
        ziel = ziel_dir / f"{stem}__f{i}.png"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}",
                 "-i", str(pfad), "-frames:v", "1", "-q:v", "2", str(ziel)],
                check=True, timeout=30, capture_output=True)
            if not ziel.exists() or ziel.stat().st_size == 0:
                raise RuntimeError("ffmpeg lieferte Exit 0, aber keine Datei "
                                   "(EOF-Randfall)")
            aus.append(ziel)
        except Exception as e:
            rr.log.info("Clip %s: Frame bei %.2fs fehlgeschlagen: %s",
                       stem, t, e)
    return aus


def klip_pruefen(
        clips: list[Path], frames: dict[Path, list[Path]],
) -> tuple[dict[Path, str], dict[Path, str]]:
    """Sichtpruefung wie run_report.hintergrund_pruefen (gleiches Stapel-
    und Alle-Frames-ok-Prinzip), aber das Ergebnis ist eine Beschreibung
    statt Bewertungszahlen: Clips werden spaeter inhaltlich (per LLM-
    Zuordnung), nicht nach Bild-Rang zugeordnet."""
    frei: dict[Path, str] = {}
    gruende: dict[Path, str] = {}
    gruppen = [(p, frames.get(p) or []) for p in clips]
    for p, fr in gruppen:
        if not fr:
            gruende[p] = "keine Pruefframes extrahiert"
    gruppen = [(p, fr) for p, fr in gruppen if fr]
    stapel: list[list[tuple[Path, list[Path]]]] = []
    aktuell: list[tuple[Path, list[Path]]] = []
    aktuell_n = 0
    for gruppe in gruppen:
        n = len(gruppe[1])
        if aktuell and aktuell_n + n > KLIP_STAPEL:
            stapel.append(aktuell)
            aktuell, aktuell_n = [], 0
        aktuell.append(gruppe)
        aktuell_n += n
    if aktuell:
        stapel.append(aktuell)
    for nr, teil in enumerate(stapel, 1):
        alle_frames = [f for _, fr in teil for f in fr]
        nach_name = {f.name: f for f in alle_frames}
        eingabe = ("Kandidaten (Dateiname: Pfad):\n"
                   + "\n".join(f"- {f.name}: {f}" for f in alle_frames))
        try:
            daten = rr._sicht_antwort(KLIP_PROMPT, alle_frames, eingabe,
                                      TIMEOUT_KLIP, KLIP_DULDUNG)
        except Exception as e:
            rr.log.warning("Clip-Stapel %d/%d verworfen: %s",
                          nr, len(stapel), e)
            for p, _ in teil:
                gruende[p] = f"Stapel verworfen: {e}"
            continue
        urteil_nach_name = {}
        for urteil in daten["bilder"]:
            name = str(urteil.get("datei") or "")
            if name in nach_name:
                urteil_nach_name[name] = urteil
        for p, fr in teil:
            roh = [urteil_nach_name.get(f.name) for f in fr]
            if any(u is None for u in roh):
                gruende[p] = "kein Urteil in der Antwort"
                continue
            urteile = [u for u in roh if u is not None]
            verdaechtig = [u for u in urteile if u.get("_verdacht")]
            if verdaechtig:
                gruende[p] = str(verdaechtig[0]["_verdacht"])
                continue
            abgelehnte = [u for u in urteile if not u.get("ok")]
            if abgelehnte:
                grund = str(abgelehnte[0].get("grund") or "kein Grund genannt")
                gruende[p] = grund
                rr.log.info("Clip %s abgelehnt: %s", p.name, grund)
                continue
            frei[p] = str(urteile[0].get("beschreibung") or "").strip()
    for p in clips:
        if p not in frei and p not in gruende:
            gruende[p] = "kein Urteil in der Antwort"
    return frei, gruende


def katalog_laden() -> dict:
    try:
        daten = json.loads(KLIP_KATALOG_DATEI.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"clips": {}}
    if not isinstance(daten.get("clips"), dict):
        daten["clips"] = {}
    return daten


def katalog_speichern(katalog: dict) -> None:
    KLIP_KATALOG_DATEI.parent.mkdir(parents=True, exist_ok=True)
    KLIP_KATALOG_DATEI.write_text(
        json.dumps(katalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def klips_ernten(manifest: dict, datum: str) -> int:
    """Neue WebM/MP4-Clips ernten, sichtpruefen und in den kumulativen
    Katalog aufnehmen. Bereits bekannte MD5s (frei oder abgelehnt) werden
    nicht erneut heruntergeladen oder geprueft - das ist der Sinn des
    kumulativen Katalogs gegenueber motive.json."""
    katalog = katalog_laden()
    bekannt = katalog["clips"]
    kandidaten = klip_kandidaten(manifest)
    neu = [k for k in kandidaten if k["md5"] not in bekannt]
    if not neu:
        rr.log.info("keine neuen Clip-Kandidaten im Snapshot")
        return 0
    ziel_dir = KLIP_DIR / datum
    geladen = _klip_laden(neu, ziel_dir)
    nach_name = {k["datei"]: k for k in neu}
    metadaten: dict[Path, dict] = {}
    brauchbar: list[Path] = []
    technisch_abgelehnt: dict[Path, str] = {}
    for p in geladen:
        meta = _klip_metadaten(p)
        if meta is None:
            technisch_abgelehnt[p] = "ffprobe fehlgeschlagen oder kaputte Datei"
            continue
        if meta["dauer_s"] > KLIP_MAX_SEKUNDEN:
            technisch_abgelehnt[p] = f"zu lang ({meta['dauer_s']:.0f}s)"
            continue
        metadaten[p] = meta
        brauchbar.append(p)
    frames = {p: _klip_frames_fuer_pruefung(
                  p, metadaten[p]["dauer_s"], ziel_dir / "vorschau", p.stem)
             for p in brauchbar}
    frei, gruende = klip_pruefen(brauchbar, frames)
    ablage = ziel_dir / "abgelehnt"
    neue_freigaben = 0
    for p in geladen:
        k = nach_name[p.name]
        md5 = k["md5"]
        if p in frei:
            meta = metadaten[p]
            bekannt[md5] = {
                "datei": p.name, "dauer_s": round(meta["dauer_s"], 1),
                "breite": meta["breite"], "hoehe": meta["hoehe"],
                "fps": round(meta["fps"], 1), "status": "frei",
                "beschreibung": frei[p], "thread": k["thread"],
                "url": k["url"], "zuletzt_verwendet": None,
            }
            neue_freigaben += 1
        else:
            grund = gruende.get(p) or technisch_abgelehnt.get(p, "kein Urteil")
            bekannt[md5] = {
                "datei": p.name, "status": "abgelehnt", "grund": grund,
                "thread": k["thread"], "url": k["url"],
            }
            ablage.mkdir(parents=True, exist_ok=True)
            p.replace(ablage / f"{p.stem}__{rr._grund_slug(grund)}{p.suffix}")
    shutil.rmtree(ziel_dir / "vorschau", ignore_errors=True)
    katalog_speichern(katalog)
    rr.log.info("%d neue Clips freigegeben, %d abgelehnt",
               neue_freigaben, len(neu) - neue_freigaben)
    return neue_freigaben


def klip_datei(md5: str, katalog: dict, ziel_dir: Path) -> Path | None:
    """Pfad zur Rohdatei eines freigegebenen Katalog-Clips - laedt sie bei
    Bedarf ueber die gemerkte URL erneut, falls klip_bereinigen() sie
    zwischenzeitlich geloescht hat. None nur, wenn der Clip nicht (mehr)
    frei ist oder der Nachladeversuch scheitert (Thread 404, URL abgelaufen)."""
    eintrag = katalog.get("clips", {}).get(md5)
    if not eintrag or eintrag.get("status") != "frei":
        return None
    ziel = ziel_dir / eintrag["datei"]
    if ziel.exists():
        return ziel
    try:
        req = urllib.request.Request(eintrag["url"], headers=rr.BILD_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            daten = resp.read(KLIP_MAX_BYTES + 1)
    except Exception as e:
        rr.log.info("Clip %s nicht nachgeladen: %s", eintrag["datei"], e)
        return None
    if len(daten) > KLIP_MAX_BYTES:
        return None
    ziel_dir.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(daten)
    return ziel


def klip_bereinigen(clip_alter_stunden: float = 48.0,
                    abgelehnt_alter_tage: float = 7.0,
                    trockenlauf: bool = False) -> int:
    """Platzverbrauch der Clip-Ernte begrenzen (hp-ubuntu war am 17.08.2026
    zu 83% belegt): freigegebene Rohclips nach Verwendung oder
    clip_alter_stunden loeschen (der Katalog-Eintrag bleibt, siehe
    klip_datei() zum Nachladen), abgelehnte Clips nach abgelehnt_alter_tage
    (Gegenpruefungsfenster, analog den Hintergrundbildern). Anders als
    motive.json wird katalog.json nie komplett neu geschrieben - ohne diese
    Bereinigung wuerden die Tagesordner unter arbeit/clips/ unbegrenzt
    wachsen. Mit trockenlauf wird nichts geloescht, nur geloggt, was faellig
    waere; katalog.json bleibt in beiden Faellen unberuehrt."""
    if not KLIP_DIR.exists():
        return 0
    katalog = katalog_laden()
    verwendet = {e["datei"] for e in katalog["clips"].values()
                if e.get("zuletzt_verwendet") and "datei" in e}
    jetzt = time.time()
    geloescht = 0
    for tag_dir in KLIP_DIR.iterdir():
        if not tag_dir.is_dir():
            continue
        for pfad in tag_dir.glob("*"):
            if pfad.is_dir():
                continue
            alter_s = jetzt - pfad.stat().st_mtime
            if pfad.name in verwendet or alter_s > clip_alter_stunden * 3600:
                if trockenlauf:
                    rr.log.info("[Trockenlauf] wuerde Rohclip loeschen: %s",
                                pfad.relative_to(KLIP_DIR))
                else:
                    pfad.unlink()
                geloescht += 1
        ablage = tag_dir / "abgelehnt"
        if ablage.is_dir():
            for pfad in ablage.glob("*"):
                if (jetzt - pfad.stat().st_mtime) > abgelehnt_alter_tage * 86400:
                    if trockenlauf:
                        rr.log.info("[Trockenlauf] wuerde abgelehnten Clip "
                                    "loeschen: %s", pfad.relative_to(KLIP_DIR))
                    else:
                        pfad.unlink()
                    geloescht += 1
    return geloescht


if __name__ == "__main__":
    import argparse
    import logging
    import sys
    # Ohne Handler blieben die [Trockenlauf]-Zeilen (rr.log.info) im
    # Standalone-Aufruf (video.sh) unsichtbar - schlicht auf stderr geben,
    # ohne die Log-Datei von run_report anzufassen.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--trockenlauf", action="store_true",
                    help="einheitliches Dry-Run-Flag der Pipeline: nichts "
                         "loeschen, nur loggen, was faellig waere")
    args = ap.parse_args()
    geloescht = klip_bereinigen(trockenlauf=args.trockenlauf)
    if args.trockenlauf:
        print(f"Clip-Bereinigung (Trockenlauf): {geloescht} Datei(en) "
              f"waeren faellig, nichts geloescht")
    else:
        print(f"Clip-Bereinigung: {geloescht} Datei(en) geloescht")
    sys.exit(0)
