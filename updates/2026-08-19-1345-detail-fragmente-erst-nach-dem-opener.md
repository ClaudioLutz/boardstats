---
datum: 2026-08-19
agent: worktree-detail-opener-fenster
typ: bugfix
commit: <Hash, sobald bekannt>
---

# Stichwort-Fragmente setzen nach dem Opener ein, statt zu entfallen

Korrigiert [2026-08-19-1330-stichwort-fragmente-unter-dem-bulletpoint.md](2026-08-19-1330-stichwort-fragmente-unter-dem-bulletpoint.md).

**Was:** In `video_report.py` blendet der Detail-Kasten während des
Kapitel-Openers nicht mehr komplett aus, sondern setzt erst danach ein:
`det_von = max(t_n, opener_bis)`, und `zeigt_detail` misst die Standzeit ab
`det_von` statt ab `t_n`. Der `KartenStand` im `detail_plan` beginnt
entsprechend bei `det_von`.

**Warum:** Die erste Fassung strich die Fragmente, sobald ein Punkt vor
`opener_bis` begann. Nachgerechnet ist das kein Randfall, sondern die Regel:
`OPENER_MIN = 4.0`, der Opener steht also bis `kopf_start + 4.0`, während der
erste Stichpunkt eines Kapitels schon bei rund `rumpf_start + 0.6` erscheint.
Damit hätte **jeder** Abschnitt die Fragmente seines ersten — oft
substanzreichsten — Bullets verloren, ohne dass das im fertigen Video als
Fehler erkennbar gewesen wäre.

**Auswirkung:**

- Der erste Stichpunkt eines Kapitels behält seine Fragmente, sofern nach dem
  Opener noch `DETAIL_MIN` (2.6 s) Standzeit bleibt.
- Die Fokus-Karte steht dabei von Anfang an auf ihrer Stapel-Position, nicht
  erst ab `opener_bis` — sie endet oberhalb von y=400 und berührt die
  Opener-Bande (ab y=426) ohnehin nie. Nur der Detail-Kasten reicht bis etwa
  y=465, und genau der wartet jetzt.
- Kein Wechsel der Geometrie mitten im Punkt: `fokus_punkt()` bekommt
  `details[n]` immer dann, wenn der Detail-Kasten später erscheint, die Karte
  springt also nicht.

**Zusätzlich geprüft (beides vorher offen):**

- `folien_generieren()` mit dem neuen Prompt auf `extrakte/2026-08-19/bericht.md`:
  JSON kommt vollständig an (9'188 Zeichen), kein Timeout, kein Output-Limit.
  9 Abschnitte, 46 Stichworte, 29 davon mit Fragmenten (63 %), 48 Fragmente
  gesamt, längstes 35 Zeichen. Verteilung: 17× keins, 14× eins, 11× zwei,
  4× drei — das Modell bleibt unter den erbetenen „2 oder 3", liefert dafür
  aber inhaltlich Tragendes (Gegenargument, Attribution, Zahl) statt Füllung.
- Echter ffmpeg-Render einer Szenenfolge mit Detail-Overlay über eine
  Szenennaht: Overlay kommt durch den Filtergraphen und sitzt im fertigen
  Frame an der berechneten Stelle. (Der Testlauf brach erst im Ton-Mux ab —
  `loudnorm` an synthetischer Stille, ein Fehler des Prüfskripts, nicht des
  Renderpfads.)

**Offen:** Ob `DETAIL_MAX = 3` auf unruhigem Board-Motiv ruhig genug wirkt,
zeigt erst der Cron-Lauf gegen echte Screenshot-Texturen — die Sichtprüfung
lief gegen eine Ersatzfläche, weil der Bild-Cache lokal leer war. Und ob die
Fragment-Ausbeute (63 % der Bullets) reicht oder der Prompt härter fordern
muss, entscheidet sich am ersten echten Video.
