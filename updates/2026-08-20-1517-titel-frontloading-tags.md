---
datum: 2026-08-20
agent: worktree-agent-a6efd0c4caee62612
typ: feature
commit: 7f90c51
---

# Titel-Frontloading (Hook ≤55) und Tag-Phrasen statt Fragmente

**Was:**
- `run_report.py`: `TITEL_PROMPT` verlangt jetzt frontloadete Suchbegriffe
  (Ticker/Firmen-/Asset-Name zuerst, CAPS nur auf Suchbegriffen, kein Hype-
  Füller davor) und maximal 55 Zeichen Hook; neue Konstante `HOOK_MAX_ZEICHEN`,
  `_hook_bereinigen()` kappt per `_wortgrenze()` an der Wortgrenze statt hart
  bei 75. `TITEL_SUFFIX`, Wiederholungssperre und Zweitversuch unverändert.
- `video_report.py`: `tags_bauen()` baut Tagesthemen als vollständige
  Suchphrasen — Titel-Eigennamen, Firmenname+Ticker aus dem Bericht
  («Klarna (KLAR)» liefert beide), ##-Überschriften-Teil NACH dem Doppelpunkt,
  Kapiteltitel aus `folien.json` (nur Abschnitte mit Doppelpunkt-Thema),
  zuletzt Themenköpfe; feste Serien-Tags mit reserviertem Budget am Ende.
  Neue Helfer `_tag_saeubern()` (Apostroph ersatzlos: kein «day s») und
  `_phrase_kuerzen()` (Teil vor dem Komma, ohne führenden Artikel, mind.
  zwei Wörter). `STOPP_TAGS` um `macro`, `glossary`, `board life` ergänzt.
  `_hook_gesprochen()` lässt Klammer-Ticker in der Sprechfassung weg.
- Tests in `tests/test_upload_metadaten.py` ergänzt (Phrasen, folien.json-
  Quelle, Firmenname+Ticker, Serien-Tag-Budget, gesprochener Hook).

**Warum:** 43 von 54 Views kommen über die Suche, aber YouTube kappt Titel
dort bei ~60–70 Zeichen — das Suffix und teils der Hook fielen weg (Titel
65–82 Zeichen). `tags_bauen()` nutzte nur 108 von 450 Zeichen und lieferte
Rauschen wie «impossible» oder «moderna pumps»
(research/messung-metadaten-upload-2026-08-20.md, Abschnitte 2 und 4;
Prio 3 aus research/brainstorming/brainstorm-zuschauerzahl-erhoehen-2026-08-20).

**Auswirkung:** Ab dem Bericht-Cron heute 20:35 entstehen Titel mit
Suchbegriffen vorn und ≤~74 Zeichen gesamt (Sonnet-Testlauf gegen den
Bericht vom 20.08.: «MRNA Cancer Vaccine Pump: $60B Cap, 200% in 1 Day
| /biz/ …», Hook 49 Zeichen). Die Tag-Listen der letzten fünf Tage kämen
neu auf 164–334 statt 106–127 von 450 Zeichen, ohne Fragmente. Bewusst
NICHT geändert: Separator-Konvention « | /biz/ », Hook-Rückgewinnung per
`split(" | ")`, Kappungsregel `len(t)+2`, defensive 100-Zeichen-Kappung
in `titel_laden()`.

**Offen:** —
