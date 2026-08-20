---
datum: 2026-08-20
agent: main
typ: docs
commit: <wird beim Commit ergänzt>
---

# Overseer-Skill: sechs neu deployte Features nachgetragen

**Was:** `.claude/skills/pipeline-overseer/SKILL.md` um die Commits seit dem
letzten Abgleich (`ea9c56c`) ergänzt:

- **Testlauf-Isolation** (`c33885c`) und **Delta-Zustand-Guards**
  (`2bb3bf6`/`43d3fac`) in "Testvideos generieren" dokumentiert: Testlauf-
  Ausgaben liegen jetzt unter `arbeit/<stamp>-test/`, Cache/Sperrlisten/
  Katalog-Stempel bleiben unter Testflags unberührt.
- Neuer "Geklärte Fälle"-Eintrag zum eigenen Vorfall: meine drei
  Overseer-Testläufe vom 19.08. (14:49/20:12/20:25) haben den Delta-Zustand
  der Produktion ca. zwölf Stunden nach vorne geschoben und mussten von
  Hand zurückgerollt werden (`258506a`) — jetzt durch die obigen Guards
  behoben.
- Neuer "Geklärte Fälle"-Eintrag zum YouTube-Metadaten-Bug
  (`e0cad36`/`57763f8`): `videos.update` mit unvollständigem `status`-Part
  hatte `embeddable`/`publicStatsViewable` auf `false` zurückgesetzt; Fix
  per Read-Modify-Write, verallgemeinerte Lehre zur YouTube-API ergänzt.
- Neuer "Geklärte Fälle"-Eintrag zur Absatz-Abdeckungsprüfung (`4810739`):
  erklärt lange stichwortlose Strecken im Video vom 19.08. und den seither
  eingebauten Nachtrag-Mechanismus.
- Betriebswerte aktualisiert: Testanzahl 61→149, TTS-Kontingent 12→16.1 %,
  neue Kaltstart-/Fragment-Timingwerte aus `50621da`.

**Warum:** Nutzerauftrag "schaue dir die neu gepushten deployeten features
an. Update den overseerskill mit diesen informationen wo sinnvoll" — Teil
der stehenden Pflicht, das Skill-Dokument nach jeder Overseer-relevanten
Erkenntnis zu erweitern statt nur im Gedächtnis zu behalten.

**Auswirkung:** Keine Code-Änderung. Das neu deployte Designsystem
(`a1c78b1`) war bereits vor dieser Session per Memory dokumentiert und
wurde deshalb nicht erneut aufgenommen; die Worktree-Pflicht-Verankerung
(`9118581`) ist reine CLAUDE.md-Doku ohne Pipeline-Bezug.

**Offen:** Der Delta-Zustand-Guard (`2bb3bf6`/`43d3fac`) war laut eigener
Story-Datei am 20.08. im Feld noch nicht bestätigt — beim nächsten
Testlauf die mtime-Gegenprobe nachholen (siehe SKILL.md).
