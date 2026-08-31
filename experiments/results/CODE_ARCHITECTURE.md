# Codebase Architecture — RAG Citation Faithfulness System

**Project:** Master's Thesis — Adversarial Correction Loop for RAG Citation Faithfulness  
**Corpus:** 38,692 active DACH companies  
**Models:** Gemini 2.5 Flash (API) + Mistral 7B (local via Ollama)  
**Last updated:** 27 July 2026

---

## Folder Map

```
Thesis/
│
├── config.py                          Global settings (threshold, model names, paths)
│
├── ingestion/
│   └── build_corpus.py                One-time: pull from PostgreSQL → save JSONL + load ChromaDB
│
├── data/
│   ├── corpus_38k.jsonl               38,692 company profiles (plain text, one per line)
│   ├── chroma_db_38k/                 Vector database (binary — not human-readable)
│   └── queries/
│       ├── eval_queries.json          v1 queries (deprecated)
│       ├── eval_queries_v2.json       50 queries — used in v3 experiments
│       └── eval_queries_v3.json       75 typed queries (A/B/C/D) — used in v4 experiments
│
├── models/
│   ├── gemini_client.py               Wrapper: Gemini API — generate() and embed()
│   └── ollama_client.py               Wrapper: local Mistral — generate() only
│
├── pipeline/
│   ├── retriever.py                   Step 1: embed query → find top-5 chunks in ChromaDB
│   └── baseline.py                    Step 2: build prompt → call model → return answer + chunks
│
├── audit/
│   ├── similarity.py                  Cosine similarity between two embedded answers (8 lines)
│   └── chunk_removal.py               The causal test: remove cited chunks, regenerate, compare
│
├── adversarial/
│   └── loop.py                        The full feedback loop: audit → discriminate → re-prompt
│
├── evaluation/
│   ├── metrics.py                     Compute PRR, discriminator accuracy, confusion matrix
│   ├── stats.py                       Statistical tests (z-test, Cohen's h) — pending
│   └── build_results_table.py         Read .jsonl logs → output CSV and markdown tables
│
├── generate_baselines.py              Pre-generate answers so C1/C2 and C3/C4 start identically
├── run_experiment.py                  Main entry point — run one condition or all six
└── run_v4_all_conditions.sh           Shell script: runs all 6 conditions in sequence (v4)
```

---

## Data Flow — Step by Step

```
PostgreSQL (thesis_startup DB)
        │
        │  ingestion/build_corpus.py  [run once]
        ▼
data/corpus_38k.jsonl  +  data/chroma_db_38k/
        │
        │  pipeline/retriever.py
        │  embed query → nearest-neighbour search
        ▼
Top-5 company chunks  [index 1–5, text, name, country, tags]
        │
        │  pipeline/baseline.py
        │  build prompt with citation instruction → call generator
        ▼
Original answer  [cites [1][2][3] etc.]
        │
        ├──────────────────────────────────────────────┐
        │  BASELINE CONDITIONS (C1, C3)                │  ADVERSARIAL CONDITIONS (C2, C4, C5, C6)
        │  audit_fn() → measure PRR                   │  adversarial/loop.py
        │  prr_before = prr_after (no change)          │
        ▼                                              ▼
   Save result                            audit/chunk_removal.py
                                          Sequential removal: remove [1], regenerate,
                                          compare via cosine similarity (threshold 0.85)
                                                       │
                                          ┌────────────┴────────────┐
                                          │                         │
                                   sim ≥ 0.85               sim < 0.85
                                   post-rationalised         genuine → STOP
                                          │
                                  discriminator runs (passive)
                                  asks other model: genuine or PR?
                                  verdict recorded but NOT used for re-prompting
                                          │
                                   pr_indices from AUDIT (not discriminator)
                                          │
                                  build_feedback_prompt()
                                  "you cited [1][3] but removal showed
                                   they weren't needed — please revise"
                                          │
                                   generator produces revised_answer
                                          │
                                   audit again → prr_after
                                          │
                                   Save result {prr_before, prr_after, discriminator_verdicts}
```

