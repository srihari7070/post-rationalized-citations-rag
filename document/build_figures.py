"""
Build every data figure for the thesis from the real numbers already reported in
chapters 3-5, so nothing is redrawn by hand or guessed by an image generator.

Palette: Okabe-Ito, a standard colorblind-safe categorical set. Colors are
assigned in a fixed order per series identity (Gemini, Mistral, Llama 3) across
every figure, never re-cycled per chart.

    python document/build_figures.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

# Okabe-Ito, colorblind-safe. Fixed assignment by identity, used across all figures.
GEMINI, MISTRAL, LLAMA = "#0072B2", "#D55E00", "#009E73"
GRAY, LGRAY = "#4D4D4D", "#BBBBBB"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": GRAY, "axes.labelcolor": GRAY,
    "xtick.color": GRAY, "ytick.color": GRAY,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)
    print(f"  {name}.png")


# ---- Figure 1: PRR before/after, all twelve conditions (Table 4.2) --------------
def fig_prr_conditions():
    conds = ["C1", "C2", "C5", "C10", "C3", "C4", "C6", "C11", "C7", "C8", "C9", "C12"]
    gen =   ["Gemini"]*4 + ["Mistral"]*4 + ["Llama 3"]*4
    before = [24.6, 24.2, 26.0, 24.9, 22.2, 22.2, 22.2, 22.2, 20.6, 20.6, 20.6, 20.6]
    after  = [24.6, 24.2, 22.4, 24.7, 22.2, 9.4, 9.4, 9.4, 20.6, 14.1, 14.1, 14.1]
    colors = {"Gemini": GEMINI, "Mistral": MISTRAL, "Llama 3": LLAMA}

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(conds))
    w = 0.35
    ax.bar([i - w/2 for i in x], before, w, color=LGRAY, label="Before correction")
    ax.bar([i + w/2 for i in x], after, w,
           color=[colors[g] for g in gen], label="After correction")
    ax.set_xticks(list(x)); ax.set_xticklabels(conds)
    ax.set_ylabel("Post-rationalisation rate (%)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.legend(frameon=False, loc="upper right")
    for i, g in enumerate(gen):
        if i in (0, 4, 8):
            ax.text(i, -4.5, g, ha="left", fontsize=9, color=colors[g], fontweight="bold")
    ax.set_ylim(0, 30)
    fig.suptitle("Figure 3: Post-rationalisation rate before and after correction, all twelve conditions", fontsize=10, y=1.02)
    save(fig, "fig1_prr_all_conditions")


# ---- Figure 2: discriminator flag rate matrix, same-model vs cross-model (4.5a) -
def fig_discriminator_matrix():
    models = ["Gemini", "Mistral", "Llama 3"]
    data = [[3.1, 9.4, 8.3], [0.0, 0.0, 0.0], [10.7, 7.5, 13.3]]  # rows=discriminator, cols=generator

    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(data, cmap="Blues", vmin=0, vmax=14)
    ax.set_xticks(range(3)); ax.set_xticklabels(models)
    ax.set_yticks(range(3)); ax.set_yticklabels(models)
    ax.set_xlabel("Generator judged"); ax.set_ylabel("Discriminator")
    for i in range(3):
        for j in range(3):
            v = data[i][j]
            txt_color = "white" if v > 7 else GRAY
            weight = "bold" if i == j else "normal"
            ax.text(j, i, f"{v:.1f}%", ha="center", va="center", color=txt_color,
                     fontsize=11, fontweight=weight)
    for i in range(3):
        ax.add_patch(plt.Rectangle((i-0.5, i-0.5), 1, 1, fill=False, edgecolor=GRAY, lw=1.5))
    fig.colorbar(im, ax=ax, label="Citations flagged post-rationalised (%)", shrink=0.8)
    fig.suptitle("Figure 4: Discriminator flag rate, same-model (boxed) vs cross-model", fontsize=10, y=1.02)
    save(fig, "fig2_discriminator_matrix")


# ---- Figure 3: threshold sensitivity, two panels, same x-axis, no dual y-axis ---
def fig_threshold_sensitivity():
    thresholds = [0.75, 0.80, 0.85, 0.90, 0.95]
    mistral_effect = [2.2, 6.2, 12.8, 1.1, 0.0]
    llama_effect   = [2.3, 2.4, 6.4, 1.1, 0.4]
    gemini_effect  = [2.4, 2.5, 3.5, 1.5, 0.6]
    pilot_agreement = [29.6, 44.4, 63.0, 66.7, 74.1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), sharex=True)
    ax1.plot(thresholds, mistral_effect, "-o", color=MISTRAL, label="Mistral")
    ax1.plot(thresholds, llama_effect, "-o", color=LLAMA, label="Llama 3")
    ax1.plot(thresholds, gemini_effect, "-o", color=GEMINI, label="Gemini")
    ax1.set_xlabel("Similarity threshold"); ax1.set_ylabel("Correction effect (pp)")
    ax1.axvline(0.85, color=LGRAY, lw=1, ls="--", zorder=0)
    ax1.legend(frameon=False, fontsize=9)
    ax1.set_title("Correction effect (chapter 4)", fontsize=10)

    ax2.plot(thresholds, pilot_agreement, "-o", color=GRAY)
    ax2.set_xlabel("Similarity threshold"); ax2.set_ylabel("Agreement with pilot annotator (%)")
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax2.axvline(0.85, color=LGRAY, lw=1, ls="--", zorder=0)
    ax2.set_title("Agreement with human judgment (4.10)", fontsize=10)

    fig.suptitle("Figure 9: The correction effect peaks at 0.85; validation agreement does not", fontsize=10, y=1.04)
    save(fig, "fig3_threshold_sensitivity")


# ---- Figure 4: ROC curve, pass-3 validation (AUC 0.691) -------------------------
def fig_roc():
    # Exact per-item points from experiments/results/validation/answer_key.json and
    # the corrected pass-3 CSV (27 usable items: 5 "not really used", 22 "genuinely used").
    points = [
        (0.6807, 0), (0.6897, 0), (0.6999, 0), (0.7549, 0), (0.7653, 0), (0.7668, 0),
        (0.7766, 0), (0.8146, 0), (0.8445, 0), (0.8458, 0), (0.8483, 0), (0.8497, 0),
        (0.8531, 0), (0.862, 1), (0.8702, 1), (0.874, 1), (0.8743, 0), (0.8793, 0),
        (0.8824, 1), (0.8863, 0), (0.896, 0), (0.9351, 0), (0.9482, 0), (0.955, 0),
        (0.9608, 0), (0.9609, 0), (0.995, 1),
    ]
    pos = sum(1 for _, y in points if y == 1)
    neg = sum(1 for _, y in points if y == 0)
    # Threshold sweep over the observed similarity scores, high to low.
    thresholds = sorted({s for s, _ in points}, reverse=True)
    thresholds = [1.01] + thresholds + [0.0]
    fpr, tpr = [], []
    for t in thresholds:
        tp = sum(1 for s, y in points if y == 1 and s >= t)
        fp = sum(1 for s, y in points if y == 0 and s >= t)
        tpr.append(tp / pos)
        fpr.append(fp / neg)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(fpr, tpr, color=GEMINI, lw=2, label="Similarity score (AUC = 0.691)")
    ax.plot([0, 1], [0, 1], color=LGRAY, lw=1, ls="--", label="No signal (AUC = 0.50)")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    fig.suptitle("Figure 6: Similarity score vs. pilot annotator judgment (section 4.10)", fontsize=10, y=1.02)
    # trapezoidal AUC as a sanity check against the reported 0.691
    auc = sum((fpr[i]-fpr[i-1])*(tpr[i]+tpr[i-1])/2 for i in range(1, len(fpr)))
    print(f"    (recomputed AUC = {auc:.3f}, n_pos={pos}, n_neg={neg})")
    save(fig, "fig4_roc_curve")


# ---- Figure 5: macro vs micro aggregation (Table 4.16 / 4.12) -------------------
def fig_macro_micro():
    models = ["Gemini", "Mistral", "Llama 3"]
    macro = [24.6, 22.2, 20.6]
    micro = [43.5, 31.1, 29.2]
    colors = [GEMINI, MISTRAL, LLAMA]

    fig, ax = plt.subplots(figsize=(6, 4.2))
    x = range(3); w = 0.35
    ax.bar([i - w/2 for i in x], macro, w, color=colors, alpha=0.55, label="Macro-average")
    ax.bar([i + w/2 for i in x], micro, w, color=colors, label="Micro-average")
    ax.set_xticks(list(x)); ax.set_xticklabels(models)
    ax.set_ylabel("Baseline PRR (%)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.legend(frameon=False)
    fig.suptitle("Figure 8: Baseline PRR under macro- vs micro-averaging", fontsize=10, y=1.02)
    save(fig, "fig5_macro_micro")


# ---- Figure 6: enumeration finding (Table 4.15 / section 4.11) ------------------
def fig_enumeration():
    n_companies = [1, 2, 3, 4, 5]
    pct_flagged = [12, 29, 51, 71, 82]

    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.plot(n_companies, pct_flagged, "-o", color=GEMINI, lw=2, markersize=7)
    ax.set_xlabel("Companies named in the original answer")
    ax.set_ylabel("Classified post-rationalised (%)")
    ax.set_xticks(n_companies)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_ylim(0, 90)
    for x, y in zip(n_companies, pct_flagged):
        ax.annotate(f"{y}%", (x, y), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9, color=GRAY)
    fig.suptitle("Figure 7: Whole-answer similarity misses enumerated answers", fontsize=10, y=1.02)
    save(fig, "fig6_enumeration")


# ---- Figure 7: GCR by model (Table 4.6) -----------------------------------------
def fig_gcr():
    models = ["Mistral", "Llama 3", "Gemini"]
    gcr = [59.1, 36.4, 14.8]
    colors = [MISTRAL, LLAMA, GEMINI]

    fig, ax = plt.subplots(figsize=(5.5, 4))
    bars = ax.bar(models, gcr, color=colors, width=0.55)
    ax.set_ylabel("Generator correction receptivity (%)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_ylim(0, 70)
    for b, v in zip(bars, gcr):
        ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v}%", ha="center", fontsize=10, color=GRAY)
    fig.suptitle("Figure 5: Generator correction receptivity, by model", fontsize=10, y=1.02)
    save(fig, "fig7_gcr")


# ---- Figure 8: corpus/embedding relational diagram (schematic, TODO item) -------
def fig_corpus_diagram():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")

    def box(x, y, w, h, text, fc="#F0F0F0", ec=GRAY, fontsize=9.5, weight="normal"):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.3))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fontsize,
                weight=weight, wrap=True)

    box(0.3, 2.0, 3.0, 1.6,
        "Company record\nname, founded, size, country,\ncity, sector tags, description",
        fc="#E6F0F7", fontsize=8.8)
    box(3.9, 2.0, 2.6, 1.6, "Profile text\n(fields concatenated\ninto one string)", fontsize=8.8)
    box(7.1, 2.0, 2.6, 1.6, "Embedding vector\n768 dimensions\n(gemini-embedding-001)",
        fc="#E6F0F7", fontsize=8.8)

    ax.annotate("", xy=(3.9, 2.8), xytext=(3.3, 2.8),
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.5))
    ax.annotate("", xy=(7.1, 2.8), xytext=(6.5, 2.8),
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.5))

    ax.text(5.0, 1.4, "linked by a company identifier (foreign key) --\none company = one citable unit (section 3.2)",
            ha="center", fontsize=8.5, color=MISTRAL, style="italic")

    ax.text(5.0, 4.4, "38,692 companies after filtering (of 65,000 raw records) -- ChromaDB, cosine similarity",
            ha="center", fontsize=8.5, color=GRAY)
    save(fig, "fig8_corpus_diagram")


# ---- Figure: the chunk-removal audit loop and the correction loop (3.8) ---------
def fig_experiment_loop():
    fig, ax = plt.subplots(figsize=(11.6, 7.4))
    ax.set_xlim(0, 13); ax.set_ylim(0, 12); ax.axis("off")

    def box(x, y, w, h, text, fc="#F0F0F0", ec=GRAY, fontsize=8.8, weight="normal"):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.3))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fontsize,
                weight=weight, wrap=True)

    def diamond(x, y, w, h, text, fc="#FDF3E7", ec=GRAY, fontsize=8.6):
        cx, cy = x + w/2, y + h/2
        pts = [(cx, y + h), (x + w, cy), (cx, y), (x, cy)]
        ax.add_patch(plt.Polygon(pts, fc=fc, ec=ec, lw=1.3))
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, wrap=True)

    def arrow(xy, xytext, color=GRAY, rad=0.0, lw=1.4):
        ax.annotate("", xy=xy, xytext=xytext,
                    arrowprops=dict(arrowstyle="->", color=color, lw=lw,
                                     connectionstyle=f"arc3,rad={rad}"))

    # outer audit loop
    box(3.2, 10.4, 3.6, 1.2, "Query, and generator\nproduces an answer with citations", fc="#E6F0F7", fontsize=8.4)
    box(3.2, 8.55, 3.6, 1.35,
        "Discriminator removes one cited\npassage and regenerates the answer",
        fc="#E6F0F7", fontsize=8.4)
    diamond(2.6, 6.55, 4.8, 1.85, "Similarity to the\noriginal answer ≥ 0.85?", fontsize=8.2)
    box(0.2, 6.9, 2.2, 1.15, "Yes → genuine\ncitation, next passage", fc="#EAF5EA", fontsize=8.2)
    box(7.6, 6.9, 2.2, 1.15, "No → flag as\npost-rationalised", fc="#FBEAEA", fontsize=8.2)

    arrow((5.0, 9.9), (5.0, 10.4), rad=0)
    arrow((5.0, 8.4), (5.0, 8.55), rad=0)
    arrow((2.4, 7.475), (2.6, 7.475), rad=0)
    arrow((7.6, 7.475), (7.4, 7.475), rad=0)

    # loop back: after a genuine verdict, remove the next cited passage
    arrow((3.2, 9.2), (1.3, 8.05), rad=-0.3)
    ax.text(1.3, 6.55, "loop: next\ncited passage", fontsize=7.4, color=GRAY, ha="center", va="top")

    # correction loop, triggered only if >=1 flag
    diamond(2.6, 4.55, 4.8, 1.65, "≥1 citation flagged\nfor this answer?", fontsize=8.2)
    arrow((5.0, 6.55), (5.0, 6.2), rad=0)
    box(7.6, 4.8, 2.2, 1.1, "No → done,\nanswer stands", fc="#EAF5EA", fontsize=8.2)
    arrow((7.6, 5.375), (7.4, 5.375), rad=0)

    box(3.0, 2.95, 4.0, 1.15,
        "Re-prompt the same generator:\n\"removing this passage did not change the answer\"",
        fc="#FDEFE0", fontsize=8.2)
    arrow((5.0, 4.1), (5.0, 4.55), rad=0)

    box(3.0, 1.4, 4.0, 1.15, "Generator produces a revised answer", fc="#FDEFE0", fontsize=8.2)
    arrow((5.0, 2.55), (5.0, 2.95), rad=0)

    # re-audit loop: revised answer goes back through the discriminator step,
    # routed as a clean elbow around the right side so it crosses no other box
    ax.plot([7.0, 10.4, 10.4, 6.8], [1.975, 1.975, 9.225, 9.225],
            color=MISTRAL, lw=1.6, solid_capstyle="round", zorder=1)
    ax.annotate("", xy=(6.8, 9.225), xytext=(6.9, 9.225),
                arrowprops=dict(arrowstyle="->", color=MISTRAL, lw=1.6))
    ax.text(10.55, 5.6, "re-audited the same way --\nremoval test repeats. This is\nwhere GCR is measured:\ndid the revision actually\ndrop PRR?",
            ha="center", fontsize=7.4, color=MISTRAL, style="italic")

    ax.text(5.0, 11.85,
            "Discriminator role: may be the same model as the generator (same-model condition)\n"
            "or a different one (cross-model condition) -- its verdict never reaches the generator directly,\n"
            "only the audit result does (section 3.8, 5.2).",
            ha="center", fontsize=7.6, color=GRAY)

    save(fig, "fig9_experiment_loop")


def main():
    print(f"writing figures to {OUT}/")
    fig_experiment_loop()
    fig_prr_conditions()
    fig_discriminator_matrix()
    fig_threshold_sensitivity()
    fig_roc()
    fig_macro_micro()
    fig_enumeration()
    fig_gcr()
    fig_corpus_diagram()


if __name__ == "__main__":
    main()
