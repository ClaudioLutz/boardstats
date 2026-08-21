---
datum: 2026-08-22
agent: main
typ: bugfix
commit: <Hash, sobald bekannt>
---

# Shorts: letzte Story endet vor dem neuen Schluss-Beat

**Was:** `shorts.ENDE_PHRASEN` um den Anfang des Zitat-Rahmens
(`vr.PRAES_ZITAT` vor der Platzhalter-Klammer) und um die **vor** dem 21.08.2026
gültigen Formulierungen von `PRAES_ZAHLEN`/`PRAES_OUTRO` erweitert. Zwei Tests in
`tests/test_shorts.py` sichern beides ab.

**Warum:** Folgefehler der Stossrichtung C. Der neue Schluss-Beat (Board-Zitat +
Cliffhanger-Frage) steht **zwischen** der letzten Story und dem Outro.
`stories_finden()` beendet die letzte Story an der frühesten Fundstelle aus
`ENDE_PHRASEN` — und die kannte nur Outro und Zahlenblock-Kopf. Das letzte Short
hätte deshalb Zitat und Frage als fremdes Anhängsel getragen.

Gegenprobe mit der alten Liste, bevor der Fix griff:

```
OHNE Fix, letzte Story endet mit:
  ...the board: "we are all gonna make it" Does alpha hold ten?
```

Der Fehler wäre beim `video.sh`-Lauf heute um 21:15 produktiv aufgetreten — die
16 bestehenden Shorts-Tests decken ihn nicht ab, weil sie den neuen Berichtsaufbau
nicht kennen.

Zweiter Teil: der Kommentar an `ENDE_PHRASEN` verlangt ausdrücklich „aktuelle wie
frühere Formulierung — die Tonspur des Tages kann von einem älteren Codestand
stammen". Da A/C beide Konstanten geändert haben, standen die alten Fassungen
nirgends mehr; ein Wiederanlauf gegen eine ältere Tonspur hätte die letzte Story
ins Outro laufen lassen.

**Auswirkung:** Das letzte Short des Tages endet wieder am Ende seiner Story.
Gegen ältere Tonspuren bleibt `shorts.py` robust.

**Nicht betroffen und geprüft:** Die Story-Blöcke kommen über
`vr.drehbuch_bauen()` → `abschnitte_erzeugen()`, wo „Still true from yesterday"
bereits gefiltert ist — für dieses Kapitel entsteht also von vornherein kein Short.

**Offen:** —
