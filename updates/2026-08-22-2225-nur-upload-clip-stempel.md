---
datum: 2026-08-22
agent: worktree-nur-upload-clip-stempel
typ: bugfix
commit: <wird beim Commit ergaenzt>
---

# `--nur-upload` ordnet die Clips nicht mehr neu zu, sondern uebernimmt die Auswahl des Bau-Laufs

**Was:** `_klip_zuordnung()` kennt jetzt `nur_upload`. In diesem Modus geht
kein Modellaufruf mehr raus; stattdessen liest `_klip_merk_stempeln()` die
Auswahl, die der Bau-Lauf in `arbeit/clips/zuordnung-<datum>.json`
hinterlegt hat (`_klip_merk_schreiben()`, wird bei **jedem** Lauf
geschrieben, auch im Trockenlauf), und stempelt genau diese Clips im
Katalog als verwendet. 2 neue Tests, gesamt 289 gruen.

**Warum:** Ein Fehler im gestern eingebauten `--nur-upload` (`124b032`),
beim ersten echten Einsatz sofort aufgetreten. Das Flag laesst den Render
aus — der Szenenbau lief aber weiter und rief dabei `_klip_zuordnung()`
erneut auf. Das Modell ist nicht deterministisch, also kam eine **andere**
Auswahl heraus als die, mit der das hochgeladene Bild gerendert worden war:

| | |
|---|---|
| Clips im gerenderten Video (Rebuild 22:02) | **10** |
| Clips, die der Upload-Lauf zuordnete und stempelte | **6** |

Alle 6 waren zufaellig auch im Video, falsch gesperrt wurde also nichts —
aber **vier im Video sichtbare Clips blieben ungestempelt** und haetten am
Folgetag erneut gezogen werden koennen. Genau die Wiederholung, gegen die
`naechstes_motiv()` schon eine eigene Sperre traegt (Nutzerbefund
18.08.2026: "Clip 10x am Berichtsende wiederholt, 0 Relevanz und 0
Unterhaltungswert"). Dazu ein unnoetiger Sonnet-Aufruf pro Upload.

Der Katalog auf hp-ubuntu wurde von Hand nachgezogen (4 Stempel ergaenzt,
Sicherung unter `arbeit/clips/katalog.json.bak-2026-08-22`); Stand jetzt 10
Stempel fuer den 22.08., passend zum Video `0V9DGLtRkdk`.

**Auswirkung:** Der Upload-Lauf stempelt, was tatsaechlich im Bild laeuft,
und spart den Modellaufruf. Fehlt die Merkdatei (etwa weil das Video von
einem aelteren Stand stammt), laeuft der Upload trotzdem durch und sagt im
Log, dass die Sperre fuer diese Clips offen bleibt — lieber ein offener
Stempel als ein abgebrochener Upload. `ruff`/`mypy` sauber.

**Offen:** Die Merkdatei wird nicht aufgeraeumt; sie ist winzig, liegt
unter `arbeit/clips/` und wird pro Tag einmal ueberschrieben. Falls
`arbeit/clips/` je wieder von einer generischen Aufraeum-Logik erfasst
wird, gilt dieselbe Falle wie 19.08.2026 bei `katalog.json` (siehe
`034ae86`).

**Lehre:** Ein Flag, das eine teure Stufe ueberspringt, muss auch pruefen,
welche **Seiteneffekte** der uebersprungene Weg sonst erzeugt haette — hier
der Stempel der Wiederverwendungssperre. Dieselbe Klasse Fehler wie bei den
Trockenlauf-Guards am 19.08.2026 (`2bb3bf6`): Git und Upload abzuschalten
schuetzt nicht automatisch den Zustand, den der naechste Lauf liest.
