# Thesis Explainer — Full Conceptual Walkthrough
> Written: 2026-07-26. This document explains the entire experiment from first principles —
> what each component is, why it was built this way, and what the results mean.
> Intended as a reference before presentations or supervisor meetings.

---

## The Problem Being Solved

When you use a RAG system — a language model that retrieves documents and cites them — the model often **post-rationalises**. It generates a fluent answer first, using its own internal knowledge, and then attaches citations that *look* relevant. The citations are real documents from the corpus, they're related to the topic, but the model didn't *actually need them* to produce the answer. It's fabricating the dependency.

This matters because citations are supposed to be trust signals. If a doctor or lawyer uses a RAG system and sees [Source 3] cited, they assume the system's answer *came from* Source 3. If it didn't, the citation is misleading — a form of hallucination that's hard to detect because the cited document IS about the right topic.

**Thesis question:** Can you detect and reduce this post-rationalisation using a causal test + adversarial feedback?

---

## The Corpus — What You're Searching Over

38,692 DACH startup companies (Germany, Austria, Switzerland) from Startup Insider's proprietary database.

Each company is one "chunk" — a text profile containing: name, founding year, city, size, sector tags, description, mission/vision. This is the **source_text**.

### Why one company = one chunk?

This is a core design decision. Fixed-size chunking (e.g., 256 tokens) was deliberately not used because:

- Each company profile is naturally short (30–416 words, median ~45 words)
- Splitting would cut descriptions mid-sentence and destroy the citation unit
- When the model cites [2], that unambiguously means "the second company retrieved" — not a fragment spanning chunks 2 and 3

The chunk isn't a fixed token window — it's a **meaningful unit of attribution**. One chunk = one citeable source.

### Why 38,692 and not more or less?

- 63,664 embeddings exist in the database total
- ~24K excluded: active companies with fewer than 30 words in their profile (too sparse for meaningful retrieval)
- 38,692 is every eligible active DACH company with a real description and a pre-existing embedding
- The pilot (v1) accidentally used only 2,835 — a SQL join bug pulled from the wrong table. Fixed in v2.

### Why the 38K corpus doesn't make experiments slower

ChromaDB uses **HNSW indexing** (Hierarchical Navigable Small World — approximate nearest neighbour, O(log n)). Retrieval from 38K vs 3K adds ~40ms. The bottleneck is API calls (1–3s each), not database size.

---

## The Embeddings — How Retrieval Works

Every company profile was pre-embedded using **Gemini's embedding model** (`gemini-embedding-001`, 768 dimensions). This turns text into a vector — a point in 768-dimensional space.

When a query arrives, it is also embedded into the same 768-dimensional space. ChromaDB finds the **5 nearest company vectors** by cosine similarity (TOP_K = 5). These 5 companies are retrieved — the candidates the model will read and cite.

**Cosine similarity** measures the angle between two vectors — not their magnitude, just their direction. Two vectors pointing in the same direction = similarity 1.0 (identical meaning). This is used in two places:
1. **Retrieval:** find the 5 most semantically similar companies to the query
2. **Audit:** compare the original answer to a regenerated answer after chunk removal (threshold = 0.85)

---

## The Baseline Pipeline — Control Condition

The baseline is RAG as it normally works, with no correction mechanism.

**Steps:**
1. Embed query → retrieve top-5 company chunks from ChromaDB
2. Build prompt: "Here are 5 companies [1]–[5]. Answer this question and cite which companies you used."
3. Send to generator model → get an answer with citations like "According to [1] and [3]..."
4. Run the chunk removal audit to measure PRR

No discriminator, no re-prompting, no revision. PRR before = PRR after. This is the control — it tells you the natural post-rationalisation rate without any intervention.

---

## The Chunk Removal Audit — The Core Causal Test

This is the heart of the thesis. The question it asks: **Did the model's answer actually come from this cited chunk?**

**The test:** Remove the chunk and see if the answer changes.

