#!/usr/bin/env python3
"""Verdichtet den juengsten /biz/-Snapshot zu einem kleinen Report.

Drei Kennzahlen, alle ohne OPs:
  1. Posts nach Anzahl VERSCHIEDENER Antwortender, gefiltert auf inhaltliche
     Substanz (Mindestlaenge). Der Laengenfilter ist noetig, weil Ein-Zeichen-
     Gags sonst die Rangliste dominieren.
  2. Diskussionsketten nach Score = Laenge^0.5 * Poster^0.5 (geometrisches
     Mittel), damit weder Zweikaempfe noch kurze Breitendiskussionen gewinnen.
  3. Schnell fuellende Threads: Posts/Stunde in der letzten Stunde gegen den
     eigenen bisherigen Schnitt des Threads (nicht gegen andere Threads), damit
     dauerbelebte Generals (/smg/ etc.) nur auffallen, wenn sie selbst gerade
     schneller werden als sonst. Zu junge Threads ohne eigene Baseline landen
     separat als "neu_aktiv". Braucht nur den aktuellen Snapshot, weil jeder
     Post seinen echten 4chan-Zeitstempel mitbringt.

Novelty: bereits gemeldete Posts stehen in seen.json und werden im Report als
"bereits gemeldet" markiert, damit aufeinanderfolgende Laeufe nicht dieselben
Eintraege als neu ausgeben. Gilt fuer Kennzahl 1 und 2; Kennzahl 3 beschreibt
einen Momentanzustand und braucht keine Deduplizierung ueber Laeufe hinweg.

Hinweis zu Poster-IDs: sie sind pro Thread vergeben und durch IP-Wechsel
manipulierbar. Alle ID-Zahlen sind Obergrenzen, keine Personenzaehlung.
"""
import gzip
import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
REPORTS = ROOT / "reports"
SEEN_FILE = ROOT / "seen.json"

MIN_LEN = 40        # Mindestzeichen fuer "inhaltliche Substanz"
TOP_POSTS = 10
TOP_CHAINS = 3
ALPHA = 0.5

FENSTER_JETZT_S = 3600   # Beobachtungsfenster "gerade eben" fuer Kennzahl 3
MIN_POSTS_JETZT = 4      # Mindest-Posts im Fenster, sonst zu viel Rauschen
MIN_BASIS_STUNDEN = 1.0  # Mindestvorgeschichte, um eine eigene Baseline zu bilden
BASIS_FLOOR = 2.0        # Mindest-Nenner Posts/h, gegen absurde Werte bei Fast-Null-Basis
TOP_VELOCITY = 5
GENERAL_RE = re.compile(r"^/\w{2,10}/")  # Format wie /smg/, /pmg/, /GME/

QUOTE = re.compile(r'<a href="#p(\d+)" class="quotelink">')
TAG = re.compile(r"<[^>]+>")


def plain(com: str) -> str:
    t = html.unescape(TAG.sub("", (com or "").replace("<br>", " ")))
    return re.sub(r"^(>>\d+\s*)+", "", re.sub(r"\s+", " ", t)).strip()


