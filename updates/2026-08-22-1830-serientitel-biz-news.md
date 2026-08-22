---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# Serientitel im Bild: BIZ-NEWS (Brainstorm-Intent C5)

**Was:** Alle Serientitel-Bildstellen von `4CHAN /biz/ · BOARD REPORT` bzw.
`/biz/ BOARD REPORT` auf `BIZ-NEWS` umgestellt: `szenen.BUG_TEXT` (Ecken-Bug
jeder Szene), `szenen.outro_tafel` (Abbinder), `folien.KOPF_TEXT` und
`folien.OUTRO_TITEL` (v6-Fallback), `shorts.KOPF_TEXT` (Shorts-Kopfzeile),
`thumbnail.bauen`-Default `kopf` (Vorschaubild-Chip). Neuer Test
`tests/test_serientitel.py`.

**Warum:** Nutzerentscheid 22.08.2026 im Brainstorming
(`brainstorm-text-animationen-dynamik-2026-08-22`): kein 4chan-Label mehr im
Bild, die Slash-Schreibweise ist Board-Notation und Herkunftsstempel;
"NEWS" trägt den Genre-Entscheid (Datenjournalismus + Nachrichtenoptik).
Passt zur laufenden Strategieprüfung weg vom 4chan-Branding.

**Auswirkung:** Der Bug schrumpft von 30 auf 9 Zeichen und gibt Bildfläche
frei. Bewusst NICHT geändert: die Zitat-Post-Karte (`Datum · /biz/` ist
Herkunftsangabe eines echten Posts) und die YouTube-Metadaten
(Beschreibung/Tags nennen weiter "4chan" — Reichweitenfrage, getrennt zu
entscheiden, per Test festgehalten).

**Offen:** Metadaten-Entscheid (#4chan-Tags) steht aus.
