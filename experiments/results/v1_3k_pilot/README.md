# v1 — Pilot Experiment

---

## What We Wanted to Do
First end-to-end proof that the full pipeline works. Goal was to verify:
- The RAG system retrieves sensible companies for a given question
- The chunk removal audit correctly identifies whether citations are genuine
- The adversarial loop (discriminator + feedback re-prompt) reduces PRR
- All 4 experimental conditions (2×2 factorial) run successfully

This was a pilot — not intended to be the final result. We expected PRR to be high
and results to be noisy. The purpose was to confirm the pipeline, discover bugs, and
calibrate settings before the main experiment.

---

## What We Did

### Pipeline built (before this run)
- `pipeline/baseline.py` — retrieve top-5 chunks from ChromaDB → build prompt → generate cited answer
- `audit/chunk_removal.py` — for each cited chunk: remove it, regenerate, compute cosine similarity
- `adversarial/loop.py` — discriminator (cross-model) + feedback re-prompt + re-audit
- `evaluation/metrics.py` — PRR, discriminator accuracy, confusion matrix
- `ui/app.py` — Streamlit demo app

### What we ran
4 conditions in sequence, 50 queries each:

```bash
python run_experiment.py --condition C1   # Gemini + Baseline
python run_experiment.py --condition C2   # Gemini + Adversarial
python run_experiment.py --condition C3   # Mistral + Baseline
python run_experiment.py --condition C4   # Mistral + Adversarial
```

C1 was run twice (first run hit free-tier Gemini rate limit of 5 RPM). After upgrading
to paid tier, C1 was re-run. The second C1 log (`C1_20260615_150202.jsonl`) is the one
used for results.

C4 crashed multiple times mid-run due to session interruptions. This led to implementing
**incremental saving** (each query result written to JSONL immediately, with flush) and
**resume logic** (re-run picks up from last completed query_id).

---

## Dataset

### Corpus
- **Source:** Startup Insider GmbH proprietary PostgreSQL database
- **Companies used:** 2,835 DACH companies (Germany, Austria, Switzerland)
- **Why 2,835:** Bug — `build_corpus.py` accidentally joined on `companyboard_description`
  table which only had 2,835 entries. The actual text and vectors were in
  `companyboard_companyembedding` — we should have had ~38K companies. Fixed in v2.
- **Breakdown:** DE=1,939 / CH=624 / AT=272
- **Filter:** active companies, description >50 words, has embedding
- **Embeddings:** 768-dim Gemini embeddings (`gemini-embedding-001`), pre-existing in DB
- **Vector store:** ChromaDB at `data/chroma_db/` (cosine similarity)
- **Chunk format:** one company = one chunk, variable length

### Queries
- **File:** `data/queries/eval_queries.json` (copy: `queries_used.json` in this folder)
- **Count:** 50 queries
- **Type:** Generic — comparative, trend, and open-ended questions
- **Examples:**
  - "What trends exist in German SaaS startups?"
  - "Which Austrian fintech companies raised funding recently?"
  - "Compare business models of Berlin vs Munich startups"
- **Problem:** These queries are STRUCTURALLY unanswerable with specific citations.
  Any startup chunk can substitute for any other on a trend question → PRR always ~100%.
  This was the main lesson of v1 — query design matters enormously.

### Configuration
- TOP_K = 5 (retrieve 5 chunks per query)
- Similarity threshold = 0.85 (cosine similarity of answer embeddings)
- Generator (C1/C2): `models/gemini-2.5-flash`
- Generator (C3/C4): `mistral` via Ollama (Mistral 7B, local)
- Discriminator (C2): Mistral judges Gemini's citations
- Discriminator (C4): Gemini judges Mistral's citations
- Embeddings for similarity: `gemini-embedding-001` (768-dim)

---

## Bugs Found and Fixed During This Run
1. **Free tier rate limit (429):** Gemini free tier = 5 RPM. Upgraded to paid tier.
2. **Retry logic:** Added `_retry()` with exponential backoff in `gemini_client.py`
3. **C4 crashes:** Implemented incremental saving + resume logic in `run_experiment.py`
4. **ZeroDivisionError:** `compute_prr_after()` divided by zero on empty results. Fixed with `if not results: return 0.0`
5. **ConnectError/DNS failures:** Extended retry to handle network drops

---

## Results Summary

| Condition | Model | Pipeline | PRR Before | PRR After | Delta | Disc Acc |
|---|---|---|---|---|---|---|
| C1 | Gemini | Baseline | 95.2% | 95.2% | 0 | — |
| C2 | Gemini | Adversarial | 94.7% | 87.9% | -6.8pp | 2.9% |
| C3 | Mistral | Baseline | 93.2% | 93.2% | 0 | — |
| C4 | Mistral | Adversarial | 98.5% | 92.3% | -6.2pp | 10.2% |

**Full per-query results:** `results_table.csv`

---

## Why PRR Was So High (~93–98%)
Four reasons identified:

1. **Generic queries are structurally broken** — trend/comparative questions can be
   answered by ANY chunk. Removing any single chunk leaves substitutes. PRR always ~100%.
   Fix: redesign queries to be fact-specific (v2).

2. **Corpus homogeneity** — 2,835 similar startups. When you remove chunk [1], chunk [2]
   describes a similar company and substitutes perfectly. PRR overstated.
   Fix: expand to 38K (more diversity) + better queries (v2).

3. **Single removal only** — tests each chunk independently. Misses cumulative redundancy.
   Fix: sequential removal (v3).

4. **No shared baselines** — C3 and C4 generated different answers, making the before/after
   comparison inconsistent.
   Fix: shared baseline generation (v3).

---

## Key Lessons
- Query design is the single biggest factor in PRR measurement
- Corpus size matters less than corpus diversity and query specificity
- The pipeline itself works — discriminator, re-prompt, and re-audit all function correctly
- Incremental saving + resume is essential for long runs

---

## Files in This Folder
| File | Description |
|---|---|
| README.md | This file |
| queries_used.json | The 50 generic queries used in this run |
| results_table.csv | Per-query PRR for all 4 conditions |
| C1_20260615_123050.jsonl | C1 first run (rate-limited, partial) |
| C1_20260615_150202.jsonl | C1 final run (paid tier, complete) |
| C2_20260615_190002.jsonl | C2 complete |
| C3_20260616_154232.jsonl | C3 complete |
| C4_20260623_154801.jsonl | C4 complete (multiple resume cycles) |
