---
datum: 2026-08-19
agent: worktree-detail-einblendzeit
typ: feature
commit: b28a298 (Nachtrag 0d1a1cd: Blende an Szenennaehten)
---

# Stichwort-Fragmente erscheinen einzeln, wenn ihr Inhalt gesprochen wird

**Was:** Die Fragmente unter dem Bulletpoint stehen nicht mehr von Anfang an
alle da. Jedes erscheint an der Stelle, an der sein Inhalt in der Tonspur
fällt; der Kasten wächst dabei Zeile um Zeile nach unten.

- `video_report.py`: `_detail_fundort()` sucht die Sprechstelle eines
  Fragments, `_detail_zeiten()` macht daraus die Einblendzeiten (Reihenfolge
  des Kastens, Lesezeit vor dem Abflug). `KartenStand` trägt jetzt `blende`
  und `haelt`, damit sich die Kastenstufen hart ablösen können.
- `szenen.py`: `detail_teile()` liefert den Kasten in Aufbaustufen plus die
  Zeilen einzeln; `detail_karte()` setzt daraus das Endbild zusammen.
- `detail_frag_boden()` neu: Lesezeit-Boden je Fragment (1.4 s), weil
  `DETAIL_MIN` dem ganzen Kasten galt.
- `tests/test_detail_einblendzeit.py`: 15 Tests.

**Warum:** Nutzerwunsch 19.08.2026 — "die stichworte sollen zur richtigen
zeit eingeblendet werden, nicht von anfang an schon". Bisher bekam jedes
Fragment die Startzeit seines Bulletpoints und nahm damit vorweg, was erst
noch gesprochen wurde.

Die Fundstelle ist **kein** Folgenvergleich wie bei den Ankern
(`_anker_spanne`): Fragmente sind verdichtete Stichworte, "CAFC order
8-17-2026" steht im Text als "a CAFC order dated 8-17-2026". Gesucht wird
deshalb die Stelle, an der die meisten Fragment-Wörter dicht beieinander
fallen; ein einzelnes Wort trägt nur, wenn es im Fenster selten ist.

**Gemessen** (echtes Drehbuch aus einem Sonnet-Lauf über `bericht.md`
2026-08-19, dazu die echten Wort-Zeitstempel derselben Vertonung —
`research/messung_detail_zeit.py`):

- 47 Punkte mit Fragmenten, 72 Fragmente. Fundstelle gefunden: 65 (90 %).
- Nach der Verteilung: **62 von 70 gestaffelt (89 %)**, Median-Versatz zum
  Bulletpoint 2.5 s. Die 8 verbleibenden fallen echt mit dem Satzbeginn
  zusammen.
- Stichprobe gegen den Sprechkontext: die Fundstellen sitzen im richtigen
  Satzteil ("$14 in, now $12.50" → "I have 12.50", "claim is unsourced" →
  "Unsourced.").
- 2 Punkte verlieren ihre Fragmente, weil das Fenster für die
  aufaddierten Lesezeiten zu eng ist.

**Zwei Entscheidungen gegen den naheliegenden Weg**, beide aus der
Render-Probe (`research/probe_einblendzeit.py`, echtes Board-Motiv):

1. **Der Kasten steht nicht von Anfang an in Endhöhe.** Das wäre die ruhige
   Variante gewesen (nichts wandert), sah im Frame aber aus wie ein
   Ladefehler: zwei Drittel leere schwarze Fläche unter der einen Zeile.
   Stattdessen wächst er in Stufen. Die Stufen lösen sich **hart** ab — zwei
   Kästen ineinandergeblendet ergäben zweimal `KARTE_ALPHA`, einen sichtbaren
   Dunkel-Puls. Nachgemessen über die Naht: die Helligkeit im Kastengrund
   bleibt bei 34.3–34.5, es gibt keinen Puls. Die Textzeile blendet weich auf.
2. **Erst alle Kastenstufen, dann alle Zeilen.** Die erste Fassung hängte je
   Fragment Kasten und Zeile hintereinander in den Plan — die spätere, höhere
   Kastenstufe legte sich damit über die schon eingetragenen Zeilen, die im
   Bild nur noch schemenhaft standen.

Ein dritter, kleinerer Punkt: die Blende gilt nur im Stueck mit dem echten
Beginn — sonst blendet dieselbe Zeile an jeder Szenennaht neu auf. Das
Overlay-Muster ist dasselbe wie bisher, betrifft jetzt aber mehr Overlays.

**Preis:** Pro Stichpunkt entstehen bis zu sechs Overlays statt einem. Nach
oben wandert nichts: die Stapelgeometrie rechnet weiterhin mit der vollen
Fragmentliste, sonst spränge der Fokus-Punkt darüber, der als eigenes
Overlay festliegt und später seinen Flug fährt.

**Geprüft:** ruff, mypy, 126 Tests. Render-Probe über ein echtes Board-Motiv
mit Frames bei 1.5 s (nur Bulletpoint), 5.0 s (erste Zeile), 5.6 s (zweite)
und 11.0 s (alle drei, Kasten eng um den Text).
