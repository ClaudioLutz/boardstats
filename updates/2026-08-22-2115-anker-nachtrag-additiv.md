---
datum: 2026-08-22
agent: worktree-anker-nachtrag-merge
typ: bugfix
commit: 9ef57d9
---

# Anker-Nachforderung traegt Stichworte nach, statt das Drehbuch neu zu schreiben

**Was:** `folien_generieren()` fordert bei ankerlosen Absaetzen nicht mehr
das ganze Drehbuch erneut an, sondern holt mit `ANKER_NACHTRAG_PROMPT` nur
die fehlenden Stichworte und mergt sie ein. Neu dafuer:
`_nachtrag_holen()` (kleiner Sonnet-Aufruf, gibt nur `{"nachtrag": [...]}`
zurueck), `_nachtrag_mergen()` (findet den Abschnitt, verwirft Stichworte
ohne auffindbaren Anker, ruft den Sortierer), `_nach_anker_ordnen()`
(einsortieren an der Ankerstelle) und `_abschnitt_flachtext()` (Rumpftext
je Abschnitt ohne Laengenfilter, fuer die Positionssuche).
`_abdeckung_nachtrag()` liefert jetzt die betroffenen Absaetze im Volltext
(600 statt 90 Zeichen) — das Modell soll seine Anker daraus waehlen, dafuer
muss es sie lesen koennen. 6 neue Tests in `tests/test_abdeckung.py`.

**Warum:** Am 22.08.2026 im produktiven Report gemessen: die Nachforderung
ging mit **3** ankerlosen Absaetzen hinein und kam mit **12** heraus. Der
Grund steckte im Prompt selbst — er verlangte *"Write the whole storyboard
again … keep the rest of the coverage"*. Das Modell reparierte die drei
genannten Absaetze und verlor die Abdeckung anderswo. Der Schutz in
`folien_generieren()` (den besseren von beiden nehmen) griff korrekt, das
Ergebnis wurde verworfen — aber der Aufruf kostete einen vollen
Sonnet-Durchgang: das Drehbuch dauerte **11:20** statt der sonst ueblichen
gut 5 Minuten, ohne je etwas beizutragen. Ein Mechanismus, der die
Laufzeit verdoppelt und strukturell nichts liefern kann, ist schlimmer als
keiner.

Die Ursache dahinter bleibt bestehen und ist separat zu behandeln: das
Modell verteilt die Stichworte extrem ungleich. Im selben Bericht bekam der
**laengste** Abschnitt die **wenigsten** Punkte (Iran/Hormuz: 5 Absaetze,
4 Stichworte = 0,8 je Absatz), waehrend `50% tariffs on Canada` bei 2
Absaetzen 12 Stichworte trug (6,0). Faktor 7.

**Auswirkung:** Der Nachtrag ist rein additiv und kann die Abdeckung
anderswo darum nicht mehr kosten — das war der eigentliche Defekt. Gegen
die echten Produktionsdaten von heute verifiziert: 3 Luecken → **0**, drei
von vier angebotenen Stichworten uebernommen, das vierte (erfundener Anker)
verworfen, Ankerstellen danach streng aufsteigend
(`120, 260, 361, 501, 585, 1040, 1255`) — die neuen Punkte sitzen an ihrer
Sprechstelle mitten im Kapitel, nicht angehaengt am Ende. Das ist wichtig,
weil die Reihenfolge im Renderer die Zeit traegt. Der zweite Aufruf ist
zudem deutlich kleiner (nur die Luecken statt des ganzen Drehbuchs), die
Drehbuch-Stufe sollte wieder Richtung 5–6 Minuten gehen.
`ruff`/`mypy` sauber, **269 Tests gruen** (263 + 6).

**Offen:** Die ungleiche Stichwortverteilung selbst (Faktor 7 zwischen
laengstem und kuerzestem Abschnitt) — der Nachtrag heilt jetzt das Symptom
zuverlaessig, erzeugt aber weiterhin jeden Tag einen zweiten Modellaufruf.
Ein Budget je Abschnitt im `FOLIEN_PROMPT` waere der Angriff auf die
Ursache. Ausserdem noch nicht im echten Cron-Lauf beobachtet: der Fix
greift erstmals beim Report am 23.08. 20:35.
