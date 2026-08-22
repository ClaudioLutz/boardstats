---
datum: 2026-08-22
agent: claude/video-thumbnail-meme-60c124
typ: feature
commit: <Hash, sobald bekannt>
---

# Vorschaubild wird Meme: Titel frei über dem Motiv, keine dunkle Abdeckung mehr

**Was:** `thumbnail.py` — `bauen()` und die Geometrie-Konstanten umgebaut. Weg
sind der Diagonalanschnitt (`DIAG_OBEN/DIAG_UNTEN/DIAG_STREIFEN`), die opake
dunkle Textflaeche ueber der linken Bildhaelfte und der Amber-Balken
(`BALKEN_BREITE/BALKEN_ABSTAND`). Neu: das Motiv laeuft als Vollbild durch, der
Aufhaenger steht als Meme-Text zentriert am oberen Rand (`TEXT_OBEN`,
`TEXT_BREITE` = volle Bildbreite minus Rand, `GROESSEN` bis 132 px) und wird
allein durch eine dicke schwarze Kontur lesbar (`KONTUR_FAKTOR` = 0.085 der
Schriftgroesse). Der Amber-Chip mit der Serienmarke ist von oben links nach
unten links gewandert und kleiner (`CHIP_HOEHE` 46, Schrift 28), der Fusstext
steht daneben in Weiss mit Kontur statt in Grau auf dunkler Flaeche. Das letzte
Wort bleibt amber.

**Warum:** Anweisung nach dem Upload vom 22.08. (`0V9DGLtRkdk`): das Vorschaubild
war schwach, weil die dunkle Textflaeche die halbe Bildbreite und damit das
Motiv verdeckt hat. Gewuenscht ist ein Meme-Thumbnail — Bildmakro-Optik, Titel
einfach ueber dem Bild.

**Auswirkung:** Ab dem naechsten Lauf sieht jedes Vorschaubild so aus; das
Board-Motiv ist vollflaechig sichtbar. Zusaetzlich wurde das Vorschaubild des
bereits hochgeladenen Videos `0V9DGLtRkdk` per `youtube_auth.thumbnail_setzen`
nachtraeglich ersetzt — als Motiv das Rage-Wojak-Bild
(`62620482-1787421789908773.jpg`), das im Video bei 01:30 als Kulisse laeuft,
mit dem Schlagwort `50% TARIFFS` aus `titel.json`. Bewusst nicht geaendert:
`videohintergrund()` mit seinem unteren Verlauf (das ist die Video-Kulisse, nicht
das Vorschaubild) und die Motiv-Auswahl in `video_report.vorschaubild()`.

**Offen:** Die Motiv-Auswahl nimmt weiterhin das erste geprueft-ausgewaehlte
Board-Bild des Tages — nicht bewertet, ob das das memetauglichste ist.
