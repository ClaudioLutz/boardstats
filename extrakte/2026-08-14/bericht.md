# /biz/-Lagebericht 2026-08-14

*Datenstand: 14.08.2026 07:20 Ortszeit (Europe/Zurich), 15 ausgewertete Threads.*

[Extrakte und Quell-Threads dieses Tages](README.md)

---

## BITCOIN: DIE KETTENSPALTUNG IST EINGETRETEN

Aus dem Grundsatzstreit ist eine Tatsache geworden. Die Kette mit BIP-110 (umgesetzt in der Node-Software Bitcoin Knots, verbietet das Einbetten beliebiger Daten) hat sich per UASF von der Core-Kette getrennt. Anschliessend produzierte sie über Stunden keinen Block mehr.

- Abspaltung rund um Block 961'632 beziehungsweise 961'633; ab Block 965'664 lehnt ein BIP-110-Node zusätzlich die betroffenen Transaktionen ab.
- 15, später 25 Stunden ohne einen einzigen Block auf der abgespaltenen Kette.
- Miner-Signalisierung für BIP-110: 1 Prozent.
- Rechnung eines Kritikers: bei dieser Hashrate dauert es rund 1,5 Jahre bis zur nächsten Schwierigkeitsanpassung, weil die Schwierigkeit pro Periode höchstens um 75 Prozent fallen darf. Er hält die Kette damit für tot.
- Der Eröffnungsposter widerspricht und macht einen Angriff des Mining-Pools AntPool verantwortlich. Unbelegt.

Praktisch heisst das für Halter: Es gibt zwei Ketten. Guthaben und Transaktionen rund um die Abspaltungshöhe sind getrennt zu behandeln, Bestätigungen auf der Minderheitskette tragen ein Wipeout-Risiko.

Parallel läuft eine Diebstahlwelle bei Coldcard-Hardware-Wallets, laut Postern durch schwache Zufallszahlen in der Firmware (Mk3, teils Mk4, auch mit Passphrase). Der Angriffsweg: Bei einer Multisig-Ausgabe werden öffentliche Schlüssel sichtbar, danach ersetzt der Angreifer die Transaktion per RBF durch eine höher bezahlte. Empfohlenes Gegenmittel: das gesamte Guthaben in einer einzigen Transaktion auf einen neuen Seed sweepen, ausreichend Gebühr für den nächsten Block, nach Möglichkeit direkt bei einem Pool mit First-seen-Politik einreichen; Knots kennt dazu mempoolreplacement=0, Core nicht. Als Alternative wird SeedSigner genannt, gegen das ein anderer Poster wegen der Finanzierung durch die Human Rights Foundation einen unbelegten Backdoor-Verdacht äussert.

Quellen im Thread: bip110.org, die Knots-Release-Notes v29.3.knots20260508, die am Einreichungstag geschlossenen Core-Pull-Requests #34929 und #34930. Verlässlichkeit: ein einzelner Poster dominiert den Thread, alle Node- und Hashrate-Anteile sind unbelegt und widersprechen sich. Keine Referral-Links, aber deutliche Werbung für eine Position samt Node-Software.

## HALBLEITER UND SPEICHER

Der Speicherzyklus ist das dichteste Aktienthema des Tages, und die Poster belegen ihn erstmals mit Endkundenpreisen.

- 139 Dollar Ausverkaufspreis für eine 1-TB-NVMe-SSD; ein anderer Poster nennt 99 Dollar für 2 TB als Schwelle, ab der sich die Preise wieder entspannen.
- Ein Poster nutzt fallende Einzelhandelspreise ausdrücklich als Ausstiegssignal für seine NAND-Wette auf SanDisk (SNDK).
- Argument dafür: NAND werde unabhängig vom KI-Hype gebraucht, und Endkunden-Flash lasse sich anders als Server-RAM leicht weiterverkaufen.
- Micron: genannter Boden 700 Dollar, Kursziel 2'100 Dollar bis Anfang nächsten Jahres. Ein anderer Poster behauptet, der Kurs falle nie mehr unter 900 Dollar. Beides unbelegt und untereinander unstimmig.
- Neu ist Chinas YMTC: laut zitierten Zahlen von Counterpoint Research im zweiten Quartal auf Platz 3 des globalen Speicherabsatzes, hinter Samsung und SK Hynix, vor Micron und Kioxia. Eine Seite liest das bullisch (stärkeres Preiskartell), eine andere bärisch (mehr Angebot), eine dritte hält es für irrelevant, weil chinesische GPUs AMD und Nvidia nur ein bis zwei Quartale Marge gekostet hätten.

## MAKRO: YEN, ANLEIHEN UND ZÖLLE

