---
datum: 2026-08-19
agent: worktree/schlussbild-und-zitatdauer
typ: bugfix
commit: <folgt>
---

# Zitatkarte steht nur noch so lange wie ihr gesprochener Satz

**Was:** Die Zitat-Szene endet jetzt am Ende des zitierten Satzes plus
`ZITAT_NACHLAUF` (1.5 s), mit `ZITAT_MIN` (4.0 s) als Lesezeit-Boden und
`ZITAT_MAX` (12.0 s) weiterhin als Obergrenze. Dafuer gibt es zwei neue
Helfer: `_anker_spanne()` liefert Start **und** Ende einer Anker-Phrase
(`_anker_zeit()` ist jetzt ein Wrapper darauf), `_satz_ende()` findet das
Ende des Satzes, in dem eine Zeit liegt, ohne an Abkuerzungen aus
`STUDIO_ABKUERZUNGEN` oder an Initialen wie "E." zu zerbrechen. Die
Ereignisliste in `szenen_bauen()` traegt als vierten Eintrag das natuerliche
Ende (`None` = keins bekannt).

**Warum:** Nutzer-Feedback zum Video vom 19.08.2026: bei 10:31 stand die
Karte mit «Idiots want the security blanket of an American company like
XOM.» noch im Bild, waehrend der Ton schon beim naechsten Thema war. Die
Dauer war eine feste Konstante — 12 s Karte fuer einen rund 4 s langen Satz,
also gut 7 s Ueberhang in das nachfolgende Thema hinein. Aus den Ankern des
Tages (`extrakte/2026-08-19/folien.json`, 7 Zitate) ist das kein Einzelfall:
die Anker sind durchweg 3–6 Woerter lang.

**Auswirkung:** Die Zitat-Szene wird kuerzer, die anschliessende Story-Szene
entsprechend laenger; die Reihenfolge und der `EREIGNIS_ABSTAND` bleiben
unveraendert. 17 neue Tests in `tests/test_schlussbild.py`, Suite bei 88
gruen.

**Offen:** Kennzahl-Szene (`KARTE_MAX` 9 s) und NEXT-UP-Karte
(`ZWISCHEN_MAX` 6 s) haben dieselbe Bauart und koennten denselben Ueberhang
zeigen; bewusst nicht mitgeaendert, weil dafuer kein Befund vorliegt. Der
Mechanismus (vierter Eintrag der Ereignisliste) ist fuer beide schon da.
