---
datum: 2026-08-19
agent: main
typ: feature
commit: 9fe00f6
---

# Pacing-Befunde der Messung vom 19.08. umgesetzt (Lesezeit, Stillstand, Kurzszenen)

**Was:** Sechs der Befunde aus `research/recherche-video-pacing-2026-08-19.md`
sind in `video_report.py` (und ein Satz im Drehbuch-Prompt in `run_report.py`)
umgesetzt:

- **A1 — Blitz-Overlays.** Neuer Helper `sicht_bis()` in `kapitel_bauen()`:
  er rechnet das *effektiv sichtbare* Fenster eines Overlays als
  zusammenhängende Schnittmenge mit den Story-Strecken. Sonderszenen
  (NEXT UP, Zitat, Kennzahl) bekommen kein `karte_auflegen()` und verdecken
  deshalb, was die Planung als sichtbar annahm. Die Prüfung ersetzt an allen
  drei Stellen (`f`, `steht`, `zeigt`) und beim Detail-Kasten das bisher
  geplante Fenster `zeit[n] → land[n]`. Fällt das effektive Fenster durch,
  greift der vorhandene `zeigt=False`-Pfad: der Punkt erscheint direkt in der
  Liste, statt 0.15 s aufzublitzen.
- **A2 — Standzeit nach Textlänge.** `fokus_boden()` = `0.9 s + Zeichen/15`,
  `detail_boden()` = `Fragmentzeichen/12`; `FOKUS_MIN`/`DETAIL_MIN` bleiben
  nur noch absoluter Boden für sehr kurze Texte.
- **A3 — Agenda-Pausen.** Dritte Pausenstufe: der Trenner in `ton_text()`
  kodiert jetzt vier Umbrüche = Kapitelgrenze, drei = Agenda-Eintrag
  (`GOOGLE_AGENDA_PAUSE = 1200ms`), zwei = Absatz. Beide Vertonungspfade
  (`_ssml_gruppen`, `_studio_stuecke`) lesen sie über den gemeinsamen Helper
  `_pause_fuer_trenner()`; die Vorspann-Schätzung rechnet die Stufen mit.
- **A4 — Opener-Quellzeile.** `OPENER_QUELLE_MIN = 6.0` statt `OPENER_MIN = 4.0`,
  sobald eine Quellzeile gesetzt ist.
- **B1 — Stillstand.** `LUECKE_MAX` 16 → 10 s, plus neue Obergrenze
  `FOKUS_MAX = 12 s`: danach parkt ein Punkt auch ohne Nachfolger in der Karte.
  Im Drehbuch-Prompt (`FOLIEN_PROMPT`) ein Satz, der für zahlenlastige
  Passagen ausdrücklich mehr Stichpunkte fordert.
- **B2 — Kulissen-Flash.** Story-Reststücke unter `STORY_REST_MIN = 2.5 s`
  ziehen kein frisches Motiv mehr, sondern laufen auf dem der Vorszene weiter.

Neue Tests in `tests/test_pacing.py` (Lesezeit-Böden, drei Pausenstufen,
Trenner in `ton_text`, Agenda-`<break>` im SSML); das Fixture in
`tests/test_prosodie.py` ist auf die vierstufige Kapitelgrenze nachgezogen.

**Warum:** Die Pacing-Messung des Laufs vom 19.08.2026 (70 Szenen, 309
Overlay-Stücke deterministisch nachgerechnet, Stichproben frame-verifiziert)
fand am selben Video beides: Text, der ungelesen wegblitzt
(`$29B HYNIX BUYBACK` 0.15 s, ein Detail-Fragment mit 38 cps), und bis zu
20.6 s, in denen sich im Bild nichts bewegt — im Target-Fenster zusammen mit
dem Sprechtempo-Minimum von 80 wpm.

**Auswirkung:** Ab dem nächsten Cron-Lauf auf hp-ubuntu. Erwartete
Nebenwirkungen, bewusst in Kauf genommen:

- Der Ton-Cache-Hash ändert sich durch die neuen Trenner — der nächste Lauf
  vertont einmal komplett neu (ein zusätzlicher TTS-Lauf).
- Der längere Detail-Boden lässt spürbar mehr Detail-Kästen ganz weg (drei
  Fragmente à 25 Zeichen brauchen jetzt ~6.3 s Fenster). Der Stellknopf dafür
  ist `DETAIL_CPS`, nicht die Struktur.
- Der längere Opener verschiebt `det_von` beim ersten Stichpunkt eines
  Kapitels um ~2 s nach hinten; zusammen mit dem Punkt darüber fallen dessen
  Fragmente jetzt öfter weg.
- `LUECKE_MAX = 10` verengt über den Faktor `* 0.6` auch den Abstand der
  Füll-Bullets auf 6 s — es kommen deutlich mehr Fallback-Bullets aus den
  Satz-Cues ins Bild.

Bewusst *nicht* geändert: **B3** (Story-Szenen laufen bis 22.9 s statt
`STORY_MAX = 20`, weil der Opener-Teil in die Szene zählt — unterhalb der
Reizschwelle), das **28-Zeichen-Limit für Agenda-Titel** (die Agenda-Titel
sind identisch mit den Kapitel-Titeln; das Limit würde überall Substanz
kosten, während die Agenda-Pause das Lesezeit-Problem direkt löst) und der
**1.3-s-Flash zwischen Intro und Agenda** (liegt außerhalb von
`kapitel_bauen()`, in der Vorspann-Planung).

**Offen:** Verifikation am nächsten echten Lauf mit
`research/messung_pacing.py <datum>` auf hp-ubuntu — vorher ist sie nicht
aussagekräftig, weil der 19.08-Ton-Cache durch A3 nicht mehr passt. Zu prüfen
sind dort vor allem die drei Stellknöpfe `DETAIL_CPS`, `FOKUS_MAX` und
`LUECKE_MAX`.
