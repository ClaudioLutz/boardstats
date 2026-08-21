---
datum: 2026-08-22
agent: main (Branch retention-a-bis-d)
typ: feature
commit: <Hash, sobald bekannt>
---

# Stossrichtungen B und C: Headlines als Behauptung, Video-Ende umgebaut

**Was:**

*B — Headline-Regeln (`run_report.py`, `bericht_html.py`):*

- `bericht_html._ist_ueberschrift()` erkennt jetzt zusätzlich Zeilen, die mit
  `## ` beginnen. Die alte Versalien-Heuristik bleibt als zweiter Pfad.
- Synthese-Prompt Regel 1: Überschriften werden vom Modell selbst als `## `-Zeile
  geschrieben (die einzige Markdown-Ausnahme im sonst reinen Plain-Text).
- Neue Regeln 4a/4b: Überschrift ist eine **Behauptung oder Frage mit Einsatz** in
  sentence case, **hart auf 40 Zeichen** begrenzt (= YouTube-Kapitelname), mit
  Kernzahl verschmolzen; Reliability als **Tag in eckigen Klammern** am Ende
  (ersetzt den früheren Schlusssatz je Thema, alte Regel 10). Darunter eine
  **Deck-Zeile**: ein Satz mit dem schärfsten Fakt des Abschnitts.
- Regel 9: **kein eigener Abschnitt „FILLING FAST" mehr** — die Beschleunigung
  wandert in den Satz des jeweiligen Themas.
- Regel 8b: unveränderte Themen sammeln sich unter der festen Überschrift
  `## Still true from yesterday` (neue Konstante `ABSCHNITT_STILL_TRUE`, Erkennung
  über `ist_still_true()`, die auch die alte Form `UNCHANGED …` matcht).
- `kapitel_bauen()` strippt den `[...]`-Tag aus dem YouTube-Kapitelnamen.

*C — Video-Ende (`video_report.py`, `szenen.py`):*

- `abschnitte_erzeugen()` nimmt den „Still true"-Abschnitt **ganz aus der
  Tonspur** (inkl. seiner Thread-URLs, die sonst Bilder beanspruchen würden). Im
  `bericht.md` bleibt er stehen.
- Neuer Schluss-Beat vor dem Abbinder: Drehbuch-Feld `"schluss"` mit `zitat`
  (stärkste Board-Zeile des Tages) und `frage` (Cliffhanger für morgen). Neue
  Block-Rollen `schluss_zitat`/`schluss_frage`, eigene Zitat-Szene im v7-Pfad.
- `szenen.outro_tafel(frage)` zeigt die Cliffhanger-Frage bis zum letzten Frame.
- Tempo-Badge: neues Drehbuch-Feld `"tempo"` je Abschnitt erscheint am
  Kapitelzähler (`CHAPTER 03 / 05 · 2.5x`).
- `PRAES_OUTRO` von drei Sätzen auf einen gekürzt (< 5 s gesprochen).

**Warum:** Brainstorming-Session vom 21.08.2026, Stossrichtungen B und C.
Headlines wie „STOCKS: URANIUM, HOOD, ADOBE" sind Etiketten, keine Gründe
weiterzuschauen; „UNCHANGED FROM YESTERDAY" stand als letztes Kapitel im Video
(gemessen 07:07 im Lauf vom 21.08.) — die schwächste Stelle des Berichts an der
auffälligsten Stelle des Videos.

**Der strukturell heikle Teil:** `_ist_ueberschrift()` verwarf bis dahin **jede**
Zeile mit Kleinbuchstaben. Eine sentence-case-Headline hätte die gesamte
`##`-Abschnittserkennung still zerstört — daran hängen Video-Kapitel,
`folien_zuordnen()` und `shorts.py`. Deshalb der explizite Marker statt einer
gelockerten Heuristik, und deshalb sichern `tests/test_headlines_schluss.py`
beide Schreibweisen ab.

**Auswirkung:** Ab dem nächsten Lauf tragen die Kapitel Behauptungen statt Listen,
das Video endet mit Zitat + offener Frage statt mit unveränderten Themen. Bewusst
**nicht** geändert: der Kapitelzähler `CHAPTER 03 / 05` — den gab es bereits, der
Intent-Punkt „Fortschrittssignal 3 of 5" war schon erfüllt. Die Deck-Zeile wird im
Video nicht als eigenes Overlay gerendert; sie wird gesprochen und vom Drehbuch als
erster Stichpunkt aufgegriffen.

**Offen:** Stossrichtung D (Kapitel-Retention-Messung).
