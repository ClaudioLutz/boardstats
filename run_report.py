#!/usr/bin/env python3
"""/biz/ Lagebericht - dreistufige Pipeline mit Extrakt-Cache.

Warum dreistufig: Ein einzelnes Modell bekam frueher den auf 22 KB verdichteten
Report. Genau diese Verdichtung warf das Detail weg, das den Bericht wertvoll
macht (Strikes, Guidance, Bezugsquellen, "welches Verfahren eigentlich").
Stattdessen liest ein guenstigeres Modell je einen ganzen Thread; nur die
Extrakte gehen an das teure Modell, das den Bericht schreibt.

  Stufe 1  bundle_biz.py schneidet Volltext-Buendel
  Stufe 2  Sonnet extrahiert je Buendel (parallel, Ergebnis je Datei)
  Stufe 3  Opus synthetisiert den Bericht und veroeffentlicht ihn

Seit 16.08.2026 laeuft die gesamte Pipeline auf Englisch: das Board ist
englisch, und jede Uebersetzung ins Deutsche (frueher: deutsche Extrakte,
deutscher Bericht, Rueckuebersetzung fuer das Video) verlor den Jargon und
den Boardhumor. Extrakte, Bericht, Titel und Folien entstehen jetzt direkt
in der Originalsprache; der fruehere Mailversand ist abgebaut.

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
import gzip
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image

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
               tools: str | None = None, cwd: Path | None = None,
               effort: str | None = None) -> str:
    """Ein headless-Aufruf. Die Eingabe geht ueber stdin, nicht ueber die
    Kommandozeile: Windows kappt Kommandozeilen bei ~32767 Zeichen, und die
    Buendel sind groesser.

    cwd wird nur dort gesetzt, wo der Aufruf Dateien lesen soll (Sichtpruefung
    der Bildkandidaten) - Werkzeuge duerfen nur unterhalb des Arbeitsordners
    zugreifen. Die uebrigen Aufrufe bleiben bewusst ohne.

    effort bleibt fuer Titel/Folien/Synthese auf None (CLI-Default "high"):
    dort kostet ein Fehlurteil (falscher Anker, luecklige Synthese) mehr als
    das Thinking-Budget einspart. Extraktion und Sichtpruefung laufen mit
    "low" - reines Format-Ausfuellen bzw. Klassifikation nach festen
    Kriterien, ohne Mehrwert durch tieferes Nachdenken, dafuer mit hohem
    Aufrufvolumen (20.08.2026)."""
    cmd = [claude_pfad(), "-p", prompt, "--model", modell,
           "--output-format", "text"]
    if effort:
        cmd += ["--effort", effort]
    if tools:
        cmd += ["--allowedTools", tools]
    r = subprocess.run(cmd, input=eingabe, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout,
                       cwd=cwd)
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
            "PART 1 - EXISTING EXTRACT FOR THIS THREAD\n"
            + "=" * 70 + "\n"
            + alt.read_text(encoding="utf-8", errors="replace")
            + "\n\n" + "=" * 70 + "\n"
            + "PART 2 - POSTS THAT ARRIVED SINCE THEN\n"
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
            prompt + "\n\nIMPORTANT: Respond ONLY with the sections, starting "
            "with the line TOPIC. No follow-up question, no introduction, no "
            "asking about the purpose.")
        try:
            r = claude_ruf(p, eingabe, "sonnet", TIMEOUT_EXTRAKT, effort="low")
        except subprocess.TimeoutExpired:
            return rueckfall("Zeitueberschreitung")
        except OSError as e:
            return rueckfall(str(e))
        # Nur brauchbar, wenn es wie ein Extrakt aussieht - sonst ist es eine
        # Rueckfrage oder eine CLI-Fehlermeldung und wuerde die Synthese mit
        # Muell fuellen.
        if "TOPIC" in r:
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
# und update_prompt.txt; seit 16.08.2026 englisch). MOOD AND MEMES traegt
# den Boardhumor woertlich in die Synthese - der Grund fuer die Umstellung
# der ganzen Pipeline auf Englisch.
ABSCHNITTE = (
    "TOPIC", "TICKERS AND COINS", "HARD NUMBERS",
    "CLAIMS AND ARGUMENTS", "MOOD AND MEMES", "PRACTICAL", "SOURCES",
    "TERMS AND SLANG", "OPEN QUESTIONS", "RELIABILITY",
    "NEW SINCE LAST RUN",
)
# Diese Abschnitte bleiben im Extrakt-Cache (er ist das Gedaechtnis des
# Threads), gehen aber nicht mehr in die Synthese: gemessen am 06.08. blieben
# 94 % der Glossar-Eintraege ungenutzt (19 von 293 kamen im Bericht vor), und
# irrelevanter Kontext verschlechtert nachweislich die Nutzung des Rests
# ("context rot"). Das Glossar entsteht stattdessen in glossar_bauen().
NUR_CACHE = ("TERMS AND SLANG", "OPEN QUESTIONS")


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
    """Das Glossar deterministisch statt vom Modell: aus den TERMS-AND-SLANG-
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
                drin = s == "TERMS AND SLANG"
                continue
            if not drin or not s:
                continue
            s = s.lstrip("-•*").strip()
            if not s or s.lower() in ("none", "keine"):
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
    # Bericht als Markdown veroeffentlicht wird.
    return "GLOSSARY\n\n" + "\n".join(f"- {b} - {e}" for b, e in treffer[:maximal])


def abdeckung_trennen(text: str) -> tuple[str, str]:
    """Der COVERAGE-Block (je Thread: verwendet oder ausgelassen mit Grund)
    ist Rechenschaft fuer das Log, nicht fuer den Leser - er wird vor der
    Veroeffentlichung abgetrennt."""
    zeilen = text.splitlines()
    for i, z in enumerate(zeilen):
        if z.strip().rstrip(":").upper() in ("COVERAGE", "ABDECKUNG"):
            return ("\n".join(zeilen[:i]).rstrip(),
                    "\n".join(zeilen[i + 1:]).strip())
    return text, ""


# Schoene Ueberschriften fuer die oeffentliche Markdown-Fassung. Die rohen
# Abschnittsnamen (Vertrag mit den Extraktions-Prompts) bleiben in Grossschrift,
# damit ABSCHNITTE weiterhin fuer beide Zwecke passt.
ABSCHNITT_TITEL = {
    "TOPIC": "Topic",
    "TICKERS AND COINS": "Tickers and coins",
    "HARD NUMBERS": "Hard numbers",
    "CLAIMS AND ARGUMENTS": "Claims and arguments",
    "MOOD AND MEMES": "Mood and memes",
    "PRACTICAL": "Practical",
    "SOURCES": "Sources",
    "TERMS AND SLANG": "Terms and slang",
    "OPEN QUESTIONS": "Open questions",
    "RELIABILITY": "Reliability",
    "NEW SINCE LAST RUN": "New since last run",
    # Alt-deutsche Ueberschriften (Archiv-Seiten bis 16.08.2026), damit
    # extrakt_zu_markdown gemischte Cache-Uebergaenge sauber rendert.
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
    "voll": "read in full",
    "delta": "incrementally updated",
    "unveraendert": "unchanged since the last run",
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
        f"Source: [4chan /biz/ thread {meta.get('thread', '')}]"
        f"({meta.get('url', '')}) &middot; as of {datum} &middot; {modus}"
        + (f" &middot; {meta['posts_gesamt']} posts in total"
           if meta.get("posts_gesamt") is not None else ""),
        "",
        "Generated automatically from public posts on the board /biz/ by a "
        "language model. Poster statements are claims, not facts, and not "
        "financial advice.",
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
    zeilen = [f"# /biz/ Situation Report: {datum}", ""]
    if (tag_dir / "bericht.md").exists():
        zeilen += ["[Report of the day](bericht.md)", ""]
    zeilen += [f"{len(eintraege)} threads, by substance density.", "",
               "| Thread | Mode | Posts | Substance |", "|---|---|---|---|"]
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
        "# /biz/ Situation Report: extract archive", "",
        "Daily, structurally extracted summaries of threads from the 4chan "
        "board /biz/ (Business & Finance). A language model reads each thread "
        "and pulls out topic, mentioned tickers/coins, hard numbers, claims "
        "with their reasoning, sources and jargon - discourse documentation, "
        "not financial advice. Part of the [boardstats](..) project. "
        "Days up to 2026-08-15 are in German, later days in English.", "",
        "| Date | Threads |", "|---|---|",
    ]
    for t in tage:
        anzahl = len([p for p in t.glob("*.md")
                      if p.name not in ("README.md", "bericht.md")])
        bericht_stern = " (with report)" if (t / "bericht.md").exists() else ""
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
    """Der fertige Bericht als eigenstaendige, oeffentliche Markdown-Seite.
    Die Ueberschriften-Erkennung (bericht_html._ist_ueberschrift) stammt noch
    aus der Mail-Zeit und funktioniert sprachunabhaengig fuer Grossbuchstaben-
    Zeilen - Aufzaehlungen sind schon "- "-Zeilen, also gueltiges Markdown,
    und muessen nicht extra umgeformt werden."""
    zeilen = bericht.replace("\r\n", "\n").split("\n")
    kopf = ""
    if zeilen and zeilen[0].lower().startswith("data as of"):
        kopf = zeilen[0].strip()
        zeilen = zeilen[1:]

    koerper = [f"## {z.strip()}" if z.strip() and ist_ueberschrift(z.strip()) else z
               for z in zeilen]
    return (
        f"# /biz/ Situation Report {datum}\n\n"
        + (f"*{kopf}*\n\n" if kopf else "")
        + "[Extracts and source threads of the day](README.md)\n\n---\n\n"
        + "\n".join(koerper).strip() + "\n"
    )


