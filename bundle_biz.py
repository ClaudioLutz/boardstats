#!/usr/bin/env python3
"""Schneidet aus dem juengsten /biz/-Snapshot Volltext-Buendel fuer die
Extraktionsstufe (Sonnet) heraus.

Warum zusaetzlich zu aggregate_biz.py: dessen Report ist auf ~22 KB verdichtet,
damit ein einzelnes Modell alles auf einmal lesen kann. Genau diese Verdichtung
wirft aber das Detail weg, das den Bericht wertvoll macht (Strikes, Guidance,
Bezugsquellen, welches Verfahren gemeint ist). Die Buendel gehen stattdessen
einzeln und parallel an ein guenstigeres Modell, das je einen ganzen Thread
liest; erst deren Extrakte werden zusammengefuehrt. aggregate_biz.py bleibt
unberuehrt und liefert weiter die Kennzahlen.

Auswahl der Threads (Vereinigung, damit nichts Wichtiges wegfaellt):
  A  schnell_fuellend  - IMMER, ohne Substanzschwelle. Genau diese Threads sind
     jung und duenn (der KI-Thread hatte 5 Posts), jede Schwelle wuerde sie
     rauswerfen - obwohl "was steht da eigentlich drin" die offene Frage ist.
  B  top_chains        - die Threads der staerksten Diskussionsketten
  C  Substanz-Ranking  - Threads mit den meisten inhaltlich dichten Posts
                         (Zahlen, Betraege, Prozente, externe Quellen, Tickers)

DELTA-MODUS (--cache-status): Gemessen an drei aufeinanderfolgenden Abenden
waren rund 50 % des gebuendelten Textes schon am Vortag gebuendelt; einzelne
Threads hatten 0 bis 3 % neue Posts und liefen trotzdem vollstaendig durchs
Modell. Liegt fuer einen Thread ein Extrakt aus einem frueheren Lauf vor, wird
deshalb nur noch geschnitten, was seither dazukam. Der Extrakt ist das
Gedaechtnis, das Delta die einzige neue Leseleistung. Nebeneffekt: der
40-KB-Deckel wirft bei grossen Threads nicht mehr dauerhaft Inhalt weg,
sondern nur einmal - das Delta bekommt in jedem Lauf ein frisches Budget.

Ausgabe: bundles/<thread>.txt je Thread + manifest.json auf stdout.
"""
import argparse
import gzip
import html
import itertools
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
REPORTS = ROOT / "reports"
BUNDLES = ROOT / "bundles"
LOKAL = ZoneInfo("Europe/Zurich")

MAX_ZEICHEN = 40_000     # Obergrenze pro Buendel; groesste Threads haben ~61 KB
FENSTER_AKTUELL_S = 5400  # "gerade eben" - diese Posts bleiben immer drin
SUBSTANZ_MIN = 4.0        # ab hier gilt ein Post als inhaltlich dicht
MIN_POSTS_DICHTE = 20     # darunter ist die Dichte je Post statistisch Rauschen

# --- Delta-Modus ---
# Unter dieser Threadgroesse lohnt der Cache nicht: gemessen war der Extrakt
# kleiner Threads groesser als ihr Buendel (1.1 KB -> 3.7 KB), weil das
# Abschnittsgeruest mit "- keine" mehr kostet als der Thread selbst.
# 15'000 statt der zuerst gesetzten 8'000: bei einer Kontrolle nach dem ersten
# Lauf war der Extrakt noch bei 8.8 KB Buendel groesser als das Buendel
# (10.0 KB). Inkrementell lohnt sich erst, wenn Extrakt + Delta < Buendel.
MIN_CACHE_ZEICHEN = 15_000
ZITAT_KURZ = 60           # so viele Zeichen einer erkannten Zitatzeile bleiben
RAUSCH_MAX = 80           # Posts kuerzer als das, ohne Zahl/Link/Antwort, fliegen raus

TAG = re.compile(r"<[^>]+>")
QUOTE = re.compile(r'<a href="#p(\d+)" class="quotelink">')

