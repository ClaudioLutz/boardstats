---
datum: 2026-08-22
agent: worktree-nur-upload-flag
typ: feature
commit: 124b032
---

# `--nur-upload`: ein fertig gebautes Video hochladen, ohne es neu zu rendern

**Was:** Neues Flag `video_report.py --nur-upload`. Es laesst den Render
(`szenen_video()`) aus, wenn `video_<sprache>.mp4` bereits vorliegt, und
laeuft ansonsten den normalen Weg: Kapitelmarken, Beschreibung, Upload,
Thumbnail, Untertitel, Playlist, Marker. Die Pruefung davor steckt in der
eigenen Funktion `nur_upload_hindernis()` (6 Tests in
`tests/test_nur_upload.py`).

**Warum:** Nach einem Trockenlauf liegt ein fertiges, geprueftes Video da.
Es trotzdem hochzuladen kostete bisher einen kompletten Neubau: rund 40
Minuten Rendern plus ~9'900 TTS-Zeichen fuer eine bitgleiche Tonspur — der
Vertonungs-Cache wird bei einem produktiven Lauf bewusst nicht gelesen
(`ton_holen`-Docstring: "der Cron-Lauf vertont also immer frisch"). Der
Code war fuer die Trennung schon gebaut: Rendern und Upload sind durch
`if args.nur_video: return` sauber getrennt.

**Der Riegel ist der eigentliche Inhalt.** Die Kapitelmarken entstehen aus
den Wort-Zeitstempeln der Vertonung. Wuerde bei `--nur-upload` neu vertont,
gehoerten sie zu einer anderen Aufnahme als der, gegen die das Bild
gerendert wurde — die Marken laegen daneben, auf einem oeffentlichen Video.
`nur_upload_hindernis()` bricht deshalb ab, wenn:

- die MP4 fehlt,
- die MP3 waehrend des Laufs neu geschrieben wurde (mtime bewegt sich nur
  beim echten Vertonen — so laesst sich ein Cache-Treffer nachweisen, ohne
  `ton_holen()` umzubauen),
- es vorher gar keine MP3 gab (dann wurde zwingend neu vertont),
- das Video aelter ist als seine Tonspur.

Zweiter Riegel: schlaegt der Szenenbau fehl, wuerde sonst die Ersatzstaffel
(v6-Folien, dann v5-Text) anspringen und die vorhandene Datei
**ueberschreiben** — genau das, was das Flag verhindern soll. Bei
`--nur-upload` gilt der Bau dann als fertig und die vorhandene Datei bleibt
unangetastet.

**Auswirkung:** Ein gesichtetes Trockenlauf-Video kann ohne Neubau und ohne
TTS-Kosten veroeffentlicht werden. `--nur-upload` setzt `nur_video`
bewusst **nicht** (ein eigener Test haelt das fest, sonst kaeme main() vor
dem Upload zurueck); kombiniert mit `--trockenlauf` gewinnt weiterhin der
Trockenlauf, es wird also nichts hochgeladen. `ruff`/`mypy` sauber,
**287 Tests gruen** (281 + 6).

**Offen:** Im Feld noch nicht ausgefuehrt — ein echter `--nur-upload`-Lauf
laedt auf den Produktionskanal und wurde deshalb bewusst nicht zum Testen
gestartet. Die Riegel sind an der extrahierten Funktion geprueft, der
Upload-Pfad selbst ist unveraendert derselbe wie im Cron-Lauf.
