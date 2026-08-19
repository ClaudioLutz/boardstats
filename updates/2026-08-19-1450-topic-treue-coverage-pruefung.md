---
datum: 2026-08-19
agent: main
typ: feature
commit: <folgt>
---

# Topic-Treue im Synthese-Prompt und Gegenprobe des COVERAGE-Blocks

**Was:** Drei Änderungen in `run_report.py`:

- Neue Prompt-Regel 14 (TOPIC FIDELITY): Wird ein Thread verwendet, ist die
  erzählte Geschichte die, die sein Extrakt unter `Topic` nennt. Trägt eine
  Randbemerkung des Threads ein anderes Thema, gilt sein eigenes Topic als
  nicht abgedeckt und muss im COVERAGE-Block als `partly - <was wegfiel>`
  vermerkt werden.
- Das COVERAGE-Format verlangt jetzt bei `used` das Topic in maximal acht
  Wörtern, kennt zusätzlich den Zustand `partly` und schreibt die
  Thread-Nummer als blosse Zahl an den Zeilenanfang.
- Neue Funktion `abdeckung_pruefen()` plus Auswertung in `main()`: Die im
  COVERAGE-Block genannten Thread-Nummern werden gegen die Nummern der
  tatsächlichen Synthese-Eingabe gehalten. Fehlende und unbekannte Nummern
  landen als `log.warning`. Dafür gibt `stufe3()` neu ein Tupel
  `(Ausgabe, Eingabe-Threads)` zurück.

**Warum:** Regel 13 verlangt seit dem 06.08. jede Thread-Nummer genau einmal
im COVERAGE-Block, geprüft wurde das nie — nur die `omitted`-Zeilen wurden
gezählt. Ein still verschwundener Thread sah im Log exakt aus wie ein
vollständig abgedeckter Lauf. Dazu die zweite Lücke: Ein Thread konnte als
`used` gelten, obwohl der Bericht nur eine Nebenbemerkung daraus aufgriff und
das eigentliche Thema fallen liess. Für das Video heisst das, dass beim
stärksten Thread des Tages die falsche Geschichte erzählt wird — ein Fehler
unabhängig von der Zuschauerzahl.

**Auswirkung:** Der Bericht selbst ändert sich inhaltlich nur dort, wo die
Synthese bisher am Topic vorbeischrieb. Der COVERAGE-Block wird länger (Topic
je verwendetem Thread), bleibt aber wie bisher vor der Veröffentlichung
abgetrennt und landet in `arbeit/abdeckung.txt`. Neu im Log: die Zahl der nur
teilweise abgedeckten Threads sowie Warnungen bei fehlenden Nummern.

Bewusst **nicht** gegen das Manifest verglichen, sondern gegen die
Extrakt-Liste: Das Manifest kann Bündel enthalten, zu denen gar kein Extrakt
entstand — die dürfen im COVERAGE-Block fehlen, ohne dass es ein Fehler ist.

**Offen:** Die Warnung ist vorerst nur Diagnose; ob aus wiederholt fehlenden
Nummern ein harter Fehler werden soll, entscheidet sich nach ein paar Läufen.