EXT_LINK = re.compile(r"https?://(?!boards\.4chan|i\.4cdn)")
PROZENT = re.compile(r"\d+(?:[.,]\d+)?\s?%")
GELD = re.compile(r"[$€£]\s?\d|\b\d+(?:[.,]\d+)?\s?(?:k|K|bn|mn|USD|usd|eur|EUR)\b")
ZAHL = re.compile(r"\b\d+(?:[.,]\d+)?\b")
DOLLAR_TICKER = re.compile(r"\$[A-Za-z]{1,5}\b")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("bundle")


def plain(com: str, quotes_behalten: bool = True) -> str:
    """HTML zu Klartext. Reply-Referenzen bleiben als >>12345 stehen, weil der
    Extraktor sonst nicht sieht, welcher Post auf welchen antwortet."""
    t = (com or "").replace("<br>", "\n")
    t = html.unescape(TAG.sub("", t))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if not quotes_behalten:
        t = re.sub(r"^(>>\d+\s*)+", "", t)
    return t.strip()


def substanz(text: str) -> float:
    """Grobe Dichte-Heuristik. Bewusst keine Ticker-Whitelist: Caps-Token wie
    LIST, APR oder LARP wuerden als Ticker durchgehen, deshalb zaehlt hier nur
    die $-Form, die eindeutig ist. Die eigentliche Erkennung macht das Modell."""
    s = 0.0
    if EXT_LINK.search(text):
        s += 2.0
    if PROZENT.search(text):
        s += 1.5
    if GELD.search(text):
        s += 1.5
    if len(ZAHL.findall(text)) >= 3:
        s += 1.5
    if DOLLAR_TICKER.search(text):
        s += 1.5
    if len(text) >= 250:
        s += 0.5
    return s


def id_verteilung(posts: list[dict]) -> tuple[int, float, int]:
    """Wie viele Poster-IDs, wie viele Posts je ID, welchen Anteil haelt die
    lauteste. Die 4chan-API liefert kein unique_ips (am 19.08.2026 gegen die
    Live-API geprueft: das Feld fehlt am OP), aber /biz/ vergibt Poster-IDs,
    und die tragen dieselbe Information - mit derselben Einschraenkung, dass
    sie nur eine Obergrenze der Personen sind.

    Die beiden Verhaeltniszahlen sind auch dann belastbar, wenn die absolute
    Zahl es nicht ist: gemessen am 19.08.2026 kamen die 242 Posts von /BBBYQ/
    aus 37 IDs (6.5 je ID), die 107 Posts von "Bitcoin is 17 years old" aus
    83 IDs (1.3) - ein kleiner lauter Kreis gegen ein breites Gespraech. Bei
    "8 years day trading" stammten 44 % aller Posts von einer einzigen ID."""
    zaehler: defaultdict[str, int] = defaultdict(int)
    for p in posts:
        pid = p.get("id")
        if pid:
            zaehler[pid] += 1
    if not zaehler:
        return 0, 0.0, 0
    gesamt = sum(zaehler.values())
    return (len(zaehler),
            round(gesamt / len(zaehler), 1),
            round(100 * max(zaehler.values()) / gesamt))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def zitate_kuerzen(text: str, eltern_texte: list[str]) -> str:
    """Kuerzt nur ECHTE Zitatzeilen, also solche, deren Inhalt woertlich in
    einem der Posts steht, auf die dieser Post antwortet.

    Wichtig: Auf /biz/ ist Greentext auch Stilmittel fuer eigene Aussagen
    (">be me", Aufzaehlungen, Pointen). Pauschal jede Zeile mit ">" zu kuerzen
    wuerde also Inhalt zerstoeren, nicht Redundanz. Der Abgleich gegen die
    Elternposts trennt beides sauber."""
    if not eltern_texte:
        return text
    eltern_norm = [_norm(e) for e in eltern_texte]
    raus = []
    for zeile in text.split("\n"):
        z = zeile.strip()
        if (z.startswith(">") and not re.match(r"^>>\d+", z)
                and len(z) > ZITAT_KURZ):
            kern = _norm(z.lstrip(">"))
            if len(kern) > 20 and any(kern in e for e in eltern_norm):
                raus.append(z[:ZITAT_KURZ].rstrip() + " [...]")
                continue
        raus.append(zeile)
    return "\n".join(raus)