# Die Hooks sind bewusst reisserisch (Entscheid 14.08.2026: voll Clickbait,
# Hook + Serien-Suffix, keine Emoji, keine Wiederholung ueber die Tage).
# Seit 16.08.2026 nur noch englisch, im nativen Jargon des Boards.
TITEL_PROMPT = """\
You get today's /biz/ situation report (Markdown, English), possibly
followed by a block TITLES ALREADY USED.

Write one sensational title hook for today's YouTube video.

Rules:
- Pick the ONE most compelling story of the report: the biggest
  development, the largest number or the sharpest conflict.
- Full clickbait: pointed, urgent, one or two words in CAPITAL LETTERS.
  No emoji. Invent nothing: every statement of the hook must be backed by
  the report.
- Write in the native voice of the board /biz/ - its jargon and meme
  language are welcome where the report supports them.
- At most 75 characters, no period at the end.
- No em dash in the hook: use a colon or comma instead.
- If a block TITLES ALREADY USED is present, none of those hooks and no
  close paraphrase of them may return. If the topic of the day is the
  same, pick a different angle, a new number or a new twist.

Also write the keyword for the video's thumbnail: at most three words and
20 characters, the core of the hook (like "CHAIN SPLIT" or "$2 TRILLION").
It is printed on the image in large letters and must stay readable on a
phone, so no full sentences and no punctuation.

Output ONLY one JSON object, no preamble, no postscript, no code fence:
{"hook": "...", "thumb": "..."}
"""

TITEL_SUFFIX = " | /biz/ "
THUMB_MAX_ZEICHEN = 20  # Schlagwort fuers Vorschaubild, Handy-Lesbarkeit


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
        if not isinstance(daten, dict):
            continue
        # Nur die Titel selbst: titel.json fuehrt daneben die Schlagworte
        # fuers Vorschaubild, die keine Wiederholungssperre brauchen.
        for schluessel in ("de", "en"):
            wert = daten.get(schluessel)
            if isinstance(wert, str) and wert.strip():
                titel.append(wert)
    return titel


def _hook_bereinigen(hook: str) -> str:
    # "<" und ">" sind in YouTube-Titeln verboten; der lange Gedankenstrich
    # ist im Titel unerwuenscht (Schreibstil-Vorgabe fuer externe Texte);
    # 75 Zeichen lassen dem Serien-Suffix Platz unter dem 100-Zeichen-Limit.
    hook = hook.replace("<", "").replace(">", "").replace(" — ", ": ").replace("—", "-")
    return re.sub(r"\s+", " ", hook).strip()[:75].rstrip()


def _thumb_bereinigen(schlagwort: str, hook: str) -> str:
    """Schlagwort fuers Vorschaubild: Grossbuchstaben, keine Satzzeichen,
    hoechstens THUMB_MAX_ZEICHEN. Fehlt es oder bleibt nichts uebrig, wird es
    aus dem Hook abgeleitet - dessen grossgeschriebene Woerter sind genau die
    Zuspitzung, die aufs Bild gehoert."""
    def saeubern(roh: str) -> str:
        return re.sub(r"\s+", " ",
                      re.sub(r"[^0-9A-Za-zÄÖÜäöü %$&+.-]+", " ", roh)).strip().upper()

    kandidat = saeubern(schlagwort)
    if not kandidat:
        gross = [w for w in hook.split() if len(w) > 2 and w.isupper()]
        kandidat = saeubern(" ".join(gross) or hook)
    aus = ""
    for wort in kandidat.split()[:3]:
        if aus and len(f"{aus} {wort}") > THUMB_MAX_ZEICHEN:
            break
        aus = f"{aus} {wort}".strip()
    return aus[:THUMB_MAX_ZEICHEN].strip()


def _hook_normalisiert(hook: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\wäöüÄÖÜ ]+", "", hook.lower())).strip()


def _json_schneiden(out: str) -> str:
    """Das JSON-Objekt aus einer Modell-Antwort schneiden. Trotz "nur JSON"
    im Prompt stellt das Modell gelegentlich einen Satz voran (16.08.2026:
    "All within limits." vor dem ```json-Zaun - der Titel fiel deshalb auf
    den Serientitel zurueck). Ein Zaun irgendwo in der Antwort gewinnt,
    sonst zaehlt das aeusserste {...}."""
    zaun = re.search(r"```(?:json)?\s*(\{.*\})\s*```", out, re.DOTALL)
    if zaun:
        return zaun.group(1)
    anfang, ende = out.find("{"), out.rfind("}")
    if anfang != -1 and ende > anfang:
        return out[anfang:ende + 1]
    return out


def titel_generieren(bericht_md: str, datum: str) -> dict[str, str]:
    """Reisserischer Tagestitel (Hook + Serien-Suffix, englisch) in einem
    Sonnet-Aufruf. Die bisherigen Titel gehen mit, und ein wiederholter Hook
    bekommt genau einen zweiten Versuch - danach ist der statische
    Serientitel (Fallback in video_report.py) die bessere Antwort.
    Die JSON-Schluessel "en"/"thumb_en" bleiben, wie video_report.py sie
    liest - auch nach dem Wegfall der deutschen Fassung (16.08.2026)."""
    gebraucht = bisherige_titel(datum)
    gesehen = {_hook_normalisiert(t.split(TITEL_SUFFIX)[0]) for t in gebraucht}
    eingabe = bericht_md
    if gebraucht:
        eingabe += ("\n\nTITLES ALREADY USED:\n"
                    + "\n".join(f"- {t}" for t in gebraucht))

    hinweis = ""
    hook = ""
    for _ in range(2):
        out = claude_ruf(TITEL_PROMPT + hinweis, eingabe, "sonnet",
                         TIMEOUT_TITEL).strip()
        out = _json_schneiden(out)
        # Plausibilitaet: eine CLI-Fehlermeldung parst nie als genau dieses
        # JSON.
        try:
            daten = json.loads(out)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Titel-Ausgabe kein JSON: {out[:200]!r}") from e
        hook = _hook_bereinigen(str(daten.get("hook") or ""))
        if not hook:
            raise RuntimeError(f"Titel-Ausgabe unvollstaendig: {out[:200]!r}")
        if _hook_normalisiert(hook) not in gesehen:
            # Das Bild-Schlagwort ist Beiwerk: fehlt es, wird es aus dem Hook
            # abgeleitet statt den ganzen Titel scheitern zu lassen.
            return {"en": f"{hook}{TITEL_SUFFIX}{datum}",
                    "thumb_en": _thumb_bereinigen(
                        str(daten.get("thumb") or ""), hook)}
        hinweis = ("\nADDITION: Your last suggestion repeated a hook that was "
                   f"already used ({hook}) - you must pick a different angle.")
    raise RuntimeError(f"Hook wiederholt sich trotz zweitem Versuch: {hook!r}")


# -------------------------------------------- Drehbuch fuers Video (v7)

# Der Drehbuch-Prompt ist englisch wie der Bericht selbst: alle Ausgaben
# muessen im Wortlaut des Berichts verankert sein, denn die Anker-Phrasen
# steuern, wann ein Element waehrend der Vorlesung erscheint. Seit v7
# (16.08.2026) plant das Modell den Aufbau je Abschnitt selbst: Stichwort-
# Momente, optionale Zwischenthemen, ein Board-Zitat, eine Kennzahl - die
# Mischung soll von Abschnitt zu Abschnitt und von Tag zu Tag variieren.
FOLIEN_PROMPT = """\
You get today's /biz/ situation report (Markdown, English). The daily video
shows it as a moving picture story: full-screen board images while the
report is read aloud, with a persistent on-screen card (chapter title plus
bullet points that light up one by one and stay) carrying the narration.
You write the storyboard. Vary the mix from section to section - not every
section needs every element; pick what fits the material.

Output ONLY one JSON object, no preamble, no code fence:
{"abschnitte": [{"ueberschrift": "...", "titel": "...", "lage": "left",
                 "stichworte": [{"text": "...", "anker": "..."}, ...],
                 "zwischenthemen": [{"titel": "...", "anker": "...",
                                     "lage": "right"}, ...],
                 "zitat": {"text": "...", "anker": "..."},
                 "karte": {"wert": "...", "titel": "...", "sub": "...",
                           "anker": "..."}},
                ...],
 "zahlen": [{"wert": "...", "titel": "...", "sub": "...", "satz": "..."},
            ...]}

Anchors: every "anker" is 3 to 5 CONSECUTIVE words copied VERBATIM from the
section's body text (not from the heading). It times when the element
appears on screen while the report is read aloud - it must match the body
text exactly (capitalization does not matter), and all anchors of a section
must appear in the body in the same order as their elements. Never pick a
phrase containing a URL - links are not read aloud.

Rules per "## " section (one entry each, same order; skip the GLOSSARY):
- "ueberschrift": the section heading COPIED VERBATIM (without "## ").
- "titel": a short chapter title, max 44 characters, sentence case,
  no period.
- "lage": "left" or "right" - the screen side of the bullet card. Place it
  deliberately and switch sides between chapters so the frame stays fresh.
- "stichworte": the running commentary. One bullet for roughly EVERY
  sentence of the section - 8 to 14 for a normal section; never let two
  consecutive sentences pass without one. "text" is the on-screen bullet:
  2 to 6 punchy words, max 34 characters, tickers and figures welcome
  (e.g. "$120B CUT", "BTC BACK AT 61K", "SHORTS WIPED"). Each bullet
  paraphrases the sentence its anker sits in; together they must let a
  muted viewer follow the whole story.
- "zwischenthemen": 0 to 2 entries, ONLY when the section clearly switches
  to a second storyline. "titel" (max 40 characters) names the new
  sub-story; its anker sits where the switch happens. The bullet card
  restarts there ("lage" optional), so at least one stichwort must follow
  each switch.
- "zitat" (optional): the single best board one-liner quoted in the
  section, COPIED VERBATIM, max 130 characters, no slurs. Omit if the
  section has no quotable line.
- "karte" (optional): the ONE most striking figure of the section.
  "wert" max 12 characters as shown on screen (e.g. "$2 TRILLION",
  "70.28 %"), "titel" max 28 characters, "sub" max 32 characters, "anker"
  where the figure is spoken.
- Sections that only say "unchanged since yesterday": 2 stichworte,
  nothing else.

Rules for "zahlen" (the closing "Numbers of the day" segment):
- Exactly 4 entries, the most striking figures across the whole report.
- "wert" max 12 characters, "titel" max 28, "sub" max 32.
- "satz": one short spoken sentence for the narrator. TTS-friendly: write
  units out ("1.26 trillion dollars", not "$1.26T"), no abbreviations.
"""

