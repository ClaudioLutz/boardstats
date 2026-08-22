---
datum: 2026-08-22
agent: worktree-clip-ernte-ganzer-snapshot
typ: bugfix
commit: <wird beim Commit ergaenzt>
---

# Clip-Ernte nimmt den ganzen Snapshot statt nur der ausgewerteten Threads

**Was:** `klip_kandidaten()` erntet WebM/MP4-Anhaenge jetzt aus allen
Threads des Snapshots. Die ausgewerteten Threads kommen weiterhin zuerst,
damit sie unter `KLIP_MAX` (24) nicht verdraengt werden. Dafuer nimmt
`rr._snapshot_posts()` / `_posts_lesen()` neu `threads=None` fuer "alle"
(rueckwaertskompatibel, alle bisherigen Aufrufer uebergeben weiter ihre
Menge).

**Warum:** Am 22.08.2026 meldete der Report "1 neue Clips freigegeben" —
am 21.08. waren es 8. Die Messung zeigt, dass nicht die Sichtpruefung
knausert, sondern die Ernte verhungert:

| Messung am Snapshot 2026-08-22T1820 | |
|---|---|
| Clip-Anhaenge im Snapshot gesamt | **18** (12 webm, 6 mp4) |
| davon in den 16 ausgewerteten Threads | **5** |
| davon bereits im Katalog | **5** |
| neue Kandidaten moeglich | **0** |

**72 % aller Clip-Anhaenge lagen ausserhalb der ausgewerteten Threads.**
`KLIP_JE_THREAD` (3) war unschuldig — kein Thread hatte mehr als einen
Clip.

Dazu die Mengenrechnung, die strukturell nicht aufging: Verbrauch bis zu
9 Clips taeglich (8 Kapitel + Intro), Sperre 5 Tage
(`rr.VERWENDET_TAGE`) → noetiger Pool rund **45**. Vorhanden waren 29
freie, davon **11** nicht gesperrt (18 blockiert vom 20./21.08.). Zufluss
der letzten vier Laeufe: 3, 2, 8, 1 — im Mittel 3.5/Tag. Der Pool wurde
schneller leergesaugt, als er sich fuellte.

Die Kopplung an die ausgewerteten Threads war ohnehin wirkungslos: ein
Clip wird nicht ueber seine Herkunft eingesetzt, sondern spaeter per LLM
ueber seine **Beschreibung** einem Abschnitt zugeordnet
(`video_report._klip_zuordnung`). Woher er stammt, spielt fuer seine
Verwendung keine Rolle.

**Auswirkung:** Statt 5 erreichbarer Anhaenge stehen taeglich rund 18 zur
Auswahl. Erwarteter Zufluss nach Sichtpruefung grob 10-12/Tag statt 3.5 —
damit traegt der Pool die 5-Tage-Sperre, ohne dass an ihr gedreht werden
muss. Kosten bleiben durch `KLIP_MAX` gedeckelt, die Sichtpruefung wird
aber merklich mehr zu tun bekommen (Laufzeit der Clip-Stufe beobachten:
am 22.08. 18s fuer 3 Kandidaten, am 21.08. 99s fuer 9).
`ruff`/`mypy` sauber, 272 Tests gruen.

**Offen — und wichtiger als diese Aenderung:** Mehr Clips im Katalog
heisst noch nicht mehr Bewegtbild im Video. Ein zugeteilter Clip ersetzt
heute **nur das Opener-Motiv seines Kapitels** (`video_report.py:3169`,
bewusst so gebaut: "Clips sind eine Ergaenzung, kein Ersatz") — also rund
4-8 Sekunden je Kapitel. Am 22.08. wurden 4 Clips zugeordnet und 3
normalisiert gerendert; das sind grob 20 Sekunden Bewegtbild in einem
Zehn-Minuten-Video. Wer mehr bewegte Kulisse will, muss dort ansetzen,
nicht an der Ernte. Nutzerhinweis vom 22.08. dazu: "die clips ernte muss
auch im video gerendert werden."
