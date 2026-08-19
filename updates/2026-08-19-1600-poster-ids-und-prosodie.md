---
datum: 2026-08-19
agent: main
typ: feature
commit: <folgt>
---

# Poster-ID-Verteilung im Bündelkopf und SSML-Prosodie im Studio-Pfad

**Was:** Zwei getrennte Änderungen.

*Beteiligung je Thread* — `bundle_biz.py`: neue Funktion `id_verteilung()`
liefert die Zahl der Poster-IDs, die Posts je ID und den Anteil der lautesten
ID. Alle drei stehen jetzt im Bündelkopf und in den Manifest-Metadaten
(`beteiligte`, `posts_je_id`, `lauteste_id_anteil`), im `unveraendert`-Zweig
ebenso. `run_report.py` gibt sie im Thread-Kopf der Synthese-Eingabe weiter.
`extract_prompt.txt` (RELIABILITY) und Synthese-Regel 11 erklären, wie sie zu
lesen sind.

*Prosodie* — `video_report.py`: neuer Datentyp `Stueck` (Klartext, Stille
davor, optionale SSML-Fassung, Token-Gewichte). `_studio_stuecke()` setzt drei
Eingriffe: Überschrift **und** erster Satz eines Kapitels laufen auf
`rate="92%"`, harte Zahlen auf `rate="88%"`, und vor dem Schlusssatz eines
Absatzes ab drei Sätzen steht eine längere Stille (0.45 s statt 0.20 s).
`_worte_verteilen()` nimmt Streckfaktoren entgegen, damit die Untertitel den
verlangsamten Tokens folgen. Neu `tests/test_prosodie.py` (15 Tests).

**Warum:** `unique_ips` liefert die 4chan-API nicht — am 19.08.2026 gegen den
Snapshot **und** gegen die Live-API geprüft, das Feld fehlt am OP komplett.
Die Poster-IDs tragen dieselbe Information und liegen bereits vor. Die beiden
Verhältniszahlen sind auch dann belastbar, wenn die absolute Zahl nur eine
Obergrenze ist: `/BBBYQ/` hat 242 Posts aus 37 IDs (6.5 je ID, ein kleiner
lauter Kreis), «Bitcoin is 17 years old» 107 Posts aus 83 IDs (1.3, ein
breites Gespräch). Bei «8 years day trading» stammen 44 % aller Posts von
einer einzigen ID.

Für die Prosodie ist am 19.08.2026 gegen die Live-API gemessen, was
en-US-Studio-Q annimmt:

| Tag | Ergebnis |
|---|---|
| `<prosody rate>` | ok — 4.47 s → 4.97 s bei `85%` |
| `<prosody volume>` | ok |
| `<break>` | ok — 4.47 s → 4.88 s bei 400 ms |
| `<say-as>`, `<s>` | ok |
| `<prosody pitch>` | HTTP 400 — «do not currently support `pitch` attributes for Studio voices» |
| `<emphasis>` | HTTP 400 — «not currently supported by Studio voices» |

Betonung gibt es also nicht; der Ersatz ist Verlangsamung. Pausen kommen
weiterhin als PCM-Stille zwischen den Stücken statt als `<break>`, weil
Stille zwischen zwei Aufrufen sample-exakt ist und ein `<break>` innerhalb
eines Satzes die interpolierten Wortzeiten der Untertitel verschöbe.

**Auswirkung:** Am Bericht vom 19.08. laufen 16 Stücke als Kapiteleröffnung
langsamer und 23 Sätze mit hervorgehobenen Zahlen; 7 Absätze bekommen die
Pointen-Pause. Die Abrechnung steigt von 7'866 auf 10'581 Zeichen je Bericht
(+34.5 %), das sind rund 317'000 von 1 Mio Studio-Zeichen im Monat. SSML geht
nur an die Sätze, die es brauchen — alle anderen weiterhin als `text`, sonst
wäre der Aufschlag ein Vielfaches.

Zwei Defekte fielen beim Trockenlauf auf und sind behoben, bevor etwas
gerendert wurde: die Grössenordnung wurde zerschnitten («$303 m» plus
«illion», weil die Alternative `m` vor `million` griff), und `2%` fiel durch
das Muster, weil hinter dem Prozentzeichen nie eine `\b`-Grenze steht.

Bewusst nicht geändert: die Satzgrenzen bleiben sample-exakt, weil jeder Satz
weiterhin ein eigener Aufruf ist. Der Klartext, an dem Zeitachse und
Untertitel hängen, bleibt vom Markup unberührt.

**Offen:** Ob 92 % und 88 % die richtigen Werte sind, lässt sich erst am
fertigen Video hören — die Zahlen sind eine Starthypothese.
