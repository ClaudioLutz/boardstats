# /biz/-Lagebericht 2026-08-09

*Datenstand: 09.08.2026 12:56 Ortszeit (Europe/Zurich), 15 ausgewertete Threads.*

[Extrakte und Quell-Threads dieses Tages](README.md)

---

## BITCOIN: DIE KETTE HAT SICH TATSÄCHLICH GESPALTEN

Die wichtigste Neuigkeit des Tages: Der Soft Fork BIP-110 wurde per UASF aktiviert, und die Bitcoin-Knots-Kette hat sich rund um Block 961'632 von der Core-Kette getrennt. Streitgegenstand ist, ob beliebige Daten wieder per Konsensregel aus der Blockchain verbannt werden sollen, nachdem Core ab Version 30 die Begrenzung der OP_RETURN-Datenfelder aufgehoben hat.

Die abgespaltene Kette steht schlecht da:

- 15 bis 25 Stunden lang wurde nach der Abspaltung kein einziger Block gefunden.
- Ein Poster rechnet vor: 10 Minuten geteilt durch 0,025 mal 2'016 Blöcke ergibt rund 1,5 Jahre bis zur nächsten Schwierigkeitsanpassung, weil die Schwierigkeit pro Periode höchstens 75 Prozent fallen darf.
- Die Miner-Signalisierung für BIP-110 liegt laut einem Poster bei 1 Prozent.

Der Eröffnungsposter hält dagegen, macht einen "Angriff" des Mining-Pools AntPool verantwortlich und beansprucht den Namen Bitcoin für seine Kette. Alle genannten Node- und Hashrate-Anteile sind unbelegt und widersprechen sich im Zeitverlauf. Praktisch heisst das für Halter: zwei Ketten existieren parallel, Bestätigungen auf der Minderheitskette tragen ein Wipeout-Risiko.

Zweiter Strang: eine laufende Diebstahlwelle bei Coldcard-Hardware-Wallets, laut Postern durch schwache Zufallszahlen in der Firmware (Mk3, teils Mk4 mit Passphrase). Empfohlen wird, beim Umzug auf einen neuen Seed das gesamte Guthaben in einer Transaktion mit hoher Gebühr zu sweepen; Knots kennt dafür die Einstellung mempoolreplacement=0, Core nicht. Als Alternative wird SeedSigner genannt, dem ein anderer Poster wegen Finanzierung durch die Human Rights Foundation eine mögliche Backdoor unterstellt — unbelegt. Belege: bip110.org, github.com/bitcoinknots/bitcoin (Release Notes v29.3.knots20260508), Pull Requests #34929 und #34930 auf github.com/bitcoin/bitcoin.
Verlässlichkeit: ein einzelner Poster dominiert den Thread, neue unbelegte Spekulationen über KI-gesteuerte Börsen- und Konsensangriffe nehmen zu. Keine Referral-Links, keine Kursziele.
https://boards.4chan.org/biz/thread/62508806

## MONERO UND XRP