def neuester_snapshot() -> Path:
    kandidaten = sorted(RAW.glob("*.jsonl.gz"))
    if not kandidaten:
        raise SystemExit("kein Snapshot in raw/")
    return kandidaten[-1]


def lade(snapshot: Path):
    threads = {}
    with gzip.open(snapshot, "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            threads[d["thread"]] = d["posts"]
    return threads


def betreff(posts) -> str:
    op = posts[0]
    sub = plain(op.get("sub") or "", quotes_behalten=False)
    if sub:
        return sub
    return plain(op.get("com") or "", quotes_behalten=False)[:80]


def report_threads():
    """Thread-Nummern aus dem vorhandenen Report, mit Begruendung der Auswahl."""
    rollen = defaultdict(list)
    p = REPORTS / "latest.json"
    if not p.exists():
        log.warning("kein latest.json - Auswahl A/B entfaellt")
        return rollen, {}
    d = json.loads(p.read_text(encoding="utf-8"))
    sf = d.get("schnell_fuellend", {})
    for eintrag in sf.get("beschleunigend", []) or []:
        rollen[eintrag["thread"]].append(
            f"schnell fuellend: {eintrag.get('posts_letzte_stunde')} Posts in der letzten Stunde, "
            f"{eintrag.get('beschleunigung')}x des eigenen Schnitts von "
            f"{eintrag.get('rate_bisher_pro_h')} Posts/h"
        )
    for eintrag in sf.get("neu_aktiv", []) or []:
        rollen[eintrag["thread"]].append(
            f"neu und auffaellig aktiv: {eintrag.get('posts_letzte_stunde')} Posts, "
            f"Thread erst {eintrag.get('alter_h')} h alt"
        )
    for k in d.get("top_chains", []) or []:
        rollen[k["thread"]].append(
            f"traegt die staerkste Diskussionskette (Score {k.get('score')}, "
            f"{k.get('posts')} Posts, bis zu {k.get('poster')} Poster-IDs)"
        )
    for p_ in d.get("top_posts", []) or []:
        rollen[p_["thread"]].append(
            f"enthaelt einen breit beantworteten Post ({p_.get('antwortende')} Antwortende)"
        )
    return rollen, d


def baue_buendel(thread_no, posts, rollen, jetzt, seit_post=0) -> tuple[str, dict]:
    """Baut das Buendel. seit_post > 0 schaltet den Delta-Modus: nur Posts mit
    hoeherer Nummer kommen hinein, plus die aelteren Posts, die von ihnen
    zitiert werden (sonst haengen die >>Nr-Bezuege in der Luft)."""
    kinder = defaultdict(list)
    eltern = defaultdict(list)
    for p in posts:
        for tgt in QUOTE.findall(p.get("com") or ""):
            kinder[int(tgt)].append(p["no"])
            eltern[p["no"]].append(int(tgt))

    roh = {p["no"]: plain(p.get("com") or "") for p in posts}

    aufbereitet = []
    for p in posts:
        text = zitate_kuerzen(roh[p["no"]],
                              [roh[e] for e in eltern[p["no"]] if e in roh])
        aufbereitet.append({
            "no": p["no"],
            "zeit": p.get("time", 0),
            "id": p.get("id", "?"),
            "text": text,
            "score": substanz(text),
            "antworten": len(kinder[p["no"]]),
            "ist_op": p["no"] == thread_no,
        })

    # Rauschposts: kurz, ohne Zahl, ohne Link, von niemandem beantwortet.
    # Gemessen 1'279 Posts und 12 % des Textes, ohne einen einzigen der 35
    # Substanzposts zu beruehren.
    vorher = len(aufbereitet)
    aufbereitet = [a for a in aufbereitet
                   if a["ist_op"] or a["score"] > 0 or a["antworten"] > 0
                   or len(a["text"]) >= RAUSCH_MAX]
    rausch_weg = vorher - len(aufbereitet)

    delta_modus = seit_post > 0
    kontext_nos = set()
    if delta_modus:
        neu = {a["no"] for a in aufbereitet if a["no"] > seit_post}
        # Zitat-Closure: eine Ebene zurueck, damit Antworten verstaendlich sind
        for n in list(neu):
            for e in eltern.get(n, []):
                if e not in neu and e in roh:
                    kontext_nos.add(e)
        aufbereitet_delta = [a for a in aufbereitet
                             if a["no"] in neu or a["no"] in kontext_nos]
    else:
        aufbereitet_delta = aufbereitet

    gesamt = sum(len(a["text"]) for a in aufbereitet_delta)
    # Bei zu grossen Threads priorisieren statt vorne abschneiden: OP, alles
    # aus dem aktuellen Fenster und die dichtesten Posts bleiben.
    if gesamt <= MAX_ZEICHEN:
        auswahl = aufbereitet_delta
        gekuerzt = False
    else:
        pflicht = {a["no"] for a in aufbereitet_delta
                   if a["ist_op"] or a["zeit"] >= jetzt - FENSTER_AKTUELL_S}
        rest = sorted((a for a in aufbereitet_delta if a["no"] not in pflicht),
                      key=lambda a: (a["score"], a["antworten"]), reverse=True)
        budget = MAX_ZEICHEN - sum(len(a["text"]) for a in aufbereitet_delta
                                   if a["no"] in pflicht)
        for a in rest:
            if budget <= 0:
                break
            pflicht.add(a["no"])
            budget -= len(a["text"])
        auswahl = [a for a in aufbereitet_delta if a["no"] in pflicht]
        gekuerzt = True

    auswahl.sort(key=lambda a: a["zeit"])
    sub = betreff(posts)
    zeiten = [a["zeit"] for a in aufbereitet if a["zeit"]]
    alter_h = round((jetzt - min(zeiten)) / 3600, 1) if zeiten else 0.0
    letzte_h = sum(1 for z in zeiten if z >= jetzt - 3600)
    neue_posts = sum(1 for a in auswahl if a["no"] > seit_post)
    beteiligte, je_id, lauteste = id_verteilung(posts)

    kopf = [
        f"THREAD {thread_no} - {sub}",
        f"URL: https://boards.4chan.org/biz/thread/{thread_no}",
        f"Posts insgesamt: {len(posts)} | Thread-Alter: {alter_h} h | "
        f"Posts in der letzten Stunde: {letzte_h}",
        f"Poster-IDs: {beteiligte} | Posts je ID: {je_id} | "
        f"lauteste ID: {lauteste}% aller Posts",
        "Ausgewaehlt weil: " + "; ".join(rollen.get(thread_no, ["inhaltlich dichte Posts"])),
    ]
    if delta_modus:
        kopf.append(
            f"FORTSETZUNG: Zu diesem Thread liegt bereits ein Extrakt aus einem "
            f"frueheren Lauf vor. Enthalten sind hier NUR die {neue_posts} Posts, die "
            f"seither dazugekommen sind"
            + (f", dazu {len(kontext_nos)} aeltere Posts als Zitatkontext"
               if kontext_nos else "")
            + ". Alles Fruehere steht im Extrakt."
        )
    if gekuerzt:
        kopf.append(
            f"HINWEIS: Zu gross fuer das Buendel ({gesamt} Zeichen). Enthalten sind "
            f"{len(auswahl)} von {len(aufbereitet_delta)} in Frage kommenden Posts: der OP, "
            f"alles aus den letzten {FENSTER_AKTUELL_S // 60} Minuten und die "
            f"inhaltlich dichtesten uebrigen."
        )
    if rausch_weg:
        kopf.append(f"({rausch_weg} sehr kurze Posts ohne Zahl, Link und Antwort weggelassen.)")
    kopf.append("")
    kopf.append("Format je Post: [Post-Nr | Poster-ID | Uhrzeit lokal] Text. "
                "Ein vorangestelltes >>Nr verweist auf den Post, auf den geantwortet wird. "
                "'[...]' markiert eine gekuerzte woertliche Zitatzeile.")
    kopf.append("=" * 70)

    zeilen = []
    for a in auswahl:
        uhr = (datetime.fromtimestamp(a["zeit"], timezone.utc).astimezone(LOKAL).strftime("%H:%M")
               if a["zeit"] else "??:??")
        marke = " [OP]" if a["ist_op"] else ""
        if delta_modus and a["no"] in kontext_nos:
            marke = " [ZITIERTER AELTERER POST]"
        zeilen.append(f"[{a['no']} | ID {a['id']} | {uhr}]{marke} {a['text']}")

    inhalt = "\n".join(kopf) + "\n" + "\n\n".join(zeilen) + "\n"
    meta = {
        "thread": thread_no,
        "betreff": sub,
        "url": f"https://boards.4chan.org/biz/thread/{thread_no}",
        "posts_gesamt": len(posts),
        "posts_im_buendel": len(auswahl),
        "alter_h": alter_h,
        "posts_letzte_stunde": letzte_h,
        "beteiligte": beteiligte,
        "posts_je_id": je_id,
        "lauteste_id_anteil": lauteste,
        "zeichen": len(inhalt),
        "gekuerzt": gekuerzt,
        "rollen": rollen.get(thread_no, ["inhaltlich dichte Posts"]),
        "substanz_summe": round(sum(a["score"] for a in aufbereitet), 1),
        "substanz_posts": sum(1 for a in aufbereitet if a["score"] >= SUBSTANZ_MIN),
        "modus": "delta" if delta_modus else "voll",
        "neue_posts": neue_posts,
        "last_post_no": max((p["no"] for p in posts), default=0),
        "thread_zeichen": sum(len(t) for t in roh.values()),
    }
    return inhalt, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12, help="Anzahl Buendel")
    ap.add_argument("--snapshot", help="Pfad, sonst der juengste")
    ap.add_argument("--cache-status", help="JSON mit {thread: {last_post_no, ...}} "
                                           "aus dem Extrakt-Cache der Gegenstelle")
    args = ap.parse_args()

    cache = {}
    if args.cache_status:
        p = Path(args.cache_status)
        if p.exists():
            try:
                cache = {int(k): v for k, v in
                         json.loads(p.read_text(encoding="utf-8")).items()}
                log.info("Cache-Status: %d Threads bekannt", len(cache))
            except (ValueError, json.JSONDecodeError) as e:
                log.warning("Cache-Status unlesbar (%s) - alle Threads voll", e)
        else:
            log.info("kein Cache-Status - alle Threads voll")

    snapshot = Path(args.snapshot) if args.snapshot else neuester_snapshot()
    threads = lade(snapshot)
    rollen, report = report_threads()
    jetzt = max((p.get("time", 0) for posts in threads.values() for p in posts), default=0)

    # A + B: alles, was der Report als auffaellig meldet - ohne Schwelle
    gesetzt = [t for t in rollen if t in threads]
    # C: nach Substanz auffuellen. Zwei Ranglisten, abwechselnd gezogen: die
    # Summe belohnt vor allem Laenge (ein 400-Post-General hat immer mehr
    # dichte Posts als ein knapper Thread, der dafuer fast nur aus solchen
    # besteht), die Dichte je Post belohnt Kompaktheit. Nur eine von beiden
    # laesst systematisch eine ganze Sorte Thread draussen.
    kandidaten = []
    for t, posts in threads.items():
        if t in rollen:
            continue
        werte = [substanz(plain(p.get("com") or "")) for p in posts]
        s = sum(1 for x in werte if x >= SUBSTANZ_MIN)
        if s:
            kandidaten.append((s, sum(werte), t, len(posts)))
    nach_summe = sorted(kandidaten, key=lambda k: (k[0], k[1]), reverse=True)
    # Unter MIN_POSTS_DICHTE ist die Dichte Rauschen - ein einzelner Post mit
    # Link und drei Zahlen ergaebe sonst den Spitzenwert der Rangliste.
    nach_dichte = sorted(
        (k for k in kandidaten if k[3] >= MIN_POSTS_DICHTE),
        key=lambda k: k[1] / k[3], reverse=True)
    plaetze = max(0, args.top - len(gesetzt))
    auffuellen: list[int] = []
    for a, b in itertools.zip_longest(nach_summe, nach_dichte):
        for k in (a, b):
            if k and k[2] not in auffuellen and len(auffuellen) < plaetze:
                auffuellen.append(k[2])
    gewaehlt = gesetzt + auffuellen

    if BUNDLES.exists():
        for alt in BUNDLES.glob("*.txt"):
            alt.unlink()
    BUNDLES.mkdir(exist_ok=True)

    manifest = {
        "stamp_utc": report.get("stamp"),
        "erzeugt_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot": snapshot.name,
        "snapshot_zeit_lokal": (
            datetime.fromtimestamp(jetzt, timezone.utc).astimezone(LOKAL).strftime("%d.%m.%Y %H:%M")
            if jetzt else None
        ),
        "threads_im_board": len(threads),
        "buendel": [],
    }
    for t in gewaehlt:
        posts = threads[t]
        eintrag = cache.get(t) or {}
        seit = int(eintrag.get("last_post_no") or 0)
        thread_zeichen = sum(len(plain(p.get("com") or "")) for p in posts)

        # Kein Delta, wenn der Thread zu klein ist (Extrakt kostet dann mehr als
        # das Buendel) oder wenn der Cache-Eintrag zu oft fortgeschrieben wurde
        # (Fortschreibung einer Fortschreibung driftet - Rohdaten bleiben da,
        # der Neuaufbau ist also billig und jederzeit moeglich).
        grund_voll = None
        if seit and thread_zeichen < MIN_CACHE_ZEICHEN:
            grund_voll = "Thread zu klein fuer Delta"
        if seit and eintrag.get("neuaufbau_faellig"):
            grund_voll = "Neuaufbau faellig"
        if grund_voll:
            seit = 0

        neu_da = sum(1 for p in posts if p["no"] > seit) if seit else None
        if seit and not neu_da:
            # Nichts Neues: der vorhandene Extrakt gilt unveraendert weiter.
            # Genau dieser Fall trat gemessen bei einem 48-KB-Thread mit 0.0 KB
            # Delta auf, der trotzdem komplett durchs Modell lief.
            u_bet, u_je_id, u_laut = id_verteilung(posts)
            manifest["buendel"].append({
                "thread": t,
                "betreff": betreff(posts),
                "url": f"https://boards.4chan.org/biz/thread/{t}",
                "posts_gesamt": len(posts),
                "alter_h": round((jetzt - min(p.get("time", jetzt) for p in posts)) / 3600, 1),
                "posts_letzte_stunde": 0,
                "beteiligte": u_bet,
                "posts_je_id": u_je_id,
                "lauteste_id_anteil": u_laut,
                "rollen": rollen.get(t, ["inhaltlich dichte Posts"]),
                "modus": "unveraendert",
                "neue_posts": 0,
                "zeichen": 0,
                # Auch ohne neues Buendel braucht die Synthese-Stufe den
                # Substanz-Score: er bestimmt dort die Eingabe-Reihenfolge.
                "substanz_summe": round(
                    sum(substanz(plain(p.get("com") or "")) for p in posts), 1),
                "last_post_no": max((p["no"] for p in posts), default=0),
            })
            log.info("  %s  unveraendert - Extrakt gilt weiter", t)
            continue

        inhalt, meta = baue_buendel(t, posts, rollen, jetzt, seit_post=seit)
        if grund_voll:
            meta["voll_weil"] = grund_voll
        ziel = BUNDLES / f"{t}.txt"
        ziel.write_text(inhalt, encoding="utf-8")
        meta["datei"] = str(ziel)
        manifest["buendel"].append(meta)
        log.info("  %s  %6d Zeichen  [%s]  %s", ziel.name, meta["zeichen"],
                 meta["modus"], meta["betreff"][:40])

    voll = sum(1 for b in manifest["buendel"] if b["modus"] == "voll")
    delta = sum(1 for b in manifest["buendel"] if b["modus"] == "delta")
    unver = sum(1 for b in manifest["buendel"] if b["modus"] == "unveraendert")
    (BUNDLES / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("%d Buendel (%d voll, %d delta, %d unveraendert), %d KB gesamt",
             len(manifest["buendel"]), voll, delta, unver,
             sum(b["zeichen"] for b in manifest["buendel"]) // 1024)
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
