---
datum: 2026-08-22
agent: main (Branch retention-a-bis-d)
typ: bugfix
commit: <Hash, sobald bekannt>
---

# Vorspann: Kürzen hört am Boden auf, statt den Serien-Satz auszulösen

**Was:** In `video_report.praesentations_bloecke()` bricht die Deckel-Schleife ab,
wenn das Entfernen des nächsten Zahlensatzes den Vorspann unter `INTRO_BODEN`
drücken würde. Der Zahlensatz bleibt dann gesprochen, auch wenn der Vorspann
dadurch etwas über `INTRO_DECKEL` liegt.

**Warum:** Im Testlauf vom 22.08.2026 (Kettentest gegen den Stand `a5d1db3`) trat
die Kombination real auf, und sie ist in beiden Zielgrössen schlechter:

```
Vorspann geschaetzt ueber 15s - Zahlensatz '...Ryan Co' nur noch im Bild, jetzt 11.3s
Vorspann geschaetzt 11.3s - Serien-Satz bleibt drin, damit Kapitel 1 nicht unter 10s rutscht
→ Vorspann bis 16.4s
```

Erst fiel ein Zahlensatz weg, dann hängte der Boden den Serien-Satz an („This is the
4chan business board report for …") — und der ist **länger** als der gerade entfernte
Zahlensatz. Ergebnis: 16.4 s statt 15.9 s, und statt einer harten Zahl stand die
Seriennennung im Opener, also genau das, was Stossrichtung A dort entfernen wollte.

Mit den echten Tagesdaten nachgerechnet: beide Zahlensätze bleiben, **15.9 s** statt
16.4 s, kein Serien-Satz.

**Auswirkung:** Der Vorspann kann jetzt in seltenen Fällen leicht über 15 s liegen —
das ist der bewusste Preis dafür, dass der Boden (YouTube-Kapitelregel) Vorrang behält
und dabei kein Inhalt gegen die Seriennennung getauscht wird. Der Testlauf zeigt: die
Überschreitung ist kleiner als der Schaden, den sie verhindert.

**Hinweis zum Testvideo:** Das lokal gebaute `video/2026-08-22/video_en.mp4` entstand
noch **vor** dieser Korrektur, hat also 16.4 s Vorspann mit Serien-Satz. Die Wirkung
der Korrektur ist am Blockaufbau mit denselben Tagesdaten nachgerechnet und in
`tests/test_vorspann.py::test_nie_kuerzen_und_dann_serien_satz` als Invariante über
die ganze Bandbreite der Satzlängen abgesichert.

**Offen:** —
