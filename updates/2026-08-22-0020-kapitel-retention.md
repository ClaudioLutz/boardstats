---
datum: 2026-08-22
agent: main (Branch retention-a-bis-d)
typ: feature
commit: <Hash, sobald bekannt>
---

# Stossrichtung D: Abbruchkurve gegen Kapitelmarken, „killed chapters" im Prompt

**Was:**

- `analytics_bericht.py`: neue Funktion `kapitel_aus_beschreibung()` liest die
  Kapitelmarken (`00:48 Silver hits 70`) aus der YouTube-Videobeschreibung
  zurück — dieselbe Liste, die `video_report.kapitel_bauen()` beim Upload
  erzeugt. `_video_meta()` nimmt sie mit (der `snippet`-Part lieferte die
  Beschreibung ohnehin schon mit, sie wurde nur nicht gespeichert),
  `kurven_erheben()` schreibt sie als Feld `kapitel` in die Messung.
- `run_report.py`: `_kapitel_verluste()` legt die Abbruchkurve gegen die Marken
  und rechnet den Bindungsverlust je Kapitel **pro Minute** (nicht als Summe —
  sonst stünde das längste Kapitel allein wegen seiner Länge oben). Das erste
  Kapitel bleibt draussen: dort fällt jede Kurve, das ist der Einstiegsverlust.
- `_kapitel_zeilen()` hängt die vier verlustreichsten Kapitel als
  „CHAPTERS THAT LOST THE MOST AUDIENCE" an den Retention-Befund — und damit
  automatisch an **beide** Prompts (Synthese und Drehbuch), die den Befund schon
  bekommen. Neue Konstanten `KAPITEL_NENNEN = 4`, `KAPITEL_SCHWELLE = 0.02`.
- `_bindung_bei()` interpoliert die Kurve linear zwischen den Stützpunkten.

**Warum:** Brainstorming-Session vom 21.08.2026, Stossrichtung D. Die
Gesamtkurve sagt, *wann* Zuschauer gehen, aber nicht *wobei*. Erst gegen die
Kapitelmarken gelegt wird daraus eine Aussage über Inhalte, die sich in den
Drehbuch-Prompt zurückspeisen lässt.

**Auswirkung:** Ab der ersten Analytics-Messung nach diesem Deploy (Cron 23:30)
tragen die Kurven Kapitelmarken; ab dem Bericht danach nennt der Retention-Block
konkrete Kapitel, die Zuschauer gekostet haben. Messungen von **vor** diesem
Deploy kennen das Feld nicht — der Block bleibt dann exakt wie bisher (durch
`test_block_ohne_kapitel_unveraendert` abgesichert).

**Offen — bewusst nicht geliefert:** Der vierte Punkt von D, „Titel-Hook getrennt
von Retention messen — A/B-Titel über zwei Shorts-Varianten desselben Tages", ist
mit den verfügbaren Schnittstellen **nicht automatisierbar**. Die Messgrösse dafür
wäre die Klickrate, und Impressionen/CTR gibt die YouTube-API nicht heraus (steht
so seit je im Modul-Docstring von `analytics_bericht.py` — nur YouTube Studio zeigt
sie in der Oberfläche). Ein A/B ohne CTR bliebe ein Views-Vergleich zweier Shorts,
die sich gegenseitig kannibalisieren; ob dafür täglich ein zusätzliches Short
hochgeladen werden soll, ist ausserdem eine Kanal-Entscheidung, keine technische.
Der Rest von D ist vollständig umgesetzt.
