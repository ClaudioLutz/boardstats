---
datum: 2026-08-20
agent: worktree-agent-a50edd5dd83449881
typ: feature
commit: 2e2d63a
---

# Abbruchkurven fliessen automatisch in Bericht und Drehbuch ein

**Was:** Rückkopplungsschleife von der Analytics-Messung in die Generierung
(Prio 4 aus dem Brainstorming vom 20.08.).

- `analytics_bericht.py`: `kurven_erheben()` — bei `--speichern` werden
  automatisch die Abbruchkurven aller Uploads der letzten 10 Tage
  (`KURVEN_TAGE`) miterhoben und als Feld `kurven` gespeichert
  (`{video_id, titel, veroeffentlicht, laufzeit_s, views, kurve}`). Eigene
  `je_video`-Abfrage mit kurzem Fenster, weil die grosse Top-50-Rangliste
  nach Views genau die jüngsten (viewärmsten) Uploads verlieren würde.
  Fehler je Video (gelöscht, keine Bindungsdaten) kosten nur dieses Video.
  Das bestehende `kurve`-Feld (CLI `--kurve`) bleibt unverändert, der
  Cron-Aufruf braucht keine Änderung.
- `run_report.py`: `retention_befund()` liest die jüngste brauchbare Messung
  aus `arbeit/analytics/` (max. 3 Tage alt; kaputte/kurvenlose Messtage
  werden übersprungen, solange eine ältere frische trägt), leitet
  deterministische Kennwerte ab (`_retention_kennwerte`: Kurvenmittel,
  Zeitpunkt unter 50 %/30 % Bindung, steilste Abbruchzone) und baut daraus
  einen englischen Kontextblock (`_retention_block`), der an den
  Synthese-Prompt (stufe3) und `FOLIEN_PROMPT` angehängt wird. Ohne Daten
  liefert die Funktion `""` — die Prompts sind dann per Konstruktion
  byte-gleich zum bisherigen Stand; eine Logzeile (`Retention: ...`)
  dokumentiert jeden Ausgang.

**Warum:** Bisher gab es keinerlei Rückkopplung — die Abbruchmessung vom
19.08. (50 % weg nach 1:08 bei 11 min) wurde einmalig von Hand nachgezogen.
Jetzt speist sich die Ziel-Länge des nächsten Berichts automatisch aus der
gemessenen Kurve.

**Auswirkung:** Ab morgen Abend hängt am Synthese- und Drehbuch-Prompt ein
Block wie: Median-Laufzeit 10:54, Ø Wiedergabe 2:05 (19 %), 50 % weg nach
0:33, unter 30 % nach 0:45 → Ziellaufzeit ~5.5 min, 350–500 Wörter,
front-loaden, straffen. Heute Abend (20:35) läuft der Bericht noch als
No-Op mit Logzeile, weil die Datei auf hp-ubuntu erst um 23:30 mit Kurven
entsteht — gewollt.

Zwei bewusste Abweichungen vom Auftrag:

1. Injiziert wird in den Synthese-Prompt in `stufe3()` statt in die
   `update_prompt.txt`-Aufrufstelle: `update_prompt.txt` ist der
   Thread-Extrakt-Prompt ("You do not write a report") — eine Ziellänge
   dort wäre wirkungslos und würde in die gecachten Extrakte durchsickern.
   Die Berichtslänge steht in Regel 3 des Synthese-Prompts.
2. Ziellaufzeit ist `max(Median-t30, Median-Laufzeit/2)` statt rohem t30:
   die echten Kurven kollabieren im Intro (unter 30 % nach 0:45 von 10:54)
   — rohes t30 hätte 0.8 min / 50 Wörter gefordert und der Loop
   (kürzer → früheres t30 → noch kürzer) liefe gegen null. Die /2-Klausel
   ist Schleifendämpfung (max. Halbierung pro Iteration), kein Richtwert.

**Offen:** Stichprobe ist winzig (12–25 Views je Video) — der Block sagt
das als "treat as directional" dazu. Ein transienter Data-API-500 kann
eine Tagesdatei ohne Kurven hinterlassen (beobachtet beim Testen); der
Konsument fällt dann auf die nächstältere frische Messung zurück.