### Single removal (used in v1, v2)
The answer cites [1], [3], [5]. Test each independently:
- Remove [1], regenerate with [2][3][4][5], compare answers
- Remove [3], regenerate with [1][2][4][5], compare
- Remove [5], regenerate with [1][2][3][4], compare

### Sequential removal (used in v3 onwards)
Remove cumulatively and stop at the first change:
- Remove {[1]} → regenerate → compare. Unchanged → [1] wasn't needed
- Remove {[1],[3]} → regenerate → compare. Still unchanged → neither needed
- Remove {[1],[3],[5]} → regenerate → compare. **Answer changes** → something in this set was needed. The culprit is [5] (the last one added)
- Stop. Verdict: [5] = genuine, [1] and [3] = post-rationalised

**Why sequential is better:** In a homogeneous corpus (38K similar startups), removing [1] alone leaves [2] as a substitute — a similar company. The answer barely changes so [1] gets labelled post-rationalised, even if it was load-bearing. Sequential removal removes the substitution effect by accumulating removals until the model truly can't find an alternative.

### How "answer changed" is measured

Both the original and regenerated answers are embedded using `gemini-embedding-001`. Cosine similarity between the two embeddings:
- Similarity ≥ 0.85 → answers are semantically the same → chunk wasn't needed → **post-rationalised**
- Similarity < 0.85 → answers diverged meaningfully → chunk was needed → **genuine**

**Why 0.85?** Chosen as the midpoint of the observed similarity distribution. Fixed (not dynamic) so results are reproducible and defensible. Sensitivity analysis at 0.80 and 0.90 planned.

### PRR — Post-Rationalisation Rate

```
PRR = number of post-rationalised citations / total cited citations
```

PRR of 25% means 1 in 4 citations were fake — the model cited a company it didn't actually use. Baseline conditions measure natural PRR. Adversarial conditions measure PRR before and after intervention.

---

## The Adversarial Loop — The Treatment Condition

Three additions on top of the baseline:

### Step 1 — Discriminator judgment
A second model (different from the generator) reads the answer and its citations and judges whether each citation seems genuinely necessary or is just decorative.

This is the **discriminator** — borrowed from GAN (Generative Adversarial Network) terminology. In a GAN, a discriminator tries to detect fake outputs from a generator. Here, the discriminator tries to detect fake citations.

### Step 2 — Feedback re-prompt
If the discriminator flags suspicious citations, the generator is re-prompted: "The following citations were flagged as potentially post-rationalised: [1], [3]. Please revise your answer to only cite sources you genuinely used."

### Step 3 — Re-audit
The revised answer is run through the chunk removal audit again → **PRR after**. The delta (PRR before − PRR after) measures how much the loop helped.

**Critical distinction:** The chunk removal audit is ground truth. The discriminator is just a signal — it can be wrong (~30–35% of the time). The audit uses pure maths (cosine similarity), not AI judgment. The discriminator is the *trigger* for revision; the audit is the *measurement* of whether revision worked.

---

## The Six Conditions — The Full Experimental Design

Two generators × three pipeline types:

| | Baseline | Adversarial (cross-model disc) | Adversarial (same-model disc) |
|---|---|---|---|
| **Gemini 2.5 Flash** | C1 | C2 (Mistral judges Gemini) | C5 (Gemini judges Gemini) |
| **Mistral 7B local** | C3 | C4 (Gemini judges Mistral) | C6 (Mistral judges Mistral) |

**C1/C3** = controls. Measure natural PRR with no intervention.

**C2/C4** = main treatment. Cross-model discrimination: the other model judges citations. The idea: a different model has no incentive to protect the generator's choices, so it may be a more honest judge.

**C5/C6** = self-assessment test. Can a model catch its own post-rationalisation?

### Why two generator models?

**Gemini** (2.5 Flash, cloud API) — large, capable, frontier commercial model.
**Mistral 7B** (local via Ollama, quantized) — smaller, free to run, open weights. Represents lightweight deployable models.

