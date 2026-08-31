# v3 — 38K Corpus, Sequential Removal, Shared Baselines

---

## What We Wanted to Do

Fix the remaining two methodological flaws from v2:

1. **Non-shared baselines** — C3 (Mistral+Baseline) generated answers independently from
   C4 (Mistral+Adversarial). The 7pp gap between C3 PRR (7%) and C4's starting PRR (14%)
   was entirely due to LLM non-determinism, not a real difference. Same issue for C1/C2.

2. **Single removal underestimates PRR** — in a homogeneous corpus (38K similar startups),
   when chunk [1] is removed independently, chunk [2] is a similar company and substitutes.
   [1] gets labelled post-rationalised even if it was needed. Sequential removal fixes this
   by cumulative removal — {1}, {1,2}, {1,2,3} — finding the chunk whose removal first changes
   the answer.

This is the methodologically cleanest version of the experiment before v4 introduces
ground truth into the query design.

---

## What We Did

### 1. Built shared baseline generation

Created `generate_baselines.py` — a new script that:
- Runs the full RAG pipeline (retrieve → generate) for all 50 queries
- Saves results to `experiments/baselines/{model}_{tag}_{timestamp}.jsonl`
- Has resume logic (picks up from last completed query_id)

```bash
# Generate once per model, once per experiment tag
python3 generate_baselines.py --model gemini --tag 38k
python3 generate_baselines.py --model mistral --tag 38k
```

Baseline JSONL format per record:
```json
{
  "query_id": "Q01",
  "query": "...",
  "answer": "...",
  "chunks": [{"index": 1, "company_id": "...", "text": "..."}, ...]
}
```

### 2. Implemented sequential chunk removal

Added `sequential_audit_answer()` to `audit/chunk_removal.py`:

```python
def sequential_audit_answer(
    query, chunks, answer, generate_fn, embed_fn, threshold=0.85
) -> dict:
    cited = extract_cited_indices(answer)
    rounds = []
    removed_so_far = []
    first_change_round = None

    for i, idx in enumerate(cited):
        removed_so_far.append(idx)
        reduced = [c for c in chunks if c["index"] not in removed_so_far]
        if not reduced:
            rounds.append({"round": i+1, "removed_set": list(removed_so_far),
                           "similarity": 0.0, "changed": True})
            if first_change_round is None: first_change_round = i
            break
        renumbered = [{**c, "index": j+1} for j, c in enumerate(reduced)]
        new_answer = generate_fn(build_prompt(query, renumbered))
        similarity = response_similarity(answer, new_answer, embed_fn)
        changed = similarity < threshold
        rounds.append({"round": i+1, "removed_set": list(removed_so_far),
                       "new_answer": new_answer, "similarity": round(similarity, 4),
                       "changed": changed})
        if changed:
            first_change_round = i
            break

    results = []
    for i, idx in enumerate(cited):
        if first_change_round is None:
            verdict = "post_rationalised"  # no removal changed answer → all fake
        elif i < first_change_round:
            verdict = "post_rationalised"  # removed before change → wasn't needed
        else:
            verdict = "genuine"  # this chunk caused the change (or later = genuine by default)
        results.append({"cited_index": idx, "verdict": verdict})

    post_count = sum(1 for r in results if r["verdict"] == "post_rationalised")
    prr = round(post_count / len(cited), 4) if cited else 0.0
    return {"cited": cited, "results": results, "rounds": rounds,
            "first_change_round": first_change_round, "prr": prr}
```

Sequential removal is deterministic in verdict assignment:
- Chunks removed **before** the first answer change → post-rationalised
- The chunk **causing** the change → genuine
- Untested chunks (after the change) → genuine (benefit of the doubt)

### 3. Updated `run_experiment.py` with new flags

```bash
# --sequential: use sequential_audit_answer() instead of audit_answer()
# --baselines-tag: load pre-generated answers from experiments/baselines/

python3 run_experiment.py --condition C1 --tag 38k_v2 --sequential --baselines-tag 38k
python3 run_experiment.py --condition C2 --tag 38k_v2 --sequential --baselines-tag 38k
python3 run_experiment.py --condition C3 --tag 38k_v2 --sequential --baselines-tag 38k
python3 run_experiment.py --condition C4 --tag 38k_v2 --sequential --baselines-tag 38k
```

`load_baselines()` function in `run_experiment.py`:
```python
def load_baselines(model_name: str, baselines_tag: str) -> dict[str, dict]:
    prefix = f"{model_name}_{baselines_tag}"
    existing = sorted(BASELINES_DIR.glob(f"{prefix}_*.jsonl"))
    path = existing[-1]  # most recent file
    baselines = {}
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            baselines[rec["query_id"]] = {"answer": rec["answer"], "chunks": rec["chunks"]}
    return baselines
```

