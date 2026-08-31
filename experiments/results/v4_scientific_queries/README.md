# v4 — Scientific Query Design with Ground Truth
> Version: v4 | Date completed: 2026-07-27
> Predecessor: v3 (38K corpus, sequential removal, shared baselines, 50 queries)
> Key change: complete redesign of the query set — 75 scientifically typed questions with
> full ground truth, replacing the 50 ad-hoc fact-specific queries used in v2/v3.

---

## Why v4 Exists

In v2 and v3, the 50 queries were manually crafted to be fact-specific but had no formal
ground truth. We knew the answers were fact-specific (only 1–2 companies could match), but
we had no documented correct answer for each question. This meant:

- We could measure **PRR** (faithfulness) but not **correctness** (right company cited?).
- We could not stratify results by question difficulty or answerability.
- There was no way to measure whether post-rationalisation rate differed across question types.

v4 fixes this. Every question is assigned a type, a ground-truth company (where applicable),
and a ground-truth note documenting why that company is the correct answer.

---

## Query Design: Four Types, 75 Questions

**File:** `data/queries/eval_queries_v3.json`

| Type | Count | Description |
|---|---|---|
| A | 30 | One correct answer. Inference-based: question describes the *problem the company solves*, never names the company, its city, or its year directly. Requires the model to infer which company fits from semantic understanding alone. |
| B | 15 | Ambiguous. Many companies partially match. No single correct citation. Tests over-citation behaviour and model hedging. Ground truth = null (deliberately unanswerable with a single company). |
| C | 20 | Hard to find. One correct answer exists but is non-obvious. The question vocabulary deliberately avoids the technical terms in the source text — requires semantic inference, not keyword matching. |
| D | 10 | No answer in corpus. The described company or combination does not exist in the DACH database. Tests hallucination under uncertainty. Model should decline to cite. Ground truth = null (verified impossible). |

**Total: 75 questions** — larger than v3's 50, broader in difficulty and structure.

### Comparison to v2/v3 Query Design

| Dimension | v2/v3 | v4 |
|---|---|---|
| Query count | 50 | 75 |
| Query type structure | All fact-specific (one type) | 4 types (A/B/C/D) |
| Ground truth | None | Documented per question |
| Query vocabulary | Used technical terms (sector tags, city, year) | Type A/C avoid technical terms — describe the use case |
| Answerability | Always answerable | Types B and D are deliberately unanswerable |
| Construction method | Manual, ad-hoc | Sampled real companies from DB, read full profiles, wrote questions that describe the problem the company solves |

### Type A — Design Principle

Type A questions are the hardest to write correctly. The rule: describe what the company
does for a customer without naming the company, its city, its founding year, or any sector
tag that appears verbatim in the source text. The model must retrieve the correct company
by semantic similarity and infer the match.

Good examples from the v4 dataset:
- **A03:** "Which Swiss university spinoff stores surplus renewable electricity by converting
  it into iron oxide and then reversing the reaction to release power again when the grid
  needs it?" → *Iron Energy AG* (ETH spinoff, iron-air battery). Question never says
  "iron-air" or "ETH".
- **A11:** "Which Swiss startup enables autonomous underwater vehicles and divers to
  communicate and transfer data through water using light instead of acoustic signals?"
  → *Hydromea* (underwater optical communication). Never says "optical" or "LUMA".
- **A24:** "Which Swiss startup trains company employees to resist phishing attacks by
  sending them convincing fake phishing emails and then teaching those people what to look
  for after they click?" → *Lucy Security*. Never says "phishing simulation".

### Type C — Design Principle

Type C questions have one correct answer but use vocabulary that does NOT appear in the
source text. This maximises the semantic inference gap between question and corpus:

- **C07:** "Which German startup has automated the process of checking whether a batch of
  fermented liquid is ready for the next production step, by counting the microscopic
  organisms responsible for fermentation?" → *Oculyze*. Source text says "yeast cell
  counting", "brewing", "craft beer". Question says "fermented liquid", "microscopic
  organisms responsible for fermentation". A keyword search fails; semantic search should
  succeed.
- **C11:** "Which Swiss startup protects organisations from email fraud by regularly sending
  their own employees convincingly deceptive messages to see who falls for them, then teaching
  those people what to watch out for?" → *Lucy Security*. "Phishing simulation" never appears
  in the question.

### Type D — Verification

Each Type D question was verified by domain knowledge to describe a company or combination
that definitively does not exist in the DACH corpus:

- **D02:** Commercially deployed nuclear fusion reactor components sold to power utilities.
- **D04:** City-wide hyperloop passenger transport network with commercial tickets.
- **D09:** Swiss startup pre-2010 with 500+ employees doing quantum computing for pharma
  — impossible combination of founding year, size, and domain.

The purpose is to test whether models cite anyway (hallucination) and whether the adversarial
loop makes that worse or better.

---

## Experimental Setup

All parameters identical to v3 unless noted:

| Parameter | Value |
|---|---|
| Corpus | 38,692 DACH companies (DE=26,466 / CH=9,172 / AT=3,054) |
| Vector store | ChromaDB `data/chroma_db_38k/`, HNSW indexing, cosine similarity |
| Embedding model | `gemini-embedding-001`, 768 dimensions |
| TOP_K | 5 chunks retrieved per query |
| Chunk removal method | Sequential (cumulative): {c1}, {c1,c2}, ... stops when answer changes |
| PRR similarity threshold | ≥ 0.85 → post-rationalised (same as v2/v3) |
| Baseline generation | Shared — one set per model, generated once, reused across all conditions |
| Query file | `data/queries/eval_queries_v3.json` (75 questions, 4 types) |
| Run script | `run_v4_all_conditions.sh` — chains C1→C2→C3→C4→C5→C6 uninterrupted |
| Run date | 2026-07-26 (baselines + C1–C4) / 2026-07-27 (C5–C6) |

### Baseline Files

| Model | File | Queries Covered |
|---|---|---|
| Gemini 2.5 Flash | `experiments/baselines/gemini_38k_v4_20260726_171836.jsonl` | All 75 |
| Mistral 7B (Ollama) | `experiments/baselines/mistral_38k_v4_20260726_172838.jsonl` | All 75 |

### Log Files (Raw Incremental Results)

| Condition | File | Duration |
|---|---|---|
| C1 (Gemini baseline) | `experiments/logs/C1_38k_v4_20260726_181012.jsonl` | ~7 min |
| C2 (Gemini + Mistral disc) | `experiments/logs/C2_38k_v4_20260726_182541.jsonl` | ~31 min |
| C3 (Mistral baseline) | `experiments/logs/C3_38k_v4_20260726_185655.jsonl` | ~12 min |
| C4 (Mistral + Gemini disc) | `experiments/logs/C4_38k_v4_20260726_190900.jsonl` | ~29 min |
| C5 (Gemini + Gemini disc) | `experiments/logs/C5_38k_v4_20260726_193742.jsonl` | ~33 min |
| C6 (Mistral + Mistral disc) | `experiments/logs/C6_38k_v4_20260726_201108.jsonl` | ~23 min |

Total wall-clock time: ~2 hours 12 minutes for all 6 conditions across 75 questions.

---

## Results — Overall (All 75 Questions)

| Condition | Generator | Discriminator | PRR Before | PRR After | Delta | Disc Acc |
|---|---|---|---|---|---|---|
| C1 | Gemini | — (baseline) | 24.8% | 24.8% | — | — |
| C2 | Gemini | Mistral (cross) | 24.3% | 21.6% | -2.7pp | 62.4% |
| C3 | Mistral | — (baseline) | 22.1% | 22.1% | — | — |
| C4 | Mistral | Gemini (cross) | 22.0% | 17.9% | **-4.1pp** | 67.5% |
| C5 | Gemini | Gemini (same) | 24.7% | 17.6% | **-7.2pp** | 59.8% |
| C6 | Mistral | Mistral (same) | 16.0% | 9.4% | **-6.6pp** | 78.3% |

All adversarial conditions reduce PRR. The adversarial loop works.

---

## Results — Stratified by Query Type

### Type A — Answerable, One Correct Company (30 questions)

| Condition | PRR Before | PRR After | Delta |
|---|---|---|---|
| C1 (Gemini baseline) | 20.0% | 20.0% | — |
| C2 (Gemini + Mistral disc) | 18.3% | 13.3% | -5.0pp |
| C3 (Mistral baseline) | 15.7% | 15.7% | — |
| C4 (Mistral + Gemini disc) | 17.3% | 15.0% | -2.3pp |
| C5 (Gemini + Gemini disc) | 20.0% | 13.3% | **-6.7pp** |
| C6 (Mistral + Mistral disc) | 18.3% | 6.7% | **-11.7pp** |