TIMEOUT_FOLIEN = 420


def folien_generieren(bericht_md: str) -> dict:
    """Szenen-Drehbuch fuer das Video (ein Sonnet-Aufruf auf den fertigen
    Bericht). Liefert das geprueft geparste JSON-Objekt mit version=2;
    video_report.py erkennt daran das v7-Szenen-Layout."""
    out = claude_ruf(FOLIEN_PROMPT, bericht_md, "sonnet", TIMEOUT_FOLIEN)
    out = _json_schneiden(out.strip())
    try:
        daten = json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Drehbuch-Ausgabe kein JSON: {out[:200]!r}") from e
    abschnitte = daten.get("abschnitte") if isinstance(daten, dict) else None
    if not isinstance(abschnitte, list) or not abschnitte:
        raise RuntimeError(f"Drehbuch-Ausgabe ohne Abschnitte: {out[:200]!r}")
    for a in abschnitte:
        if not isinstance(a, dict) or not str(a.get("titel") or "").strip():
            raise RuntimeError("Drehbuch-Abschnitt ohne Titel")
        a["titel"] = str(a["titel"]).strip()[:60]
        lg = str(a.get("lage") or "").strip().lower()
        if lg in ("left", "right"):
            a["lage"] = lg
        else:
            a.pop("lage", None)
        stich = a.get("stichworte")
        a["stichworte"] = [
            {"text": str(p["text"]).strip()[:38],
             "anker": str(p.get("anker") or "").strip()}
            for p in (stich if isinstance(stich, list) else [])
            if isinstance(p, dict) and str(p.get("text") or "").strip()][:16]
        zwischen = a.get("zwischenthemen")
        a["zwischenthemen"] = [
            {"titel": str(z["titel"]).strip()[:44],
             "anker": str(z.get("anker") or "").strip(),
             **({"lage": str(z["lage"]).strip().lower()}
                if str(z.get("lage") or "").strip().lower()
                in ("left", "right") else {})}
            for z in (zwischen if isinstance(zwischen, list) else [])
            if isinstance(z, dict) and str(z.get("titel") or "").strip()][:2]
        zit = a.get("zitat")
        if isinstance(zit, dict) and str(zit.get("text") or "").strip():
            a["zitat"] = {"text": str(zit["text"]).strip()[:140],
                          "anker": str(zit.get("anker") or "").strip()}
        else:
            a.pop("zitat", None)
        if not (isinstance(a.get("karte"), dict)
                and str(a["karte"].get("wert") or "").strip()):
            a.pop("karte", None)
    zahlen = daten.get("zahlen")
    daten["zahlen"] = [z for z in zahlen if isinstance(z, dict)
                       and str(z.get("wert") or "").strip()][:4] \
        if isinstance(zahlen, list) else []
    daten["version"] = 2
    return daten


# ------------------------------------------------- Motiv fuers Vorschaubild

MOTIV_THREADS = 8        # so viele der substanzstaerksten Threads liefern Bilder
MOTIV_KANDIDATEN = 8     # so viele gehen an die Sichtpruefung
MOTIV_MIN_BREITE = 500   # schmaler wird auf der halben Bildflaeche matschig
MOTIV_MIN_HOEHE = 400
MOTIV_MAX_BYTES = 4_000_000
MOTIV_ENDUNGEN = (".jpg", ".jpeg", ".png", ".gif")
MOTIV_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a")
MOTIV_SEITE = (0.5, 2.2)  # Banner und schmale Streifen taugen nicht als Motiv
TIMEOUT_MOTIV = 420
BILD_BASIS = "https://i.4cdn.org/biz"
BILD_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; boardstats/1.0)"}

# Schon gezeigte Bilder (Video-Hintergruende und Thumbnail-Motive) werden
# per MD5 gemerkt und fuer VERWENDET_TAGE Tage nicht wiederverwendet -
# langlebige General-Threads wuerden sonst jeden Tag dieselben fruehen
# Anhaenge liefern. Analog zur 14-Tage-Sperrliste der Videotitel.
VERWENDET_DATEI = ARBEIT / "motive" / "verwendet.json"
VERWENDET_TAGE = 14