Die ernsthafteste Makro-Debatte dreht sich um Japan. Ein Poster führt die seit rund 18 Jahren steigende US-Marktentwicklung auf billige Kredite in Yen zurück und erwartet bei weiter steigenden japanischen Renditen einen Zwangsverkauf; er rechnet mit 80 bis 150 Basispunkten zusätzlichem Zinsanstieg. Die Gegenrede: ein Kollaps bräuchte gleichzeitig Zinsanstieg, Yen-Aufwertung, US-Einbruch und eine asiatische Liquiditätskrise.

- Der Yen steht wieder bei 160 zum Dollar; ein Poster wertet die Intervention als gescheitert, ein anderer entgegnet, Ziel sei nur ein Boden gewesen, kein starker Anstieg.
- Ein Poster hält japanische Staatsanleihen für praktisch unverkäuflich und schätzt, der Dollar müsste um rund 70 Prozent abwerten, um gegenüber China wettbewerbsfähig zu sein. Unbelegt.
- Zitiertes Trump-Statement: die Zollfreigrenze von 800 Dollar für Kleinimporte ("de minimis") ist nach einem Urteil des U.S. Court of International Trade aufgehoben; genannt werden 10'800'000'000 Dollar entgangene Zolleinnahmen für 2024.
- Bloomberg-Schlagzeile im Thread: 100 Prozent Zölle auf bestimmte Drohnen aus China.
- Laut WSJ soll die US-Navy beim vierten Ford-Träger auf das elektromagnetische Katapult EMALS verzichten und zu Dampfkatapulten zurückkehren; ein weiterer WSJ-Bericht meldet einen zusätzlichen Flugzeugträger im Nahen Osten, den ein Teil der Poster als turnusmässige Ablösung einordnet.

## EINZELWERTE

- Reddit (RDDT) wird in den S&P 500 aufgenommen, laut Poster nachbörslich 15 Prozent im Plus. Kaufargument: erzwungene Indexkäufe durch Pensions- und 401k-Gelder. Gegenstimmen halten den Titel schlicht für schlecht.
- Canadian Natural Resources (CNQ) als Öl-Wette: viel Heavy-Sour-Öl für Diesel, sichere Jurisdiktion, ausgebaute Pipelines.
- IREN und Nebius (NBIS) werden als "Visa und Mastercard der Neoclouds" bezeichnet, weil sie die Preise für Rechenleistung hochhalten; CoreWeave gilt demgegenüber als schuldenbelastet.
- Virgin Galactic (SPCE) nennt ein Poster wegen wiederholt verschobener Flüge eine Betrugsfirma. Einzelmeinung ohne Beleg.
- Mehrere Poster behaupten unbelegt, Anthropics Claude-Modelle seien in den letzten Wochen gedrosselt worden und hätten ein kürzeres Kontextfenster; als Grund vermuten sie Kapazitätsengpässe durch stark gestiegene Nutzerzahlen.

## WENDY'S: SQUEEZE-AUFRUF MIT ZAHLEN DAGEGEN

Ein Thread bewirbt einen Short Squeeze bei der Fast-Food-Kette Wendy's und behauptet, Reddit habe eine entsprechende Retail-Bewegung aus den grossen Finanz-Subreddits gelöscht. Die einzigen belastbaren Zahlen sprechen gegen die These: Die Short-Quote liegt laut einem Poster bei 37 Prozent des Streubesitzes gegenüber 250 Prozent bei GameStop 2021; derselbe Poster verlor Geld mit Hertz bei einer Quote von 69 Prozent, ohne dass ein Squeeze eintrat. Verlässlichkeit: Der Eröffnungsposter wiederholt seine These über den ganzen Thread, das deutet auf eigenes Interesse an einer Kursbewegung.

## EDELMETALLE

Der Sammelthread wird von einem einzelnen bärischen Poster dominiert, der Silber unter 13 Dollar fallen sieht, einen täglichen Angebotsüberschuss von 1'800'000 Unzen behauptet und Gold seit 1980 um 58 Prozent im Wert gefallen sieht. Er liefert trotz mehrfacher Nachfrage keinen Beleg, auch nicht für seine eigene Rendite von 15 Prozent pro Jahr. Der einzige harte Datenpunkt kommt von der Gegenseite: Der Händler Summit Metals verlangt für Libertads 20 Dollar Aufgeld über Spot, was auf angespannte physische Verfügbarkeit hindeutet.

## KRYPTO KURZ

Chainlink-Streit um Payment Abstraction: Neu ist nur der Einwand, ein Marktkauf von LINK sei gar nicht nötig, wenn die Node-Zahlungen direkt aus Wallets von Chainlink Labs stammten; dagegen wird gehalten, das Verfahren kaufe die Token tatsächlich über Uniswap. Zur Standard-Chartered-Prognose kam hinzu, dass der Report als Ausgangskurs 8 Dollar nennt, woraus Kritiker für das Ziel von 200 Dollar bis 2030 nur 3,84-fache Rendite in neun Jahren errechnen.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

