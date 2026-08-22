---
datum: 2026-08-22
agent: claude/video-thumbnail-meme-60c124
typ: feature
commit: 505565c
---

# Sonnet bestimmt auch Blockbreite und Zeilenumbruch der Meme-Schlagzeile

**Was:** `thumbnail.bauen()` nimmt zusaetzlich `block_breite`
(`BLOCK_BREITEN`: voll 1.0 / halb 0.52 / drittel 0.38 der Satzbreite) und
`umbruch` (feste Zeilenteilung). `_passende_schrift()` sucht bei Vorgabe nur
noch die Schriftgroesse, in der die laengste Vorgabezeile in die Spalte
passt; passt sie selbst in der kleinsten Schrift nicht, bricht der Code
wieder selbst um. Neu `umbruch_pruefen()`: nimmt die Zeilenteilung nur an,
wenn sie dieselben Woerter in derselben Reihenfolge traegt, hoechstens
`ZEILEN_MAX` Zeilen, keine leere Zeile. In `video_report.py` liefert
`_thumb_platzierung()` jetzt ein Urteil-Dict (zone, ausrichtung,
block_breite, umbruch) statt eines Tupels, und `THUMB_PROMPT_PLATZIERUNG`
fragt die vier Felder ab.

**Warum:** Anweisung: Sonnet soll auch die Textausrichtung steuern — konkret
waere beim Rage-Wojak-Motiv "rechts, 50% / TARIFFS im dunklen Bereich" am
schoensten. Mit fester Vollbreite geht das nicht: eine einzeilige Schlagzeile
ueber die ganze Bildbreite liegt zwangslaeufig auf dem Motiv. Erst die
schmale Spalte plus eigener Umbruch stellt den Text NEBEN die Figur.

**Auswirkung:** Der Modellaufruf bleibt einer pro Video-Lauf. Die
Prompt-Kriterien wurden nach einer Probe nachgeschaerft: der erste Entwurf
("voll bleibt erste Wahl") liess Sonnet weiter die Vollbreite waehlen; jetzt
gilt die Spalte neben der Figur ausdruecklich als besser als eine Zeile quer
ueber das Motiv, auch wenn die Schrift dadurch kleiner wird. Danach urteilte
Sonnet am selben Motiv "oben/rechts, halb, [50%, TARIFFS]" — genau das
gewuenschte Bild. Der Umbruch-Riegel ist der Sicherheitsteil: ein Modell,
das Zeilen teilen darf, darf die Schlagzeile nicht umschreiben, kuerzen oder
etwas dazuerfinden — das stuende sonst als Kanalanstrich im Netz. Faellt
das Urteil aus, greift wie zuvor die Messung mit Vollbreite und
Code-Umbruch.

**Offen:** `BLOCK_BREITEN` sind gesetzte Werte, nicht gemessene — ob 0.52 /
0.38 fuer die typischen Board-Motive die richtigen Spaltenbreiten sind,
zeigen die naechsten Laeufe.
