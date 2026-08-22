---
datum: 2026-08-22
agent: main
typ: feature
commit: 8ef71fb
---

# Analytics: echte Aufrufe (engagedViews) und Wiedergabedauer je Video

**Was:** `analytics_bericht.py` erhebt zusätzlich `engagedViews` — Aufrufe mit
tatsächlicher Wiedergabe statt bloss serviert — in `tageszahlen()`,
`je_video()` und `traffic_quellen()`. Die Video-Tabelle zeigt neu `echt` und
`Ø Dauer`, die Tagestabelle `davon echt`. Neue pure Funktion
`engagement_luecke()` listet Einträge, bei denen Aufrufe gezählt, aber nicht
angeschaut wurden.

**Warum:** Der Nutzer hat dem „Faktor 15" widersprochen, mit dem ich die Shorts
(44 Aufrufe) gegen das Hauptvideo (3) gestellt hatte — wörtlich: „Der short
wird einfach serviert und der viewer scrollt weiter mit dem Daumen. = +1 View.
Das ist kein Erfolg in meinen Augen." Der Einwand ist berechtigt: die Data-API-
Zahl trifft diese Unterscheidung nicht, der Vergleich stellte zwei Währungen
nebeneinander. `engagedViews` ist die Metrik, die es entscheidet — im Gegensatz
zu Impressionen/CTR gibt die API sie her (getestet).

Zusätzlich hat der Nutzer die Shorts inzwischen selbst gesichtet und für
schlecht befunden. Die Messung entscheidet damit nur noch, ob die Reichweite
echt ist, nicht ob das Material taugt.

**Auswirkung:** Ab dem 23:30-Lauf steht in der Ausgabe, wie viele Aufrufe
tatsächlich Wiedergaben waren. Am **24.08.** liegen erstmals Analytics-Daten
für die Shorts vom 21.08. vor — dann ist die Frage entscheidbar. Die
Entscheidungsregel steht **vorab** im Overseer-Skill, damit die Zahl nicht
nachträglich passend gedeutet wird: Haupttest ist die Ø Dauer, die
Views-Differenz nur der Zweittest (Gleichheit beweist nichts, weil offen ist,
ob `engagedViews` bei Shorts überhaupt abweichen kann).

**Risiko abgesichert:** `je_video()` speist über `kurven_erheben()` die
Retention-Rückkopplung an `run_report`. Würde YouTube die neue Metrik dort je
ablehnen, fiele nicht nur die Zusatzspalte, sondern die Abbruchkurven des Tages
aus. Deshalb wiederholt `je_video()` die Abfrage bei `RuntimeError` einmal ohne
`engagedViews` und loggt das. Vorab gegen die Produktions-API geprüft: alle drei
Abfragen (`day`, `video`, `day,insightTrafficSourceType`) akzeptieren die
Metrik.

**Fehlende Metrik ≠ null:** Ältere Messungen und der Rückfall kennen
`engagedViews` nicht. Anzeige schreibt dort `.` statt `0`, und
`engagement_luecke()` wertet den Eintrag als unauffällig — sonst erschiene jede
Altmessung als „alles weggewischt". Zwei Tests sichern das ab.

**Validierung:** `ruff check` und `mypy` sauber, 245 Tests grün (7 neu), echter
Lauf gegen die Produktions-API mit und ohne `--speichern` geprüft, danach
`retention_befund()` gegen die neu geschriebene Datei — liefert weiterhin einen
Befund aus 4 Abbruchkurven. Testdatei wieder entfernt.

**Offen:** Ob die Shorts-Aufrufe echt sind (Messung am 24.08.). Bis dahin ist
„Shorts laufen besser" zurückgezogen und die Empfehlung „am Format ansetzen"
ausgesetzt.
