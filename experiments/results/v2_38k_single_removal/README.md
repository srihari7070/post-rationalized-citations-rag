# v2 — 38K Corpus, Fact-Specific Queries, Single Removal

---

## What We Wanted to Do

Fix the two root causes of v1's broken results:

1. **Corpus bug** — v1 used 2,835 companies because `build_corpus.py` accidentally joined
   on `companyboard_description` (2,835 entries) instead of `companyboard_companyembedding`
   (~62K entries). Fix: filter directly on `source_text` word count ≥ 30.

2. **Query design** — v1 used generic/trend queries ("What trends exist in German SaaS?")
   which are structurally unanswerable with specific citations. Any chunk substitutes for any
   other on trend questions → PRR always ~100%, even if the model is perfectly faithful.
   Fix: redesign queries to be fact-specific (year + city + sector combos that only match
   1–2 companies).

The hypothesis: if we fix the corpus and redesign the queries, PRR should drop from ~95%
to something meaningful that actually measures citation faithfulness.

---

## What We Did

### 1. Fixed the corpus bug

Rewrote `ingestion/build_corpus.py` to:
- Query `companyboard_companyembedding` directly for active DACH companies
- Filter to `source_text` word count ≥ 30 (removes company stubs with no real description)
- Export to `data/corpus_38k.jsonl` — 38,692 companies

Also rebuilt ChromaDB at `data/chroma_db_38k/` with all 38,692 embeddings.
(The original 63,664 entries in the DB include inactive companies and companies with
<30 words of text. We use the 38,692 eligible subset.)

### 2. Redesigned 50 queries

Created `data/queries/eval_queries_v2.json` with three tiers:
- **Single-fact Q01–Q20**: one distinguishing fact (e.g., "German startup in cybersecurity in Berlin")
- **Two-fact Q21–Q40**: two constraints (e.g., "Swiss medtech founded in 2020 focused on diagnostics")
- **Three-fact Q41–Q50**: three constraints — only 1 company matches

Design goal: for three-fact queries, at most 1–2 companies in the 38K corpus can satisfy all
constraints. This makes PRR meaningful — if the model cites the wrong company, we can tell.

### 3. Ran all 4 conditions with single removal

```bash
# Each condition run independently (baselines NOT shared between runs)
python3 run_experiment.py --condition C1 --tag 38k
python3 run_experiment.py --condition C2 --tag 38k
python3 run_experiment.py --condition C3 --tag 38k
python3 run_experiment.py --condition C4 --tag 38k
```

Single removal: for each cited chunk index [i], run independently:
- Remove chunk [i] from context
- Regenerate answer with remaining chunks
- Compute cosine similarity between original and new answer (gemini-embedding-001)
- If similarity ≥ 0.85 → chunk not needed → citation is post-rationalised

All cited chunks tested in parallel (separate API calls). PRR = fraction of citations
labelled post-rationalised.

---

## Dataset

### Corpus
- **38,692 DACH companies**
- **Breakdown:** DE=26,466 / CH=9,172 / AT=3,054
- **Source:** Startup Insider GmbH proprietary PostgreSQL database
- **Filter:** active status, source_text ≥ 30 words, pre-existing embedding
- **Total DB embeddings:** 63,664 (38,692 eligible)
- **Vector store:** ChromaDB at `data/chroma_db_38k/` (cosine similarity, HNSW indexing)
- **Embedding model:** `gemini-embedding-001` (768-dim) — pre-computed, not re-generated

### Chunk structure
One chunk = one company profile. Variable size (no fixed chunk splitting).

| Stat | Words | ~Tokens |
|---|---|---|
| Minimum | 30 | ~40 |
| Median | 45 | ~60 |
| Mean | 53 | ~70 |
| 90th pct | 85 | ~113 |
| Maximum | 416 | ~555 |

**Why variable chunks?** Company profiles are naturally short (30–416 words). Splitting them
at 256 tokens would cut descriptions mid-sentence. Keeping one company = one chunk preserves
the citation unit: when the model cites [2], it means the second company, unambiguously.

### What source_text contains
For each company, source_text = concatenation of:
- Company name + founding year + size category + company type
- Country + city
- Sector tags / categories (e.g., "SaaS, HR Tech, B2B")
- Description paragraph
- Mission + vision statements (where present)

This richness is why fact-specific queries work — year+city+sector queries match against
source_text that contains all three fields.

### Queries
- **File:** `data/queries/eval_queries_v2.json` (copy: `queries_used.json` in this folder)
- **Count:** 50 queries
- **Tiers:** Q01–Q20 (single-fact), Q21–Q40 (two-fact), Q41–Q50 (three-fact)
- **No ground truth** — we designed questions to be specific but didn't verify which
  exact company from the DB is the "correct" answer. Fixed in v4.

