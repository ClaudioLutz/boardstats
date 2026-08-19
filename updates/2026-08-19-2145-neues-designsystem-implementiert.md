# Neues Designsystem (Claude Design 19.08.2026) in die Renderer übernommen

**Wann:** 2026-08-19, ca. 21:45
**Wer:** Haupt-Session (Worktree `worktree-neues-designsystem`)
**Was:** szenen.py, folien.py, thumbnail.py, video_report.py, tests/test_bullet_kappung.py

## Warum

Die zwölf Mockups des Designsystems wurden als Claude-Design-Projekt
(«boardstats Video-Designsystem») überarbeitet; 9 von 12 kamen verändert
zurück (unverändert: Lower Third, Zitat-Post, Tokens). Dieser Commit
setzt den überarbeiteten Stand pixelnah in den PIL-Renderern um.

## Was sich ändert

- **Szene v7 → Randspalte:** Themen-Titel und geparkte Punkte sind EIN
  Kasten, bündig an der Bildkante (nur bildinnere Ecken gerundet, Radius 16),
  mit Amber-Tab, Lesezeichen-Icon und Trennlinie. Gerendert weiterhin als
  zwei Overlays (Titel-Teil bis zum ersten Kartenstand, dann Voll-Spalte),
  die sich hart abloesen — Titelpixel identisch, kein Alpha-Doppel.
  `themen_titel`/`themen_karte`/`karte_punkt_ziel` tragen jetzt den Titel
  bzw. die Lage als Parameter; `karte_oben` ist gefallen.
- **Fokus-Block:** Fokus-Punkt (Space Grotesk 42/52, Breite 650) und
  Detail-Fragmente (Inter Medium 24/33, ohne Strich-Marker) bilden optisch
  einen Kasten mit durchgehendem Amber-Balken und kurzer Trennlinie; der
  Detail-Teil schliesst ohne Luecke an (1 px versetzt gegen Alpha-Doppel
  an der Naht) und waechst weiter stufig. Nur der Fokus-Teil fliegt.
- **Vignette:** der untere 320-px-Verlauf ist weg (jeder Text steht auf
  eigenem Kasten), oben bleibt der 96-px-Hauch fuer den Bug.
- **Zahl-Tafel:** 200-px-Mono-Wert (Leiter 200/160/128/96), Bande 154–574,
  Titel 44 in VERSALIEN, Trend-Icon 0.48×.
- **Outro-Tafel/-Folie:** fast schwarzer Grund, Serientitel 84 linksbuendig,
  Amber-Linie 548×10, Abbinderzeilen.
- **Folien v6 → Broadcast-Look:** Motiv vollflaechig und roh (statt
  _grund/abgedunkelt), Text auf 89-%-Kaesten (`ImageDraw.Draw(bild,
  "RGBA")`), Szenen-Bug statt Kopfzeile-mit-Linie. Intro als Karte 860,
  Agenda als Seitenpanel 730 buendig links, Reveal-Kasten 760 buendig
  links, Themen-Folie mit Titel-Kasten+Icon/Punkte-Kasten 660/Zahlen-Karte
  452×204/Quellen-Chip, Zahlen-Folie mit #232342-Karten 560×204 und
  72-px-Werten.
- **Thumbnail:** Vollbild-Motiv in voller Farbe, harter Diagonalanschnitt
  (62 %→50 %) mit Amber-Kante, Amber-Chip mit Serienmarke, Titel bis 108 px
  mit amberfarbenem Schlusswort, Balken 14 px.

## Verifikation

- `ruff check` sauber, `mypy` sauber, alle 135 Unit-Tests gruen
  (test_bullet_kappung an KARTE_PAD_R angepasst, Detail-Naht-Overlap-Test
  deckte den 1-px-Fehler auf und ist wieder gruen).
- Render-Probe mit den echten Tagesdaten (extrakte/2026-08-19) fuer alle
  Bausteine: research/probe-design-2026-08-19/ (lokal).
- Pillow-`corners=` braucht ≥9.4: lokal 11.3.0, hp-ubuntu 10.2.0 — ok.

## Risiken / Offenes

- Reveal ist nicht mehr deckungsgleich mit dem Themen-Folien-Titel; die
  Blende laeuft trotzdem sauber (beide Kaesten oben links).
- Der Ecken-Bug liegt im Outro unter der fast schwarzen Tafel — bewusst,
  das Mockup zeigt dort nur das Datum.