## UNVERÄNDERT SEIT GESTERN

SpaceX-Aktie (S-1 schliesst Dividenden und Rückkäufe aus, Starlink profitabel, 40 Prozent Kursrisiko je Raketenexplosion, Rückkehr auf 200 Dollar strittig): unverändert. Im Tagesthread werden dazu nur Kursmarken gehandelt, Stop-Loss bei 135 Dollar, ein zitiertes Analystenziel von 800 Dollar auf Jahressicht.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

Tod von Harry Yeh und die Sicherheitsratschläge für Krypto-Vermögende (Personenschutz ab rund 50 Mio. Dollar, Online-Präsenz löschen): unverändert.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

Managed-Futures-ETFs (DBMF und Verwandte, Brutto-Exposure 2 bis 4 Dollar je investiertem Dollar bei rund 1,50 Dollar gerichtetem Risiko) sowie der Free-Cash-Flow-Vergleich Apple gegen Tesla (3,26 gegen 0,54 Prozent): unverändert.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

## GERADE SCHNELL FÜLLENDE THREADS

- Der Wendy's-Thread läuft mit dem Doppelten seines eigenen Schnitts; Inhalt oben.
- Der Edelmetall-Sammelthread läuft mit dem 1,5-Fachen seines Schnitts; getragen wird das fast ausschliesslich vom oben beschriebenen Schlagabtausch sowie von Berichten über Münzkäufe (Gold-Sovereign von 1899, belgische 20-Francs-Münze über MonumentMetals.com, ein 40-Prozent-Silber-Half-Dollar aus dem Durchsuchen von Münzrollen).
- Neu und auffällig aktiv ist ein Thread zu PEPE: Ein Poster behauptet, der Meme-Coin sei für das erste Quartal 2025 für eine Verzehnfachung bereit gewesen und der Sektor sei dann eingebrochen; zwei Gegenstimmen halten ausgelaufene Meme-Coins grundsätzlich für verloren. Keine Zahlen, keine Quellen.
- Ebenfalls neu ist ein Thread, in dem jemand US-Staatsanleihen gegen niedriger verzinste Anleihen Singapurs getauscht haben will, ohne Begründung. Ausser abwertenden Kommentaren steht nichts darin.
- Der jüngste /smg/-Thread füllt sich mit nur 0,3-fachem Tempo seines eigenen Schnitts, obwohl er in absoluten Zahlen der aktivste ist; seine Inhalte stehen oben.

## GLOSSAR

- /smg/ - wiederkehrender Sammelthread zu Aktien auf dem Board /biz/
- 401k - US-amerikanisches arbeitgebergefoerdertes Altersvorsorgekonto, oft mit prozentualem "Match" durch den Arbeitgeber.
- Aufgeld/Premium - Aufschlag auf den Spotpreis, den Haendler beim Verkauf von Muenzen/Barren verlangen.
- BIP - Bitcoin Improvement Proposal, standardisierter Vorschlag zur Änderung von Bitcoin.
- EMALS - Electromagnetic Aircraft Launch System, elektromagnetisches Katapultsystem für Flugzeugträger.
- Hashrate / EH/s / ASIC / Mining Pool - Rechenleistung im Mining / Exahashes pro Sekunde / dafür gebaute Spezialchips / Zusammenschluss von Minern, der gemeinsam Blöcke baut.
- Knots / Core - die beiden konkurrierenden Bitcoin-Node-Programme; Anhänger der jeweils anderen Seite beschimpfen sich im Thread, teils mit ethnischen und persönlichen Verunglimpfungen, die hier nicht wiedergegeben werden.
- LINK - nativer Token des Chainlink-Netzwerks (Oracle-Dienst, verbindet Blockchains mit externen Daten).
- Mempool / RBF / Full-RBF / First-seen - Warteschlange unbestätigter Transaktionen / Ersetzung durch höhere Gebühr / uneingeschränkte Variante davon / Gegenpolitik, die die zuerst gesehene Transaktion behält.
- Neoclouds - neuere Cloud-Computing-Anbieter, die Rechenleistung (v.a. GPUs) fuer KI-Training vermieten (z.B. CoreWeave, Nebius, IREN).
- Node - ein am Netzwerk teilnehmender Rechner, der hier für die Datenübermittlung bezahlt wird.
- Reorg / Wipeout - nachträgliches Verwerfen bereits geminter Blöcke samt ihrer Belohnungen und Bestätigungen.
- short squeeze - Situation, in der Leerverkaeufer gezwungen werden, ihre Position durch Rueckkauf zu schliessen, was den Kurs weiter nach oben treibt
- UASF / MASF / URSF - Aktivierung einer Regel durch Nutzer-Nodes ohne Miner-Mehrheit / durch Miner-Mehrheit / aktive Ablehnung einer Aktivierung.