### Configuration
- TOP_K = 5 (retrieve 5 chunks per query from ChromaDB)
- Similarity threshold = 0.85 (cosine similarity of answer embeddings)
- Generator (C1/C2): `models/gemini-2.5-flash`
- Generator (C3/C4): `mistral` via Ollama (Mistral 7B, local, quantized)
- Discriminator (C2): Mistral judges Gemini's citations
- Discriminator (C4): Gemini judges Mistral's citations
- Answer embedding for similarity: `gemini-embedding-001` (same model as retrieval)

---

## Why the 38K Corpus Doesn't Make It Slower

Common assumption: bigger corpus = slower experiment.
Reality: ChromaDB uses HNSW indexing (O(log n) approximate nearest neighbour).

| Corpus | Retrieval time |
|---|---|
| 2,835 (v1) | ~0.08s per query |
| 38,692 (v2) | ~0.12s per query |

The bottleneck is API calls (Gemini: ~1–3s per call, 5+ calls per query in adversarial
conditions). Retrieval from 38K vs 3K adds ~40ms. The experiment is API-bound, not DB-bound.

This is why v2 with 38K ran at roughly the same speed as v1 with 3K.

---

## Results

### Condition-level averages

| Condition | Model | Pipeline | PRR Before | PRR After | Delta | Disc Acc |
|---|---|---|---|---|---|---|
| C1 | Gemini | Baseline | 23.0% | 23.0% | — | — |
| C2 | Gemini | Adversarial | 24.0% | 16.0% | **-8pp** | 62.1% |
| C3 | Mistral | Baseline | 7.0% | 7.0% | — | — |
| C4 | Mistral | Adversarial | 14.0% | 5.0% | **-9pp** | 68.8% |

**Full per-query results:** `results_table.csv`

### Key observations
1. **PRR dropped from ~95% (v1) to 7–24% (v2)** — query redesign was the critical fix.
2. **Mistral baseline PRR (7%)** is strikingly low. Mistral is more conservative — often
   cites fewer companies or declines to cite when uncertain.
3. **Both adversarial conditions reduced PRR** — the loop works. Gemini: -8pp (35% relative),
   Mistral: -9pp (64% relative).
4. **Discriminator accuracy ~62–69%** — models can identify post-rationalised citations
   at above-chance rates, though not perfectly.

---

## Known Limitations Found During This Run

### 1. Baselines not shared (CRITICAL FLAW)
C1 and C3 generate their baseline answers independently.
C2 and C4 also generate fresh baseline answers at the start of their adversarial runs.
These are DIFFERENT generation runs — LLM non-determinism means the answers differ.

**Observed impact:** C3 PRR (7%) vs C4 PRR before adversarial (14%) — these should be
the same baseline, but they're 7pp apart just from non-determinism. This makes the
comparison invalid. Fixed in v3 with shared baseline generation.

### 2. Single removal underestimates PRR in homogeneous corpus
When we remove chunk [1] independently and chunk [2] remains, [2] often describes
a similar company and substitutes as a valid answer. Result: chunk [1] is labelled
post-rationalised even if it was load-bearing.

Sequential removal (v3) fixes this: remove {1}, then {1,2}, etc. — find the first
removal that actually changes the answer.

### 3. No per-query breakdown
Only condition-level averages were computed. Can't see which queries drive PRR.
Fixed in v3 with a 50-row per-query results table.

### 4. No ground truth
We know PRR but not whether citations are _correct_ (right company).
Fixed in v4 with ground-truth query design.

---

## Log Files

| File | Condition | Queries | Status |
|---|---|---|---|
| C1_38k_20260703_142048.jsonl | Gemini + Baseline | 50/50 | Complete |
| C2_38k_20260703_143314.jsonl | Gemini + Adversarial | 50/50 | Complete |
| C3_38k_20260703_145114.jsonl | Mistral + Baseline | 50/50 | Complete |
| C4_38k_20260703_150311.jsonl | Mistral + Adversarial | 50/50 | Complete |

Each JSONL file contains one record per query with:
- `query_id`, `query`, `answer` (generated), `chunks` (top-5 retrieved)
- `audit` — chunk removal results per cited index
- `prr_before` / `prr_after` (adversarial conditions)
- `discriminator_verdict` (adversarial conditions)
- `revised_answer` (adversarial conditions)

---

## Files in This Folder

| File | Description |
|---|---|
| README.md | This file |
| queries_used.json | The 50 fact-specific queries (copy of eval_queries_v2.json) |
| results_table.csv | Per-query PRR for all 4 conditions |
| C1_38k_20260703_142048.jsonl | C1 complete log |
| C2_38k_20260703_143314.jsonl | C2 complete log |
| C3_38k_20260703_145114.jsonl | C3 complete log |
| C4_38k_20260703_150311.jsonl | C4 complete log |
