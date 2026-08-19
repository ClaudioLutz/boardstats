---
datum: 2026-08-19
agent: main
typ: infra
commit: <Hash, sobald bekannt>
---

# Delta-Zustand auf den Stand nach dem YouTube-Upload zurueckgerollt

**Was:** Auf hp-ubuntu den gesamten Zustand, den die Pipeline als "schon
gesehen" fuehrt, auf den Stand direkt nach dem produktiven Upload von heute
(Video `Q5Mbsfmkvnc`, 08:26, Datenstand 07:19) zurueckgesetzt:

- `cache/status.json`: bei den 14 Threads des Morgenlaufs `last_post_no` zurueck
  auf die hoechste Post-Nummer im Snapshot `raw/2026-08-19T0520.jsonl.gz`;
  12 Threads, die erst ein Testlauf in den Cache brachte, ganz entfernt (werden
  morgen voll gelesen). Die Neuaufbau-Zaehler wurden bei den morgens voll
  gelesenen Threads exakt zurueckgesetzt, bei den fortgeschriebenen auf
  `NEUAUFBAU_NACH - 1` gedeckelt, damit die Testlaeufe keinen unnoetigen
  Neuaufbau erzwingen.
- `cache/<thread>.txt`: die 15 Extrakte aus dem Morgen-Commit `673fac7`
  rekonstruiert (Markdown zurueck in den Extrakt-Text). Sonst haette der
  Update-Prompt die Abendposts schon in Teil 1 stehen gehabt und das
  "neu seit dem letzten Lauf"-Signal des Berichts waere falsch.
- `arbeit/motive/verwendet.json`: 32 Bildsperren entfernt, die Bilder betreffen,
  die morgens in keinem der 15 Bericht-Threads lagen.
- `arbeit/clips/katalog.json`: alle 14 `zuletzt_verwendet: 2026-08-19` entfernt —
  das Morgenvideo hatte nachweislich keine Clip-Zuordnung (`logs/video_cron.log`
  zum Lauf 08:10 zeigt keine Clip-Zeile).
- `extrakte/2026-08-19/`: das oeffentliche Archiv auf den Morgen-Commit `4626269`
  zurueckgesetzt, 4 getrackte und 8 ungetrackte Testlauf-Extrakte entfernt. Der
  Upload-Marker `video_en.json` bleibt bewusst stehen.

**Warum:** Die drei Testlaeufe des Tages (14:49, 20:12, 20:25) und die
zugehoerigen Video-Laeufe schreiben denselben Zustand fort wie ein produktiver
Lauf. `--trockenlauf` und `--nur-video` ueberspringen nur Git und Upload, nicht
`cache_pflegen()`, `verwendete_merken()` und das Stempeln des Clip-Katalogs.
Ohne Ruecksetzung haette der Cron-Lauf morgen 07:35 nur das Delta seit 20:27
statt seit dem letzten Upload geholt — rund zwoelf Stunden Board-Aktivitaet
waeren im Video nie aufgetaucht. Ausserdem zeigte das Archiv einen Teststand
statt der Fassung, zu der das hochgeladene Video gehoert, und der dirty
Working Tree haette morgen `git pull --ff-only` in `report.sh` gefaehrdet.

**Auswirkung:** Der Lauf morgen frueh sieht das volle Delta Upload-zu-Upload,
bei Posts wie bei Bildern und Clips. Bewusst *nicht* geaendert: `berichte/`
(wird morgen ohnehin neu geschrieben) und die alten `video*.json`-Streuner in
`extrakte/2026-08-1[4-8]/`.

**Offen:** Die Wurzelursache — Testlaeufe duerfen den Delta-Zustand gar nicht
erst fortschreiben — wird separat behoben. Nicht rekonstruierbar: welche der
78 verbleibenden Bildsperren vom 19.08. wirklich im Video landeten
(`motive.json` wurde von den Testlaeufen ueberschrieben); rund 31 waren es,
der Rest bleibt uebersperrt und laeuft am 24.08. aus. Threads, die bis zum
Snapshot morgen frueh sterben, sind fuer den Bericht ohnehin verloren — ihr
heutiges Delta liegt nur noch in `raw/2026-08-19T1120` und `T1820`.
