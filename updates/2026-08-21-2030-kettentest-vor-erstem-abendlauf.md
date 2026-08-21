---
datum: 2026-08-21
agent: main
typ: docs
commit: 90c03b8
---

# Kettentest Report→Video→Shorts vor dem ersten produktiven Abendlauf

**Was:** Vollständiger lokaler Testlauf der Kette (19:04–20:16 CEST), um die
seit dem 20.08. gemergte Feature-Serie vor ihrem ersten echten Cron-Durchlauf
an realer Ausgabe zu prüfen — ohne den Produktions-Delta anfassen zu können.
Befunde in `.claude/skills/pipeline-overseer/SKILL.md` nachgetragen:

- Der Abschnitt „Report→Video-Kettentest nicht mehr ohne Weiteres möglich"
  vom Vormittag ist **widerlegt und durch ein erprobtes Rezept ersetzt**: die
  Einschränkung galt nur für einen Test *auf hp-ubuntu*. Lokal gibt es keinen
  produktiven Zustand, den man verderben könnte — dokumentiert sind jetzt das
  Spiegeln von Cache/Analytics/Rohsnapshot, die Kettennaht von Hand, das
  Pflicht-Aufräumen und die Gegenprobe.
- Neuer Abschnitt „Serie vom 20.08. im Kettentest verifiziert" mit
  Nachweistabelle für alle fünf zuvor offenen Prüfpunkte.
- Neuer Betriebswert-Befund: der TTS-Verbrauchszähler ist **pro Maschine**,
  nicht global — die Prozentanzeige eines lokalen Laufs (1.6 %) ist nicht der
  Kontingentstand (hp-ubuntu steht bei 17.3 %, echt ist die Summe).
- Intro-Länge als Betriebswert aktualisiert: 29.6 s → **37.0 s** durch den
  TL;DR-Block; Videolaufzeit 513.8 s (8:34) statt Median 11:39.

**Warum:** Nutzerauftrag: Testlauf starten, dabei sicherstellen, dass der
Delta-Zustand nicht kaputtgehen kann und der Abendlauf mit den richtigen Daten
der Periode „letzter produktiver Lauf → produktiver Run" läuft.

**Auswirkung:** Keine Code-Änderung, nur Dokumentation. Verifiziert an echter
Ausgabe: Retention-Rückkopplung greift (1801 → 878 Wörter, 11:39 → 8:34),
Titel-Frontloading (Hook 50 Zeichen), TL;DR-Zahlenblock (4 Zahlen, Frame
geprüft), Stimme en-US-Studio-O, Shorts mit Ähnlichkeits-Guard 1.000 und 7
verschiedenen Kapitel-Motiven (Frame geprüft). Der Zustandsschutz ist
gegengeprüft: `cache/status.json`, `arbeit/motive/verwendet.json` und
`arbeit/clips/katalog.json` auf hp-ubuntu trugen vor und nach dem Test
unverändert den Stempel vom 20.08.; auf hp-ubuntu wurden nur `bundles/` und
die temporäre `cache_status.json` berührt, die `report.sh` ohnehin neu
erzeugt. Die Delta-Periode für heute Abend ist damit belegt 20.08. 20:37 →
20:20-Snapshot von heute. Kein `extrakte/2026-08-21/` auf hp-ubuntu, also
weder Video- noch Shorts-Marker — beide Stufen laufen durch.

**Offen:**

- **Wortzahl-Ableitung in `_retention_block()` (`run_report.py:2101`) ist
  falsch kalibriert**: skaliert das Soll-Budget `WORTBUDGET` mit der
  Ist-Laufzeit einer Messung, die zu ~1800-Wörter-Berichten gehört — das
  Wortziel fällt dadurch rund um Faktor 2 zu niedrig aus (350–500 Wörter
  ergäben 3:25–4:50 statt der angepeilten 5.8 min). Bewusst nicht mehr vor
  dem produktiven Lauf geändert.
- Upload-Seite bleibt ungetestet (Kapitelmarken in der Beschreibung, Tags,
  Shorts-Marker, privat→public) — der Trockenlauf baut keine Beschreibung.
  Morgen an den Cron-Logs und am hochgeladenen Video prüfen.
- Sichtprüfung lässt Anime-Motive mit betonter Körperlichkeit als
  Kapitelhintergrund durch (Short 3). Positionierungsfrage für den Kanal;
  falls unerwünscht, gehört ein Kriterium in `HINTERGRUND_PROMPT`.