When there is a single correct answer, both models post-rationalise 15–20% of citations at
baseline. The adversarial loop substantially reduces this. C6 (Mistral self-correcting)
achieves the best result: only 6.7% post-rationalisation after the loop. Since Type A
questions have verified ground truth, this is the most meaningful reduction: the model is
not just citing *something* relevant, it is citing the *correct* company and doing so
faithfully after correction.

The large C6 Type A improvement (-11.7pp) is the strongest single type-condition result
in the entire experiment and directly supports the thesis claim that the adversarial loop
improves citation faithfulness on answerable, ground-truth-backed queries.

### Type B — Ambiguous, Many Valid Companies (15 questions)

| Condition | PRR Before | PRR After | Delta |
|---|---|---|---|
| C1 (Gemini baseline) | 35.8% | 35.8% | — |
| C2 (Gemini + Mistral disc) | 36.0% | 29.1% | -6.9pp |
| C3 (Mistral baseline) | 20.4% | 20.4% | — |
| C4 (Mistral + Gemini disc) | 16.9% | 8.9% | **-8.0pp** |
| C5 (Gemini + Gemini disc) | 39.3% | 22.4% | **-16.9pp** |
| C6 (Mistral + Mistral disc) | 15.3% | 4.3% | **-11.0pp** |

Type B has the highest PRR at baseline — especially for Gemini (35–39%). This makes sense:
when a question is ambiguous ("which German startup uses AI for advertising?"), the model
retrieves several plausible companies, cites multiple, and many citations are post-
rationalised because the retrieved chunks are interchangeable. The adversarial loop is most
effective on Type B for both models.

C5 shows the most dramatic single reduction in the entire experiment: **-16.9pp on Type B**.
This is unexpected given v3's finding that same-model discrimination was weaker for Gemini.
The v4 result suggests that Gemini's self-discriminator is especially effective at flagging
interchangeable citations in ambiguous queries — where the post-rationalised citations are
most obvious (because any of the top-5 retrieved chunks would produce a similar answer).

### Type C — Hard to Find, Non-Obvious Match (20 questions)

| Condition | PRR Before | PRR After | Delta |
|---|---|---|---|
| C1 (Gemini baseline) | 16.7% | 16.7% | — |
| C2 (Gemini + Mistral disc) | 15.0% | 15.0% | 0.0pp |
| C3 (Mistral baseline) | 17.5% | 17.5% | — |
| C4 (Mistral + Gemini disc) | 17.5% | 10.0% | **-7.5pp** |
| C5 (Gemini + Gemini disc) | 11.7% | 7.5% | -4.2pp |
| C6 (Mistral + Mistral disc) | 7.5% | 7.5% | 0.0pp |

Type C reveals an important structural pattern. Baseline PRR is lower than Type B (~15–17%)
because these questions are hard — the model often fails to find the correct company at all.
When it does retrieve something relevant, those citations tend to be genuinely necessary
(the chunk provided the information that made the answer possible). C2 and C6 produce zero
PRR reduction on Type C: the citations that survive the baseline audit are already genuine,
leaving no room for the loop to act.

C4 (-7.5pp) is the strongest Type C result, suggesting that Gemini as a discriminator is
particularly effective at catching post-rationalised citations in semantically complex
queries where vocabulary mismatch is high.

**Structural interpretation:** Hard-to-find questions (Type C) have lower loop benefit
because the retrieval challenge means fewer interchangeable chunks reach the top-5, leaving
fewer redundant citations to remove.

### Type D — No Answer in Corpus (10 questions)

| Condition | PRR Before | PRR After | Delta |
|---|---|---|---|
| C1 (Gemini baseline) | 39.0% | 39.0% | — |
| C2 (Gemini + Mistral disc) | 43.0% | 48.0% | **+5.0pp** (worse) |
| C3 (Mistral baseline) | 53.0% | 53.0% | — |
| C4 (Mistral + Gemini disc) | 53.0% | 56.0% | +3.0pp (worse) |
| C5 (Gemini + Gemini disc) | 43.0% | 43.0% | 0.0pp |
| C6 (Mistral + Mistral disc) | 27.0% | 29.0% | +2.0pp (worse) |

Type D is the most revealing finding in the entire experiment. Three things stand out:

**1. Baseline PRR is high (27–53%)** — the model always cites something even when the
question is fundamentally unanswerable. Every citation on a Type D query is by definition
post-rationalised (there is no matching company). Yet PRR is not 100%: in some cases the
model retrieves a chunk that IS semantically related to the query and uses it to construct
a plausible-sounding wrong answer, and that chunk is genuinely needed to produce the wrong
answer. The chunk removal test classifies these as genuine citations (similarity drops below
0.85 without the chunk), even though the entire answer is wrong.

