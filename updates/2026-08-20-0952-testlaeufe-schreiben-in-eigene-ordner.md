---
datum: 2026-08-20
agent: worktree-testlauf-isolation
typ: infra
commit: <Hash, sobald bekannt>
---

# Testlaeufe schreiben nur noch in eigene Ordner

**Was:** In `run_report.py` landen alle Ausgaben eines `--trockenlauf` jetzt
abseits der produktiven Pfade:

- Neue Hilfsfunktion `ausgabe_tag(datum, trockenlauf)` liefert `<datum>-test`
  statt `<datum>`. `motiv_waehlen()` und `hintergruende_waehlen()` nutzen sie
  fuer `arbeit/thumbs/<tag>.*` und `arbeit/motive/<tag>/`.
- `markdown_tag_schreiben()` nimmt ein optionales `ziel`; im Trockenlauf
  schreibt `main()` die Markdown-Fassung nach `arbeit/<stamp>-test/extrakte-md/`
  und laesst `markdown_index_aktualisieren()` samt Git aus.
- Der Bericht geht im Trockenlauf nach `arbeit/<stamp>-test/bericht.txt`
  statt nach `berichte/<datum>.txt`; die `.fehler`-Datei folgt ihm.
- Das Laufverzeichnis heisst `arbeit/<stamp>-test`.
- Neu `testumgebung.py`: kopiert `cache/`, `berichte/`, `verwendet.json` und
  `katalog.json` aus dem Haupt-Checkout in einen Worktree. Nur in diese
  Richtung, nie zurueck. Ohne `--kopieren` zeigt es nur an, was es taete.
- Neu `tests/test_testlauf_isolation.py` (9 Tests) auf die Stellen, die sich
  still wieder loesen koennten.

Nebenbei behoben: Das Aufraeumen der Laufverzeichnisse am Ende von `main()`
suchte nach `^\d{4}-\d{2}-\d{2}$`, die Ordner heissen aber `20260820-073501`
— es raeumte seit der Korrektur vom 19.08. gar nichts, auf hp-ubuntu lagen
vier Laufverzeichnisse. Das Muster passt jetzt auf den Stempel, und
`LAEUFE_BEHALTEN` zaehlt Test- und produktive Laeufe getrennt, sonst
verdraengen fuenf Testlaeufe alle produktiven.

**Warum:** Der Guard vom 19.08. (`2bb3bf6`) deckt den *Delta-Zustand* ab, nicht
die *Ausgaben*. Ein Testlauf schrieb weiterhin in dieselben Ordner wie die
Produktion, und dort liegt, was der naechste Lauf wieder liest:

- `berichte/<datum>.txt` geht am Folgetag als "gestern" in den Themenverlauf
  der Synthese ein (`VERLAUF_TAGE`) — ein Testbericht dort verfaelscht den
  naechsten produktiven Bericht.
- `extrakte/<datum>/` ist die oeffentliche Fassung zum hochgeladenen Video und
  der einzige getrackte Pfad, den ein Testlauf anfasst; der dirty Working Tree
  gefaehrdet nachts `git pull --ff-only` in `report.sh`.
- `arbeit/thumbs/<datum>.*` und `arbeit/motive/<datum>/` liest `video_report.py`
  erst um 08:10, der Bericht ist um 07:50 fertig — ein Testlauf dazwischen
  loescht die Kulisse des Tages.

**Auswirkung:** Ein Trockenlauf ist ab jetzt fuer den produktiven Zustand
folgenlos, bleibt aber vollstaendig inspizierbar — alles liegt beisammen unter
`arbeit/<stamp>-test/`. Der produktive Pfad ist unveraendert: alle neuen
Parameter defaulten auf `False` bzw. `None`. Bewusst *nicht* geaendert:
`arbeit/tts_verbrauch.json` und die Clip-Freigaben in `arbeit/clips/katalog.json`
schreiben weiter in die Produktion — das Google-Kontingent ist real verbraucht,
egal unter welchem Flag, und Sichtpruefungs-Ergebnisse sind bewusst kumulativ.
Aus demselben Grund gibt es keinen pauschalen Sandkasten-Modus: die richtige
Einheit ist die einzelne Schreibstelle mit ihrer Bedeutung, nicht der Ordner.
`klip_bereinigen()` bleibt ebenfalls unangetastet — sie laeuft nur aus
`video.sh`, nicht aus `video_report.py`, und kennt `trockenlauf` bereits.

**Offen:** Der Guard von `2bb3bf6` ist im Feld noch nicht ausgeuebt worden —
am 20.08. lief kein Testlauf zwischen den produktiven Laeufen. Beim naechsten
echten Testlauf die mtimes von `cache/status.json`,
`arbeit/motive/verwendet.json` und `arbeit/clips/katalog.json` vorher und
nachher vergleichen; bleiben sie stehen, ist er bestaetigt.
