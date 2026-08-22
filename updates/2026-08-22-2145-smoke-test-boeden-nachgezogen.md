---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: bugfix
commit: folgt
---

# Smoke-Test am echten Tag 21.08.: Lesezeit-Böden der neuen Beats nachgezogen

**Was:** End-to-End-Render (100-s-Vorschau, v7-Weg komplett, TTS aus dem
Cache) über den Bericht vom 21.08. Die Lesezeit-Verifikation meldete
36 Verstösse — alle systematisch von den neuen Beats verursacht. Fixes:

1. **Count-up-Budget:** das Zählwerk bekommt nur die Zeit, die nach dem
   Endstand-Boden (`ZAHL_COUNTUP_MIN`) übrig bleibt (der 45-%-Deckel
   liess den TL;DR-Endständen nur 1,1–1,5 s); Endstand-Boden ist nur noch
   der Zahl-Boden (Wert+Titel werden auch gesprochen).
2. **Opener/Zitat-Sichtzuschläge:** `OPENER_SICHT_ZUSCHLAG` (1,1 s) und
   `ZITAT_SICHT_ZUSCHLAG` (0,9 s) — Textstart-Versatz + Einflug +
   Ausblende gehören zum Fenster, nicht zur Lesezeit.
3. **Detail-Fragmente:** `DETAIL_BLENDEN` (0,7 s) steckt jetzt in der
   Rückwärts-Reserve von `_detail_zeiten` und im Fenster-Check.
4. **Fokus-Punkte:** nicht-fliegende Punkte budgetieren ihre Ausblende
   (0,35 s); fliegende lesen bis zum Flugbeginn (auch im zeigt-Check).
5. **Multiples-Fenster:** `ZAHL_UEBERSICHT_FENSTER` = Boden + Blenden +
   Staffelversatz.
6. **Gesprochene Ansagen** (Hook-Karte, Zahlen-Kopf) prüfen nicht mehr
   gegen einen Lese-Boden — sie werden wortgleich gesprochen und können
   strukturell nicht länger stehen.
7. **Verifikation:** Einflug zählt nur als Verlust, wenn `_lage` ihn
   wirklich fährt (Standzeiten < 2×EINFLUG_DAUER bleiben statisch).

**Ergebnis:** zweiter Lauf **88 Textelemente, alle über ihrem Boden**;
38 Szenen, 280 Overlays, 19 Flüge, 50 Klang-Ereignisse, natives 1080p —
Frames visuell geprüft (Hook-Lower-Third, Kapitel mit blauem
Aktien-Akzent, Randspalte, Datenstand-Bug).

**Warum:** Genau der Zweck der Leitplanke-3-Verifikation: jeder neue Beat
frisst Lesezeit, und ohne Nachrechnen am echten Lauf wäre es niemandem
aufgefallen.

**Auswirkung:** Mehr Fragmente fallen an engen Stellen weg (15 von 49 am
Testtag, geloggt) — Lesbarkeit vor Menge. Kein Verstoss mehr am Testtag.

**Offen:** Ton-Feinabnahme (Effektpegel, Bett-Senke) am ersten echten
Cron-Video per Ohr.
