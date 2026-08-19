---
datum: 2026-08-19
agent: main
typ: docs
commit: <wird beim Commit ergänzt>
---

# Overseer-Skill: Font-Bereitstellung auf hp-ubuntu verifiziert und dokumentiert

**Was:** `.claude/skills/pipeline-overseer/SKILL.md` — neuen Abschnitt zu
`assets/fonts/` ergänzt: die vier eigenen Schriften (SpaceGrotesk-Bold,
Inter-Regular, Inter-Medium, IBMPlexMono-Bold) sind git-tracked und werden
repo-relativ über `thumbnail.FONT_DIR` geladen, keine System-Font-
Installation auf hp-ubuntu nötig. Zusätzlich vermerkt, dass `aktivitaet.py`
(der neue Balkengrafik-Chart) laut eigenem Docstring noch nicht in
`video_report.py` verdrahtet ist.

**Warum:** Nutzerfrage "sind die Schriften auf hp-ubuntu auch installiert?"
— Overseer-Pflicht, produktive Annahmen zu belegen statt zu vermuten
(vgl. Memory zur pytest-Falle vom 19.08.). Geprüft: `git log`/`ls` auf
hp-ubuntu bestätigt alle vier `.ttf`-Dateien vorhanden (Commit `556aef9`),
`PIL.ImageFont.truetype()` lädt sie dort fehlerfrei. Zusätzlich per
Pixelvergleich (belichtete Pixel bei identischem Text) bestätigt, dass
Inter-Medium tatsächlich fetter rendert als Inter-Regular (2'251 vs. 1'922),
obwohl die interne Namenstabelle beider Dateien fälschlich "Regular"
meldet (`getname()`) — ein kosmetisches Metadaten-Artefakt aus dem
Variable-Font-Export, kein Rendering-Bug.

**Auswirkung:** Keine Code-Änderung. Klarstellung im Skill, damit künftige
Überprüfungen nicht erneut denselben Sachverhalt herleiten müssen und die
"getname() sagt Regular"-Beobachtung nicht fälschlich als Bug gemeldet wird.

**Offen:** —