def verwendete_bilder(datum: str) -> dict[str, str]:
    """MD5 -> Datum der zuletzt gezeigten Bilder, beschnitten auf die
    letzten VERWENDET_TAGE Tage. Leer bei fehlender/kaputter Datei."""
    try:
        daten = json.loads(VERWENDET_DATEI.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    grenze = (date.fromisoformat(datum)
              - timedelta(days=VERWENDET_TAGE)).isoformat()
    return {m: d for m, d in daten.items()
            if isinstance(d, str) and d >= grenze}


def verwendete_merken(md5s: list[str], datum: str) -> None:
    """Die heute gezeigten Bilder in die Merkliste schreiben (alte Eintraege
    fallen beim Zurueckschneiden von selbst raus)."""
    liste = verwendete_bilder(datum)
    for m in md5s:
        liste[m] = datum
    VERWENDET_DATEI.parent.mkdir(parents=True, exist_ok=True)
    VERWENDET_DATEI.write_text(
        json.dumps(liste, indent=2, sort_keys=True) + "\n", encoding="utf-8")

MOTIV_PROMPT = """\
Du wählst das Motiv für das YouTube-Vorschaubild eines Nachrichtenvideos aus.
Die Kandidaten stammen aus den heute ausgewerteten Threads des 4chan-Boards
/biz/. Das ist ein "blue board", auf dem die Moderation nicht jugendfreies
Material entfernt; grob Anstössiges ist dort die Ausnahme. Deine Hauptfrage
ist deshalb nicht, ob ein Bild harmlos ist, sondern welches als Vorschaubild
am besten wirkt.

Sieh dir JEDES unten genannte Bild mit dem Read-Werkzeug an. Urteile nur nach
dem, was du wirklich siehst, und rate nichts.

Ein Bild ist NUR dann geeignet, wenn alles zutrifft:
- Es verstösst nicht gegen die YouTube-Richtlinien für Vorschaubilder: keine
  Nacktheit und nichts Sexualisiertes, keine Gewalt, kein Blut, keine Hass-
  oder Extremismus-Symbolik, keine Beschimpfungen im Bildtext, keine Drogen,
  keine reale Person in kompromittierender Lage.
- Es passt zum Video: entweder zum Thema des Tages, das dir in der Eingabe
  genannt wird, oder es ist ein typisches Motiv dieses Boards (gezeichneter
  Frosch oder Wojak, Trader-Meme, Kurschart, Krypto-Symbolik). Ein Bild ohne
  jeden Bezug zu Finanzen, Krypto oder der Bildsprache des Boards ist
  ungeeignet.
- Es wirkt als Vorschaubild: ein klar erkennbares Motiv, das auch klein noch
  wirkt. Screenshots mit viel Kleinschrift, nichtssagende Charts und reine
  Textbilder sind ungeeignet.
Beim ersten Punkt gilt im Zweifel Ablehnung, denn ein Richtlinienverstoss
kostet den Kanal. Bei den beiden anderen darfst du zugreifen: ein
brauchbares Board-Motiv ist besser als gar keines.

Gib NUR ein JSON-Objekt aus, ohne Vor- oder Nachbemerkungen und ohne
Code-Zaun. Die Beschreibung ist Pflicht und benennt sachlich, was auf genau
diesem Bild zu sehen ist:
{"bilder": [{"datei": "...", "beschreibung": "...", "geeignet": true,
"grund": "..."}], "wahl": "Dateiname des besten geeigneten Bildes oder null"}

Gewählt wird das stärkste geeignete Bild: bevorzugt eines mit Bezug zum
Thema des Tages, sonst das ausdrucksstärkste Board-Motiv. Ist keines
geeignet, ist die Wahl null.
"""


def _snapshot_posts(threads: set[str]) -> dict[str, list[dict]]:
    """Posts der genannten Threads aus dem juengsten Crawl-Snapshot. Leer,
    wenn keiner da ist: mit --host laeuft der Crawl auf einem anderen Rechner,
    dann gibt es hier keine Rohdaten und damit kein Board-Bild."""
    snapshots = sorted((BASE / "raw").glob("*.jsonl.gz"))
    if not snapshots:
        return {}
    posts: dict[str, list[dict]] = {}
    with gzip.open(snapshots[-1], "rt", encoding="utf-8") as f:
        for zeile in f:
            try:
                daten = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            no = str(daten.get("thread"))
            if no in threads:
                posts[no] = daten.get("posts") or []
    return posts


def motiv_kandidaten(manifest: dict,
                     gesperrt: set[str] | None = None) -> list[dict]:
    """Bild-Anhaenge der substanzstaerksten Threads des Tages. Nur was als
    Vorschaubild taugen kann: gaengiges Format, gross genug, nicht gespoilert,
    nicht geloescht, je Bild nur einmal und keines aus der Merkliste
    (gesperrt). OP-Bilder zuerst - sie tragen das Thema des Threads."""
    threads = [str(b["thread"]) for b in manifest.get("buendel", [])][:MOTIV_THREADS]
    posts = _snapshot_posts(set(threads))
    gesehen: set[str] = set()
    aus: list[dict] = []
    for no in threads:  # Reihenfolge des Manifests = Substanzdichte
        for post in posts.get(no, []):
            tim, ext = post.get("tim"), str(post.get("ext") or "").lower()
            if not tim or ext not in MOTIV_ENDUNGEN:
                continue
            # Gespoilerte Bilder sind ueberproportional NSFW, von Moderatoren
            # geloeschte gibt es ohnehin nicht mehr.
            if post.get("spoiler") or post.get("filedeleted"):
                continue
            breite, hoehe = post.get("w") or 0, post.get("h") or 0
            if (breite < MOTIV_MIN_BREITE or hoehe < MOTIV_MIN_HOEHE
                    or (post.get("fsize") or 0) > MOTIV_MAX_BYTES
                    or not MOTIV_SEITE[0] <= breite / hoehe <= MOTIV_SEITE[1]):
                continue
            md5 = str(post.get("md5") or tim)
            if md5 in gesehen or md5 in (gesperrt or set()):
                continue
            gesehen.add(md5)
            aus.append({"thread": no, "datei": f"{tim}{ext}",
                        "url": f"{BILD_BASIS}/{tim}{ext}", "md5": md5,
                        "op": (post.get("resto") or 0) == 0})
    aus.sort(key=lambda k: not k["op"])  # stabil: OP-Bilder nach vorn
    return aus[:MOTIV_KANDIDATEN]


def _gif_erstes_bild(daten: bytes) -> bytes:
    """Erstes Frame eines GIF als PNG-Bytes. Die Szenen-Kulisse (v7) fuettert
    Motive roh in ffmpegs zoompan, das eine einzelne Standbildquelle erwartet -
    ein animiertes Mehrbild-GIF wuerde dort als Bildfolge ankommen und die
    Zoom-Dauer-Logik zerreissen. Ein Standbild eignet sich fuer Sichtpruefung
    und v6-Fallback (thumbnail.videohintergrund) genauso wie JPG/PNG."""
    with io.BytesIO(daten) as puffer, Image.open(puffer) as bild:
        bild.seek(0)
        aus = io.BytesIO()
        bild.convert("RGB").save(aus, "PNG")
        return aus.getvalue()


def _gif_frames_fuer_pruefung(daten: bytes, ziel_dir: Path, stem: str,
                              anzahl: int = 3) -> list[Path]:
    """Bis zu `anzahl` Pruefframes (Start/Mitte/Ende) eines animierten GIF als
    PNG ablegen. Ein einzelnes Posterframe deckt spaeteren Inhalt eines GIFs
    nicht ab - die Sichtpruefung eines echten animierten Motivs muss deshalb
    mehr als nur das erste Bild sehen."""
    ziel_dir.mkdir(parents=True, exist_ok=True)
    aus: list[Path] = []
    with io.BytesIO(daten) as puffer, Image.open(puffer) as bild:
        n = getattr(bild, "n_frames", 1)
        indizes = sorted({0, n // 2, n - 1})[:anzahl]
        for i in indizes:
            bild.seek(i)
            ziel = ziel_dir / f"{stem}__f{i}.png"
            bild.convert("RGB").save(ziel, "PNG")
            aus.append(ziel)
    return aus


def motiv_laden(
        kandidaten: list[dict], ziel_dir: Path,
        animiert_erlauben: bool = False,
) -> tuple[list[Path], dict[Path, list[Path]]]:
    """Kandidaten herunterladen, mit dem Rate-Limit des Crawlers (1 req/s).
    Was kein Bild ist, fliegt sofort raus.

    Ohne animiert_erlauben (Thumbnail-Pfad) werden GIFs weiterhin auf ihr
    erstes Frame reduziert (siehe _gif_erstes_bild) - dabei aendert sich die
    Endung im kandidaten-Dict selbst auf .png, damit spaetere Zuordnungen
    ueber k["datei"] (z. B. die md5-Merkliste) den tatsaechlichen Dateinamen
    sehen.

    Mit animiert_erlauben=True (Video-Hintergrund-Pfad) bleibt ein GIF als
    echtes animiertes Motiv erhalten (Endung .gif), und die Funktion legt
    zusaetzlich ein paar Pruefframes (Start/Mitte/Ende) dafuer an - die
    liefert das zweite Rueckgabeelement, ein Motiv-Pfad -> Pruefframe-Liste.
    Motive ohne Eintrag darin sind Standbilder, deren Pruefframe sie selbst
    sind."""
    if ziel_dir.exists():
        shutil.rmtree(ziel_dir)  # Kandidaten des Vortags nicht mitschleppen
    ziel_dir.mkdir(parents=True, exist_ok=True)
    geladen: list[Path] = []
    pruefframes: dict[Path, list[Path]] = {}
    for k in kandidaten:
        try:
            req = urllib.request.Request(k["url"], headers=BILD_HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                daten = resp.read(MOTIV_MAX_BYTES + 1)
        except Exception as e:
            log.info("Motiv %s nicht geladen: %s", k["datei"], e)
            continue
        finally:
            time.sleep(1.0)
        if len(daten) > MOTIV_MAX_BYTES or not daten.startswith(MOTIV_MAGIC):
            continue
        ist_gif = daten.startswith((b"GIF87a", b"GIF89a"))
        mehrframe = False
        if ist_gif and animiert_erlauben:
            try:
                with io.BytesIO(daten) as puffer, Image.open(puffer) as bild:
                    mehrframe = getattr(bild, "n_frames", 1) > 1
            except Exception:
                mehrframe = False  # kaputtes GIF faellt unten wie gehabt raus
        if ist_gif and (not animiert_erlauben or not mehrframe):
            # Ohne echte Mehrbildigkeit (oder ohne animiert_erlauben) bringt
            # der animierte Renderpfad nichts - dann gilt der alte Weg: auf
            # das erste Frame reduzieren wie bisher.
            try:
                daten = _gif_erstes_bild(daten)
            except Exception as e:
                log.info("GIF %s nicht konvertiert: %s", k["datei"], e)
                continue
            k["datei"] = str(Path(k["datei"]).with_suffix(".png"))
        ziel = ziel_dir / k["datei"]
        ziel.write_bytes(daten)
        geladen.append(ziel)
        if ist_gif and animiert_erlauben and mehrframe:
            try:
                pruefframes[ziel] = _gif_frames_fuer_pruefung(
                    daten, ziel_dir / "vorschau", ziel.stem)
            except Exception as e:
                log.info("GIF %s: Pruefframes fehlgeschlagen: %s",
                         k["datei"], e)
                # Ohne Pruefframes bleibt das Motiv ungeprueft pruefbar -
                # hintergrund_pruefen() lehnt es dann mangels Urteil ab,
                # statt es ungesehen freizugeben.
    return geladen, pruefframes


def _sicht_antwort(prompt: str, bilder: list[Path], eingabe: str,
                   timeout: int, duldung: float = 0.0) -> dict:
    """Gemeinsames Netz aller Sichtpruefungen: Aufruf, Parsen und der Beleg,
    dass wirklich hingesehen wurde. Ein headless-Aufruf kann sonst ein
    wohlgeformtes Urteil liefern, ohne die Dateien je geoeffnet zu haben
    (verweigertes Werkzeug, Pfad ausserhalb des Arbeitsordners) - deshalb
    braucht jedes Bild eine eigene, nicht leere Beschreibung.

    Urteile ohne eigene Beschreibung tragen danach die Marke "_verdacht" und
    sind fuer den Aufrufer verbrannt. `duldung` sagt, welcher Anteil davon
    noch als Schlamperei an einzelnen Bildern durchgeht: 0.0 heisst
    alles-oder-nichts (so beim Vorschaubild - ein ungepruefter Kanalanstrich
    kostet im schlimmsten Fall den Kanal), ein hoeherer Wert laesst die
    uebrigen Urteile stehen. Letzteres kam vom Ausfall am 16. und 18.08.2026:
    ein einziges doppelt beschriebenes Bildpaar kippte die Freigabe aller 36
    Hintergrundbilder, und das Video lief mit einem einzigen Bild.

    Oberhalb der Duldung bleibt es beim Fehler - viele gleiche Beschreibungen
    sind kein Ausrutscher, sondern eine Antwort, die nichts gesehen hat. Die
    Richtung bleibt in jedem Fall sicher: Verdaechtige werden ausgeschlossen,
    nie freigegeben.

    Ausnahme seit der GIF-Animation (18.08.2026): mehrere Pruefframes
    desselben Motivs heissen "<stem>__f0.png", "<stem>__f1.png" usw. und
    duerfen sich sehr aehnlich sehen (langsame GIFs) oder sogar wortgleich
    beschrieben werden, ohne dass das ein Zeichen fuer ein ungesehenes
    Urteil ist. Nur eine wortgleiche Beschreibung ueber verschiedene Motive
    (unterschiedliche Stems) hinweg bleibt verdaechtig - genau das war der
    Ausfall vom 16./18.08.2026."""
    out = claude_ruf(prompt, eingabe, "sonnet", timeout,
                     tools="Read", cwd=BASE, effort="low").strip()
    out = _json_schneiden(out)
    daten = json.loads(out)
    urteile = daten.get("bilder")
    if not isinstance(urteile, list) or len(urteile) < len(bilder):
        raise RuntimeError(f"Sichtpruefung unvollstaendig: {out[:200]!r}")
    nach_text: dict[str, list[dict]] = {}
    for urteil in urteile:
        if not isinstance(urteil, dict):
            raise RuntimeError(f"Sichtpruefung unlesbar: {out[:200]!r}")
        text = re.sub(r"\W+", " ", str(urteil.get("beschreibung") or "")).strip()
        if len(text) < 20:
            urteil["_verdacht"] = "ohne Beschreibung"
            continue
        nach_text.setdefault(text.lower(), []).append(urteil)
    for gleiche in nach_text.values():
        if len(gleiche) <= 1:
            continue
        # Frames desselben animierten Motivs (gleicher Stem vor "__f")
        # duerfen sich gleich lesen - nur eine Wortgleichheit ueber
        # verschiedene Motive hinweg ist der eigentliche Verdachtsfall.
        stems = {re.sub(r"__f\d+(?=\.[^.]*$)", "",
                        str(u.get("datei") or "")) for u in gleiche}
        if len(stems) > 1:
            for urteil in gleiche:
                urteil["_verdacht"] = "Beschreibung doppelt"
    verdacht = [u for u in urteile if u.get("_verdacht")]
    if len(verdacht) > duldung * len(urteile):
        raise RuntimeError(f"{len(verdacht)} von {len(urteile)} Urteilen ohne "
                           f"eigene Beschreibung - vermutlich ungesehen")
    for urteil in verdacht:
        log.info("Sichtpruefung: %s %s - nicht freigegeben",
                 urteil.get("datei"), urteil["_verdacht"])
    return daten


def motiv_pruefen(bilder: list[Path], thema: str) -> Path | None:
    """Sichtpruefung der Kandidaten durch das Modell.

    Der Standard ist Ablehnung: benutzt wird ein Board-Bild nur, wenn die
    Antwort das Netz von _sicht_antwort() passiert und genau einen der
    heruntergeladenen Kandidaten waehlt - ungepruefte Board-Bilder als
    oeffentliches Vorschaubild kosten im schlimmsten Fall den Kanal."""
    if not bilder:
        return None
    nach_name = {p.name: p for p in bilder}
    eingabe = (f"Thema des Tages: {thema}\n\nKandidaten (Dateiname: Pfad):\n"
               + "\n".join(f"- {p.name}: {p}" for p in bilder))
    daten = _sicht_antwort(MOTIV_PROMPT, bilder, eingabe, TIMEOUT_MOTIV)
    urteile = daten["bilder"]

    wahl = daten.get("wahl")
    if not isinstance(wahl, str) or wahl not in nach_name:
        log.info("Sichtpruefung waehlt kein Board-Bild aus")
        return None
    urteil = next((u for u in urteile if u.get("datei") == wahl), None)
    if not urteil or not urteil.get("geeignet"):
        log.info("gewaehltes Bild ist nicht als geeignet markiert")
        return None
    log.info("Motiv: %s (%s)", wahl, urteil.get("grund"))
    return nach_name[wahl]


def motiv_waehlen(manifest: dict, datum: str, thema: str) -> Path | None:
    """Board-Bild des Tages fuers Vorschaubild aussuchen und bereitlegen.

    Das Ergebnis landet unter arbeit/ und damit ausserhalb des Repos: fremdes
    Bildmaterial gehoert nicht ins oeffentliche Archiv. Findet sich keins,
    nimmt video_report.py das Serienbild aus assets/."""
    thumbs = ARBEIT / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    for alt in thumbs.glob(f"{datum}.*"):
        alt.unlink()  # Rest eines frueheren Laufs nicht weiterverwenden
    # Frische Bilder bevorzugen; liefern die Threads nur schon gezeigte,
    # duerfen die noch einmal ran - lieber Wiederholung als Serienbild.
    gesperrt = set(verwendete_bilder(datum))
    kandidaten = motiv_kandidaten(manifest, gesperrt) or motiv_kandidaten(manifest)
    if not kandidaten:
        log.info("keine Bild-Kandidaten im Snapshot")
        return None
    geladen, _ = motiv_laden(kandidaten, thumbs / "kandidaten")
    gewaehlt = motiv_pruefen(geladen, thema)
    if gewaehlt is None:
        return None
    md5 = next((k["md5"] for k in kandidaten if k["datei"] == gewaehlt.name), "")
    if md5:
        verwendete_merken([md5], datum)
    ziel = thumbs / f"{datum}{gewaehlt.suffix}"
    shutil.copy2(gewaehlt, ziel)
    return ziel


# ------------------------------------------- Hintergrundbilder fuers Video

HG_JE_THREAD = 4         # so viele Bilder liefert ein Thread hoechstens
HG_MAX = 36              # Gesamtdeckel fuer die Sichtpruefung
HG_SEITE = (0.4, 3.5)    # Hintergruende werden cover-beschnitten, fast alles geht
HG_STAPEL = 12           # Bilder je Sichtpruefungs-Aufruf (Schadensgrenze)
HG_DULDUNG = 0.34        # so viel Verdacht je Stapel gilt als Schlamperei
TIMEOUT_HINTERGRUND = 300  # je Stapel; 36/12 Stapel = dasselbe Gesamtbudget

HINTERGRUND_PROMPT = """\
Du prüfst Bilder für den Videohintergrund eines Nachrichtenvideos über das
4chan-Board /biz/. Das ist ein "blue board", auf dem die Moderation nicht
jugendfreies Material entfernt; grob Anstössiges ist dort die Ausnahme. Die
Bilder laufen als Kulisse HINTER dem Untertiteltext. Es
geht darum, ob ein Bild öffentlich gezeigt werden darf - nicht darum, ob es
schön ist oder zum Thema passt.

Sieh dir JEDES unten genannte Bild mit dem Read-Werkzeug an. Urteile nur
nach dem, was du wirklich siehst, und rate nichts.

Dateien mit demselben Namen vor "__f" (z. B. "123-456__f0.png",
"123-456__f12.png") sind mehrere Frames DESSELBEN animierten Motivs (Start/
Mitte/Ende eines GIF) - kein eigenstaendiges Bild je Frame. Benenne in der
Beschreibung, was diesen Frame von den anderen Frames desselben Motivs
unterscheidet (Bewegung, Textwechsel, neue Figur im Bild), auch wenn die
Frames sich stark aehneln - eine wortgleiche Beschreibung mehrerer Frames
desselben Motivs ist in Ordnung, wortgleiche Beschreibungen ueber
VERSCHIEDENE Motive hinweg sind es nicht.

Ein Bild ist NUR dann ungeeignet, wenn es gegen die YouTube-Richtlinien
verstösst: Nacktheit oder Sexualisiertes, Gewalt oder Blut, Hass- oder
Extremismus-Symbolik, Drogen, grobe Beschimpfungen oder Slurs im Bildtext,
eine reale Person in kompromittierender Lage. Nur bei dieser Frage gilt im
Zweifel Ablehnung.

ALLES andere ist geeignet: Charts, Screenshots, Textbilder, Memes, Froesche,
Wojaks, Fotos, auch Bilder ohne jeden Finanzbezug. Lehne nichts wegen
Qualität, Stil, Kleinteiligkeit oder fehlendem Themenbezug ab - erwartet
wird, dass die grosse Mehrheit der Kandidaten durchgeht.

Bewerte zusätzlich JEDES Bild mit drei ganzen Zahlen von 1 bis 5 (das
beeinflusst nur die Reihenfolge im Video, nicht die Freigabe):
- "bildlich": Wie viel echtes Bildmotiv statt Text ist zu sehen? Schätze den
  Flächenanteil, den geschriebener Text einnimmt. 5 = Foto, Zeichnung, Meme,
  Frosch, Wojak, Comic, Symbolbild - Text höchstens als Bildunterschrift.
  3 = Kurs-Chart oder Grafik mit vielen Beschriftungen, aber erkennbarer
  Bildwirkung. 1 = fast nur Text, also Screenshot einer Artikel- oder
  Suchergebnisseite, Chatverlauf, Kurstabelle, Zahlenliste, Textwand.
  Nimmt Text mehr als die Hälfte der Fläche ein, ist die Antwort 1 oder 2.
- "unterhaltung": Wie viel macht das Bild als Kulisse her? Memes, Wojaks,
  Frösche, ausdrucksstarke Fotos und markante Motive hoch; kleinteilige
  Screenshots, Textwände und triste Tabellen niedrig.
- "themen": Wie deutlich hat der sichtbare Inhalt mit Finanzen, Märkten,
  Krypto oder Wirtschaft zu tun? Kurs-Charts und Depot-Screenshots hoch,
  themenfremde Bilder niedrig.

Gib NUR ein JSON-Objekt aus, ohne Vor- oder Nachbemerkungen und ohne
Code-Zaun. Die Beschreibung ist Pflicht und benennt sachlich, was auf genau
diesem Bild zu sehen ist:
{"bilder": [{"datei": "...", "beschreibung": "...", "ok": true,
"grund": "...", "bildlich": 3, "unterhaltung": 3, "themen": 3}]}
"""


def _wert_1_5(roh: object) -> int:
    """Bewertung aus der Sichtpruefung als ganze Zahl 1-5; alles
    Unbrauchbare wird zur neutralen 3."""
    try:
        return max(1, min(5, int(roh)))  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return 3


def _grund_slug(text: str, laenge: int = 44) -> str:
    """Ablehnungsgrund als Teil eines Dateinamens: ASCII, klein, Bindestriche.
    Damit steht der Grund im Ordner `abgelehnt/` direkt am Bild und laesst
    sich ohne Log durchsehen."""
    roh = (text or "kein grund").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        roh = roh.replace(a, b)
    roh = re.sub(r"[^a-z0-9]+", "-", roh).strip("-")
    return roh[:laenge].rstrip("-") or "kein-grund"


def hintergrund_kandidaten(manifest: dict,
                           gesperrt: set[str] | None = None) -> list[dict]:
    """Bild-Anhaenge ALLER ausgewerteten Threads, je Thread bis zu
    HG_JE_THREAD Stueck (OP-Bilder zuerst). Die mechanischen Filter sind
    dieselben wie beim Vorschaubild-Motiv, nur das Seitenverhaeltnis ist
    lockerer - Hintergruende werden ohnehin auf 16:9 cover-beschnitten.

    Bilder aus der Merkliste (gesperrt) werden uebersprungen, damit jeden
    Tag frische zu sehen sind; liefert ein Thread dadurch gar keins mehr
    (langlebiger General, dessen fruehe Anhaenge schon liefen), duerfen
    seine alten in einem zweiten Durchgang noch einmal ran."""
    threads = [str(b["thread"]) for b in manifest.get("buendel", [])]
    posts = _snapshot_posts(set(threads))
    gesehen: set[str] = set()
    aus: list[dict] = []
    for no in threads:  # Reihenfolge des Manifests = Substanzdichte
        gefunden: list[dict] = []
        sortiert = sorted(posts.get(no, []),
                          key=lambda p: (p.get("resto") or 0) != 0)
        for alte_erlaubt in (False, True):
            if gefunden:
                break
            for post in sortiert:
                if len(gefunden) >= HG_JE_THREAD:
                    break
                tim, ext = post.get("tim"), str(post.get("ext") or "").lower()
                if not tim or ext not in MOTIV_ENDUNGEN:
                    continue
                if post.get("spoiler") or post.get("filedeleted"):
                    continue
                breite, hoehe = post.get("w") or 0, post.get("h") or 0
                if (breite < MOTIV_MIN_BREITE or hoehe < MOTIV_MIN_HOEHE
                        or (post.get("fsize") or 0) > MOTIV_MAX_BYTES
                        or not HG_SEITE[0] <= breite / hoehe <= HG_SEITE[1]):
                    continue
                md5 = str(post.get("md5") or tim)
                if md5 in gesehen:
                    continue
                if not alte_erlaubt and md5 in (gesperrt or set()):
                    continue
                gesehen.add(md5)
                # Threadnummer im Dateinamen: video_report.py ordnet die
                # Bilder darueber den Berichtsabschnitten zu.
                gefunden.append({"thread": no, "datei": f"{no}-{tim}{ext}",
                                 "url": f"{BILD_BASIS}/{tim}{ext}",
                                 "md5": md5})
        aus.extend(gefunden)
    return aus[:HG_MAX]


def hintergrund_pruefen(
        bilder: list[Path],
        pruefframes: dict[Path, list[Path]] | None = None,
) -> tuple[dict[Path, dict[str, int]], dict[Path, str]]:
    """Lockere Sichtpruefung fuer Videohintergruende: einzige Frage ist der
    Richtlinienverstoss, alles andere geht durch. Liefert je freigegebenem
    Bild die Bewertungen (bildlich/unterhaltung/themen, 1-5) - der Video-Lauf
    sortiert die Bildauswahl danach.

    Geprueft wird in Stapeln von hoechstens HG_STAPEL Pruefframes, und ein
    misslungener Stapel kostet nur seine eigenen Bilder. Grund ist der
    Ausfall am 16. und 18.08.2026: ein einziger Aufruf ueber alle 36 Bilder
    lieferte zweimal dieselbe Beschreibung, das Netz gegen ungesehene
    Urteile verwarf darauf die ganze Freigabe, es entstand kein motive.json -
    und das Video lief mit einem einzigen Bild. Zwoelf Bilder je Aufruf
    bekommen zudem mehr Aufmerksamkeit als 36, doppelte Beschreibungen
    werden also seltener.

    Ein animiertes Motiv (Eintrag in pruefframes) bringt mehrere Pruefframes
    statt einem mit - Start/Mitte/Ende, weil spaetere GIF-Frames anderen
    Inhalt zeigen koennen als das erste. Diese Frames werden nie ueber zwei
    Stapel verteilt (sonst zerreisst die Alle-Frames-ok-Regel unten), und
    ein Motiv gilt nur als frei, wenn ALLE seine Frames ok sind - strenger
    als bei einem Standbild, das nur ein einziges Urteil braucht. Die
    Bewertungen (bildlich/unterhaltung/themen) stammen vom ersten Frame.

    Ueberlebt kein Stapel, ist das ein Fehler und kein leeres Ergebnis: der
    Aufrufer darf dann kein motive.json schreiben, sonst gilt der Tag als
    versorgt und der Rueckgriff im Video-Lauf greift nicht.

    Zurueck kommen zwei Zuordnungen: die freigegebenen Bilder mit ihren
    Bewertungen und je abgelehntem Bild der Grund. Der Grund ist die einzige
    Chance, eine zu strenge oder zu lasche Sichtpruefung zu bemerken - er
    gehoert deshalb ans Bild und nicht nur ins Log."""
    pruefframes = pruefframes or {}
    gruppen = [(p, pruefframes.get(p) or [p]) for p in bilder]
    stapel: list[list[tuple[Path, list[Path]]]] = []
    aktuell: list[tuple[Path, list[Path]]] = []
    aktuell_n = 0
    for gruppe in gruppen:
        n = len(gruppe[1])
        if aktuell and aktuell_n + n > HG_STAPEL:
            stapel.append(aktuell)
            aktuell, aktuell_n = [], 0
        aktuell.append(gruppe)
        aktuell_n += n
    if aktuell:
        stapel.append(aktuell)

    frei: dict[Path, dict[str, int]] = {}
    gruende: dict[Path, str] = {}
    for nr, teil in enumerate(stapel, 1):
        alle_frames = [f for _, frames in teil for f in frames]
        nach_name = {f.name: f for f in alle_frames}
        eingabe = ("Kandidaten (Dateiname: Pfad):\n"
                   + "\n".join(f"- {f.name}: {f}" for f in alle_frames))
        try:
            daten = _sicht_antwort(HINTERGRUND_PROMPT, alle_frames, eingabe,
                                   TIMEOUT_HINTERGRUND, HG_DULDUNG)
        except Exception as e:
            log.warning("Hintergrund-Stapel %d/%d verworfen: %s",
                        nr, len(stapel), e)
            for p, _ in teil:
                gruende[p] = f"Stapel verworfen: {e}"
            continue
        urteil_nach_name = {}
        for urteil in daten["bilder"]:
            name = str(urteil.get("datei") or "")
            if name in nach_name:
                urteil_nach_name[name] = urteil
        for p, frames in teil:
            roh_urteile = [urteil_nach_name.get(f.name) for f in frames]
            if any(u is None for u in roh_urteile):
                gruende[p] = "kein Urteil in der Antwort"
                continue
            frame_urteile = [u for u in roh_urteile if u is not None]
            verdaechtig = [u for u in frame_urteile if u.get("_verdacht")]
            if verdaechtig:
                # ein ungesehenes Urteil ist nie eine Freigabe
                gruende[p] = str(verdaechtig[0]["_verdacht"])
                continue
            abgelehnte = [u for u in frame_urteile if not u.get("ok")]
            if abgelehnte:
                grund = str(abgelehnte[0].get("grund") or "kein Grund genannt")
                gruende[p] = grund
                log.info("Hintergrund %s abgelehnt: %s", p.name, grund)
                continue
            poster = frame_urteile[0]
            frei[p] = {
                "bildlich": _wert_1_5(poster.get("bildlich")),
                "unterhaltung": _wert_1_5(poster.get("unterhaltung")),
                "themen": _wert_1_5(poster.get("themen")),
            }
        # Fehlt die Bildlichkeit ganz, hat das Modell das Feld verschluckt:
        # dann bekommt jedes Bild die neutrale 3 und der Video-Lauf erkennt
        # Textwaende nur noch am Unterhaltungswert - das gehoert ins Log.
        if not any("bildlich" in u for u in daten["bilder"]):
            log.warning("Stapel %d ohne bildlich-Bewertung - Textwaende "
                        "werden nur ueber den Unterhaltungswert erkannt", nr)
    if not frei:
        raise RuntimeError(f"kein brauchbares Urteil aus {len(stapel)} "
                           f"Stapeln ({len(bilder)} Bilder)")
    for p in bilder:                     # nie stumm verschwinden lassen
        if p not in frei:
            gruende.setdefault(p, "kein Urteil in der Antwort")
    return frei, gruende


def hintergruende_waehlen(manifest: dict, datum: str) -> int:
    """Freigegebene Hintergrundbilder je Thread unter arbeit/motive/<datum>/
    bereitlegen (ausserhalb des Repos, wie das Thumbnail-Motiv). motive.json
    haelt die Zuordnung Thread -> Dateien fuer den Video-Lauf fest.

    Abgelehnte Bilder werden nicht mehr geloescht, sondern nach
    arbeit/motive/<datum>/abgelehnt/ verschoben, mit dem Grund im Dateinamen
    (Nutzerwunsch 18.08.2026: die Ablehnungen gegenpruefen koennen). Der
    Ordner liegt wie alles unter arbeit/ ausserhalb des Repos und wird vom
    naechsten Lauf desselben Tages mit ueberschrieben; der Video-Lauf sieht
    ihn nie, weil er nur Namen aus motive.json anfasst. Dieselben Gruende
    stehen zusaetzlich in motive.json unter "abgelehnt".

    GIFs bleiben hier animiert (animiert_erlauben=True) - motive.json haelt
    zusaetzlich unter "typ" fest, welche Dateien ein echtes animiertes Motiv
    sind, und unter "poster" ein Standbild dazu (erstes Pruefframe, dauerhaft
    unter dem Hauptordner statt im geloeschten vorschau/-Zwischenordner),
    damit der Video-Lauf ueber den zoompan-d=1-Renderpfad rendert und bei
    Bedarf (Crossfade, Fallback bei Renderfehler) ein Standbild zur Hand hat."""
    ziel_dir = ARBEIT / "motive" / datum
    gesperrt = set(verwendete_bilder(datum))
    kandidaten = hintergrund_kandidaten(manifest, gesperrt)
    if not kandidaten:
        log.info("keine Hintergrund-Kandidaten im Snapshot")
        return 0
    geladen, pruefframes = motiv_laden(kandidaten, ziel_dir,
                                       animiert_erlauben=True)
    frei, gruende = hintergrund_pruefen(geladen, pruefframes)
    md5_nach_datei = {k["datei"]: k["md5"] for k in kandidaten}
    threads: dict[str, list[str]] = {}
    werte: dict[str, dict[str, int]] = {}
    typ: dict[str, str] = {}
    poster: dict[str, str] = {}
    abgelehnt: dict[str, str] = {}
    gezeigt: list[str] = []
    ablage = ziel_dir / "abgelehnt"
    for p in geladen:
        if p not in frei:
            grund = gruende.get(p, "kein Urteil in der Antwort")
            abgelehnt[p.name] = grund
            ablage.mkdir(parents=True, exist_ok=True)
            p.replace(ablage / f"{p.stem}__{_grund_slug(grund)}{p.suffix}")
            continue
        threads.setdefault(p.name.split("-", 1)[0], []).append(p.name)
        werte[p.name] = frei[p]
        if p in pruefframes:
            typ[p.name] = "animiert"
            poster_ziel = ziel_dir / f"{p.stem}__poster.png"
            try:
                shutil.copy2(pruefframes[p][0], poster_ziel)
                poster[p.name] = poster_ziel.name
            except OSError as e:
                log.info("Posterframe fuer %s nicht kopiert: %s", p.name, e)
        else:
            typ[p.name] = "standbild"
        if p.name in md5_nach_datei:
            gezeigt.append(md5_nach_datei[p.name])
    (ziel_dir / "motive.json").write_text(
        json.dumps({"threads": threads, "werte": werte, "typ": typ,
                    "poster": poster, "abgelehnt": abgelehnt}, indent=2)
        + "\n", encoding="utf-8")
    if abgelehnt:
        log.info("%d abgelehnte Bilder liegen mit Grund im Dateinamen unter "
                 "%s", len(abgelehnt), ablage)
    shutil.rmtree(ziel_dir / "vorschau", ignore_errors=True)  # Posterframes
    # sind schon herauskopiert, der Rest ist reiner Platzverbrauch
    verwendete_merken(gezeigt, datum)
    return len(frei)


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
    titel: dict[str, str] = {}
    try:
        log.info("Erzeuge Video-Titel (Sonnet) ...")
        titel = titel_generieren(bericht_md, datum)
        (tag_dir / "titel.json").write_text(
            json.dumps(titel, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        log.info("Video-Titel: %s", titel["en"])
    except Exception as e:
        # Ohne titel.json nimmt video_report.py den statischen Serientitel -
        # ein Titelfehler darf den Upload nie verhindern.
        log.warning("Titel-Generierung fehlgeschlagen (Video nimmt den "
                    "statischen Serientitel): %s", e)
    try:
        log.info("Erzeuge Video-Drehbuch (Sonnet) ...")
        daten = folien_generieren(bericht_md)
        (tag_dir / "folien.json").write_text(
            json.dumps(daten, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        log.info("Drehbuch: %d Abschnitte, %d Tageszahlen",
                 len(daten["abschnitte"]), len(daten["zahlen"]))
    except Exception as e:
        # Ohne folien.json baut video_report.py das Video im alten
        # Text-Layout weiter - die Praesentation darf nie blockieren.
        log.warning("Folien-Generierung fehlgeschlagen (Video nimmt das "
                    "Text-Layout): %s", e)
    try:
        log.info("Suche Motiv fuers Vorschaubild (Sonnet, Sichtpruefung) ...")
        thema = titel.get("en") or bericht_md[:400]
        log.info("Vorschaubild-Motiv: %s",
                 motiv_waehlen(manifest, datum, thema) or "keins, Serienbild")
    except Exception as e:
        # Auch hier gilt: das Video entsteht mit dem Serienbild weiter.
        log.warning("Motiv-Auswahl fehlgeschlagen (Video nimmt das "
                    "Serienbild): %s", e)
    try:
        log.info("Pruefe Hintergrundbilder fuers Video (Sonnet, "
                 "Sichtpruefung) ...")
        log.info("%d Hintergrundbilder freigegeben",
                 hintergruende_waehlen(manifest, datum))
    except Exception as e:
        # Ohne freigegebene Bilder legt video_report.py das Vorschaubild
        # als Hintergrund unter den Text - auch das darf nie blockieren.
        log.warning("Hintergrund-Auswahl fehlgeschlagen (Video nimmt das "
                    "Vorschaubild als Hintergrund): %s", e)
    try:
        log.info("Pruefe WebM/MP4-Clips fuers Video (Sonnet, "
                 "Sichtpruefung) ...")
        import klip_katalog
        log.info("%d neue Clips freigegeben",
                 klip_katalog.klips_ernten(manifest, datum))
    except Exception as e:
        # Clips sind eine Ergaenzung zur Bild-Kulisse, kein Ersatz - eine
        # gescheiterte Ernte darf den Bericht nie blockieren.
        log.warning("Clip-Ernte fehlgeschlagen (Video nimmt die "
                    "Bild-Kulisse ohne Clips): %s", e)
    (tag_dir / "README.md").write_text(
        _tag_readme_bauen(manifest, datum, tag_dir), encoding="utf-8")
    markdown_index_aktualisieren()
    git_veroeffentlichen([tag_dir, EXTRAKTE / "README.md"], f"Bericht vom {datum}")


def stufe3(manifest: dict, eDir: Path, arbeit: Path, datum: str) -> str:
    meta_nach_thread = {str(b["thread"]): b for b in manifest["buendel"]}
    extrakte = sandwich(sorted(eDir.glob("*.txt")), meta_nach_thread)
    anteil = len(extrakte) / max(1, len(manifest["buendel"]))
    luecke = ""
    if anteil < MIN_EXTRAKTE:
        luecke = (f"ATTENTION: only {len(extrakte)} of {len(manifest['buendel'])} "
                  "threads could be analyzed. State in the first line of the "
                  "report that today's picture is incomplete.")

    vorbericht = voriger_bericht(datum)
    delta_block = ""
    if vorbericht:
        vor_text, vor_url = vorbericht
        delta_block = f"""
YESTERDAY'S REPORT (for comparison only, NOT part of today's extracts;
older reports may be written in German - compare by content):
Source: {vor_url}
{"=" * 74}
{vor_text}
{"=" * 74}
"""
    teile = [
        f"DATA AS OF: {manifest.get('snapshot_zeit_lokal')} local time (Europe/Zurich)",
        f"BOARD: {manifest.get('threads_im_board')} threads in the catalog",
        f"THREADS ANALYZED: {len(extrakte)} of {len(manifest['buendel'])}",
        "",
    ]
    for e in extrakte:
        t = e.stem
        m = meta_nach_thread.get(t, {})
        modus = m.get("modus", "voll")
        hinweis = {
            "voll": "read in full",
            "delta": f"incrementally updated, {m.get('neue_posts', 0)} new posts since the last run",
            "unveraendert": "unchanged since the last run, no new posts",
        }.get(modus, modus)
        teile += [
            "=" * 74,
            f"THREAD {t} - {m.get('betreff', '')}",
            f"URL: {m.get('url', '')}",
            (f"Posts: {m.get('posts_gesamt')} | age: {m.get('alter_h')} h | "
             f"last hour: {m.get('posts_letzte_stunde')} | "
             f"selected because: {'; '.join(m.get('rollen', []))}"),
            f"Extract status: {hinweis}",
            "=" * 74,
            ohne_cache_abschnitte(e.read_text(encoding="utf-8", errors="replace")),
            "",
        ]
    if delta_block:
        teile.append(delta_block)
    eingabe = "\n".join(teile)
    (arbeit / "synthese_eingabe.txt").write_text(eingabe, encoding="utf-8")

    prompt = f"""You receive structured extracts from several threads of the 4chan board
/biz/ (Business & Finance). A cheaper model pulled them from the full texts
beforehand. Write today's situation report from them.

{luecke}

The reader is an interested investor who does not know the board and does
not speak its jargon. He wants the KNOWLEDGE in the posts: which tickers
and coins are mentioned, which hard numbers come up, which claims are made
with what reasoning, which sources are shared, what is practically usable.
On top of that he wants a feel for the board itself - its humor, its memes,
its mood - which is why this report is written in the board's language.

Rules:
1. English plain text, NO Markdown formatting, no asterisks, no hash
   headings. Headings in capital letters on their own line.
2. Start with a line "Data as of: <value> local time" taken from the
   DATA AS OF line of the input, plus the number of threads analyzed.
3. Length: around 700 to 1000 words for the report body.
   Concrete and dense beats complete - but everything mentioned must be
   traceable.
3b. READABILITY, important: The report is skimmed, not studied.
   - Paragraphs of at most four sentences, then a blank line.
   - When several numbers, facts or arguments follow each other, write them
     as a list: each line starts with "- ". Do not pack them into one long
     sentence. Rule of thumb: three related items or more become a list.
   - The first sentence of a section states the result, not the backstory.
   - No nested sentences with more than one subordinate clause.
4. Structure the report body by topic, most important first. Pick sensible
   headings, for example STOCKS, CRYPTO, MACRO AND GEOPOLITICS, FILLING
   FAST. Drop any topic that has nothing to report.
5. State concrete numbers with their meaning, and give the URL per item.
   Use standard English number formatting with commas: 1,234,567.
6. Separate claim from evidence. Mark poster claims as such ("one poster
   calculates", "unsourced"). Where an external source was shared, name it.
7. VOICE OF THE BOARD: the report stays facts-first, but the board's own
   voice is half of what the reader came for - and it is the first thing
   that gets cut when space runs short. Treat it as material, not as
   decoration:
   - QUOTE BUDGET: every topic that has a usable line from MOOD AND MEMES
     carries at least one, verbatim and in quotation marks. The extracts
     offer roughly eighty per day. A report that uses five has thrown away
     the part of the story no news source can supply.
   - CANON BEATS ONE-OFFS: bullets marked "Canon:" are fixed expressions
     the board reuses across threads and days. Prefer them over a clever
     line from this morning: they show how the board habitually reacts,
     not what one poster once wrote. Where you use one, say in half a
     sentence what it means - the reader does not know it.
   - HOW THE BOARD WORKS is a finding too, wherever it explains WHY a
     discussion runs the way it does - but take it ONLY from what the
     canon bullets hand you, since they carry the meaning with them. The
     extracts' TERMS AND SLANG section does not reach you: it is stripped
     before this call and feeds the appended glossary instead. Never
     supply board mechanics from your own knowledge.
   - THE GENERALS ARE INSTITUTIONS, not just sources: recurring threads
     with fixed names and OP templates (/smg/, /pmg/, /XMR/, /XSG/) are
     re-founded every day. Where a thread carries an iteration number,
     that number is itself a finding - it says how many times the same
     argument has been had.
   - Let the board's sarcasm color a transition where it fits.
   Quotes are copied character-exact from the extracts and never repaired,
   completed or smoothed. What stays OUT: slurs, insults
   aimed at people or groups, and who-fought-whom drama - a fight is not a
   finding. If a fight thread contains an investment-relevant statement,
   report only that. Everything must stay publishable on YouTube.
   ALSO OUT, inside quotes as well: the f-word in every form (fuck,
   fucking, fucked, motherfucker, ...) and comparably hard profanity. Do
   not mask it with asterisks either - the report is read aloud in the
   video. This one point overrides the character-exact rule above: pick a
   quote that carries the finding without the word, and if none exists,
   report the statement indirectly instead of quoting it. Never a softened
   quote - rather no quote.
8. Each thread states whether its extract was read in full or only
   incrementally updated since the last run. Use that to separate NEWS from
   standing situations: what arrived since yesterday goes to the front.
   The section NEW SINCE LAST RUN in the extracts tells you. A thread
   marked unchanged provides background, not news - do not present it as a
   current development.
8b. DO NOT REPEAT WHAT YESTERDAY'S REPORT ALREADY SAID (if one is provided
    as YESTERDAY'S REPORT - otherwise write in full as usual; it may be
    written in German, compare by content). Compare topic by topic:
    - If a topic is substantively unchanged since yesterday (no new
      numbers, claims, sources, price targets), do NOT write it out again.
      Write EXACTLY ONE sentence that names the topic concretely enough
      that the reader knows what it is WITHOUT clicking - give the core
      claim or the key number, not just a label ("semiconductor debate:
      unchanged" is too little, "semiconductor debate (ASML lithography
      monopoly, logic vs. memory chips): unchanged since yesterday" is
      right). Then the URL of yesterday's report from the "Source:" line
      above, copied unchanged, on its own line.
    - If something changed or is new, write ONLY the new part in full;
      summarize the unchanged background in half a sentence (as above,
      with the reference URL), do not re-explain it.
    - A topic that did not appear in yesterday's report is entirely new
      and is written in full, with no reference line.
    - Do not confuse "thread unchanged" (extract metadata) with "topic
      unchanged": a thread can have new posts without the reportable topic
      changing - the rule still applies then.
9. The section FILLING FAST describes what these threads actually SAY, not
   just that they grow quickly. Give the acceleration factor against the
   thread's own average where the metadata provides it. A thread with
   nothing beyond its subject line is called out as such.
10. At the end of each topic, briefly judge reliability whenever the
    extracts mention signs of self-interest or promotion.
11. Poster IDs are per-thread and can be manipulated: treat them as an
    upper bound, make no statements about real head counts.
12. Write NO glossary: it is generated automatically from the extracts and
    appended after you. You may use jargon in the report without
    explaining it. ONE exception, and only it: a board phrase you quote
    under rule 7 because it carries the finding - there the half sentence
    of meaning belongs in the sentence itself, because the point is lost
    without it. That is not a definition and not a glossary entry.
13. COMPLETENESS: every thread of the input is either used in the report
    or deliberately omitted - nothing disappears silently. You account for
    this in the COVERAGE block (see output).

Publication happens outside this call. Only output the report, send
nothing and create no files.

IMPORTANT about the output, in exactly this order:
1. The complete report.
2. One line "COVERAGE:", then exactly one line per thread of the input:
      <thread number>: used
   or
      <thread number>: omitted - <reason in a few words>
   Every thread number of the input appears exactly once. This block is
   NOT part of the report and does not count toward its word count.
3. As the very last line exactly one status line:
   STATUS: DONE
or, if something prevented a complete report:
   STATUS: ERROR - short cause in a few words
The report itself contains no meta remarks about these instructions.
"""

    log.info("Stufe 3: Synthese mit Opus (%d Extrakte, %d KB)",
             len(extrakte), len(eingabe) // 1024)
    return claude_ruf(prompt, eingabe, "opus", TIMEOUT_SYNTH)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("BOARDSTATS_HOST"),
                    help="ssh-Ziel fuer bundle_biz.py; leer = lokal")
    # Bewusst bei 15 belassen (Entscheid 08.08.2026): weniger Quellen loesen
    # das Abdeckungsproblem nicht (DiverseSumm, arXiv 2309.09369: <40 %
    # Coverage schon bei 10 Quellen), sie kosten nur Substanz. Gegen den
    # Positions-Bias wirken sandwich() und der COVERAGE-Block.
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--kein-cache", action="store_true",
                    help="alle Threads voll lesen (Neuaufbau des Caches)")
    ap.add_argument("--kein-github", action="store_true",
                    help="Extrakte nicht als Markdown ablegen und veroeffentlichen")
    args = ap.parse_args()

    setup_logging()
    log.info("=== Start (host=%s) ===", args.host or "lokal")

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
        out = stufe3(manifest, eDir, arbeit, datum)
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
                       if "omitted" in z.lower() or "ausgelassen" in z.lower()]
        log.info("Abdeckung: %d Threads ausgelassen", len(ausgelassen))
        for z in ausgelassen:
            log.info("  %s", z)
    else:
        log.warning("kein COVERAGE-Block in der Synthese-Ausgabe")

    glossar = glossar_bauen(bericht, eDir)
    if glossar:
        bericht = bericht + "\n\n" + glossar
    ziel.write_text(bericht + "\n", encoding="utf-8")
    log.info("Stufe 3 fertig in %ds, Bericht gespeichert: %s",
             time.time() - t2, ziel)

    if not args.kein_github:
        bericht_veroeffentlichen(bericht, datum, tag_dir, manifest)

    log.info("=== %s ===", status[-1].strip())
    # Eine ERROR-Statuszeile muss den Lauf als Fehler beenden, sonst faellt
    # ein unvollstaendiger Bericht tagelang nicht auf (Lehre vom 07.08., als
    # die Aufgabenplanung Erfolg meldete, obwohl nichts rausging).
    if "DONE" not in status[-1] and "FERTIG" not in status[-1]:
        log.error("Synthese meldet keinen Erfolg - Bericht liegt unter %s", ziel)
        return 1

    for alt in sorted(ARBEIT.iterdir(), reverse=True)[LAEUFE_BEHALTEN:]:
        if alt.is_dir():
            shutil.rmtree(alt, ignore_errors=True)
    log.info("Gesamtdauer %d min", (time.time() - t0) / 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
