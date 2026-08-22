---
datum: 2026-08-22
agent: claude/brainstorm-intent-scope-abc (Worktree)
typ: feature
commit: folgt
---

# C-News: zweistufiges Lower Third, BREAKING-Kicker, Datenstand-Zeitstempel

**Was:**

- **Zweistufiges Lower Third (C1):** `szenen.titel_karte_teile()` trennt
  Grund (Bande + Farbbalken + optionaler Kicker) und Text; `titel_karte`
  komponiert weiter beides für einstufige Stellen. In `szenen_bauen`
  blendet der neue Helper `lower_third()` den Grund zuerst ein (Einflug
  von links) und den Text `LT_VERSATZ` (0,25 s) später — angewandt auf
  Kapitel-Opener, Intro-Hook und Zahlen-Kopf; Zwischenthemen/Agenda
  bleiben bewusst einstufig (kurze Fenster). Opener-Boden um den Versatz
  erhöht, damit die effektive Lesezeit hält.
- **BREAKING-Kicker (C-News):** roter Chip über dem Opener-Label, genau
  EINER pro Video. Kriterium wie im Intent vorgeschlagen:
  `_breaking_kapitel()` findet das Kapitel, in dessen Rumpf die erste
  TL;DR-Zahl des Tages gesprochen wird; ohne Treffer gibt es keinen.
- **Zeitstempel (C-News):** der Ecken-Bug zeigt rechts
  `<Datum> · DATA HH:MM` aus der «Data as of»-Kopfzeile des Berichts —
  Datenstand als Bildschirm-Metadatum, nie gesprochen (Retention-Entscheid
  21.08.), keine falsche Live-Behauptung.

**Warum:** Nutzerentscheid 22.08.: Nachrichten-Zweig wird mit umgesetzt;
das zweistufige Lower Third ist zugleich der Masken-Reveal-Ersatz des
PNG-Wegs (B2).

**Auswirkung:** Opener lesen sich als TV-Bauchbinde (Balken → Text),
die härteste Story trägt einen roten BREAKING-Marker, jede Szene nennt
den echten Datenstand. Visuell verifiziert (Kicker + Bug).

**Offen:** —
