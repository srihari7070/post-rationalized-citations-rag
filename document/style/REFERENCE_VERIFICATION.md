# Reference Verification

Checked 14 August 2026. Covers the 18 references in the thesis proposal and the 11 drafted
into chapter 2, roughly 26 unique after overlap.

**Headline: no fabricated references found.** Every paper checked exists, and every author
list, year and venue I verified was correct. Several entries need precision fixes, one
pair of citations is dangerously ambiguous, and one paper is far closer prior work than
the proposal acknowledges.

---

## 1. The thing that matters most

### Roy et al. (WSDM 2025) already do the measurement

Verified description of their counterfactual attribution:

> the contribution of evidence to an answer is determined by **the similarity of the
> original response to the answer obtained by removing that evidence**

That is this thesis's chunk-removal audit. Same operation, same comparison, same logic.

The proposal describes Roy et al. as showing that removal "is a reliable way to identify
which documents causally contributed", which is accurate but undersells it. They are not
adjacent work. They implemented the measurement instrument.

**This does not sink the contribution, but it does relocate it.** The novelty cannot be
the removal test itself. It has to be:

1. Using the removal result as a **correction signal fed back to the generator during
   inference**, which Roy et al. do not do
2. **Generator correction receptivity**, which requires a correction loop to observe at all
3. Evidence that **verbal discrimination has no causal effect**, which no prior work tests

The v7 results support all three. The proposal's framing of gap one, "chunk removal as a
training signal", survives. Its implication that the causal measurement approach is itself
new does not.

Chapter 2 section 2.6 and chapter 1's gap statement should be rewritten to say plainly
that the measurement exists in the literature and this work builds a control loop on top
of it. An examiner who knows the RAGonite paper will ask, and the honest answer is
stronger than a dodge.

They also released **ConfQuestions**, 300 conversational questions with ground truth over
215 Confluence pages. Worth citing in the future-work section on other corpora.

### The two Huangs

Two different papers, both cited as "Huang et al.", one year apart, on related topics.

| Cited as | Actually | Paper |
|---|---|---|
| Huang et al., 2025 (proposal) | **Lei** Huang et al. | A Survey on Hallucination in LLMs, ACM TOIS |
| Huang et al., 2024 (chapter 2) | **Jie** Huang et al. | LLMs Cannot Self-Correct Reasoning Yet, ICLR 2024 |

Verified: Jie Huang, Xinyun Chen, Swaroop Mishra, Huaixiu Steven Zheng, Adams Yu, Xinying
Song, Denny Zhou. arXiv:2310.01798.

Give both first initials on every mention, or a reader will assume one is a typo for the
other.

---

## 2. Verified in full

Author lists, years, venues and attributed claims all confirmed.

| # | Reference | Verified detail |
|---|---|---|
| 1 | **Wallat, Heuss, de Rijke, Anand (2024)** | arXiv:2412.18004, submitted 23 Dec 2024. **57% figure confirmed.** The term "post-rationalization" is theirs |
| 2 | **Dassen et al. (2026), FACTUM** | ECIR 2026, Delft, 29 Mar–2 Apr. arXiv:2601.05866v2. Full authors: Dassen, Kotula, Murray, Yates, Lawrie, Kayi, Mayfield, Duh. Attention/FFN coordination-failure claim confirmed |
| 3 | **Magesh et al. (2025)** | JELS 22, 216–242. **17–33% confirmed** (Lexis+ 17%, Westlaw 33%, GPT-4 43%) |
| 4 | **Sun et al. (2025), ReDeEP** | ICLR 2025, arXiv:2410.11414. Zhongxiang Sun et al. Knowledge-FFN / Copying-Head mechanism confirmed |
| 5 | **Cohen-Wang et al. (2024), ContextCite** | NeurIPS 2024, arXiv:2409.00729 |
| 6 | **Liu, Kandpal, Raffel (2025), AttriBoT** | ICLR 2025, arXiv:2411.15102. Fengyuan Liu. >300x speedup claim confirmed |
| 7 | **Zhu et al. (2024), ATM** | EMNLP 2024 main, arXiv:2405.18111. Junda Zhu, Lingyong Yan, Haibo Shi, Dawei Yin, Lei Sha |
| 8 | **Roy et al. (2025)** | WSDM 2025, arXiv:2412.10571. Rishiraj Saha Roy et al. See section 1 |
| 9 | **Es et al. (2024), RAGAS** | EACL 2024 **System Demonstrations**, pp. 150–158 |
| 10 | **Gao et al. (2023), ALCE** | EMNLP 2023, arXiv:2305.14627. **Tianyu** Gao, Yen, Yu, Chen |
| 11 | **Jie Huang et al. (2024)** | ICLR 2024, arXiv:2310.01798 |
| 12 | **Madaan et al. (2023), Self-Refine** | NeurIPS 2023 |
| 13 | **Bai et al. (2022), Constitutional AI** | arXiv:2212.08073 |
| 14 | **Zheng et al. (2023), LLM-as-a-Judge** | NeurIPS 2023 **Datasets and Benchmarks** track, arXiv:2306.05685. Lianmin Zheng et al. Position, verbosity and self-enhancement bias confirmed |

