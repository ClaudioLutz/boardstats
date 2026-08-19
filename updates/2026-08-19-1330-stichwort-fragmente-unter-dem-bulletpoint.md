---
datum: 2026-08-19
agent: worktree-detail-fragmente
typ: feature
commit: <Hash, sobald bekannt>
---

# Stichwort-Fragmente unter dem Fokus-Punkt

**Was:** Der Fokus-Punkt in der Bildmitte trägt jetzt einen zweiten Kasten mit
zwei bis drei Telegramm-Fragmenten zum gerade gesprochenen Satz.

- `run_report.py`: `FOLIEN_PROMPT` bekommt das optionale Stichwort-Feld
  `detail`; `_stichwort()` kappt es (max. 3 Fragmente à 40 Zeichen, Schlusspunkt
  weg) und ersetzt die bisherige Inline-Comprehension in `folien_generieren()`.
- `szenen.py`: neue `detail_karte()`, dazu `_stapel()` als gemeinsame
  Geometrie-Rechnung für Fokus-Kasten und Detail-Kasten und `_detail_bloecke()`
  /`_detail_hoehe()` als Helfer. `fokus_punkt()` nimmt `detail` und `oben_min`
  entgegen.
- `video_report.py`: `_detail_liste()` liest das Feld, `DETAIL_MIN` gibt die
  Mindeststandzeit, `detail_plan` legt die Overlays wie die Kartenstände auf.
- `tests/test_detailkarte.py`: 10 Tests auf Geometrie und Feldbehandlung.

**Warum:** Nutzervorgabe 19.08.2026. Im v7-Szenen-Layout stand als einzige
Substanz der 34-Zeichen-Bulletpoint im Bild — zu wenig Text für ein Video, das
zehn Minuten läuft. Gewünscht war ausdrücklich eine Zwischenstufe zwischen
Bulletpoint und gesprochenem Satz, nicht der Satz selbst: Stichworte, keine
eingebrannten Untertitel (den gesprochenen Wortlaut trägt bereits die SRT).

**Auswirkung:**

- Die Fragmente stehen nur, solange ihr Satz läuft. Sie blenden aus, bevor der
  Punkt in die Themen-Karte fliegt — dort parkt weiterhin nur der Bulletpoint.
  Das Prinzip aus `karte_text()` (Parken darf kein sichtbarer
  Informationsverlust sein) bleibt damit unangetastet.
- Eigenes Overlay statt in die Fokus-PNG gerendert: Flugmechanik und
  `karte_punkt_ziel()` sind unverändert.
- Typografie bewusst abgesetzt: Inter statt der fetten Display-Schrift, gemischte
  Schreibung statt Versalien, Amber-Strich statt Quadrat. Drei Zeilen Versalien
  liest in fünf Sekunden niemand.
- **Layout-Vorrang:** Der Themen-Titel oben ist harte Grenze (`oben_min` =
  `titel_unterkante() + 14`). Passt der Stapel nicht zwischen Titel und
  `STAPEL_UNTEN_MAX` (580), fallen Fragmente von hinten weg, statt den
  Kapiteltitel zu überlaufen.
- Solange der Kapitel-Opener steht, bekommt der Punkt **keine** Fragmente und
  sitzt zentriert wie bisher — Lower Third und höherer Stapel würden sonst
  aneinanderstoßen. Zwischenthema, Zitat und Kennzahl brauchen die Regel nicht:
  sie laufen in eigenen Szenen ohne Fokus-Karte.
- Ohne das Feld ändert sich nichts: ältere Drehbücher und die Fallback-Bullets
  aus `_luecken_fuellen()` liefern eine leere Liste, der Fokus-Punkt sitzt exakt
  wie vorher auf `FOKUS_MITTE` (durch Test abgedeckt).
- `entschaerft()` deckt das neue Feld automatisch ab — es läuft in
  `folien_laden()` über den rohen JSON-String. Die Wortzahl-Kopplung an die
  TTS-Zeitfenster ist nicht berührt: die Fragmente werden nie gesprochen.

**Offen:** Noch nicht an einem echten Cron-Lauf gesehen — die Sichtprüfung lief
gegen synthetische Kulissen, nicht gegen ein Board-Motiv mit Screenshot-Textur.
Ob drei Fragmente auf unruhigem Material ruhig genug wirken oder `DETAIL_MAX`
auf 2 muss, zeigt das erste echte Video.
