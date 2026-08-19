---
datum: 2026-08-19
agent: main
typ: bugfix
commit: <folgt>
---

# test_kulisse: Mock von motiv_laden an die echte Signatur angeglichen

**Was:** In `tests/test_kulisse.py` nimmt der Ersatz für `motiv_laden()` jetzt
`animiert_erlauben` entgegen und liefert das Tupel `(pfade, pruefframes)`
statt nur der Pfadliste.

**Warum:** Die Suite war rot — zwei Fehler in `AblehnungAblegen`, beide
`TypeError: laden() got an unexpected keyword argument 'animiert_erlauben'`.
Das echte `motiv_laden()` (`run_report.py:1247`) hat mit den
Bewegtbild-Anhängen einen dritten Parameter und einen zweiten Rückgabewert
bekommen, der Mock blieb auf dem alten Stand. Die Fehler bestanden vor der
heutigen Arbeit und waren nicht von ihr verursacht; eine rote Suite verdeckt
aber künftige Regressionen, deshalb hier mitrepariert.

**Auswirkung:** `python -m unittest discover -s tests` läuft mit 61 Tests
durch — lokal und auf hp-ubuntu. Am Produktivcode ändert sich nichts.

**Offen:** —
