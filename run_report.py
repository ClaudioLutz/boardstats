#!/usr/bin/env python3
"""/biz/ Lagebericht - dreistufige Pipeline mit Extrakt-Cache.

Warum dreistufig: Ein einzelnes Modell bekam frueher den auf 22 KB verdichteten
Report. Genau diese Verdichtung warf das Detail weg, das den Bericht wertvoll
macht (Strikes, Guidance, Bezugsquellen, "welches Verfahren eigentlich").
Stattdessen liest ein guenstigeres Modell je einen ganzen Thread; nur die
Extrakte gehen an das teure Modell, das den Bericht schreibt.

  Stufe 1  bundle_biz.py schneidet Volltext-Buendel
  Stufe 2  Sonnet extrahiert je Buendel (parallel, Ergebnis je Datei)
  Stufe 3  Opus synthetisiert den Bericht und versendet ihn

Warum ein Extrakt-Cache: Gemessen an drei aufeinanderfolgenden Abenden waren
rund 50 % des gebuendelten Textes schon am Vortag gebuendelt - ein Thread mit
48 KB hatte 0 KB neue Posts und lief trotzdem komplett durchs Modell. Liegt zu
einem Thread ein Extrakt vor, wird er deshalb fortgeschrieben statt neu
erstellt: der Extrakt ist das Gedaechtnis, das Delta die einzige neue
Leseleistung.

Warum Python statt PowerShell: dasselbe Skript laeuft auf dem Windows-Rechner
und auf hp-ubuntu. Auf dem Server hat es keine Abhaengigkeit vom Laptop.

Jede Stufe schreibt auf Platte, damit ein Abbruch in Stufe 2 die fertigen
Extrakte nicht wegwirft: die Synthese laeuft mit dem, was da ist.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from bericht_html import _ist_ueberschrift as ist_ueberschrift

BASE = Path(__file__).resolve().parent
LOGS = BASE / "logs"
BERICHTE = BASE / "berichte"
ARBEIT = BASE / "arbeit"
CACHE = BASE / "cache"
EXTRAKTE = BASE / "extrakte"

THROTTLE = 5            # gleichzeitige Sonnet-Aufrufe
TIMEOUT_EXTRAKT = 600   # je Buendel, Sekunden
TIMEOUT_SYNTH = 1800    # Synthese, Sekunden
TIMEOUT_UEBERSETZUNG = 600  # englische Uebersetzung des fertigen Berichts
TIMEOUT_TITEL = 300     # reisserischer Video-Titel (kleiner Sonnet-Aufruf)
MIN_EXTRAKTE = 0.6      # Anteil, ab dem die Synthese als vollstaendig gilt
# Re-Anchoring: fortgeschriebene Extrakte driften (gemessen in der Literatur:
# strukturierte Fortschreibung verliert ueber 7 Runden ~5 Prozentpunkte Recall,
# Chain-of-Key arXiv 2407.15021; Praxisregel anderswo: Neuaufbau nach 3
# Inkrementen). Eine validierte Schwelle gibt es nicht - 5 Fortschreibungen
# ODER kumuliert >50 % neue Posts seit der letzten Voll-Extraktion ist die
# Starthypothese vom 08.08.2026, bei Bedarf per A/B-Vergleich nachziehen.
NEUAUFBAU_NACH = 5      # so oft wird ein Extrakt fortgeschrieben, dann neu
NEUAUFBAU_ANTEIL = 0.5  # kumulierte neue Posts im Verhaeltnis zur Voll-Basis
CACHE_TAGE = 10         # Extrakte laenger nicht gesehener Threads wegraeumen
LAEUFE_BEHALTEN = 5

log = logging.getLogger("report")


def setup_logging() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    datei = LOGS / "run_report.log"
    if datei.exists() and datei.stat().st_size > 2 * 1024 * 1024:
        datei.replace(LOGS / "run_report.log.1")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(datei, encoding="utf-8"),
                  logging.StreamHandler(sys.stderr)],
    )


def claude_pfad() -> str:
    """Bevorzugt die native Binary, nicht den npm-Wrapper.

    Auf Windows ist `claude` eine .CMD-Batchdatei; cmd.exe deutet darin die
    Zeichen < > | & als Umleitung und zerschneidet damit den Prompt. Beobachtet
    an "STATUS: FEHLER - <kurze Ursache>": das Modell bekam den Prompt nur bis
    zur spitzen Klammer, hielt ihn fuer abgeschnitten und sah selbstaendig im
    Dateisystem nach. Die .exe umgeht die Batch-Schicht komplett.

    Auf Linux liegt claude unter nvm und ist in nicht-interaktiven Sitzungen
    (cron, ssh ohne Login-Shell) nicht im PATH - deshalb wird dort zusaetzlich
    direkt gesucht."""
    p = os.environ.get("CLAUDE_BIN")
    if p:
        return p
    kandidaten = [
        Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" /
        "@anthropic-ai" / "claude-code" / "bin" / "claude.exe",
    ]
    kandidaten += sorted(
        (Path.home() / ".nvm" / "versions" / "node").glob("v*/bin/claude"),
        reverse=True)
    kandidaten.append(Path.home() / ".npm-global" / "bin" / "claude")
    for k in kandidaten:
        if k.exists():
            return str(k)
    gefunden = shutil.which("claude")
    if not gefunden:
        raise SystemExit("claude nicht gefunden - CLAUDE_BIN setzen")
    return gefunden


def claude_ruf(prompt: str, eingabe: str, modell: str, timeout: int,
               tools: str | None = None) -> str:
    """Ein headless-Aufruf. Die Eingabe geht ueber stdin, nicht ueber die
    Kommandozeile: Windows kappt Kommandozeilen bei ~32767 Zeichen, und die
    Buendel sind groesser."""
    cmd = [claude_pfad(), "-p", prompt, "--model", modell,
           "--output-format", "text"]
    if tools:
        cmd += ["--allowedTools", tools]
    r = subprocess.run(cmd, input=eingabe, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "") + (("\n" + r.stderr) if r.returncode and r.stderr else "")


# ---------------------------------------------------------------- Cache

def cache_status() -> dict:
    """Was der Bundler wissen muss, um das Delta zu schneiden."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / "status.json"
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log.warning("Cache-Status unlesbar - starte ohne Cache")
        return {}
    # Ein Extrakt, der zu oft fortgeschrieben wurde, driftet. Die Rohsnapshots
    # bleiben erhalten, der Neuaufbau ist also jederzeit billig moeglich.
    # Zweites Kriterium: hat sich der Thread seit der letzten Voll-Extraktion
    # um mehr als die Haelfte vergroessert, traegt der alte Extrakt den
    # Grossteil des Threads nur noch aus zweiter Hand - dann neu verankern.
    for eintrag in d.values():
        if eintrag.get("fortschreibungen", 0) >= NEUAUFBAU_NACH:
            eintrag["neuaufbau_faellig"] = True
        basis = eintrag.get("posts_bei_voll", 0)
        if basis and eintrag.get("neue_posts_seit_voll", 0) > NEUAUFBAU_ANTEIL * basis:
            eintrag["neuaufbau_faellig"] = True
    return d