Bei Monero (XMR) läuft unverändert der Streit um das Upgrade aus CARROT und FCMP++. Die These: erweiterte View Keys machten Monero regulatorisch prüfbar und damit für Binance und Coinbase wieder listbar, Preis dafür sei die Privatsphäre. Die Gegenseite hält fest, dass View Key plus Key Images schon heute dieselbe Prüfbarkeit erlauben und das eigentliche Hindernis die Geldwäschevorschriften sind. Genannte Kursziele (2'000, 5'000, 10'000 USD) sind reine Behauptungen.

Neu und praktisch verwertbar ist nur eine Warnung: Ein Poster verlor 150 USD in XMR beim Versuch, über coincards.com beziehungsweise cakepay.com eine Geschenkkarte zu beziehen, und erhielt nichts. Beide Dienste stehen im Eröffnungsbeitrag als Empfehlung. Ausserdem im Umlauf: eine Netzwerkschwachstelle beim Betrieb eines Monero-Knotens über Tor (Quelle: x.com/KuptoKosmos), Kryptografie und Transaktionsinhalte sind laut derselben Quelle nicht betroffen.
https://boards.4chan.org/biz/thread/62521292

Bei XRP dreht sich alles um den US-Clarity Act. Laut verlinktem Politico-Artikel vom 06.08.2026 haben die Senatsrepublikaner die Abstimmung bis nach der Sommerpause verschoben; das Repräsentantenhaus tagt ab 31. August wieder. Ein Poster erwartet selbst bei Verabschiedung nur einen kurzen Sprung von 11 bis 12 Prozent und danach einen Rückfall unter 1 USD. Achtung: ein Beitrag zu einer OKX-Aktion (3,5 Prozent plus 5 Prozent Bonus auf Stablecoins) enthält einen Referral-Link, also klares Eigeninteresse.
https://boards.4chan.org/biz/thread/62527074

## EDELMETALLE UND ROHSTOFFE

Im neuen /smg/-Thread nennt ein einzelner Poster konkrete Kursziele: rund 6'500 USD für Gold und 150 USD für Silber in "Leg 2", begründet mit US-Haushaltsdefiziten, Fed-Lockerung, negativen Realzinsen, schwächerem Dollar und Zentralbankkäufen. Ein anderer erwartet 120 USD Öl "bis nächste Woche", ohne jede Begründung. Beides sind Einzelmeinungen ohne Threadkonsens.
https://boards.4chan.org/biz/thread/62577108

Im Edelmetall-Sammelthread ist die verwertbarste Neuigkeit rechtlicher Natur: Ein US-Bürger wurde zu 15 Jahren Haft verurteilt, weil er Angestellte in Gold und Silber statt in Fiatgeld bezahlte; steuerlich zählte der aufgeprägte Nennwert, nicht der Metallwert (Quelle: reviewjournal.com). Praktisch unterscheiden Poster neu zwischen 999er-Feinsilber für Liquidität und Bulk-Verkauf und Junk Silver für Tauschzwecke. Ein Optionshändler meldet 400 Prozent auf SLV-Calls und erwartet ein Top um 130.
Verlässlichkeit: Eine einzelne Poster-ID betreibt durchgehend Anti-Silber-Werbung und bewirbt stattdessen die Aktie NOG (rund 10 Prozent Dividendenrendite) — erkennbares Eigeninteresse. Die Makro-Aussagen zum Yen-Carry-Trade bleiben unbelegt.
https://boards.4chan.org/biz/thread/62569919

## AKTIEN

Die inhaltlich dichteste Aktien-Diskussion ist neu und betrifft Halbleiter. Ein Poster erklärt ASMLs Margen mit einer echten Technologiemonopolstellung bei fortschrittlicher Lithographie; Nikon habe trotz Milliardeninvestitionen keinen Marktanteil gewonnen. Ein zweiter trennt Logic-Chips (NVDA, AMD, lithographieintensiv) von Memory-Chips (ätzintensiv): Memory habe mehr Wachstumsspielraum und geringeres Risiko, sei aber langfristig eine Geschichte sinkender Margen. Er selbst gewichtet trotzdem Logic höher — und legt diese Abweichung von seiner eigenen Analyse offen.

Weitere konkrete Punkte aus demselben Thread:

- Prüfregel für Micro-Caps: unter rund 500 Mio. USD Marktkapitalisierung verbrennen die meisten Firmen Kapital; zuerst Bilanz und Verwässerungshistorie prüfen, wiederholt verschobene Profitabilitätsversprechen sind ein Ausstiegssignal.
- Genannte Einzelwerte: Radcom (Kurs rund 10 USD, davon rund 7 USD Netto-Cash je Aktie), Dundee Corp (rund 40 Prozent unter Nettoinventarwert), Geodrill.
- Bayhorse Silver wird von zwei Postern unabhängig als Betrugsfall bezeichnet — unbelegt.
- SpaceX (im Thread als SPCX) legte an einem Tag 15 Prozent zu und bekommt erstmals fundamentale Gegenrede: kein Gewinnausweis.

Die Substanz zu Micro-Caps stammt praktisch vollständig von einem Poster, der offenlegt, selbst investiert zu sein.
https://boards.4chan.org/biz/thread/62574359

Im älteren /smg/-Thread dominiert die Frage, ob man Hebel-ETFs halten soll. Pro: TQQQ stieg von 2,50 (2017) auf über 70. Contra: das tägliche Rebalancing vernichtet Wert, gerechnet am Beispiel QQQ 100 auf 90 auf 99 (netto 99) gegen TQQQ 100 auf 70 auf 91 (netto 91). Als Alternative für längerfristigen Hebel werden tief im Geld liegende, langlaufende Calls genannt. Daneben eine Inflationsrechnung: S&P 500 von 2'500 (2018) auf 7'700, Burritopreis von 7,50 auf 20 USD, Medianlohn von 46'000 auf 64'000 USD — real also nur rund 15 Prozent Zuwachs. Die 20-USD-Zahl wird von anderen Postern bestritten. Eine Vuzix-Empfehlung eines Einzelposters wirkt werbeähnlich.
https://boards.4chan.org/biz/thread/62575855

Zur Frage, wie man rund 178'667 USD in zehn Jahren auf eine Million bringt, liefert ein Poster die nüchternste Antwort: nötig wären 18,8 Prozent Rendite pro Jahr; bei 17 Jahren genügen 10,7 Prozent.
https://boards.4chan.org/biz/thread/62560584

## GAMESTOP UND BED BATH & BEYOND

Neu und mit Zahlen unterlegt ist die Debatte, ob sich GameStops geplanter Aktienrückkauf über 2 Mrd. USD und die möglichen 2 Mrd. USD Erlöse aus der Warrant-Ausübung (Strike 32 USD, Verfall 30.10.2026) gegenseitig aufheben. Ein Poster sagt ja, ein zweiter verneint, ein dritter weist darauf hin, dass eine Ausübung durch das Unternehmen selbst nur die Aktienzahl erhöht, ohne Geld zuzuführen. Keine Seite legt eine Modellrechnung vor. Ebenfalls abgeschwächt wurde die eBay-Übernahmespekulation, nachdem ein Yahoo-Finance-Artikel ein mögliches Engagement Carl Icahns bei eBay meldete.
https://boards.4chan.org/biz/thread/62574156

Zur BBBYQ-These gibt es nichts Belastbares. Der Skeptiker rechnet vor, dass der BBBY-Kurs von 4,57 USD um 240 bis 250 Prozent steigen müsste, damit die Warrants (Strike 15,50 USD, Verfall 07.10.2026, aktuell 34 Cent) nicht wertlos verfallen. Im parallelen /GME/-Thread bleibt der Einwand offen, ein SPAC-Zusammenschluss sei ja gerade die Fusion einer Gesellschaft mit Aktien mit einer ohne. Beide Threads bestehen fast nur aus wiederholten Standpunkten weniger IDs; ein Poster nennt seinen Thread selbst "ragebait".
https://boards.4chan.org/biz/thread/62546934 und https://boards.4chan.org/biz/thread/62536149

## GERADE SCHNELL FÜLLENDE THREADS

Ein Thread zur Frage, wie man 10 Mio. USD in Krypto steuerfrei auszahlt, füllt sich mit 2,5-fachem Tempo des eigenen Schnitts. Inhaltlich diskutiert werden drei Wege: Stablecoins in einen Trust legen und dagegen Kredite aufnehmen, Verkauf direkt an Privatpersonen statt über eine Börse, sowie Umzug in eine Steueroase. Mehrere Poster halten dagegen, dass US-Bürger unabhängig vom Wohnort steuerpflichtig bleiben und Transaktionsketten rückverfolgbar sind; ein Poster schätzt die Steuerlast bei Verbleib in den USA auf rund 50 Prozent und hält den Zugang zum US-Aktienmarkt für wertvoller. Der Thread ist laienhaft, aber ernst gemeint.
https://boards.4chan.org/biz/thread/62577203

Ein zweiter Thread wächst mit doppeltem Tempo und behandelt Chainlink (LINK). Substanz gibt es kaum: Ein Poster behauptet unbelegt, LINK sei das einzige Oracle mit den Sicherheitsstandards der Wall Street und man werde bald "ausgepreist"; ein anderer erklärt den niedrigen Kurs mit fehlender Nachfrage, ein dritter mit ausgetrockneter Marktliquidität nach einem Bitcoin-Rückgang. Keine Zahlen, keine Quellen.
https://boards.4chan.org/biz/thread/62576360

## GLOSSAR

/smg/ - Kürzel für "stock market general", die fortlaufende Threadserie zum Aktienmarkt
BBBYQ - Tickerkürzel der annullierten, außerbörslich (OTC) gehandelten Alt-Aktie der insolventen Bed Bath & Beyond, Inc.
BIP - Bitcoin Improvement Proposal, standardisierter Vorschlag zur Änderung von Bitcoin.
CARROT - geplantes neues Adress- und Transaktionsformat fuer Monero, benannt nach seiner Spezifikation; Streitpunkt sind die darin erweiterten Lese-Schluessel.
Clarity Act - in den USA diskutiertes Gesetz zur regulatorischen Einordnung von Digital Assets
CSAM / CBDC / MiCA / Clarity Act - Darstellungen von Kindesmissbrauch als rechtliches Risiko für Node-Betreiber / digitales Zentralbankgeld / EU- bzw. US-Regulierung, vom OP als Bedrohung der Selbstverwahrung angeführt.
FCMP++ - "Full-Chain Membership Proofs", ein neues Nachweisverfahren, bei dem ein Transaktionseingang nicht mehr nur mit einer kleinen Gruppe Scheinbeteiligter, sondern gegen alle bisherigen Ausgaben der Kette verschleiert wird.
fiat / Fiatgeld - staatlich gesetztes Geld ohne Sachwertdeckung
Hashpower / Hashrate - Rechenleistung eines Miners.
Hashrate / EH/s / ASIC / Mining Pool - Rechenleistung im Mining / Exahashes pro Sekunde / dafür gebaute Spezialchips / Zusammenschluss von Minern, der gemeinsam Blöcke baut.
junk silver - kursierte US-Umlaufmünzen bis 1964 mit 90% Silberanteil, gehandelt nach Metallwert
Knots / Core - die beiden konkurrierenden Bitcoin-Node-Programme; Anhänger der jeweils anderen Seite beschimpfen sich im Thread, teils mit ethnischen und persönlichen Verunglimpfungen, die hier nicht wiedergegeben werden.
Leg (hier "Leg 1/2/3") - Chart-Jargon für eine einzelne Phase/Welle einer grösseren Kursbewegung.
Lithographie - fotochemisches Strukturierungsverfahren für Halbleiter-Wafer, entscheidend für die Leistungsfähigkeit moderner Chips
Memory - hier Speicherchips (Arbeitsspeicher, Flash) beziehungsweise die Aktien ihrer Hersteller.
Netto-Cash je Aktie - Bargeldbestand abzüglich Schulden je Aktie
Node - ein Rechner, der die Blockchain vollstaendig vorhaelt; Tor ist das Anonymisierungsnetzwerk, ueber das er betrieben werden kann.
OP_RETURN / datacarriersize - Feld für nicht ausgebbare Daten in einer Transaktion / Einstellung zur Begrenzung seiner Grösse.