def cut(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + "..."


def neuester_snapshot() -> Path:
    kandidaten = sorted(RAW.glob("*.jsonl.gz"))
    if not kandidaten:
        raise SystemExit("Kein Snapshot vorhanden - erst crawl_biz.py laufen lassen.")
    return kandidaten[-1]


def lade(snapshot: Path):
    posts, thread_of, subject = {}, {}, {}
    with gzip.open(snapshot, "rt", encoding="utf-8") as fh:
        for zeile in fh:
            eintrag = json.loads(zeile)
            tno = eintrag["thread"]
            for p in eintrag["posts"]:
                posts[p["no"]] = p
                thread_of[p["no"]] = tno
                if p.get("resto", 0) == 0:
                    subject[tno] = plain(p.get("sub", "")) or cut(plain(p.get("com", "")), 60) or "(ohne Betreff)"
    return posts, thread_of, subject


def baue_graph(posts, thread_of):
    children = defaultdict(set)
    for no, p in posts.items():
        for ziel in set(int(m) for m in QUOTE.findall(p.get("com") or "")):
            if ziel != no and ziel in posts and thread_of[ziel] == thread_of[no]:
                children[ziel].add(no)
    return children


def pareto_front(root, children, depth, pid, budget):
    """Nicht-dominierte (Laenge, unique, Pfad) ab root."""
    front = []

    def dominiert(ln, uq):
        return any(a >= ln and b >= uq for a, b, _ in front)

    def dfs(node, pfad, ids):
        budget[0] -= 1
        if budget[0] <= 0:
            return
        ids2 = ids | {pid[node]}
        pfad2 = pfad + [node]
        if not dominiert(len(pfad2), len(ids2)):
            front[:] = [e for e in front if not (len(pfad2) >= e[0] and len(ids2) >= e[1])]
            front.append((len(pfad2), len(ids2), pfad2))
        rest = depth[node] - 1
        if rest and dominiert(len(pfad2) + rest, len(ids2) + rest):
            return
        for k in sorted(children[node], key=lambda x: -depth[x]):
            dfs(k, pfad2, ids2)

    dfs(root, [], frozenset())
    return front


def fuellrate(posts, thread_of, subject):
    """Kennzahl 3: Threads, die gerade schneller wachsen als sonst.

    Vergleicht bewusst gegen den eigenen Schnitt des Threads, nicht gegen
    andere Threads - sonst dominieren dauerbelebte Generals die Liste, obwohl
    die nur "immer schon so schnell" sind. Zu junge Threads ohne genug
    Vorgeschichte fuer eine Baseline laufen separat als "neu_aktiv".
    """
    zeiten_je_thread = defaultdict(list)
    for no, p in posts.items():
        if p.get("resto", 0) == 0:
            continue
        t = p.get("time")
        if t:
            zeiten_je_thread[thread_of[no]].append(t)
    if not zeiten_je_thread:
        return [], []
    jetzt = max(t for ts in zeiten_je_thread.values() for t in ts)

    beschleunigend, neu_aktiv = [], []
    for tno, zeiten in zeiten_je_thread.items():
        zeiten.sort()
        alter_h = (jetzt - zeiten[0]) / 3600
        posts_jetzt = sum(1 for t in zeiten if t >= jetzt - FENSTER_JETZT_S)
        if posts_jetzt < MIN_POSTS_JETZT:
            continue
        eintrag = {
            "thread": tno, "betreff": subject.get(tno, "?"),
            "url": f"https://boards.4chan.org/biz/thread/{tno}",
            "posts_letzte_stunde": posts_jetzt, "alter_h": round(alter_h, 1),
            "general_format": bool(GENERAL_RE.match(subject.get(tno, "") or "")),
        }
        basis_h = alter_h - FENSTER_JETZT_S / 3600
        if basis_h < MIN_BASIS_STUNDEN:
            neu_aktiv.append(eintrag)
            continue
        basis_zeiten = [t for t in zeiten if t < jetzt - FENSTER_JETZT_S]
        rate_basis = len(basis_zeiten) / basis_h
        rate_jetzt = posts_jetzt / (FENSTER_JETZT_S / 3600)
        beschleunigend.append({
            **eintrag,
            "rate_bisher_pro_h": round(rate_basis, 1),
            "beschleunigung": round(rate_jetzt / max(rate_basis, BASIS_FLOOR), 1),
        })

    beschleunigend.sort(key=lambda e: -e["beschleunigung"])
    neu_aktiv.sort(key=lambda e: -e["posts_letzte_stunde"])
    return beschleunigend[:TOP_VELOCITY], neu_aktiv[:TOP_VELOCITY]


def main() -> int:
    snapshot = neuester_snapshot()
    stamp = snapshot.name.split(".")[0]
    posts, thread_of, subject = lade(snapshot)
    children = baue_graph(posts, thread_of)
    pid = {no: p.get("id") or "?" for no, p in posts.items()}

    depth = {}
    for no in sorted(posts, reverse=True):
        depth[no] = 1 + max((depth[k] for k in children[no]), default=0)

    seen = json.loads(SEEN_FILE.read_text(encoding="utf-8")) if SEEN_FILE.exists() else {}

    # --- Kennzahl 1: Posts nach verschiedenen Antwortenden -------------------
    kandidaten = []
    for no, p in posts.items():
        if p.get("resto", 0) == 0:
            continue
        text = plain(p.get("com"))
        if len(text) < MIN_LEN:
            continue
        antwortende = set(pid[k] for k in children[no]) - {pid[no]}
        if antwortende:
            kandidaten.append((len(antwortende), len(children[no]), no, text))
    kandidaten.sort(key=lambda r: (-r[0], -r[1], r[2]))

    top_posts = []
    for anz, replies, no, text in kandidaten[:TOP_POSTS]:
        tno = thread_of[no]
        top_posts.append({
            "post": no, "thread": tno, "betreff": subject.get(tno, "?"),
            "antwortende": anz, "replies": replies,
            "url": f"https://boards.4chan.org/biz/thread/{tno}#p{no}",
            "erstmals": seen.get(str(no), stamp),
            "text": cut(text, 600),
        })

    # --- Kennzahl 2: Diskussionsketten --------------------------------------
    budget = [2_000_000]
    zeilen = []
    for no, p in posts.items():
        if p.get("resto", 0) == 0 or depth[no] < 5:
            continue
        for ln, uq, pfad in pareto_front(no, children, depth, pid, budget):
            zeilen.append(((ln ** (1 - ALPHA)) * (uq ** ALPHA), ln, uq, pfad))
    zeilen.sort(key=lambda r: (-r[0], -r[1], -r[2]))

    top_chains, gesehen_wurzeln = [], set()
    for score, ln, uq, pfad in zeilen:
        wurzel = pfad[0]
        if wurzel in gesehen_wurzeln:
            continue
        # Ketten aus demselben Thread nicht mehrfach
        if any(c["thread"] == thread_of[wurzel] for c in top_chains):
            continue
        gesehen_wurzeln.add(wurzel)
        tno = thread_of[wurzel]
        top_chains.append({
            "wurzel": wurzel, "thread": tno, "betreff": subject.get(tno, "?"),
            "score": round(score, 2), "posts": ln, "poster": uq,
            "url": f"https://boards.4chan.org/biz/thread/{tno}#p{wurzel}",
            "erstmals": seen.get(str(wurzel), stamp),
            "kette": [{"id": pid[n], "post": n, "text": cut(plain(posts[n].get("com")) or "(nur Bild)", 300)}
                      for n in pfad],
        })
        if len(top_chains) >= TOP_CHAINS:
            break

    # --- Kennzahl 3: schnell fuellende Threads ------------------------------
    beschleunigend, neu_aktiv = fuellrate(posts, thread_of, subject)

    report = {
        "stamp": stamp,
        "erzeugt_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot": snapshot.name,
        "threads": len(set(thread_of.values())),
        "posts": len(posts),
        "posts_ohne_op": sum(1 for p in posts.values() if p.get("resto", 0) != 0),
        "top_posts": top_posts,
        "top_chains": top_chains,
        "schnell_fuellend": {
            "beschleunigend": beschleunigend,
            "neu_aktiv": neu_aktiv,
            "hinweis": "beschleunigend = Posts/h in der letzten Stunde geteilt durch den "
                       "eigenen bisherigen Schnitt des Threads (>1h Vorgeschichte noetig). "
                       "neu_aktiv = Thread ist zu jung fuer eine eigene Baseline, zeigt aber "
                       f"bereits >= {MIN_POSTS_JETZT} Posts in der letzten Stunde.",
        },
        "hinweis": "Poster-IDs sind pro Thread vergeben und manipulierbar; alle ID-Zahlen sind Obergrenzen.",
    }

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{stamp}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for eintrag in top_posts:
        seen.setdefault(str(eintrag["post"]), stamp)
    for eintrag in top_chains:
        seen.setdefault(str(eintrag["wurzel"]), stamp)
    if len(seen) > 5000:  # aelteste Eintraege kappen
        seen = dict(sorted(seen.items(), key=lambda kv: kv[1])[-5000:])
    SEEN_FILE.write_text(json.dumps(seen, indent=0), encoding="utf-8")

    heute = stamp[:10]
    neu_posts = sum(1 for e in top_posts if e["erstmals"][:10] == heute)
    print(f"Report {stamp}: {report['threads']} Threads, {report['posts']} Posts, "
          f"{neu_posts}/{len(top_posts)} Top-Posts erstmals heute, {len(top_chains)} Ketten, "
          f"{len(beschleunigend)} beschleunigend, {len(neu_aktiv)} neu_aktiv")
    if budget[0] <= 0:
        print("WARNUNG: Pfadbudget der Kettensuche erschoepft - Ketten evtl. unvollstaendig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
