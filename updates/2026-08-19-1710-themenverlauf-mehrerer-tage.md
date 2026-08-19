---
datum: 2026-08-19
agent: main
typ: feature
commit: <folgt>
---

# Wiederholungsprüfung reicht weiter zurück als einen Tag

**Was:** `run_report.py`:

- Neue Funktion `themen_verlauf(datum, tage=4)` baut aus den veröffentlichten
  `bericht.md` der Tage **vor** dem gestrigen einen kompakten Block: je
  `##`-Abschnitt eine Zeile aus Überschrift und Anfang des ersten
  inhaltlichen Absatzes (`_themen_zeilen()`, gekappt auf 170 Zeichen).
- Der Block geht in `stufe3()` mit in die Synthese-Eingabe, hinter
  YESTERDAY'S REPORT.
- Neue Prompt-Regel 8c: jedes Thema, das voll ausgeschrieben werden soll,
  wird gegen diese Liste gehalten. Steht es dort, gehört in den Bericht, was
  **seither** passiert ist — und wenn nichts passiert ist, ist es kein Thema
  für heute. Ausdrücklich ausgenommen sind die Generals als Institutionen
  (Regel 7): dass /smg/ wieder existiert, ist keine Wiederholung.
- 9 neue Tests in `tests/test_auswahl.py`.

**Warum:** Regel 8b vergleicht bisher nur gegen den einen Vortag
(`voriger_bericht()` liefert genau einen). Ein Thema, das am 15. und am 17.
lief und am 18. fehlte, sieht am 19. wie neu aus — der Zuschauer hört es
trotzdem zum dritten Mal.

Der Auslöser war die Frage, ob unveränderte Threads ausgelassen werden
sollen. Die Messung sprach dagegen: an acht von elf Cron-Läufen gibt es null
Threads im Modus `unveraendert`, an den übrigen zwei — der Filter hätte am
typischen Tag nichts bewirkt, und wenn, dann hätte er die grössten Threads
getroffen (/XMR/ mit 298 Posts, /smg/ mit 410). Die tatsächliche Wiederholung
kommt aus den `delta`-Generals, die täglich neue Posts bekommen und dieselbe
Geschichte erzählen. Dort greift diese Änderung.

**Auswirkung:** Gemessen an den echten Berichten ergibt der Block 6'879
Zeichen für 4 Berichte und 34 Abschnitte — gegen rund 180 KB Extrakte in
derselben Eingabe. Der gestrige Bericht bleibt bewusst draussen, er liegt
ohnehin im Volltext vor. Ohne Archiv (erster Lauf, `--kein-github`) bleibt
der Block leer und die Synthese arbeitet wie bisher.

Bewusst **nicht** umgesetzt: ein Filter auf `modus == "unveraendert"`, aus
den oben gemessenen Gründen.

**Offen:** Ob vier Tage die richtige Tiefe sind, zeigt sich erst an den
Berichten der nächsten Woche.