def cache_schreiben(status: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")


def cache_aufraeumen(status: dict) -> None:
    """Extrakte von Threads, die lange nicht mehr auftauchten, entfernen -
    4chan-Threads werden geloescht, der Cache soll nicht unbegrenzt wachsen."""
    grenze = time.time() - CACHE_TAGE * 86400
    weg = [t for t, e in status.items() if e.get("zuletzt", 0) < grenze]
    for t in weg:
        status.pop(t, None)
        (CACHE / f"{t}.txt").unlink(missing_ok=True)
    if weg:
        log.info("Cache: %d veraltete Extrakte entfernt", len(weg))


# ---------------------------------------------------------------- Stufen

def stufe1(host: str | None, top: int, bDir: Path) -> dict:
    """Buendel erzeugen. Laeuft die Pipeline auf dem Server selbst, entfaellt
    jede Uebertragung."""
    status = cache_status()
    schlank = {t: {"last_post_no": e.get("last_post_no", 0),
                   "neuaufbau_faellig": e.get("neuaufbau_faellig", False)}
               for t, e in status.items()}
    statusdatei = CACHE / "status_fuer_bundler.json"
    CACHE.mkdir(parents=True, exist_ok=True)
    statusdatei.write_text(json.dumps(schlank), encoding="utf-8")

    if host:
        subprocess.run(["scp", "-q", str(statusdatei),
                        f"{host}:boardstats/cache_status.json"], check=True)
        r = subprocess.run(
            ["ssh", host, f"cd boardstats && python3 bundle_biz.py --top {top} "
                          f"--cache-status cache_status.json 2>/dev/null"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        manifest_json = r.stdout
    else:
        r = subprocess.run(
            [sys.executable, str(BASE / "bundle_biz.py"), "--top", str(top),
             "--cache-status", str(statusdatei)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=BASE)
        manifest_json = r.stdout

    if not manifest_json.strip():
        raise SystemExit(f"bundle_biz.py lieferte kein Manifest: {r.stderr[-500:]}")
    manifest = json.loads(manifest_json.strip().splitlines()[-1])

    bDir.mkdir(parents=True, exist_ok=True)
    if host:
        subprocess.run(["scp", "-q", f"{host}:boardstats/bundles/*.txt", str(bDir)],
                       check=False)
    else:
        for f in (BASE / "bundles").glob("*.txt"):
            shutil.copy2(f, bDir / f.name)
    return manifest


def ein_extrakt(eintrag: dict, bDir: Path, eDir: Path,
                prompt_voll: str, prompt_update: str) -> tuple[str, str]:
    """Ein Thread: entweder unveraendert aus dem Cache, fortgeschrieben oder
    neu extrahiert. Gibt (thread, ergebnis) zurueck."""
    t = str(eintrag["thread"])
    ziel = eDir / f"{t}.txt"
    alt = CACHE / f"{t}.txt"

    if eintrag["modus"] == "unveraendert":
        if alt.exists():
            shutil.copy2(alt, ziel)
            return t, "unveraendert"
        # Cache-Datei fehlt trotz Status - dann muss voll gelesen werden.
        return t, "fehler:kein Cache-Extrakt trotz Status unveraendert"

    quelle = bDir / f"{t}.txt"
    if not quelle.exists():
        return t, "fehler:kein Buendel"
    text = quelle.read_text(encoding="utf-8", errors="replace")

    if eintrag["modus"] == "delta" and alt.exists():
        eingabe = (
            "TEIL 1 - BISHERIGER EXTRAKT ZU DIESEM THREAD\n"
            + "=" * 70 + "\n"
            + alt.read_text(encoding="utf-8", errors="replace")
            + "\n\n" + "=" * 70 + "\n"
            + "TEIL 2 - POSTS, DIE SEITHER DAZUGEKOMMEN SIND\n"
            + "=" * 70 + "\n" + text
        )
        prompt = prompt_update
        art = "delta"
    else:
        eingabe = text
        prompt = prompt_voll
        art = "voll"

    # Ein Versuch, dann einer mit Nachdruck. Beobachtet: bei ungewoehnlichen
    # Threads (Umfragen, Bilderketten) antwortet das Modell gelegentlich mit
    # einer Rueckfrage statt mit dem Extrakt - unbeaufsichtigt ist das ein
    # verlorener Thread.
    def rueckfall(grund: str) -> tuple[str, str]:
        """Scheitert die Fortschreibung, ist der Extrakt aus dem letzten Lauf
        immer noch besser als ein Thread, der gar nicht im Bericht auftaucht.
        Beobachtet am 08.08. beim BIP110-Thread: eine Zeitueberschreitung liess
        einen der inhaltsreichsten Threads komplett wegfallen. last_post_no
        bleibt dabei unveraendert, der naechste Lauf holt das groessere Delta."""
        if alt.exists():
            shutil.copy2(alt, ziel)
            log.warning("  Thread %s: %s - verwende Extrakt aus dem letzten Lauf",
                        t, grund)
            return t, "unveraendert"
        return t, f"fehler:{grund}"

    r = ""
    for versuch in (1, 2):
        p = prompt if versuch == 1 else (
            prompt + "\n\nWICHTIG: Antworte AUSSCHLIESSLICH mit den Abschnitten, "
            "beginnend mit der Zeile THEMA. Keine Rueckfrage, keine Einleitung, "
            "keine Nachfrage nach dem Zweck.")
        try:
            r = claude_ruf(p, eingabe, "sonnet", TIMEOUT_EXTRAKT)
        except subprocess.TimeoutExpired:
            return rueckfall("Zeitueberschreitung")
        except OSError as e:
            return rueckfall(str(e))
        # Nur brauchbar, wenn es wie ein Extrakt aussieht - sonst ist es eine
        # Rueckfrage oder eine CLI-Fehlermeldung und wuerde die Synthese mit
        # Muell fuellen.
        if "THEMA" in r:
            ziel.write_text(r, encoding="utf-8")
            return t, art

    (eDir / f"{t}.txt.fehler").write_text(r, encoding="utf-8")
    return rueckfall("keine Abschnittsstruktur, auch im zweiten Versuch")


def stufe2(manifest: dict, bDir: Path, eDir: Path) -> dict:
    eDir.mkdir(parents=True, exist_ok=True)
    prompt_voll = (BASE / "extract_prompt.txt").read_text(encoding="utf-8")
    prompt_update = (BASE / "update_prompt.txt").read_text(encoding="utf-8")

    with ThreadPoolExecutor(max_workers=THROTTLE) as pool:
        ergebnisse = list(pool.map(
            lambda e: ein_extrakt(e, bDir, eDir, prompt_voll, prompt_update),
            manifest["buendel"]))
    return dict(ergebnisse)


def cache_pflegen(manifest: dict, eDir: Path, ergebnisse: dict) -> None:
    status = cache_status()
    jetzt = time.time()
    for b in manifest["buendel"]:
        t = str(b["thread"])
        art = ergebnisse.get(t, "")
        if art.startswith("fehler"):
            continue
        quelle = eDir / f"{t}.txt"
        if not quelle.exists():
            continue
        shutil.copy2(quelle, CACHE / f"{t}.txt")
        alt = status.get(t, {})
        fortschreibungen = alt.get("fortschreibungen", 0)
        posts_bei_voll = alt.get("posts_bei_voll", 0)
        neue_seit_voll = alt.get("neue_posts_seit_voll", 0)
        if art == "delta":
            fortschreibungen += 1
            neue_seit_voll += int(b.get("neue_posts") or 0)
        elif art == "voll":
            fortschreibungen = 0
            neue_seit_voll = 0
            posts_bei_voll = int(b.get("posts_gesamt") or 0)
        status[t] = {
            "last_post_no": b.get("last_post_no", alt.get("last_post_no", 0)),
            "betreff": b.get("betreff", "")[:60],
            "zuletzt": jetzt,
            "stand": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "fortschreibungen": fortschreibungen,
            "posts_bei_voll": posts_bei_voll,
            "neue_posts_seit_voll": neue_seit_voll,
        }
    cache_aufraeumen(status)
    cache_schreiben(status)


# Die Abschnittsueberschriften der Extrakte (Vertrag mit extract_prompt.txt
# und update_prompt.txt). Dient zum Erkennen von Abschnittsgrenzen.
ABSCHNITTE = (
    "THEMA", "WERTPAPIERE UND COINS", "KONKRETE ZAHLEN",
    "THESEN UND ARGUMENTE", "PRAKTISCHES", "QUELLEN",
    "FACHBEGRIFFE UND SLANG", "OFFENE FRAGEN", "VERLAESSLICHKEIT",
    "NEU SEIT DEM LETZTEN LAUF",
)
# Diese Abschnitte bleiben im Extrakt-Cache (er ist das Gedaechtnis des
# Threads), gehen aber nicht mehr in die Synthese: gemessen am 06.08. blieben
# 94 % der Glossar-Eintraege ungenutzt (19 von 293 kamen im Bericht vor), und
# irrelevanter Kontext verschlechtert nachweislich die Nutzung des Rests
# ("context rot"). Das Glossar entsteht stattdessen in glossar_bauen().
NUR_CACHE = ("FACHBEGRIFFE UND SLANG", "OFFENE FRAGEN")


def ohne_cache_abschnitte(text: str) -> str:
    zeilen, behalten = [], True
    for z in text.splitlines():
        s = z.strip()
        if s in ABSCHNITTE:
            behalten = s not in NUR_CACHE
        if behalten:
            zeilen.append(z)
    return "\n".join(zeilen)


def sandwich(extrakte: list[Path], meta_nach_thread: dict) -> list[Path]:
    """Reihenfolge gegen den Positions-Bias der Modelle ("lost in the middle",
    arXiv 2307.03172: U-Kurve, Anfang und Ende werden zuverlaessig genutzt,
    die Mitte faellt um 20-30 Punkte ab; Position 1 praegt die Synthese am
    staerksten). Bisher war die Reihenfolge alphabetisch nach Thread-Nummer,
    also Zufall. Jetzt: der substanzreichste Thread zuerst, der zweitstaerkste
    als letzter, die schwaechsten in die Mitte."""
    def score(p: Path) -> float:
        return float(meta_nach_thread.get(p.stem, {}).get("substanz_summe") or 0.0)
    sortiert = sorted(extrakte, key=lambda p: (-score(p), p.stem))
    vorne: list[Path] = []
    hinten: list[Path] = []
    for i, e in enumerate(sortiert):
        (vorne if i % 2 == 0 else hinten).append(e)
    return vorne + hinten[::-1]


def glossar_bauen(bericht: str, eDir: Path, maximal: int = 18) -> str:
    """Das Glossar deterministisch statt vom Modell: aus den FACHBEGRIFFE-
    Abschnitten der Extrakte genau die Begriffe ziehen, die im fertigen
    Bericht tatsaechlich vorkommen. Vorher schrieb Opus das Glossar aus 293
    angebotenen Eintraegen - Python matcht billiger und vollstaendiger.
    Das Zeilenformat "Begriff - Erklaerung" muss zum Tabellen-Parser in
    bericht_html.py passen (Begriff maximal 45 Zeichen)."""
    eintraege: dict[str, tuple[str, str]] = {}
    for e in sorted(eDir.glob("*.txt")):
        drin = False
        for z in e.read_text(encoding="utf-8", errors="replace").splitlines():
            s = z.strip()
            if s in ABSCHNITTE:
                drin = s == "FACHBEGRIFFE UND SLANG"
                continue
            if not drin or not s:
                continue
            s = s.lstrip("-•*").strip()
            if not s or s.lower() == "keine":
                continue
            m = re.match(r"^(.{1,45}?)\s+[-–—:]\s+(.+)$", s)
            if not m:
                continue
            begriff, erklaerung = m.group(1).strip(), m.group(2).strip()
            eintraege.setdefault(begriff.lower(), (begriff, erklaerung))

    tief = bericht.lower()

    def kommt_vor(begriff: str) -> bool:
        # "stacking / stack" oder "spot bzw. Spotpreis": jede Variante zaehlt.
        varianten = [v.strip().lower()
                     for v in re.split(r"\s*(?:/|bzw\.)\s*", begriff) if v.strip()]
        return any(
            re.search(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", tief)
            for v in varianten)

    treffer = sorted(
        (be for be in eintraege.values() if kommt_vor(be[0])),
        key=lambda be: be[0].lower())
    if not treffer:
        return ""
    # "- " davor: macht aus der Zeilenfolge eine echte Aufzaehlung statt eines
    # von GitHub zu einem Absatz verschmolzenen Fliesstexts, sobald der
    # Bericht als Markdown veroeffentlicht wird. bericht_html._glossar()
    # entfernt einen fuehrenden Bindestrich ohnehin schon, bleibt also
    # kompatibel mit dem HTML-Mailversand.
    return "GLOSSAR\n\n" + "\n".join(f"- {b} - {e}" for b, e in treffer[:maximal])


def abdeckung_trennen(text: str) -> tuple[str, str]:
    """Der ABDECKUNG-Block (je Thread: verwendet oder ausgelassen mit Grund)
    ist Rechenschaft fuer das Log, nicht fuer den Leser - er wird vor dem
    Versand abgetrennt."""
    zeilen = text.splitlines()
    for i, z in enumerate(zeilen):
        if z.strip().rstrip(":").upper() == "ABDECKUNG":
            return ("\n".join(zeilen[:i]).rstrip(),
                    "\n".join(zeilen[i + 1:]).strip())
    return text, ""


# Schoene Ueberschriften fuer die oeffentliche Markdown-Fassung. Die rohen
# Abschnittsnamen (Vertrag mit den Extraktions-Prompts) bleiben in Grossschrift,
# damit ABSCHNITTE weiterhin fuer beide Zwecke passt.
ABSCHNITT_TITEL = {
    "THEMA": "Thema",
    "WERTPAPIERE UND COINS": "Wertpapiere und Coins",
    "KONKRETE ZAHLEN": "Konkrete Zahlen",
    "THESEN UND ARGUMENTE": "Thesen und Argumente",
    "PRAKTISCHES": "Praktisches",
    "QUELLEN": "Quellen",
    "FACHBEGRIFFE UND SLANG": "Fachbegriffe und Slang",
    "OFFENE FRAGEN": "Offene Fragen",
    "VERLAESSLICHKEIT": "Verlaesslichkeit",
    "NEU SEIT DEM LETZTEN LAUF": "Neu seit dem letzten Lauf",
}

MODUS_TEXT = {
    "voll": "vollstaendig gelesen",
    "delta": "fortgeschrieben",
    "unveraendert": "unveraendert seit dem letzten Lauf",
}


def extrakt_zu_markdown(text: str, meta: dict, datum: str) -> str:
    """Ein Thread-Extrakt als eigenstaendige Markdown-Seite. Die Abschnitte
    des Extrakts sind bereits mit "- " als Aufzaehlung geschrieben, das ist
    schon gueltiges Markdown - nur die Grossschrift-Ueberschriften werden zu
    echten Markdown-Ueberschriften."""
    zeilen = []
    for z in text.splitlines():
        titel = ABSCHNITT_TITEL.get(z.strip())
        zeilen.append(f"## {titel}" if titel else z)
    koerper = "\n".join(zeilen).strip()

    modus = MODUS_TEXT.get(meta.get("modus", ""), meta.get("modus", ""))
    titel = meta.get("betreff") or f"Thread {meta.get('thread', '')}"
    kopf = [
        f"# {titel}",
        "",
        f"Quelle: [4chan /biz/ Thread {meta.get('thread', '')}]"
        f"({meta.get('url', '')}) &middot; Stand {datum} &middot; {modus}"
        + (f" &middot; {meta['posts_gesamt']} Posts insgesamt"
           if meta.get("posts_gesamt") is not None else ""),
        "",
        "Automatisch erstellt aus oeffentlichen Beitraegen des Boards /biz/ "
        "durch ein Sprachmodell. Aussagen von Postern sind Behauptungen, "
        "keine Tatsachen und keine Anlageberatung.",
        "",
        "---",
        "",
    ]
    return "\n".join(kopf) + koerper + "\n"


def _tag_readme_bauen(manifest: dict, datum: str, tag_dir: Path) -> str:
    """Die Tages-Uebersicht wird zweimal geschrieben (vor und nach der
    Synthese) - einmal neu aufgebaut statt fortgeschrieben, damit der Link
    auf den Bericht sauber erscheint, sobald `bericht.md` existiert, ohne
    eine zweite Codepfad fuers Nachtragen zu brauchen."""
    eintraege = sorted(manifest["buendel"],
                        key=lambda m: -(m.get("substanz_summe") or 0.0))
    zeilen = [f"# /biz/-Lagebericht: {datum}", ""]
    if (tag_dir / "bericht.md").exists():
        zeilen += ["[Bericht dieses Tages](bericht.md)", ""]
    zeilen += [f"{len(eintraege)} Threads, absteigend nach Substanzdichte.", "",
               "| Thread | Modus | Posts | Substanz |", "|---|---|---|---|"]
    for m in eintraege:
        t = str(m.get("thread", ""))
        if not (tag_dir / f"{t}.md").exists():
            continue
        betreff = (m.get("betreff") or t).replace("|", "/").replace("\n", " ")
        if len(betreff) > 70:
            betreff = betreff[:67] + "..."
        modus = MODUS_TEXT.get(m.get("modus", ""), m.get("modus", ""))
        zeilen.append(
            f"| [{betreff}]({t}.md) | {modus} | {m.get('posts_gesamt', '')} | "
            f"{m.get('substanz_summe', 0):.1f} |")
    return "\n".join(zeilen) + "\n"


def markdown_tag_schreiben(manifest: dict, eDir: Path, datum: str) -> Path | None:
    """Persistiert die Extrakte des laufenden Tages als Markdown im Repo
    (`extrakte/<datum>/`), zusammen mit einer Tages-Uebersicht. eDir enthaelt
    zu diesem Zeitpunkt den vollen aktuellen Stand aller Buendel-Threads,
    auch der unveraenderten (ein_extrakt() kopiert die aus dem Cache).
    Persistieren macht die Extrakte, nicht nur den fertigen Bericht,
    nachvollziehbar - inklusive der Abschnitte, die aus der Synthese-Eingabe
    herausgefiltert wurden (Glossar, offene Fragen bleiben hier erhalten)."""
    meta_nach_thread = {str(b["thread"]): b for b in manifest["buendel"]}
    tag_dir = EXTRAKTE / datum
    tag_dir.mkdir(parents=True, exist_ok=True)

    geschrieben = False
    for e in sorted(eDir.glob("*.txt")):
        t = e.stem
        meta = meta_nach_thread.get(t, {"thread": t})
        md = extrakt_zu_markdown(
            e.read_text(encoding="utf-8", errors="replace"), meta, datum)
        (tag_dir / f"{t}.md").write_text(md, encoding="utf-8")
        geschrieben = True

    if not geschrieben:
        return None

    (tag_dir / "README.md").write_text(
        _tag_readme_bauen(manifest, datum, tag_dir), encoding="utf-8")
    return tag_dir


def markdown_index_aktualisieren() -> None:
    """Baut extrakte/README.md neu aus den vorhandenen Tagesordnern - einfacher
    als fortzuschreiben, und die Anzahl Tage bleibt uebersichtlich klein."""
    tage = sorted((p for p in EXTRAKTE.glob("*") if p.is_dir()), reverse=True)
    zeilen = [
        "# /biz/-Lagebericht: Extrakt-Archiv", "",
        "Taegliche, strukturiert extrahierte Zusammenfassungen von Threads aus "
        "dem 4chan-Board /biz/ (Business & Finance). Ein Sprachmodell liest je "
        "Thread und zieht Thema, genannte Titel/Coins, konkrete Zahlen, Thesen "
        "samt Begruendung, Quellen und Fachbegriffe heraus - Diskurs-"
        "Dokumentation, keine Anlageberatung. Teil des Projekts "
        "[boardstats](..).", "",
        "| Datum | Threads |", "|---|---|",
    ]
    for t in tage:
        anzahl = len([p for p in t.glob("*.md")
                      if p.name not in ("README.md", "bericht.md")])
        bericht_stern = " (mit Bericht)" if (t / "bericht.md").exists() else ""
        zeilen.append(f"| [{t.name}]({t.name}/README.md) | {anzahl}{bericht_stern} |")
    (EXTRAKTE / "README.md").write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def git_veroeffentlichen(pfade: list[Path], nachricht: str) -> None:
    """Committet und pusht nur die genannten Pfade. Ein Fehlschlag (kein
    Git-Remote, keine Anmeldung, kein Netz) darf den Bericht nicht zu Fall
    bringen - er wird geloggt, der Lauf laeuft weiter."""
    rel = [str(p.relative_to(BASE)) for p in pfade]
    try:
        subprocess.run(["git", "-C", str(BASE), "add", *rel],
                       check=True, capture_output=True, text=True)
        status = subprocess.run(
            ["git", "-C", str(BASE), "status", "--porcelain", "--", *rel],
            check=True, capture_output=True, text=True)
        if not status.stdout.strip():
            log.info("Keine neuen Extrakte zu veroeffentlichen")
            return
        subprocess.run(["git", "-C", str(BASE), "commit", "-q", "-m", nachricht],
                       check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(BASE), "push", "-q"],
                       check=True, capture_output=True, text=True)
        log.info("Auf GitHub veroeffentlicht: %s", nachricht)
    except (subprocess.CalledProcessError, OSError) as e:
        meldung = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
        log.warning("Veroeffentlichung auf GitHub fehlgeschlagen (Bericht "
                    "ist davon unberuehrt): %s", meldung)


REPO_URL = "https://github.com/ClaudioLutz/boardstats/blob/main"


def voriger_bericht(datum: str) -> tuple[str, str] | None:
    """Neuester veroeffentlichter Bericht vor `datum` - Text und oeffentliche
    URL, damit die Synthese Unveraendertes verlinken statt wiederholen kann.
    None bei erstem Lauf oder wenn --kein-github das Archiv nie gefuellt hat."""
    kandidaten = sorted(
        (p for p in EXTRAKTE.glob("*/bericht.md") if p.parent.name < datum),
        reverse=True)
    if not kandidaten:
        return None
    p = kandidaten[0]
    text = p.read_text(encoding="utf-8", errors="replace")
    return text, f"{REPO_URL}/extrakte/{p.parent.name}/bericht.md"


def bericht_zu_markdown(bericht: str, datum: str) -> str:
    """Der versandte Bericht als eigenstaendige, oeffentliche Markdown-Seite.
    Nutzt dieselbe Ueberschriften-Erkennung wie der HTML-Mailversand
    (bericht_html._ist_ueberschrift), damit beide Darstellungen aus derselben
    Quelle konsistent bleiben - Aufzaehlungen sind schon "- "-Zeilen, also
    gueltiges Markdown, und muessen nicht extra umgeformt werden."""
    zeilen = bericht.replace("\r\n", "\n").split("\n")
    kopf = ""
    if zeilen and zeilen[0].lower().startswith("datenstand"):
        kopf = zeilen[0].strip()
        zeilen = zeilen[1:]

    koerper = [f"## {z.strip()}" if z.strip() and ist_ueberschrift(z.strip()) else z
               for z in zeilen]
    return (
        f"# /biz/-Lagebericht {datum}\n\n"
        + (f"*{kopf}*\n\n" if kopf else "")
        + "[Extrakte und Quell-Threads dieses Tages](README.md)\n\n---\n\n"
        + "\n".join(koerper).strip() + "\n"
    )


# Rueckuebersetzung, keine gewoehnliche Uebersetzung: die Quelle des Berichts
# ist das englischsprachige Board /biz/, der Bericht selbst ist deutsch. Der
# Jargon muss also in seiner originalen englischen Form REKONSTRUIERT werden
# ("chain split", nicht "chain splitting"), sonst klingt das Ergebnis nach
# woertlicher Uebersetzung. Ein einziger Sonnet-Aufruf auf den fertigen
# Bericht (~3'000 Tokens) statt einer zweiten Opus-Synthese aus allen
# Extrakten - das ist der token-schonende Teil (Entscheid 14.08.2026).
UEBERSETZUNG_PROMPT = """\
Du bekommst den heutigen /biz/-Lagebericht als Markdown auf Deutsch.
Uebersetze ihn vollstaendig ins Englische.

Wichtig: Das ist eine Rueckuebersetzung. Die Quelle des Berichts ist das
englischsprachige 4chan-Board /biz/ (Business & Finance) - Fachbegriffe,
Meme-Sprache und Jargon muessen in der originalen englischen Form der
Community stehen, nicht woertlich uebersetzt (z. B. "chain split",
"difficulty adjustment", "rug pull", "bagholder").

Regeln:
- Ticker, Coin-Namen, Zahlen, Prozentwerte, Datumsangaben und URLs
  unveraendert uebernehmen.
- Markdown-Struktur exakt beibehalten: gleiche Ueberschriften-Ebenen,
  gleiche Aufzaehlungen, gleiche Absatzgrenzen, Trennlinien und Links
  (relative Link-Ziele wie README.md unveraendert lassen).
- Die Titelzeile lautet "# /biz/ Situation Report <datum>".
- Die kursive Datenstand-Zeile beginnt mit "*Data as of:".
- Die Glossar-Ueberschrift lautet "## GLOSSARY".
- Gib NUR das uebersetzte Markdown aus, ohne Vor- oder Nachbemerkungen.
"""


def bericht_uebersetzen(bericht_md: str) -> str:
    """Uebersetzt den veroeffentlichten bericht.md ins Englische (Sonnet)."""
    out = claude_ruf(UEBERSETZUNG_PROMPT, bericht_md, "sonnet",
                     TIMEOUT_UEBERSETZUNG).strip()
    # Plausibilitaet statt blindem Vertrauen: eine CLI-Fehlermeldung beginnt
    # nie mit der Markdown-Titelzeile und darf nie als Bericht abgelegt werden.
    if not out.startswith("# "):
        raise RuntimeError(f"Uebersetzung unbrauchbar: {out[:200]!r}")
    return out + "\n"


# Der Titel-Prompt ist wie der Synthese-Prompt in korrektem Deutsch mit
# Umlauten geschrieben (das Modell ahmt den Stil der Anweisung nach, und der
# deutsche Hook muss echte Umlaute tragen). Die Hooks sind bewusst reisserisch
# (Entscheid 14.08.2026: voll Clickbait, Hook + Serien-Suffix, keine Emoji,
# keine Wiederholung ueber die Tage).
TITEL_PROMPT = """\
Du bekommst den heutigen /biz/-Lagebericht (Markdown, deutsch), eventuell
gefolgt von einem Block BEREITS VERWENDETE TITEL.

Schreibe für das YouTube-Video des Tages einen reisserischen Titel-Aufhänger
(Hook) auf Deutsch und einen auf Englisch.

Regeln:
- Wähle die EINE zugkräftigste Geschichte des Berichts: die wichtigste
  Entwicklung, die grösste Zahl oder den stärksten Konflikt.
- Voll Clickbait: zugespitzt, dringlich, ein bis zwei Wörter in
  GROSSBUCHSTABEN. Keine Emoji. Nichts erfinden: jede Aussage des Hooks
  muss durch den Bericht gedeckt sein.
- Der englische Hook ist KEINE Übersetzung des deutschen: formuliere ihn
  eigenständig im nativen Jargon des Boards /biz/ (die Quelle ist englisch).
- Höchstens 75 Zeichen je Hook, kein Punkt am Ende. Deutsch mit echten
  Umlauten (ä, ö, ü), Schweizer Schreibweise mit "ss" statt "ß".
- Kein langer Gedankenstrich (—) im Hook: Doppelpunkt oder Komma verwenden.
- Steht ein Block BEREITS VERWENDETE TITEL in der Eingabe, darf keiner
  dieser Hooks und keine nahe Umformulierung davon wiederkommen. Bleibt das
  Tagesthema dasselbe, wähle einen anderen Aspekt, eine neue Zahl oder eine
  neue Wendung.
- Gib NUR ein JSON-Objekt aus, ohne Vor- oder Nachbemerkungen und ohne
  Code-Zaun: {"hook_de": "...", "hook_en": "..."}
"""

TITEL_SUFFIX = " | /biz/ "


def bisherige_titel(datum: str, tage: int = 14) -> list[str]:
    """Die Video-Titel der letzten Tage aus dem Archiv - damit sich der
    Aufhaenger nicht wiederholt, auch wenn das Tagesthema dasselbe bleibt."""
    titel: list[str] = []
    kandidaten = sorted(
        (p for p in EXTRAKTE.glob("*/titel.json") if p.parent.name < datum),
        reverse=True)[:tage]
    for p in kandidaten:
        try:
            daten = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(daten, dict):
            titel += [v for v in daten.values() if isinstance(v, str) and v.strip()]
    return titel


def _hook_bereinigen(hook: str) -> str:
    # "<" und ">" sind in YouTube-Titeln verboten; der lange Gedankenstrich
    # ist im Titel unerwuenscht (Schreibstil-Vorgabe fuer externe Texte);
    # 75 Zeichen lassen dem Serien-Suffix Platz unter dem 100-Zeichen-Limit.
    hook = hook.replace("<", "").replace(">", "").replace(" — ", ": ").replace("—", "-")
    return re.sub(r"\s+", " ", hook).strip()[:75].rstrip()


def _hook_normalisiert(hook: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\wäöüÄÖÜ ]+", "", hook.lower())).strip()


def titel_generieren(bericht_md: str, datum: str) -> dict[str, str]:
    """Reisserischer Tagestitel je Sprache (Hook + Serien-Suffix) in einem
    Sonnet-Aufruf. Die bisherigen Titel gehen mit, und ein wiederholter Hook
    bekommt genau einen zweiten Versuch - danach ist der statische
    Serientitel (Fallback in video_report.py) die bessere Antwort."""
    gebraucht = bisherige_titel(datum)
    gesehen = {_hook_normalisiert(t.split(TITEL_SUFFIX)[0]) for t in gebraucht}
    eingabe = bericht_md
    if gebraucht:
        eingabe += ("\n\nBEREITS VERWENDETE TITEL:\n"
                    + "\n".join(f"- {t}" for t in gebraucht))

    hinweis = ""
    doppelt: list[str] = []
    for _ in range(2):
        out = claude_ruf(TITEL_PROMPT + hinweis, eingabe, "sonnet",
                         TIMEOUT_TITEL).strip()
        out = re.sub(r"^```(?:json)?\s*|\s*```$", "", out)
        # Plausibilitaet wie bei bericht_uebersetzen(): eine CLI-Fehlermeldung
        # parst nie als genau dieses JSON.
        try:
            daten = json.loads(out)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Titel-Ausgabe kein JSON: {out[:200]!r}") from e
        hooks = {s: _hook_bereinigen(str(daten.get(f"hook_{s}") or ""))
                 for s in ("de", "en")}
        if not all(hooks.values()):
            raise RuntimeError(f"Titel-Ausgabe unvollstaendig: {out[:200]!r}")
        doppelt = [h for h in hooks.values() if _hook_normalisiert(h) in gesehen]
        if not doppelt:
            j, m, t = datum.split("-")
            return {"de": f"{hooks['de']}{TITEL_SUFFIX}{t}.{m}.{j}",
                    "en": f"{hooks['en']}{TITEL_SUFFIX}{datum}"}
        hinweis = ("\nZUSATZ: Dein letzter Vorschlag wiederholte einen schon "
                   "verwendeten Hook (" + "; ".join(doppelt)
                   + ") - waehle zwingend einen anderen Aufhaenger.")
    raise RuntimeError(f"Hook wiederholt sich trotz zweitem Versuch: {doppelt}")


def bericht_veroeffentlichen(bericht: str, datum: str, tag_dir: Path | None,
                             manifest: dict) -> None:
    """Legt den fertigen Bericht in denselben Tagesordner wie die Extrakte
    und veroeffentlicht ihn. Getrennt von markdown_tag_schreiben(), weil der
    Bericht erst nach der Synthese existiert, die Extrakte aber schon vorher
    veroeffentlicht werden sollen (unabhaengige Fehlerquellen)."""
    if tag_dir is None:
        return
    bericht_md = bericht_zu_markdown(bericht, datum)
    (tag_dir / "bericht.md").write_text(bericht_md, encoding="utf-8")
    try:
        log.info("Uebersetze Bericht ins Englische (Sonnet) ...")
        (tag_dir / "bericht_en.md").write_text(
            bericht_uebersetzen(bericht_md), encoding="utf-8")
    except Exception as e:
        # Die englische Fassung ist ein Zusatzprodukt - ihr Scheitern darf
        # weder Versand noch Veroeffentlichung des deutschen Berichts stoppen.
        log.warning("Englische Uebersetzung fehlgeschlagen (deutscher "
                    "Bericht unberuehrt): %s", e)
    try:
        log.info("Erzeuge Video-Titel (Sonnet) ...")
        titel = titel_generieren(bericht_md, datum)
        (tag_dir / "titel.json").write_text(
            json.dumps(titel, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        log.info("Video-Titel: %s", titel["de"])
    except Exception as e:
        # Ohne titel.json nimmt video_report.py den statischen Serientitel -
        # ein Titelfehler darf den Upload nie verhindern.
        log.warning("Titel-Generierung fehlgeschlagen (Video nimmt den "
                    "statischen Serientitel): %s", e)
    (tag_dir / "README.md").write_text(
        _tag_readme_bauen(manifest, datum, tag_dir), encoding="utf-8")
    markdown_index_aktualisieren()
    git_veroeffentlichen([tag_dir, EXTRAKTE / "README.md"], f"Bericht vom {datum}")


def stufe3(manifest: dict, eDir: Path, arbeit: Path, empfaenger: str,
           versand: str, datum: str) -> str:
    meta_nach_thread = {str(b["thread"]): b for b in manifest["buendel"]}
    extrakte = sandwich(sorted(eDir.glob("*.txt")), meta_nach_thread)
    anteil = len(extrakte) / max(1, len(manifest["buendel"]))
    luecke = ""
    if anteil < MIN_EXTRAKTE:
        luecke = (f"ACHTUNG: nur {len(extrakte)} von {len(manifest['buendel'])} "
                  "Threads konnten ausgewertet werden. Weise im Bericht in der "
                  "ersten Zeile darauf hin, dass die Lage unvollstaendig erfasst ist.")

    vorbericht = voriger_bericht(datum)
    delta_block = ""
    if vorbericht:
        vor_text, vor_url = vorbericht
        delta_block = f"""
GESTRIGER BERICHT (nur zum Abgleich, NICHT Teil der heutigen Extrakte):
Quelle: {vor_url}
{"=" * 74}
{vor_text}
{"=" * 74}
"""
    teile = [
        f"DATENSTAND: {manifest.get('snapshot_zeit_lokal')} Ortszeit (Europe/Zurich)",
        f"BOARD: {manifest.get('threads_im_board')} Threads im Katalog",
        f"AUSGEWERTETE THREADS: {len(extrakte)} von {len(manifest['buendel'])}",
        "",
    ]
    for e in extrakte:
        t = e.stem
        m = meta_nach_thread.get(t, {})
        modus = m.get("modus", "voll")
        hinweis = {
            "voll": "vollstaendig gelesen",
            "delta": f"fortgeschrieben, {m.get('neue_posts', 0)} neue Posts seit dem letzten Lauf",
            "unveraendert": "unveraendert seit dem letzten Lauf, keine neuen Posts",
        }.get(modus, modus)
        teile += [
            "=" * 74,
            f"THREAD {t} - {m.get('betreff', '')}",
            f"URL: {m.get('url', '')}",
            (f"Posts: {m.get('posts_gesamt')} | Alter: {m.get('alter_h')} h | "
             f"letzte Stunde: {m.get('posts_letzte_stunde')} | "
             f"ausgewaehlt weil: {'; '.join(m.get('rollen', []))}"),
            f"Stand des Extrakts: {hinweis}",
            "=" * 74,
            ohne_cache_abschnitte(e.read_text(encoding="utf-8", errors="replace")),
            "",
        ]
    if delta_block:
        teile.append(delta_block)
    eingabe = "\n".join(teile)
    (arbeit / "synthese_eingabe.txt").write_text(eingabe, encoding="utf-8")

    versand_block = (
        f"""Versende den fertigen Bericht anschliessend mit mcp__gmail__send_email:
  Empfänger: {empfaenger}
  Betreff: "/biz/ Lagebericht {datetime.now().strftime('%d.%m.%Y')}"
  Body: der Bericht als reiner Text, OHNE den Block ABDECKUNG
Lege dabei KEINE Dateien an und ändere nichts auf der Platte."""
        if versand == "mcp" else
        "Der Versand erfolgt ausserhalb dieses Aufrufs. Gib den Bericht nur aus, "
        "verschicke nichts und lege keine Dateien an."
    )

    # Dieser Prompt ist bewusst in korrektem Deutsch mit Umlauten geschrieben,
    # anders als die Extraktions-Prompts: das Modell ahmt den Stil der Anweisung
    # nach, und ein Prompt in ae/oe/ue-Ersatzschreibung erzeugt einen Bericht
    # in ae/oe/ue-Ersatzschreibung.
    prompt = f"""Du erhältst per Eingabe strukturierte Extrakte aus mehreren Threads des
4chan-Boards /biz/ (Business & Finance). Ein günstigeres Modell hat sie zuvor
aus den Volltexten gezogen. Schreibe daraus den täglichen Lagebericht.

{luecke}

Der Leser ist ein interessierter Anleger, der das Board nicht kennt und die
Fachsprache nicht beherrscht. Er will das WISSEN aus den Posts: welche Titel
und Coins genannt werden, welche konkreten Zahlen fallen, welche Thesen mit
welcher Begründung vertreten werden, welche Quellen geteilt werden, was
praktisch verwertbar ist.

Regeln:
1. Deutscher Klartext, KEINE Markdown-Formatierung, keine Sternchen, keine
   Raute-Überschriften. Überschriften in Grossbuchstaben auf eigener Zeile.
2. RECHTSCHREIBUNG: durchgehend korrektes Deutsch mit echten Umlauten - ä, ö,
   ü, Ä, Ö, Ü. Ersatzschreibungen wie ae, oe, ue sind FALSCH und dürfen im
   Bericht nicht vorkommen, auch nicht in Überschriften. Also "für", "über",
   "Verhältnis", "GESCHÄFTSZAHLEN" - nicht "fuer", "ueber", "Verhaeltnis".
   In den Extrakten stehen stellenweise Ersatzschreibungen; korrigiere sie.
   Schweizer Schreibweise: "ss" statt "ß" ist richtig so.
3. Beginne mit einer Zeile "Datenstand: TT.MM.JJJJ HH:MM Ortszeit" aus der
   Angabe DATENSTAND der Eingabe, dazu die Zahl der ausgewerteten Threads.
4. Länge: rund 700 bis 1000 Wörter für den Berichtsteil.
   Lieber konkret und dicht als vollständig - aber jede genannte Sache muss
   nachvollziehbar sein.
4b. LESBARKEIT, wichtig: Die Mail wird überflogen, nicht studiert.
   - Absätze von höchstens vier Sätzen. Danach eine Leerzeile.
   - Folgen mehrere Zahlen, Fakten oder Argumente aufeinander, schreibe sie
     als Aufzählung: jede Zeile beginnt mit "- ". Nicht in einen langen Satz
     packen. Faustregel: ab drei zusammengehörigen Angaben eine Aufzählung.
   - Der erste Satz eines Abschnitts sagt das Ergebnis, nicht die Vorgeschichte.
   - Keine Schachtelsätze mit mehr als einem Nebensatz.
5. Gliederung des Berichtsteils nach Themen, wichtigstes zuerst. Sinnvolle
   Überschriften wählen, zum Beispiel AKTIEN, KRYPTO, MAKRO UND GEOPOLITIK,
   GERADE SCHNELL FÜLLEND. Ein Thema, zu dem es nichts gibt, weglassen.
6. Nenne konkrete Zahlen mit ihrer Bedeutung, und nenne pro Punkt die URL.
   Zahlen ab tausend mit Apostroph als Tausendertrennzeichen: 1'234'567.
7. Trenne Behauptung von Belegtem. Poster-Behauptungen als solche
   kennzeichnen ("ein Poster rechnet vor", "unbelegt"). Wo eine externe Quelle
   geteilt wurde, nenne sie.
8. Ton, Beschimpfungen, Provokationen und Gruppendynamik gehören NICHT in den
   Bericht. Wer mit wem streitet, ist kein Befund. Steckt in einem
   Streit-Thread eine anlagerelevante Aussage, gib nur diese wieder.
9. Zu jedem Thread ist angegeben, ob sein Extrakt vollständig gelesen oder
   seit dem letzten Lauf nur fortgeschrieben wurde. Nutze das, um NEUES von
   Dauerzuständen zu trennen: was seit gestern dazukam, gehört nach vorn.
   Der Abschnitt NEU SEIT DEM LETZTEN LAUF in den Extrakten sagt dir das.
   Ein Thread, der als unverändert gekennzeichnet ist, liefert Hintergrund,
   aber keine Neuigkeit - stelle ihn nicht als aktuelle Entwicklung dar.
9b. NICHT WIEDERHOLEN, WAS SCHON IM GESTRIGEN BERICHT STAND (falls einer als
    GESTRIGER BERICHT mitgegeben ist - sonst schreibst du wie gewohnt
    vollständig). Vergleiche Thema für Thema mit dem gestrigen Bericht:
    - Ist ein Thema seit gestern inhaltlich unverändert (keine neuen Zahlen,
      Thesen, Quellen, Kursziele), schreibe es NICHT erneut aus. Schreibe
      stattdessen GENAU EINEN Satz, der das Thema so konkret benennt, dass
      der Leser OHNE Klick weiss, worum es geht - nenne die Kernaussage oder
      die wichtigste Zahl, nicht nur ein Schlagwort ("Halbleiter-Debatte:
      unverändert" ist zu wenig, "Halbleiter-Debatte (ASML-Monopol bei
      Lithographie, Logic- gegen Memory-Chips): unverändert seit dem
      Vortag" ist richtig). Danach die URL des gestrigen Berichts aus der
      Zeile "Quelle:" oben, unverändert übernommen, auf eigener Zeile.
    - Hat sich etwas geändert oder ist neu dazugekommen, schreibe NUR das
      Neue ausführlich; den unveränderten Hintergrund dazu fasse in einem
      Halbsatz zusammen (wie oben, mit Verweis-URL), nicht neu erklären.
    - Ein Thema, das im gestrigen Bericht gar nicht vorkam, ist komplett neu
      und wird wie gewohnt vollständig geschrieben, ganz ohne Verweiszeile.
    - Verwechsle "Thread unverändert" (Extrakt-Metadatum) nicht mit "Thema
      unverändert": Ein Thread kann neue Posts haben, ohne dass sich am
      berichtsrelevanten Thema etwas ändert - dann gilt trotzdem diese Regel.
10. Der Abschnitt GERADE SCHNELL FÜLLENDE THREADS beschreibt, was in diesen
    Threads INHALTLICH steht, nicht nur dass sie schnell wachsen. Nenne den
    Beschleunigungsfaktor gegenüber dem eigenen Schnitt des Threads, wo er in
    den Metadaten steht. Ein Thread, in dem ausser dem Betreff nichts steht,
    wird als solcher benannt.
11. Beurteile am Ende jedes Themas knapp die Verlässlichkeit, wenn die
    Extrakte Anzeichen für Eigeninteresse oder Werbung nennen.
12. Poster-IDs gelten pro Thread und sind manipulierbar: als Obergrenze
    behandeln, keine Aussagen über echte Personenzahlen.
13. Schreibe KEIN Glossar: es wird nach dir automatisch aus den Extrakten
    erzeugt und angehängt. Fachbegriffe und Jargon darfst du im Bericht
    verwenden, ohne sie zu erklären.
14. VOLLSTÄNDIGKEIT: Jeder Thread der Eingabe ist entweder im Bericht
    verwendet oder bewusst ausgelassen - nichts fällt stillschweigend weg.
    Rechenschaft darüber legst du im Block ABDECKUNG ab (siehe Ausgabe).

{versand_block}

WICHTIG zur Ausgabe, in genau dieser Reihenfolge:
1. Der vollständige Bericht, so wie er in die Mail gehört.
2. Eine Zeile "ABDECKUNG:", danach je Thread der Eingabe genau eine Zeile:
      <Thread-Nummer>: verwendet
   oder
      <Thread-Nummer>: ausgelassen - <Grund in wenigen Worten>
   Jede Thread-Nummer der Eingabe kommt genau einmal vor. Dieser Block
   gehört NICHT in die Mail und zählt nicht zur Wortzahl des Berichts.
3. Als allerletzte Zeile genau eine Statuszeile:
   STATUS: GESENDET
oder, wenn der Versand fehlschlug:
   STATUS: FEHLER - kurze Ursache in wenigen Worten
Gib den Bericht auch dann vollständig aus, wenn der Mailversand scheitert.
Der Bericht selbst enthält keine Meta-Bemerkungen über diese Anweisung.
"""
    if versand != "mcp":
        prompt = prompt.replace("   STATUS: GESENDET", "   STATUS: FERTIG")

    tools = "mcp__gmail__send_email" if versand == "mcp" else None
    log.info("Stufe 3: Synthese mit Opus (%d Extrakte, %d KB)",
             len(extrakte), len(eingabe) // 1024)
    return claude_ruf(prompt, eingabe, "opus", TIMEOUT_SYNTH, tools=tools)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("BOARDSTATS_HOST"),
                    help="ssh-Ziel fuer bundle_biz.py; leer = lokal")
    # Bewusst bei 15 belassen (Entscheid 08.08.2026): weniger Quellen loesen
    # das Abdeckungsproblem nicht (DiverseSumm, arXiv 2309.09369: <40 %
    # Coverage schon bei 10 Quellen), sie kosten nur Substanz. Gegen den
    # Positions-Bias wirken sandwich() und der ABDECKUNG-Block.
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--empfaenger", default="claudio.lutz.cv@gmail.com")
    ap.add_argument("--versand", choices=["mcp", "smtp", "keiner"], default="mcp")
    ap.add_argument("--kein-cache", action="store_true",
                    help="alle Threads voll lesen (Neuaufbau des Caches)")
    ap.add_argument("--kein-github", action="store_true",
                    help="Extrakte nicht als Markdown ablegen und veroeffentlichen")
    args = ap.parse_args()

    setup_logging()
    log.info("=== Start (host=%s, versand=%s) ===", args.host or "lokal", args.versand)

    if args.kein_cache:
        (CACHE / "status.json").unlink(missing_ok=True)
        log.info("Cache-Status verworfen - alle Threads werden voll gelesen")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    arbeit = ARBEIT / stamp
    bDir, eDir = arbeit / "bundles", arbeit / "extrakte"
    bDir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    manifest = stufe1(args.host, args.top, bDir)
    zaehl: dict[str, int] = {}
    for b in manifest["buendel"]:
        zaehl[b["modus"]] = zaehl.get(b["modus"], 0) + 1
    kb = sum(b.get("zeichen", 0) for b in manifest["buendel"]) // 1024
    log.info("Stufe 1 ok in %ds: %d Threads (%s), %d KB, Datenstand %s",
             time.time() - t0, len(manifest["buendel"]),
             ", ".join(f"{v}x {k}" for k, v in sorted(zaehl.items())),
             kb, manifest.get("snapshot_zeit_lokal"))

    t1 = time.time()
    ergebnisse = stufe2(manifest, bDir, eDir)
    fehler = {t: v for t, v in ergebnisse.items() if v.startswith("fehler")}
    log.info("Stufe 2 fertig in %ds: %d Extrakte (%s), %d Fehler",
             time.time() - t1, len(ergebnisse) - len(fehler),
             ", ".join(f"{v}x {k}" for k, v in sorted(
                 {a: list(ergebnisse.values()).count(a)
                  for a in set(ergebnisse.values()) if not a.startswith("fehler")}.items())),
             len(fehler))
    for t, v in fehler.items():
        log.warning("  Thread %s: %s", t, v)

    if not list(eDir.glob("*.txt")):
        log.error("kein einziger Extrakt - Abbruch ohne Bericht")
        return 1

    cache_pflegen(manifest, eDir, ergebnisse)

    # Die Extrakte oeffentlich als Markdown ablegen, unabhaengig davon, ob die
    # Synthese anschliessend gelingt - sie sind ein eigenstaendiges Ergebnis
    # dieses Laufs. Ein Fehlschlag hier (kein Netz, kein Git) darf den
    # Bericht nicht verhindern. tag_dir wird unten nochmal gebraucht, um den
    # fertigen Bericht in denselben Tagesordner zu legen.
    datum = datetime.now().strftime("%Y-%m-%d")
    tag_dir = None
    if not args.kein_github:
        tag_dir = markdown_tag_schreiben(manifest, eDir, datum)
        if tag_dir is not None:
            markdown_index_aktualisieren()
            git_veroeffentlichen([tag_dir, EXTRAKTE / "README.md"],
                                 f"Extrakte vom {datum}")

    t2 = time.time()
    try:
        out = stufe3(manifest, eDir, arbeit, args.empfaenger, args.versand, datum)
    except subprocess.TimeoutExpired:
        log.error("Synthese ueberschritt %ds - kein Bericht", TIMEOUT_SYNTH)
        return 1

    BERICHTE.mkdir(parents=True, exist_ok=True)
    ziel = BERICHTE / f"{datetime.now().strftime('%Y-%m-%d')}.txt"

    # Die STATUS-Zeile ist der Vertrag: fehlt sie, ist die Ausgabe kein Bericht,
    # sondern eine Fehlermeldung des CLI. Die darf nie als Tagesbericht unter
    # ziel landen und einen echten Bericht ueberschreiben.
    status = [z for z in out.splitlines() if z.startswith("STATUS:")]
    if not status:
        (BERICHTE / f"{ziel.name}.fehler").write_text(out, encoding="utf-8")
        log.error("keine STATUS-Zeile - Rohausgabe in %s.fehler", ziel.name)
        return 1

    if ziel.exists():
        shutil.copy2(ziel, ziel.with_suffix(f".txt.bak-{stamp}"))
    bericht = "\n".join(z for z in out.splitlines() if not z.startswith("STATUS:")).strip()

    # Rechenschaft ueber die Thread-Nutzung: gehoert ins Log, nicht in die Mail.
    # Am 06.08. blieben 4 von 14 Extrakten unerwaehnt, ohne dass ein Grund
    # sichtbar war - jetzt muss die Synthese jeden Wegfall begruenden.
    bericht, abdeckung = abdeckung_trennen(bericht)
    if abdeckung:
        (arbeit / "abdeckung.txt").write_text(abdeckung + "\n", encoding="utf-8")
        ausgelassen = [z.strip() for z in abdeckung.splitlines()
                       if "ausgelassen" in z.lower()]
        log.info("Abdeckung: %d Threads ausgelassen", len(ausgelassen))
        for z in ausgelassen:
            log.info("  %s", z)
    else:
        log.warning("kein ABDECKUNG-Block in der Synthese-Ausgabe")

    glossar = glossar_bauen(bericht, eDir)
    if glossar:
        bericht = bericht + "\n\n" + glossar
    ziel.write_text(bericht + "\n", encoding="utf-8")
    log.info("Stufe 3 fertig in %ds, Bericht gespeichert: %s",
             time.time() - t2, ziel)

    if not args.kein_github:
        bericht_veroeffentlichen(bericht, datum, tag_dir, manifest)

    if args.versand == "smtp":
        from send_mail import versende
        try:
            versende(args.empfaenger,
                     f"/biz/ Lagebericht {datetime.now().strftime('%d.%m.%Y')}",
                     bericht)
            log.info("=== OK: per SMTP versandt ===")
        except Exception as e:                      # noqa: BLE001
            log.error("=== NICHT ZUGESTELLT: %s === Bericht liegt unter %s", e, ziel)
            return 1
    else:
        log.info("=== %s ===", status[-1].strip())
        # Am 07.08. meldete die Aufgabenplanung Erfolg (LastTaskResult 0),
        # obwohl gar keine Mail rausging. Ein misslungener Versand muss als
        # Fehler sichtbar sein, sonst faellt der Ausfall tagelang nicht auf.
        if args.versand == "mcp" and "GESENDET" not in status[-1]:
            log.error("Bericht liegt unter %s bereit, wurde aber nicht zugestellt", ziel)
            return 1

    for alt in sorted(ARBEIT.iterdir(), reverse=True)[LAEUFE_BEHALTEN:]:
        if alt.is_dir():
            shutil.rmtree(alt, ignore_errors=True)
    log.info("Gesamtdauer %d min", (time.time() - t0) / 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