---

## File-by-File Explanation

### `config.py`
The single source of truth for every number that matters. If you change the threshold, model name, or database path, you change it here only. Every other file imports from here.

Key values:
- `SIMILARITY_THRESHOLD = 0.85` — the cutoff that decides if a citation is post-rationalised
- `TOP_K = 5` — how many company chunks are retrieved per query
- `GEMINI_GEN_MODEL = "models/gemini-2.5-flash"` — the Gemini generation model
- `OLLAMA_MODEL = "mistral"` — runs locally on your machine

---

### `ingestion/build_corpus.py`
Run once to build the database. Connects to PostgreSQL, pulls all active DACH companies whose profile text has at least 30 words, ranks by an enrichment score (longer text + has sector tags + has funding data = higher score), saves as `.jsonl`, and loads the embedding vectors into ChromaDB.

**Not run again unless the source database changes.**

---

### `models/gemini_client.py`
Thin wrapper around the Google Gemini API. Two functions:
- `generate(prompt)` — sends a text prompt, gets a text answer back
- `embed(text)` — converts a string into a list of 768 numbers (the embedding vector)

Has automatic retry logic: if the API returns a 503 or connection error, it waits and tries again up to 5 times. This prevents a single network hiccup from crashing an experiment.

---

### `models/ollama_client.py`
Thin wrapper around Ollama (local Mistral). Only has `generate(prompt)`. Mistral cannot embed — the Gemini embedder is used for all similarity calculations, even when Mistral is the generator.

---

### `pipeline/retriever.py`
Step 1 of every pipeline run. Takes a query string, embeds it using Gemini, and asks ChromaDB to find the 5 most similar company profiles by vector distance. Returns those 5 chunks with their index numbers (1–5), text, company name, country, and sector tags.

---

### `pipeline/baseline.py`
Step 2. Takes a query and a `generate_fn` (either Gemini or Mistral). Builds a prompt that says "answer using ONLY these 5 sources, cite every claim with [1][2][3]". Calls the model. Returns the answer plus the chunks.

This is the complete pipeline for C1 and C3 (baseline conditions). No adversarial step happens.

---

### `audit/similarity.py`
Eight lines. Takes two text strings, embeds both using Gemini, computes cosine similarity. Returns a number between 0 and 1. This is the scientific measurement at the core of the entire thesis.

---

### `audit/chunk_removal.py`
The causal test. Two modes:

**`audit_answer` (v1/v2 — single removal):** Removes each cited chunk independently. Remove [1], regenerate, measure. Restore [1], remove [2], regenerate, measure. Each chunk tested in isolation.

**`sequential_audit_answer` (v3/v4 — cumulative removal):** Removes chunks cumulatively. Remove {1}, regenerate → still similar → [1] post-rationalised. Now remove {1,2}, regenerate → now different → [2] genuine. Stop. Everything not yet tested → genuine (benefit of the doubt).

The sequential method is more principled: it matches how load-bearing citations actually work. If the answer genuinely relies on a combination of chunks, removing them one at a time independently may not reveal either as load-bearing.

**Verdict logic:**
- `similarity >= 0.85` → the answer barely changed → chunk was NOT needed → `post_rationalised`
- `similarity < 0.85` → the answer changed meaningfully → chunk WAS needed → `genuine` → stop

---

### `adversarial/loop.py`
The full adversarial correction cycle. Three steps:

**Step 1 — Audit:** Calls `sequential_audit_answer` on the original answer. Gets `pr_indices` (list of chunk indices that were post-rationalised).

**Step 2 — Discriminator (passive):** For each cited chunk, asks the discriminator model "is this citation genuine or post-rationalised?" Records the answer. **This verdict is logged but does NOT trigger re-prompting.** The discriminator is a measurement instrument, not a controller.

