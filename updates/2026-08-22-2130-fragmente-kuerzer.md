---
datum: 2026-08-22
agent: worktree-fragment-fenster-messung
typ: bugfix
commit: 05aa902
---

# Stichwort-Fragmente werden kuerzer gefordert, damit die zweite Zeile ins Fenster passt

**Was:** `DETAIL_MAX_ZEICHEN` von 40 auf **26** gesenkt und die
`"detail"`-Regel im `FOLIEN_PROMPT` auf ein Ziel von **22 Zeichen**
umgeschrieben, mit der Begruendung im Prompt selbst (jedes Fragment braucht
eigene Lesezeit; zwei passen nur nebeneinander, wenn beide kurz sind).
3 neue Tests in `tests/test_detailkarte.py`, darunter einer, der zwei
Fragmente maximaler Laenge gegen ein real gemessenes Fenster rechnet — wer
die Konstante wieder anhebt, laesst ihn fallen und sieht daran, was er der
zweiten Zeile nimmt.

**Warum:** Im Testvideo vom 22.08. fielen 13 von 47 Fragmenten weg
("wegen zu enger Fenster"), produktiv am 21.08. 14 von 63. Die Messung am
echten Tag 21.08. (Instrumentierung von `szenen_bauen()`, nur zum Messen,
nicht gemergt) zeigte ein anderes Bild als die Zahl vermuten laesst:

- **Kein einziger Punkt ging ganz leer aus.** Von 24 Punkten mit geplanten
  Fragmenten zeigten 11 beide, 13 zeigten eines statt zwei. Es geht also
  nie um fehlenden Bildtext, sondern immer nur um die *zweite* Zeile.
- Die Fenster sind nicht eng: Median **4.93s**, Minimum 2.75s, keines
  unter 2.0s.
- Der Bedarf zweier Fragmente lag bei 4.6–6.4s, im Mittel ~5.1s — also
  **systematisch knapp ueber** dem Fenster. In 6 der 13 Faelle fehlten
  weniger als 0.8s, im engsten Fall **0.20s**.

Der naheliegende Hebel — die Lesezeit-Boeden senken — war versperrt:
`DETAIL_CPS` wurde am 19.08.2026 auf Nutzerbefund hin von 12 auf 10
gesenkt, weil die Fragmente zu kurz standen. Bleibt die Fragmentlaenge.
Sie lag im Median bei 26 Zeichen, 44 von 47 ueber 20 — die Grenze von 40
griff also praktisch nie und war an der Kartenbreite bemessen statt an der
Zeit im Bild.

**Auswirkung:** Simuliert an denselben Daten: die Kappung auf 26 allein
bringt 13 → **10** gekuerzte Punkte, das Prompt-Ziel von 22 Zeichen
bringt 13 → **7**. Mehr ist nicht zu holen — 7 der 24 Fenster liegen unter
4.0s und damit unter dem Boden zweier Fragmente (2× `DETAIL_FRAG_MIN`);
die tragen strukturell nie zwei Zeilen, egal wie kurz der Text ist. Die
Lesbarkeit bleibt unberuehrt: kuerzere Zeile bei gleichem Lesetempo, kein
Boden angefasst. `ruff`/`mypy` sauber, **272 Tests gruen** (269 + 3).

**Offen:** Ob das Modell die 22 Zeichen tatsaechlich einhaelt, zeigt erst
der Report am 23.08. 20:35 — haelt es sich nicht daran, kappt das
Sicherheitsnetz bei 26 mitten im Satz, und die Zahl landet naeher bei 10
als bei 7. Erste Gegenprobe im Log: die Zeile "Stichwort-Fragmente: N
gezeigt, M wegen zu enger Fenster weggefallen" gegen die 13 von heute.