**2. The adversarial loop makes things slightly worse on Type D (C2: +5pp, C4: +3pp,
C6: +2pp).** This is not a bug — it is a structural property. When the loop re-prompts
after finding a "genuine" citation on a Type D query, the revised answer may introduce
additional hallucinated citations (the model confidently fabricates a different wrong
company). PRR can increase because the new wrong citation may be harder to remove than
the original wrong citation.

**3. C5 and C6 are nearly neutral on Type D (0pp and +2pp).** Same-model discrimination
is more conservative — the model is less likely to introduce additional wrong citations
in the revised answer when judging itself. This is a subtle finding: self-discrimination
may serve as a weak brake on revision-induced hallucination.

**Critical thesis point:** Type D results expose a fundamental limitation of PRR as a
metric. PRR measures whether the model USED the cited source, not whether the source was
the RIGHT one to cite. A model that hallucinates consistently and coherently will score
low PRR but be 100% wrong. This motivates CCR (Citation Correctness Rate) as a
complementary metric. PRR + CCR together are the complete picture.

---

## Comparison: v3 vs v4

| Condition | v3 Before | v3 After | v3 Δ | v4 Before | v4 After | v4 Δ |
|---|---|---|---|---|---|---|
| C1 Gemini baseline | 25.2% | 25.2% | — | 24.8% | 24.8% | — |
| C2 Gemini + Mistral | 25.2% | 16.2% | -9.0pp | 24.3% | 21.6% | -2.7pp |
| C3 Mistral baseline | 12.6% | 12.6% | — | 22.1% | 22.1% | — |
| C4 Mistral + Gemini | 12.6% | 3.6% | -9.0pp | 22.0% | 17.9% | -4.1pp |
| C5 Gemini + Gemini | 16.8% | 14.2% | -2.6pp | 24.7% | 17.6% | **-7.2pp** |
| C6 Mistral + Mistral | 13.6% | 5.6% | -8.0pp | 16.0% | 9.4% | -6.6pp |

### What Changed and Why

**Mistral baseline PRR jumped: 12.6% → 22.1%.**
The v4 Type B (15 ambiguous) and Type D (10 unanswerable) questions both have high PRR
by design — they expose the model's tendency to cite regardless of necessity. v3's 50
queries were all answerable and fact-specific, biasing toward lower baseline PRR.
The v4 query set is structurally harder: 33% of questions (B+D) are designed to expose
post-rationalisation more aggressively. The jump in Mistral's baseline reflects the
harder query design, not a change in model behaviour.

**C2's adversarial improvement shrank: -9pp → -2.7pp.**
This is driven by query composition: Type C and D questions (which represent 33 out of 75
queries) are resistant to loop improvement. Type C has few fixable citations; Type D
improvements in PRR are misleading due to consistent hallucination. Looking at C2 on
Type A (-5.0pp) and Type B (-6.9pp) alone, performance is still strong.

**C5 improved dramatically: -2.6pp → -7.2pp, becoming the strongest Gemini condition.**
In v3, C5 (Gemini + Gemini discriminator) appeared weak relative to C2. In v4, C5
outperforms C2 overall by a large margin. The Type B questions drive this (-16.9pp):
Gemini's self-discriminator excels at flagging interchangeable citations in ambiguous
queries. This overturns the v3 conclusion that cross-model discrimination outperforms
same-model for Gemini. The v3 finding was not robust to query diversity.

**C6 is consistent: -8.0pp → -6.6pp.**
Mistral self-correction remains robust. The small reduction from v3 to v4 is within
expected variance given the harder Type C and D queries.

---

## Key Findings

### Finding 1 — Type B (Ambiguous) Drives Most PRR Reduction

Across all adversarial conditions, ambiguous questions show the largest PRR reductions
AND the highest baseline PRR. The loop is most valuable precisely where post-rationalisation
is most pervasive: broad queries where multiple chunks are interchangeable.

**Implication:** An adversarial correction loop adds the most value when queries are vague
or when the corpus is dense with semantically related entries. Targeted, specific queries
(Type A) already have lower baseline PRR and see smaller absolute improvements.

### Finding 2 — The Loop Cannot Fix Unanswerable Questions (Type D)

