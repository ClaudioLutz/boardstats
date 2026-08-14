# /biz/ Situation Report 2026-08-14

*Data as of: 14.08.2026 07:20 local time (Europe/Zurich), 15 threads analyzed.*

[Extracts and source threads for this day](README.md)

---

## BITCOIN: THE CHAIN SPLIT HAS HAPPENED

What was a theoretical dispute has become fact. The chain running BIP-110 (implemented in the node software Bitcoin Knots, which blocks embedding arbitrary data) has split off from the Core chain via UASF. It then failed to produce a single block for hours.

- Split occurred around block 961,632 / 961,633; starting at block 965,664 a BIP-110 node additionally rejects the affected transactions.
- 15, later 25 hours without a single block on the forked chain.
- Miner signaling for BIP-110: 1 percent.
- One critic's calculation: at this hashrate it will take roughly 1.5 years to reach the next difficulty adjustment, since difficulty can drop by at most 75 percent per period. He considers the chain dead.
- OP disagrees and blames an attack by the mining pool AntPool. Unsubstantiated.

In practical terms for holders: there are now two chains. Balances and transactions around the split height need to be treated separately, and confirmations on the minority chain carry a wipeout risk.

In parallel there's a wave of thefts from Coldcard hardware wallets, which posters attribute to weak random number generation in the firmware (Mk3, some Mk4, even with passphrase). The attack path: during a multisig spend, public keys become visible, after which the attacker replaces the transaction via RBF with a higher-fee one. Recommended countermeasure: sweep the entire balance in a single transaction to a new seed, pay enough fee for the next block, and if possible submit directly to a pool with a first-seen policy; Knots supports this via mempoolreplacement=0, Core does not. SeedSigner is mentioned as an alternative, though another poster raises an unsubstantiated backdoor suspicion due to its funding by the Human Rights Foundation.

Sources cited in the thread: bip110.org, the Knots release notes v29.3.knots20260508, and Core pull requests #34929 and #34930, which were closed on the day of posting. Reliability: a single poster dominates the thread, all node and hashrate share figures are unsubstantiated and contradict each other. No referral links, but clear promotion of a position along with a specific node software.

## SEMICONDUCTORS AND MEMORY

The memory cycle is today's densest stock topic, and for the first time posters back it up with retail prices.

- $139 sale price for a 1TB NVMe SSD; another poster cites $99 for 2TB as the threshold at which prices start easing again.
- One poster explicitly uses falling retail prices as an exit signal for his NAND bet on SanDisk (SNDK).
- Argument in favor: NAND demand is independent of the AI hype, and consumer flash, unlike server RAM, is easy to resell.
- Micron: cited floor of $700, price target of $2,100 by early next year. Another poster claims the stock will never fall below $900 again. Both unsubstantiated and inconsistent with each other.
- New today is China's YMTC: according to figures cited from Counterpoint Research, it ranked #3 globally in memory sales in Q2, behind Samsung and SK Hynix, ahead of Micron and Kioxia. One side reads this as bullish (stronger price cartel), another as bearish (more supply), a third considers it irrelevant, arguing Chinese GPUs only cost AMD and Nvidia one or two quarters of margin.

## MACRO: YEN, BONDS, AND TARIFFS

The most serious macro debate centers on Japan. One poster attributes the roughly 18-year uptrend in US markets to cheap yen-denominated borrowing and expects forced selling if Japanese yields keep rising; he expects an additional 80 to 150 basis points of rate increases. The counterargument: a collapse would require simultaneously rising rates, yen appreciation, a US downturn, and an Asian liquidity crisis.

- The yen is back at 160 to the dollar; one poster calls the intervention a failure, another counters that the goal was only to establish a floor, not a strong rally.
- One poster considers Japanese government bonds essentially unsellable and estimates the dollar would need to devalue by roughly 70 percent to be competitive with China. Unsubstantiated.
- Quoted Trump statement: the $800 de minimis tariff exemption for small imports has been struck down following a ruling by the U.S. Court of International Trade; $10,800,000,000 in lost tariff revenue for 2024 is cited.
- Bloomberg headline in the thread: 100 percent tariffs on certain drones from China.
- Per WSJ, the US Navy is reportedly dropping the EMALS electromagnetic catapult system on the fourth Ford-class carrier in favor of returning to steam catapults; a separate WSJ report notes an additional carrier deployed to the Middle East, which some posters characterize as a routine rotation.

## INDIVIDUAL STOCKS

- Reddit (RDDT) is being added to the S&P 500, reportedly up 15 percent after hours. Bull case: forced index buying from pension and 401k money. Bears simply consider the stock bad.
- Canadian Natural Resources (CNQ) as an oil play: plenty of heavy sour crude for diesel, safe jurisdiction, built-out pipelines.
- IREN and Nebius (NBIS) are called the "Visa and Mastercard of the neoclouds" because they keep compute prices elevated; CoreWeave, by contrast, is seen as debt-laden.
- One poster calls Virgin Galactic (SPCE) a scam company due to repeatedly delayed flights. A single, unsubstantiated opinion.
- Several posters unsubstantiatedly claim Anthropic's Claude models have been throttled in recent weeks with a shorter context window, speculating this is due to capacity constraints from sharply increased user numbers.