If the adversarial loop works for both, the finding is model-agnostic. If it only works for one, that's an important qualification.

---

## Results — All Six Conditions

| Condition | Model | Discriminator | PRR Before | PRR After | Delta | Disc Acc |
|---|---|---|---|---|---|---|
| C1 | Gemini | — (baseline) | 25.2% | 25.2% | — | — |
| C2 | Gemini | Mistral (cross) | 25.2% | 16.2% | **-9pp** | 65.6% |
| C3 | Mistral | — (baseline) | 12.6% | 12.6% | — | — |
| C4 | Mistral | Gemini (cross) | 12.6% | 3.6% | **-9pp** | 68.5% |
| C5 | Gemini | Gemini (same) | 16.8% | 14.2% | **-2.6pp** | 70.5% |
| C6 | Mistral | Mistral (same) | 13.6% | 5.6% | **-8pp** | 79.6% |

### What the results mean

**The adversarial loop works.** C2: -9pp (35% relative improvement). C4: -9pp (71% relative improvement).

**Cross-model discrimination beats same-model for Gemini, but not for Mistral:**
- Gemini: C2 (-9pp) vs C5 (-2.6pp) — cross-model wins by 6.4pp
- Mistral: C4 (-9pp) vs C6 (-8pp) — essentially tied

**Why might Gemini fail at self-assessment?** C5 discriminator accuracy (70.5%) is actually *higher* than C2 (65.6%) — Gemini *detects* the problem correctly more often. But it still doesn't *fix* it. The likely explanation: Gemini is reluctant to revise its own output even when its own discriminator flags it. It trusts itself.

**Mistral's baseline PRR is lower than Gemini's** (12.6% vs 25.2%). Mistral may be more conservative in citing, possibly due to smaller context window or training differences.

---

## The Shared Baseline Fix — Why It Matters

In v2, each condition generated its own answers independently. LLMs are non-deterministic — same prompt, different output each time. C3 and C4 started from *different* Mistral answers, creating a 7pp gap between their PRRs that was pure noise, not a real difference.

Fix in v3: `generate_baselines.py` generates answers **once per model**, saves to JSONL, and all conditions for that model load the same file. C1, C2, and C5 all start from identical Gemini answers. C3, C4, and C6 all start from identical Mistral answers. Now before/after comparisons are valid.

---

## The Query Design — Why It Matters So Much

**v1 queries** (generic): "What trends exist in German SaaS startups?" → PRR ~95%. Any chunk substitutes for any other on a trend question — the test was broken, not because citations were fake, but because they were interchangeable.

**v2/v3 queries** (fact-specific, three tiers):
- Single-fact Q01–Q20: one constraint (e.g., "German startup in cybersecurity in Berlin")
- Two-fact Q21–Q40: two constraints (e.g., "Swiss medtech founded in 2020")
- Three-fact Q41–Q50: three constraints — only 1 company matches
- PRR dropped to 7–25% — meaningful and measurable

**v4 queries** (planned, scientific):
- Type A (25 queries): one correct company, documented ground truth
- Type B (15 queries): ambiguous — many companies partially match
- Type C (10 queries): no answer in corpus — model should decline to cite
- Enables CCR (Citation Correctness Rate) on top of PRR

---

## The One-Sentence Version

> "We built a RAG system that tests whether its own citations are real by removing each cited source and seeing if the answer changes — and then uses a cross-model adversarial loop to reduce fake citations, achieving 35–71% relative improvement in citation faithfulness across two models, with the finding that cross-model discrimination significantly outperforms self-assessment for Gemini but not Mistral."

### Three things that make this a research contribution
1. **Causal test** — chunk removal is mathematical ground truth, not AI judgment
2. **Adversarial loop** — discriminator + re-prompt reduces post-rationalisation
3. **Empirical finding** — cross-model discrimination works significantly better than self-assessment for at least one model family, suggesting a self-serving bias in citation revision
