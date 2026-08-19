---
datum: 2026-08-19
agent: main
typ: bugfix
commit: 7e058b4
---

# Folien-Timeout auf 700s erhöht (Overseer-Testlauf)

**Was:** `TIMEOUT_FOLIEN` in `run_report.py` von 420s auf 700s erhöht.

**Warum:** Overseer-Kontrolle der heutigen "substantiellen Anpassungen"
(Nutzeranweisung: prüfen, ob sie greifen, bevor der nächste Cron-Lauf sie
produktiv verwendet). Ein echter Testlauf auf hp-ubuntu (`run_report.py
--top 15`, System-Python, direkt gegen die realen Rohdaten) liess
`folien_generieren()` zweimal in Folge in den 420s-Timeout laufen, obwohl
die Maschine kaum ausgelastet war (Load 0.39) und der kürzere
`titel_generieren()`-Aufruf im selben Lauf in 23s durchlief. Wahrscheinliche
Ursache: die Stichwort-Fragmente-Erweiterung von heute Nachmittag
(`4cd6c64`, rund ein Bullet je Satz plus 2-3 Detail-Fragmente je Bullet)
verlangt deutlich mehr JSON-Ausgabe als der vorherige Prompt und stösst
jetzt öfter an die alte Grenze.

**Auswirkung:** Ein Timeout bei der Folien-Generierung ist bereits durch
try/except abgefangen und fällt auf das ältere Szenen-/Text-Layout zurück
(kein Absturz) - aber genau die heutige Stichwort-Fragmente-Funktion würde
dabei verloren gehen, ohne dass der Cron-Lauf das meldet. Die Erhöhung
kostet im Erfolgsfall nichts (der Aufruf endet, sobald die Antwort da ist)
und senkt das Risiko eines stillen Rückfalls auf das alte Layout beim
morgigen `report.sh`-Lauf (7:35).

**Offen:** Ob 700s in jedem Fall reicht, zeigt sich erst über mehrere
Tage/Berichtsgrössen - falls der Fallback erneut auftritt, weiter erhöhen
oder die Bullet-Dichte im Prompt begrenzen.
