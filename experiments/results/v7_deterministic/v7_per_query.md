# Per-Query Results — v7 (temperature 0, 75 queries)

PRR per query, using one representative condition per generator (C2 Gemini, C4 Mistral, C8 Llama 3).
Replicates within a generator are identical because the discriminator is inert, so averaging all nine adversarial conditions would triple-count each generator.

`before` = PRR before correction · `Δ` = change after correction (pp)

| Query | Type | Tier | Gemini before | Gemini Δ | Mistral before | Mistral Δ | Llama3 before | Llama3 Δ |
|---|---|---|---:|---:|---:|---:|---:|---:|
| A01 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A02 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A03 | A | two | 0% | +0 | 0% | +0 | 0% | +0 |
| A04 | A | two | 0% | +0 | 100% | -100 | 0% | +0 |
| A05 | A | single | 0% | +0 | 100% | -100 | 0% | +0 |
| A06 | A | single | 100% | +0 | 0% | +0 | 50% | +0 |
| A07 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A08 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A09 | A | two | 0% | +0 | 100% | -100 | 0% | +0 |
| A10 | A | two | 0% | +0 | 50% | +0 | 50% | -50 |
| A11 | A | two | 0% | +0 | 0% | +0 | 40% | +0 |
| A12 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A13 | A | single | 50% | +0 | 100% | -100 | 50% | +50 |
| A14 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A15 | A | single | 0% | +0 | 100% | -100 | 100% | -100 |
| A16 | A | two | 0% | +0 | 0% | +0 | 0% | +0 |
| A17 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A18 | A | two | 0% | +0 | 100% | -100 | 0% | +0 |
| A19 | A | two | 0% | +0 | 0% | +0 | 0% | +0 |
| A20 | A | two | 0% | +0 | 100% | +0 | 100% | -100 |
| A21 | A | single | 50% | +0 | 0% | +0 | 0% | +0 |
| A22 | A | two | 0% | +0 | 0% | +0 | 100% | +0 |
| A23 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A24 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A25 | A | two | 0% | +0 | 0% | +0 | 0% | +0 |
| A26 | A | single | 50% | -50 | 0% | +0 | 0% | +0 |
| A27 | A | two | 0% | +0 | 0% | +0 | 0% | +0 |
| A28 | A | two | 100% | +0 | 0% | +0 | 0% | +0 |
| A29 | A | single | 0% | +0 | 0% | +0 | 0% | +0 |
| A30 | A | two | 0% | +0 | 0% | +0 | 0% | +0 |
| B01 | B | single | 0% | +0 | 0% | +0 | 0% | +0 |
| B02 | B | single | 60% | +0 | 40% | +0 | 20% | +5 |
| B03 | B | single | 60% | +0 | 40% | -20 | 33% | +0 |
| B04 | B | single | 50% | +0 | 0% | +0 | 0% | +0 |
| B05 | B | single | 0% | +0 | 50% | -50 | 0% | +0 |
| B06 | B | single | 40% | +20 | 0% | +0 | 0% | +0 |
| B07 | B | single | 67% | +0 | 80% | -30 | 0% | +0 |
| B08 | B | single | 50% | +0 | 50% | +0 | 0% | +0 |
| B09 | B | single | 60% | +40 | 67% | -33 | 100% | -67 |
| B10 | B | single | 0% | +0 | 0% | +0 | 0% | +0 |
| B11 | B | single | 100% | +0 | 50% | -50 | 50% | -50 |
| B12 | B | single | 0% | +0 | 0% | +0 | 0% | +0 |
| B13 | B | single | 75% | -25 | 33% | +0 | 100% | +0 |
| B14 | B | single | 0% | +0 | 0% | +0 | 80% | -5 |
| B15 | B | single | 50% | +0 | 25% | +0 | 33% | +33 |
| C01 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C02 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C03 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C04 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C05 | C | three | 50% | +0 | 0% | +0 | 0% | +0 |
| C06 | C | single | 100% | +0 | 100% | -100 | 100% | +0 |
| C07 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C08 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C09 | C | single | 100% | -50 | 100% | +0 | 100% | -100 |
| C10 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C11 | C | single | 0% | +0 | 0% | +0 | 0% | +0 |
| C12 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C13 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C14 | C | two | 0% | +0 | 0% | +0 | 100% | +0 |
| C15 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C16 | C | single | 33% | +67 | 0% | +0 | 75% | +0 |
| C17 | C | single | 0% | +0 | 0% | +0 | 0% | +0 |
| C18 | C | two | 0% | +0 | 0% | +0 | 100% | -100 |
| C19 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| C20 | C | two | 0% | +0 | 0% | +0 | 0% | +0 |
| D01 | D | single | 100% | +0 | 0% | +0 | 0% | +0 |
| D02 | D | single | 0% | +0 | 0% | +0 | 40% | +0 |
| D03 | D | single | 80% | +0 | 100% | +0 | 0% | +0 |
| D04 | D | single | 80% | +0 | 100% | +0 | 0% | +0 |
| D05 | D | single | 80% | +0 | 0% | +0 | 20% | +0 |
| D06 | D | single | 80% | +0 | 0% | +0 | 100% | +0 |
| D07 | D | single | 50% | +0 | 0% | +0 | 0% | +0 |
| D08 | D | single | 100% | +0 | 80% | -80 | 0% | +0 |
| D09 | D | two | 0% | +0 | 0% | +0 | 0% | +0 |
| D10 | D | two | 0% | +0 | 0% | +0 | 0% | +0 |

---

## Queries flagged by all three generators

**9 of 75 queries** show post-rationalisation in every generator. These are properties of the query and its retrieved chunks, not of any one model.

### Resistant — flagged by all, fixed by none (2)

The correction loop fails on these regardless of generator.

| Query | Type | Ground truth | Mean PRR |
|---|---|---|---:|
| B02 | B | — | 40% |
| B15 | B | — | 36% |

---

## By query type

| Type | n | Mean PRR before | Mean Δ | Flagged by all 3 | Never flagged |
|---|---:|---:|---:|---:|---:|
| A Answerable | 30 | 17.7% | -9.4pp | 1 | 16 |
| B Broad/Ambiguous | 15 | 32.5% | -5.1pp | 6 | 3 |
| C Hard/Paraphrased | 20 | 16.0% | -4.7pp | 2 | 14 |
| D Unanswerable | 10 | 33.7% | -2.7pp | 0 | 2 |