## WENDY'S: SQUEEZE CALL WITH NUMBERS AGAINST IT

A thread is promoting a short squeeze on the fast food chain Wendy's, claiming Reddit deleted a related retail movement from the major finance subreddits. The only solid numbers in the thread actually argue against the thesis: short interest sits at 37 percent of float according to one poster, versus 250 percent for GameStop in 2021; the same poster lost money on Hertz at a 69 percent short interest without a squeeze materializing. Reliability: OP repeats his thesis throughout the thread, suggesting a vested interest in a price move.

## PRECIOUS METALS

The general thread is dominated by a single bearish poster who sees silver falling below $13, claims a daily oversupply of 1,800,000 ounces, and believes gold has lost 58 percent of its value since 1980. Despite repeated requests, he provides no evidence, not even for his own claimed 15 percent annual return. The only hard data point comes from the other side: dealer Summit Metals is charging a $20 premium over spot for Libertads, suggesting tight physical availability.

## CRYPTO SHORT TAKES

Chainlink Payment Abstraction dispute: the only new wrinkle is an objection that a market buy of LINK isn't actually necessary if node payments come directly from Chainlink Labs wallets; against this it's argued the process does actually buy the tokens via Uniswap. On the Standard Chartered forecast, it emerged that the report cites $8 as the starting price, from which critics calculate only a 3.84x return over nine years for the $200 target by 2030.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

## UNCHANGED SINCE YESTERDAY

SpaceX stock (S-1 excludes dividends and buybacks, Starlink profitable, 40 percent price risk per rocket explosion, return to $200 disputed): unchanged. Today's daily thread only trades price levels, stop-loss at $135, a cited analyst target of $800 on a one-year view.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

Death of Harry Yeh and security advice for crypto whales (personal security recommended above roughly $50 million, scrub your online presence): unchanged.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

Managed futures ETFs (DBMF and similar, gross exposure of $2 to $4 per invested dollar at roughly $1.50 of directional risk) and the free cash flow comparison of Apple vs. Tesla (3.26 vs. 0.54 percent): unchanged.
https://github.com/ClaudioLutz/boardstats/blob/main/extrakte/2026-08-13/bericht.md

## THREADS FILLING UP FAST RIGHT NOW

- The Wendy's thread is running at twice its own average pace; content above.
- The precious metals general is running at 1.5x its average pace; this is driven almost entirely by the exchange described above plus reports of coin purchases (an 1899 gold sovereign, a Belgian 20-franc coin via MonumentMetals.com, a 40 percent silver half dollar found while searching coin rolls).
- New and notably active is a thread on PEPE: one poster claims the meme coin was primed for a 10x in Q1 2025 before the sector crashed; two dissenters consider dead meme coins fundamentally lost causes. No numbers, no sources.
- Also new is a thread where someone claims to have swapped US Treasuries for lower-yielding Singapore bonds, without explanation. Aside from disparaging comments, there's nothing else in it.
- The most recent /smg/ thread is filling at only 0.3x its own average pace, despite being the most active in absolute terms; its content is covered above.

## GLOSSARY

- /smg/ - recurring stocks general thread on the /biz/ board
- 401k - US employer-sponsored retirement savings account, often with a percentage employer "match."
- premium - markup over spot price that dealers charge when selling coins/bars.
- BIP - Bitcoin Improvement Proposal, a standardized proposal to change Bitcoin.
- EMALS - Electromagnetic Aircraft Launch System, an electromagnetic catapult system for aircraft carriers.
- hashrate / EH/s / ASIC / mining pool - computing power used for mining / exahashes per second / purpose-built chips for this / a group of miners that jointly build blocks.
- Knots / Core - the two competing Bitcoin node implementations; supporters of each side hurl insults at each other in the thread, including ethnic and personal attacks not reproduced here.
- LINK - the native token of the Chainlink network (an oracle service connecting blockchains to external data).
- mempool / RBF / full-RBF / first-seen - the queue of unconfirmed transactions / fee-based replacement / an unrestricted variant of this / the opposing policy that keeps the first-seen transaction.
- neoclouds - newer cloud computing providers that rent out compute (mainly GPUs) for AI training (e.g. CoreWeave, Nebius, IREN).
- node - a computer participating in the network, here one that gets paid for relaying data.
- reorg / wipeout - the after-the-fact discarding of already-mined blocks along with their rewards and confirmations.
- short squeeze - a situation where short sellers are forced to close their positions by buying back, driving the price up further
- UASF / MASF / URSF - activation of a rule by user nodes without miner majority / by miner majority / active rejection of an activation.