**Step 3 — Re-prompt:** If `pr_indices` is non-empty (the audit found fake citations), builds a feedback prompt: "you cited [1][3] but chunk removal showed they weren't needed — please revise." Sends it to the generator. Audits the revised answer again to measure `prr_after`.

**Critical finding:** The discriminator defaults to "genuine" for nearly every citation. It cannot detect post-rationalisation from text alone. Only the causal removal test can.

---

### `evaluation/metrics.py`
Reads all results from a condition run and computes:
- **PRR before/after** — mean post-rationalisation rate across all queries
- **PRR delta** — the reduction achieved by the adversarial loop
- **Discriminator accuracy** — what fraction of the discriminator's guesses matched the audit verdict
- **Confusion matrix** — TP/TN/FP/FN comparing discriminator vs audit

---

### `generate_baselines.py`
Generates answers for all queries using a specified model and saves them to `experiments/baselines/`. Run once per model before experiments.

**Why this matters:** Without shared baselines, C1 (Gemini baseline) and C2 (Gemini adversarial) would start from different randomly-generated answers. Any PRR difference could be due to random variation, not the adversarial loop. Shared baselines make the comparison clean: C1 and C2 start from identical answers, so the only variable is whether the adversarial loop ran.

---

### `run_experiment.py`
The main entry point. Accepts `--condition C1` (or `all`), loads queries, loads baselines, runs the baseline or adversarial pipeline depending on the condition, and writes results incrementally to a `.jsonl` log file (one line per query, so a crash midway loses nothing). Prints a summary table at the end.

---

### `run_v4_all_conditions.sh`
A shell script that calls `run_experiment.py` six times in sequence (C1 through C6), all using `--sequential --baselines-tag 38k_v4`. This is how v4 was run. Any condition that crashes mid-run resumes automatically from the last completed query.

---

## The 6 Experimental Conditions

| ID | Generator | Discriminator      | Pipeline    | Purpose                          |
|----|-----------|--------------------|-------------|----------------------------------|
| C1 | Gemini    | —                  | Baseline    | Control: Gemini, no correction   |
| C2 | Gemini    | Mistral (cross)    | Adversarial | Does cross-model disc help?      |
| C3 | Mistral   | —                  | Baseline    | Control: Mistral, no correction  |
| C4 | Mistral   | Gemini (cross)     | Adversarial | Does cross-model disc help?      |
| C5 | Gemini    | Gemini (same)      | Adversarial | Does same-model disc help?       |
| C6 | Mistral   | Mistral (same)     | Adversarial | Does same-model disc help?       |

The discriminator identity (cross vs same) turned out not to matter. What matters is the generator: Mistral accepts correction (~66% fix rate), Gemini resists it (~20% fix rate). This is the central empirical finding.

---

## Key Metrics

**PRR (Post-Rationalisation Rate):** Fraction of cited chunks that the removal test labels as post-rationalised. Measured before and after the correction loop. Lower is better.

**Discriminator Accuracy:** How often the discriminator's verdict matches the removal test's verdict. Used to evaluate whether discriminators can detect post-rationalisation from text alone. (Finding: they cannot — accuracy driven by defaulting to "genuine".)

**CCR (Citation Correctness Rate):** Planned metric for v4. Checks whether the cited company matches the ground-truth answer for answerable queries. Not yet computed.

---

## Experiment Version History

| Version | Corpus  | Queries | Removal method  | Key change                          |
|---------|---------|---------|-----------------|-------------------------------------|
| v1      | 3K      | 20      | Single          | Pilot — proof of concept            |
| v2      | 38K     | 50      | Single          | Scale up corpus                     |
| v3      | 38K     | 50      | Sequential      | Shared baselines, sequential removal|
| v4      | 38K     | 75      | Sequential      | Typed queries (A/B/C/D), ground truth|