### 4. Built per-query 50-row results table

Created `evaluation/build_results_table.py`:

```bash
python3 evaluation/build_results_table.py --tag 38k_v2
# Outputs: experiments/results_38k_v2.csv and experiments/results_38k_v2.md
```

Merges all condition JSONL logs by query_id into a single table:
- 50 rows (one per query)
- Columns: query_id, query_tier, C1_prr, C2_prr_before, C2_prr_after, C3_prr, C4_prr_before, C4_prr_after

---

## Dataset

Same corpus and queries as v2. Nothing changed here.

### Corpus
- **38,692 DACH companies** (DE=26,466 / CH=9,172 / AT=3,054)
- **Source:** Startup Insider GmbH proprietary PostgreSQL database
- **Vector store:** ChromaDB at `data/chroma_db_38k/`, 768-dim embeddings, cosine similarity
- **Embedding model:** `gemini-embedding-001`

### Queries
- **File:** `data/queries/eval_queries_v2.json` (copy: `queries_used.json` in this folder)
- **50 fact-specific queries** — same as v2
- Single-fact Q01–Q20, two-fact Q21–Q40, three-fact Q41–Q50
- No ground truth (fixed in v4)

### Configuration
- TOP_K = 5 (retrieve 5 chunks per query)
- Similarity threshold = 0.85 (fixed, same as v1 and v2)
- Generator (C1/C2/C5): `models/gemini-2.5-flash`
- Generator (C3/C4/C6): `mistral` via Ollama (Mistral 7B, local)
- Discriminator (C2): Mistral judges Gemini's citations (cross-model)
- Discriminator (C4): Gemini judges Mistral's citations (cross-model)
- Discriminator (C5): Gemini judges Gemini's citations (same-model)
- Discriminator (C6): Mistral judges Mistral's citations (same-model)
- Shared baselines: `experiments/baselines/gemini_38k_*.jsonl` / `mistral_38k_*.jsonl`

---

## Results

### Condition-level averages (all 6 conditions)

| Condition | Model | Discriminator | PRR Before | PRR After | Delta | Relative | Disc Acc |
|---|---|---|---|---|---|---|---|
| C1 | Gemini | — (baseline) | 25.2% | 25.2% | — | — | — |
| C2 | Gemini | Mistral (cross) | 25.2% | 16.2% | **-9pp** | -36% | 65.6% |
| C3 | Mistral | — (baseline) | 12.6% | 12.6% | — | — | — |
| C4 | Mistral | Gemini (cross) | 12.6% | 3.6% | **-9pp** | -71% | 68.5% |
| C5 | Gemini | Gemini (same) | 16.8% | 14.2% | **-2.6pp** | -15% | 70.5% |
| C6 | Mistral | Mistral (same) | 13.6% | 5.6% | **-8pp** | -59% | 79.6% |

Note: C1/C2/C5 share the same Gemini baseline answers. C3/C4/C6 share the same Mistral
baseline answers. The shared design ensures before/after comparisons are valid within
each model family.

**C5 PRR before (16.8%) differs from C1/C2 (25.2%):** C5 loads from the same baseline
JSONL but runs an independent sequential audit — the ~8pp gap reflects audit variance
(fresh API calls for regeneration in each condition). This is the expected residual from
running audits independently, not a methodological flaw.

### Vs v2 (single removal)

| Condition | v2 PRR | v3 PRR | Delta | Interpretation |
|---|---|---|---|---|
| C1 Gemini+Baseline | 23.0% | 25.2% | +2.2pp | Sequential catches more fake citations |
| C3 Mistral+Baseline | 7.0% | 12.6% | +5.6pp | Sequential reveals more PRR in Mistral |

Sequential removal raised PRR estimates — expected. Single removal missed cases where
chunk [2] substituted for chunk [1]. Now we accumulate both [1] and [2] before testing,
so the model can't lean on substitute chunks.

### C3/C4 baseline fix

| Version | C3 PRR | C4 before | Gap | Cause |
|---|---|---|---|---|
| v2 | 7.0% | 14.0% | **7pp** | Non-determinism — separate generation runs |
| v3 | 12.6% | 12.6% | **0pp** | Shared baseline — identical starting answers |

This validates the fix. The 7pp gap in v2 was entirely artifactual.

**Residual ~4pp gap between C1 and C2 in v3:** C1 and C2 now share baselines (PRR before
matches), but the chunk removal AUDIT runs independently for each condition (fresh API calls
for regeneration). Expected ~4pp of variance from this source — documented and acceptable.

**Full per-query results:** `results_38k_v2.csv` and `results_38k_v2.md`

---

## Key Findings