---

## 3. Corrections to make

**RAGAS is a demonstration paper.** EACL 2024 System Demonstrations, pages 150–158. Cite
the track. It affects how much weight the reference carries.

**Zheng is a Datasets and Benchmarks paper**, not NeurIPS main track.

**Gao needs a first initial.** Tianyu Gao. There is other Gao 2023 work in this area and
the bare surname is ambiguous.

**ContextCite is not strictly leave-one-out.** It trains a **linear surrogate model** over
context subsets. AttriBoT is the paper that squarely targets leave-one-out approximation.
The proposal's sentence saying Cohen-Wang "formalised this as leave-one-out attribution"
overstates it. Reword to "formalised context attribution by ablation".

**Dassen et al. needs the full author list**, not "et al." at first mention, since eight
authors are listed.

**Wallat et al. venue.** arXiv December 2024. The proposal says "Published at ICTIR 2025",
which I did not independently confirm. Check the arXiv page for the venue note before
submission.

---

## 4. Not individually searched

Canonical works I did not spend searches on. Confidence is high, but confirm the page
numbers and volume before submission since those are what get typed wrong.

| Reference | Expected detail |
|---|---|
| Lewis et al. (2020) | NeurIPS 33, 9459–9474 |
| Goodfellow et al. (2014) | NeurIPS 27 |
| Reimers and Gurevych (2019) | Sentence-BERT, EMNLP-IJCNLP 2019 |
| Ribeiro et al. (2016) | LIME, KDD 2016 |
| Lundberg and Lee (2017) | SHAP, NeurIPS 2017 |
| Ji et al. (2023) | ACM Computing Surveys 55(12), Article 248 |
| Turpin et al. (2023) | NeurIPS 2023 |
| Lanham et al. (2023) | arXiv:2307.13702 |
| Lei Huang et al. (2025) | ACM TOIS 43(2), Article 42 |
| Zhou et al. (2023) | Findings of EMNLP 2023 |
| Atanasova et al. (2023) | ACL 2023 Short, 222–235 |
| Chen et al. (2024) | AAAI 2024 |

---

## 5. Still outstanding

**FaithScore has no citation.** Chapter 2 section 2.3 names it in prose with no reference
attached. Either find it or drop the mention.

**The systematic database search has not happened.** Everything above is landmark work
plus what the proposal already had. The template requires Scopus, Web of Science, ACM DL,
IEEE Xplore. Two specific gaps:

- **2025 and 2026 work is almost entirely missing.** FACTUM is the only 2026 paper here,
  and it came from the proposal rather than from searching. In a field moving this fast,
  a literature review ending in 2024 will be noticed.
- **No systematic search for prior work on correction loops.** Given that Roy et al.
  turned out to be much closer than expected, there may be other near-neighbours. This is
  the search that most needs doing, because it is the one that determines whether the
  contribution claim holds.

---

## 6. Overall

The proposal's references are in good shape. Whoever assembled them was careful, the
specific numbers quoted are accurate, and nothing was invented.

My chapter 2 additions also all check out, which was not guaranteed given I drafted them
from memory. The precision problems are venue and initial level, not existence level.

The real issue is not citation accuracy. It is that **Roy et al. implemented the
measurement this thesis treats as its own instrument**, and the framing in both the
proposal and chapter 2 needs to acknowledge that directly and relocate the contribution to
the correction loop, where it genuinely holds.
