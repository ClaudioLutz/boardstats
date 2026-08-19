---
datum: 2026-08-19
agent: main
typ: feature
commit: <folgt>
---

# Substanz-Score normalisiert: Dichte je Post als zweite Rangliste

**Was:** An zwei Stellen wird die Rangfolge nicht mehr aus einer, sondern
abwechselnd aus zwei Ranglisten gezogen — der Substanz-**Summe** und der
Substanz-**Dichte je Post**:

- `run_report.py`, `sandwich()`: bestimmt die Reihenfolge der Extrakte in der
  Synthese-Eingabe. Neu belegen die zwei summenstärksten Threads die vorderen,
  die zwei dichtesten die hinteren Randplätze.
- `bundle_biz.py`, Auswahl C: füllt die Bündelplätze auf, die A+B (Rollen aus
  dem Report) offen lassen.
- Neue Konstante `MIN_POSTS_DICHTE = 20` in beiden Dateien: darunter zählt die
  Dichte nicht mit.
- Neu `tests/test_auswahl.py` (9 Tests) für `sandwich()` und
  `abdeckung_pruefen()`.

**Warum:** Gemessen am 19.08.2026 am echten Manifest. `substanz_summe` ist
eine Summe über alle Posts und damit praktisch ein Mass für Threadlänge. Alle
vier privilegierten Sandwich-Plätze gingen an die vier längsten Threads
(/XMR/ 298 Posts, /BBBYQ/ 242, /smg/ 410, /smg/ 345). Die drei pro Post
dichtesten — 0.86, 0.84 und 0.67 gegen 0.44 des Zweitplatzierten — lagen auf
Position 5, 10 und 11, also genau in der Mitte, die laut der im Docstring
zitierten Studie (arXiv 2307.03172) um 20–30 Punkte abfällt. Ein kompakter,
inhaltlich dichter Thread hatte keine Chance auf einen Randplatz.

Die Schwelle stammt aus derselben Messung: ohne sie führten Threads mit 1, 5
und 11 Posts die Dichte-Rangliste an — ein einzelner Post mit Link und drei
Zahlen erreicht rechnerisch den Spitzenwert.

**Auswirkung:** Nach der Änderung liegen auf den Randplätzen `/XMR/` und
`/smg/ 410` (Summe) sowie «40 is the new 60» und «8 years day trading»
(Dichte) — beide Sorten Thread sind vertreten. Die Auswahl selbst ändert sich
heute **nicht**: `report_threads()` liefert bereits 15 Rollen-Threads, Auswahl
C hat bei `--top 15` null freie Plätze. Der dortige Fix wirkt erst, wenn der
Report weniger auffällige Threads meldet oder `--top` steigt.

Bewusst nicht geändert: `substanz_summe` selbst bleibt als Feld im Manifest,
damit ältere Läufe vergleichbar bleiben.

**Offen:** `tests/test_kulisse.py` hat zwei Fehler, die schon vor dieser
Änderung bestanden (Mock-Signatur kennt `animiert_erlauben` nicht) — separat
zu beheben.
