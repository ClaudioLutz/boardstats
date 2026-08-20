---
datum: 2026-08-20
agent: main
typ: feature
commit: d122cb3
---

# Sprecherwechsel: en-US-Studio-O statt Studio-Q

**Was:** In `video_report.py` die Stimmenkette der Sprache `en` auf weiblich
umgestellt — `google_stimme` von `en-US-Studio-Q` auf `en-US-Studio-O`,
`google_stimme_marken` von `en-US-Neural2-J` auf `en-US-Neural2-G`, die
edge-tts-Notstimme von `en-US-GuyNeural` auf `en-US-AriaNeural`. `README.md`
an den drei Stellen nachgezogen, die die produktive Kette beschreiben, und den
Kommentar an `TOKENS_PRO_S` um die gemessene Abweichung ergänzt.

**Warum:** Anweisung des Users nach einem Hörvergleich aller en-US-Klassen
(Studio, Chirp3-HD, News, Neural2, Polyglot, Casual — 15 Proben auf dem echten
Produktionspfad, abgelegt in `research/stimmproben/`). Studio-O gewann, und
zwar ausdrücklich **ohne Nachbearbeitung**: die ebenfalls geprüften Varianten
(tiefer/wärmer sowie höher/„Anime") sind verworfen.

Die Ersatzkette zieht mit, damit ein Ausfalltag nicht plötzlich männlich klingt.
Ausgewählt nach gemessener Grundfrequenz: Studio-O 190.5 Hz, Neural2-G 193.5 Hz,
AriaNeural 196.7 Hz (Neural2-C 158.9 Hz und JennyNeural 177.8 Hz lagen weiter weg).

**Auswirkung:** Ab dem nächsten Video-Cron (21:15 CEST) spricht eine Frauenstimme.
Der Vertonungs-Cache greift nicht mehr — `_cache_schluessel` enthält den
Stimmennamen, der erste Lauf vertont also vollständig neu und kostet das volle
Kontingent. Studio-O teilt sich die Studio-Klasse mit Studio-Q, das Kontingent
ändert sich dadurch nicht.

Studio-O spricht denselben Absatz 2.5 % schneller als Studio-Q (23.6 s statt
24.2 s). `TOKENS_PRO_S` bleibt bei 2.50 — die Abweichung liegt unter der
Auflösung eines Rahmensatzes in der Vorspann-Schätzung.

Bewusst nicht geändert: die datierten Messprotokolle im Code, die Studio-Q als
Messobjekt nennen (17./19.08.), sowie der Studio-Pfad selbst — Studio-O nimmt
dasselbe SSML an wie Studio-Q.

**Offen:** Nach dem ersten echten Lauf hören, ob die Prosodie-Konstanten
(`STUDIO_SATZ_PAUSE`, `STUDIO_POINTE_PAUSE`, `STUDIO_KAPITEL_RATE`) für
Studio-O noch passen — sie sind an Studio-Q gemessen.