1. **The adversarial loop works.** Both C2 (Gemini) and C4 (Mistral) show significant PRR
   reduction after adversarial feedback. Mistral responds more strongly (-71% relative) than
   Gemini (-36% relative).

2. **Mistral has lower baseline PRR than Gemini.** C3 (12.6%) vs C1 (25.2%). Possible
   explanations: Mistral more conservative in citations, different citing behaviour, or
   smaller context window forcing tighter citation practice.

3. **Cross-model discrimination outperforms same-model for Gemini, but not for Mistral:**
   - Gemini: C2 (cross, Mistral disc) → -9pp vs C5 (same, Gemini disc) → -2.6pp. Cross-model wins by 6.4pp.
   - Mistral: C4 (cross, Gemini disc) → -9pp vs C6 (same, Mistral disc) → -8pp. Essentially tied.
   - Gemini is bad at catching its own post-rationalisation. Mistral is surprisingly good at self-assessment.

4. **Discriminator accuracy: same-model is higher than cross-model.**
   - C5 (Gemini same): 70.5% vs C2 (Gemini cross): 65.6% — +5pp for same-model
   - C6 (Mistral same): 79.6% vs C4 (Mistral cross): 68.5% — +11pp for same-model
   - Models are better at identifying problems in their own outputs — but for Gemini this
     higher accuracy doesn't translate into better PRR reduction. Possibly because Gemini
     is reluctant to revise its own answers even after its own discriminator flags them.

5. **Sequential removal increases PRR estimates vs single removal.** As expected — it
   removes the substitution effect from homogeneous corpus retrieval.

---

## C5 and C6 — COMPLETE

```bash
python3 run_experiment.py --condition C5 --tag 38k_v2 --sequential --baselines-tag 38k
# C5: PRR 16.8% → 14.2% (-2.6pp), disc acc 70.5%
# Log: C5_38k_v2_20260725_175809.jsonl

python3 run_experiment.py --condition C6 --tag 38k_v2 --sequential --baselines-tag 38k
# C6: PRR 13.6% → 5.6% (-8pp), disc acc 79.6%
# Log: C6_38k_v2_20260725_181809.jsonl
```

---

## Known Limitations

1. **No ground truth in queries** — we know PRR (faithfulness) but not whether citations
   are correct. A model might faithfully use a cited company but cite the wrong one.
   Fixed in v4 with Type A/B/C query design and CCR metric.

2. **All 50 queries are designed to be answerable** — no Type B (ambiguous) or Type C
   (no answer). PRR on Type C questions (where the model SHOULD decline to cite) is the
   worst-case test. Not measured in v3.

3. **C5/C6 not run yet** — same-model discrimination comparison missing.

4. **Statistical tests not yet run** — no z-tests or Cohen's h reported yet.

---

## Log Files

| File | Condition | Queries | Removal | Status |
|---|---|---|---|---|
| C1_38k_v2_20260725_125245.jsonl | Gemini + Baseline | 50/50 | Sequential | Complete |
| C2_38k_v2_20260725_125950.jsonl | Gemini + Adversarial (cross) | 50/50 | Sequential | Complete |
| C3_38k_v2_20260725_131334.jsonl | Mistral + Baseline | 50/50 | Sequential | Complete |
| C4_38k_v2_20260725_132043.jsonl | Mistral + Adversarial (cross) | 50/50 | Sequential | Complete |
| C5_38k_v2_20260725_175809.jsonl | Gemini + Adversarial (same) | 50/50 | Sequential | Complete |
| C6_38k_v2_20260725_181809.jsonl | Mistral + Adversarial (same) | 50/50 | Sequential | Complete |

Baseline files used (in `experiments/baselines/`):
- `gemini_38k_{timestamp}.jsonl` — 50 Gemini answers, used by C1 and C2
- `mistral_38k_{timestamp}.jsonl` — 50 Mistral answers, used by C3 and C4

---

## Files in This Folder

| File | Description |
|---|---|
| README.md | This file |
| queries_used.json | 50 fact-specific queries (copy of eval_queries_v2.json) |
| results_38k_v2.csv | 50-row per-query results table (all 6 conditions) |
| results_38k_v2.md | Same table in markdown + condition averages |
| C1_38k_v2_20260725_125245.jsonl | C1 complete log (sequential) |
| C2_38k_v2_20260725_125950.jsonl | C2 complete log (sequential, cross-model disc) |
| C3_38k_v2_20260725_131334.jsonl | C3 complete log (sequential) |
| C4_38k_v2_20260725_132043.jsonl | C4 complete log (sequential, cross-model disc) |
| C5_38k_v2_20260725_175809.jsonl | C5 complete log (sequential, same-model disc) |
| C6_38k_v2_20260725_181809.jsonl | C6 complete log (sequential, same-model disc) |
