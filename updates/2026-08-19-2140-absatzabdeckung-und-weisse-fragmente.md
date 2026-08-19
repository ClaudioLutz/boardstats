---
datum: 2026-08-19
agent: worktree-stichwort-luecke
typ: bugfix
commit: 4810739
---

# Jeder Absatz braucht ein Stichwort; die Fragmente stehen weiss

**Was:**
1. `run_report.py` — neue Abdeckungsprüfung `_abdeckung_luecken()` samt
   `_absaetze()` und `_flachtext()`: nach jedem Drehbuch-Lauf wird geprüft, ob
   jeder substanzielle Absatz (≥ 200 Zeichen) mindestens eine Anker-Phrase
   trägt. Bleiben Absätze leer, geht ein zweiter Sonnet-Aufruf mit
   `_abdeckung_nachtrag()` raus, der sie beim Namen nennt — dieselbe Mechanik
   wie beim wiederholten Titel-Hook. Der bisherige `folien_generieren()` heisst
   jetzt `_folien_versuch()`; der neue Wrapper wählt am Ende das Drehbuch mit
   weniger Lücken. `FOLIEN_PROMPT` fordert die Absatz-Abdeckung zusätzlich
   ausdrücklich.
2. `szenen.py` — die Stichwort-Fragmente in `detail_teile()` sind weiss
   (`HELL`) statt im Grau der geparkten Punkte (`KARTE_ALT`).
3. `tests/test_abdeckung.py` — 9 Tests: Absatz-Zerlegung (kurze Übergänge,
   Markdown-Links, Anker über Zeilenumbruch), Lückenfund, Ausnahme für
   „unchanged since yesterday", Nachforder-Text, Fragmentfarbe.

**Warum:** Nutzerbefund zum Video vom 19.08.: „von etwa 07:59 bis ca 09:19 gab
es keine neuen Stichworte … viel geredet und wenig geschrieben" und „die
Stichworte sollten weiss gefüllt sein, nicht grau".

Gemessen statt geraten (`research/messung_stichwort_luecke.py`, echte
`szenen_bauen()`-Pipeline auf dem Renderstand von hp-ubuntu): Das Kapitel
„SELF-REPORTED TRACK RECORDS" läuft 124.7 s — das längste des Videos, die
anderen 40–94 s — hat aber nur 6 Stichworte, und alle sechs Anker liegen in
seinen ersten 32 Sekunden (7:22.3 bis 7:51.3). Danach folgen 93 s Rede ohne
ein einziges Drehbuch-Stichwort. Der Abschnitt besteht aus sechs Absätzen
(sechs Threads); das Modell hat alle Stichworte für den ersten geschrieben.
Der Renderer füllt solche Strecken mit Fallback-Bullets aus `_luecken_fuellen()`,
und die tragen per Konstruktion kein `detail`-Feld — daher Minute 8: 3 Punkte,
0 Fragmente, alle als Füller. Kein Renderer-Fehler: alle 6 Anker wurden
gefunden, nichts wurde weggekappt.

Die Prompt-Regel „one bullet for roughly EVERY sentence of the WHOLE section"
stand da bereits — und wurde ignoriert. Deshalb die Prüfung im Code.

**Auswirkung:** Ab dem nächsten Cron-Lauf. Kalibrierung gegen die echten
Drehbücher: 17.08. 0 Lücken (kein Zusatzaufruf), 18.08. 2, der Renderstand
vom 19.08. 5 — darunter genau die vier unversorgten Absätze des gemeldeten
Fensters. Kostenrahmen: höchstens ein zusätzlicher Sonnet-Aufruf pro Tag; ein
scheiternder Nachtrag blockiert nichts, dann gilt der erste Versuch. Bewusst
nicht geändert: `LUECKE_MAX` und das Füllverhalten (die Füller sind das Netz,
nicht die Ursache) sowie das Grau der geparkten Punkte in der Themen-Karte —
aufgehellt wurde nur das Fragment, das gerade gesprochen wird.

**Offen:** Das bereits veröffentlichte Video vom 19.08. bleibt wie es ist; die
Wirkung zeigt sich erst am Drehbuch von morgen.