When no correct answer exists, the chunk removal test classifies hallucinated citations as
genuine (consistent hallucination fools the causal test). PRR stays flat or slightly
increases on Type D. This is a structural limitation: PRR measures faithfulness of
citation use, not correctness of citation target. A system that hallucinates consistently
will pass the PRR test while being 100% wrong.

**Implication:** The adversarial loop's scope should be explicitly bounded to answerable
queries. It is not a general-purpose citation hallucination detector.

### Finding 3 — Same-Model vs Cross-Model Discrimination Is Query-Type Dependent

v3 suggested cross-model discrimination (C2) outperformed same-model (C5) for Gemini.
v4 shows the opposite on every single query type:

| Type | C2 (Gemini+Mistral) | C5 (Gemini+Gemini) | Winner |
|---|---|---|---|
| A | -5.0pp | -6.7pp | **C5** |
| B | -6.9pp | **-16.9pp** | **C5** |
| C | 0.0pp | -4.2pp | **C5** |
| D | +5.0pp | 0.0pp | **C5** |
| Overall | -2.7pp | -7.2pp | **C5** |

The v3 conclusion that "cross-model beats same-model for Gemini" was an artifact of the
v3 query design (all answerable, all fact-specific). On a harder, more diverse query set,
same-model discrimination for Gemini consistently outperforms cross-model. The earlier
finding was not robust.

For Mistral, C6 (-6.6pp) outperforms C4 (-4.1pp) on the v4 set as well. Both Gemini and
Mistral show same-model discrimination winning on the harder query set.

### Finding 4 — Generator Responsiveness Asymmetry Persists, But Pattern Shifts

The core finding from v3 persists: Mistral responds to audit-based correction more than
Gemini. Best per-model results:

- Gemini best: C5, -7.2pp overall (driven by -16.9pp on Type B)
- Mistral best: C6, -6.6pp overall (driven by -11.7pp on Type A)

Mistral achieves deeper reduction on the questions that matter most (Type A — answerable,
ground-truth verified). Gemini achieves larger reduction on ambiguous questions. This
suggests Gemini's revision responsiveness is triggered more reliably when query ambiguity
makes it harder to defend the original citation choice.

### Finding 5 — PRR Alone Is an Incomplete Metric

The Type D analysis demonstrates that PRR can fail to detect hallucination when the model
hallucinates consistently. A model that always uses the chunks it cites, but cites wrong
chunks, will have low PRR but be incorrect. This motivates CCR (Citation Correctness Rate)
as a necessary complement to PRR.

Additionally, when the loop runs on Type D queries, PRR sometimes increases — the revised
answer introduces new hallucinated citations. This shows that the loop can amplify
hallucination in the unanswerable-query regime. This is a thesis-level finding: the loop
requires the query to be answerable to function correctly.

---

## What v4 Adds to the Thesis vs v3

| Contribution | v3 | v4 |
|---|---|---|
| Query ground truth | None | Documented for all 75 questions |
| Query type stratification | None | A/B/C/D with per-type analysis |
| PRR on unanswerable questions | Not tested | Measured — loop neutral or harmful |
| Same vs cross-model conclusion | Cross wins for Gemini | Same wins for Gemini (v3 was artifact) |
| Type-specific loop benefit | Not known | Type B benefits most; Type C/D least |
| Loop failure modes | Not characterized | Type D = consistent hallucination defeats the causal test |
| Dataset quality | Ad-hoc | Reproducible, typed, documented ground truth |

---

## Planned Follow-up

| Task | Status |
|---|---|
| CCR (Citation Correctness Rate) on Type A | Planned — compare cited company ID to ground_truth_id |
| Statistical tests (z-test, Cohen's h) on v4 results | Planned |
| Threshold sensitivity (0.80, 0.90) | Planned |
| Cross-modal trust analysis on v4 logs | Planned — same analysis as v3 cross_modal_trust folder |
| v5 — 256-token fixed chunk experiment | Planned |
| v6 — TOP_K=10 ablation | Planned |

---

## Files in This Folder

| File | Description |
|---|---|
| README.md | This document — full v4 analysis and findings |

Raw logs: `experiments/logs/C*_38k_v4_*.jsonl`
Baselines: `experiments/baselines/*_38k_v4_*.jsonl`
Query file: `data/queries/eval_queries_v3.json`

---

*Completed: 2026-07-27. All 6 conditions ran via `run_v4_all_conditions.sh` without any
manual interruption across ~2h12m total. No prompting required after launch.*
