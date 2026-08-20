---
datum: 2026-08-20
agent: worktree-agent-a44a02761f4528548
typ: feature
commit: 6509099e0ecee9fd80c49a26f81602a6bd3274cb
---

# TL;DR-Zahlenblock direkt nach dem Cold Open, Agenda-Teaser entfallen

**Was:** Umbau der ersten 90 Sekunden in `video_report.py`:

- `praesentations_bloecke()`: neue Blockfolge intro → zahl_kopf + 4×zahl
  (TL;DR) → Kapitel 1..n → outro. Die «Coming up»-Agenda-Strecke entfällt,
  die Zahlen werden am Ende NICHT wiederholt. Fehlen die `zahlen` in
  `folien.json` (oder Liste leer), läuft unverändert die alte
  Agenda-Struktur als Fallback; der `PRAES_INTRO`-Fallback bei fehlendem
  Hook bleibt intakt. `PRAES_ZAHLEN` heisst neu "The day in four numbers."
  (vorher End-Überleitung "Before we wrap up…").
- Neuer Helfer `zahlen_vorne()`: erkennt an der Blockfolge, ob der
  Zahlenblock vor dem ersten Kapitel steht — die Renderpfade bleiben für
  beide Ordnungen korrekt.
- `szenen_bauen()` (v7): Hook-Karte des Cold Open steht bis zum Start des
  Zahlen-Kopfs; die Zahl-Tafel-Szenen (Count-ups) werden als eigene
  Funktion `zahlen_szenen()` an der von der Blockfolge diktierten Stelle
  gebaut (vorne mit Karte "The day in four numbers" / Label "TL;DR", bei
  alter Ordnung wie bisher "Numbers of the day" vor dem Outro). Das
  Kapitel-Ende (`schluss`) filtert per Index, damit der vorgezogene
  zahl_kopf nicht als Ende des letzten Kapitels durchgeht — derselbe Fix
  in `folien_konkat()` (v6), wo die Zahlen-Folien jetzt ebenfalls in
  chronologischer Ereignis-Reihenfolge (nach dem Intro) gerendert werden.
- `kapitel_bauen()`: die 00:00-Marke heisst "TL;DR", wenn der Zahlenblock
  vorne gesprochen wird (sie deckt Cold Open + Zahlen ab, keine eigene
  Marke für den Zahlenblock); sonst weiter "Intro". Rettung von Kapitel 1
  unter 10 s unverändert.
- `INTRO_BODEN` bleibt: auf dem TL;DR-Pfad ist er faktisch tot (allein die
  vier Zahlen-Sätze sprechen ~30 s), auf dem Agenda-Fallback mit knappem
  Hook weiterhin tragend. Die Vorspann-Schätzung rechnet jetzt mit den
  tatsächlich emittierten Rahmensätzen (Absatzpause je Zahl statt
  Agenda-Pause).
- README: Absatz zu Rahmen-Sätzen/Eröffnung und die «Coming up»-Erwähnung
  angepasst.

**Warum:** Prio 1 aus dem Brainstorming «Zuschauerzahl erhöhen» (20.08.):
YouTube-Analytics zeigen eine Abbruchwand bei 1:08 (50 % weg bei 11 min).
Die vier Kennzahlen sind der dichteste Inhalt des Tages und gehören in
dieses Fenster; die Agenda-Teaser waren der schwächste Teil davor.

**Auswirkung:** Ab dem Cron-Lauf heute 21:15 CEST beginnt das Video mit
Cold Open (Schlagwort-Tafel + Hook-Karte, unverändert) und spricht ab
~10 s die vier Tageszahlen als Kapitel «TL;DR»; Kapitel 1 startet um ~40 s
(gemessen am 20.08.: "Vorspann bis 40.0s"). Die Bett-Anhebung
(`kapitel_eins_start`) deckt damit Intro+TL;DR ab — gleiche Semantik
(alles vor Kapitel 1), nur länger (~40 s statt ~30 s). Der TL;DR-Block
zieht 5 Pool-Bilder vor den Kapiteln statt danach — bewusst akzeptiert,
die Zahl-Tafeln decken das Bild ohnehin fast ganz ab. Bewusst NICHT
geändert: v5-Text-Layout (Rahmen-Sätze erscheinen dort weiter als
Absätze), Agenda-Fallback ohne Zahlen, Cold Open, Outro.

Tests: Trockentest Blockfolge mit echten Daten vom 20.08. (intro,
zahl_kopf, 4×zahl, erste Überschrift an Position 6, keine agenda-Blöcke,
outro ohne Zahlen), `kapitel_bauen` mit künstlichen Wortzeiten (00:00
TL;DR, alle 8 Kapitel, ≥10-s-Regel, Grenzfall frühes Kapitel 1 → Marke
auf 10 s), Fallback zahlen leer/fehlend → alte Agenda-Folge. pytest 155
passed, ruff und mypy grün. Sichttest `--trockenlauf --vorschau 60`:
Frames bei 1 s (Zahltafel), 12 s (+200%-Count-up), 32 s (vierte Zahl),
45 s (Kapitel 1) geprüft.

**Offen:** Erfolgskontrolle über `analytics_bericht.py` in den nächsten
Tagen — verschiebt sich die Abbruchwand hinter 1:08?
