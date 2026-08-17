"""Tight-tolerance sensitivity check for the three-way matcher (06_three_way_match.py),
mirroring 03b_match_tight_sensitivity.py's role for the original area+district
matcher: an artificially strict best-case ceiling on confident-match rate.
"""
import sys
import pickle
import random
import numpy as np
import pandas as pd

sys.path.insert(0, "analysis/scripts")
from load_dataset_a import load as load_a  # noqa: E402
from importlib import import_module

three_way = import_module("06_three_way_match")

SAMPLE_N = 3000
SEED = 42
RATIO_LO, RATIO_HI = 0.9, 1.1
ABS_SLACK = 3.0
AMBIGUITY_LOG_MARGIN = 0.15


def candidates_for(area_a, entries):
    lo = min(np.log(area_a * RATIO_LO), np.log(max(area_a - ABS_SLACK, 0.5)))
    hi = max(np.log(area_a * RATIO_HI), np.log(area_a + ABS_SLACK))
    las = np.array([e[0] for e in entries])
    left = np.searchsorted(las, lo, side="left")
    right = np.searchsorted(las, hi, side="right")
    if right <= left:
        return []
    window = entries[left:right]
    dist = [abs(e[0] - np.log(area_a)) for e in window]
    order = np.argsort(dist)
    return [(window[i], dist[i]) for i in order]


def match_row(area_a, cat_key, cand_index):
    entries = cand_index.get(cat_key)
    if not entries:
        return {"status": "no_match", "n_candidates": 0}
    ranked = candidates_for(area_a, entries)
    if len(ranked) == 0:
        return {"status": "no_match", "n_candidates": 0}
    if len(ranked) == 1:
        return {"status": "confident", "n_candidates": 1}
    dists = [d for _, d in ranked]
    if dists[1] - dists[0] >= AMBIGUITY_LOG_MARGIN:
        return {"status": "confident", "n_candidates": len(ranked)}
    return {"status": "ambiguous", "n_candidates": len(ranked)}


def main():
    with open("analysis/data/cache/dataset_d_anchored.pkl", "rb") as f:
        anchored = pickle.load(f)
    with open("analysis/data/cache/buildings_with_seniunija.pkl", "rb") as f:
        b_records = pickle.load(f)
    cand_index = three_way.build_candidate_index(anchored, b_records)

    a = load_a()
    a = a[(a["stat_pabaigos_metai"].notna()) & (a["stat_pabaigos_metai"] >= 1700)
          & (a["stat_pabaigos_metai"] <= 2026) & (a["atr_uzstatytas_plotas"].notna())
          & (a["atr_uzstatytas_plotas"] > 0)].reset_index(drop=True)

    random.seed(SEED)
    sample_idx = random.sample(range(len(a)), min(SAMPLE_N, len(a)))
    sample = a.iloc[sample_idx].reset_index(drop=True)

    rows = []
    for _, row in sample.iterrows():
        try:
            cat_key = (int(row["obje_tipas"]), int(row["pask_tipas"]), int(row["aukstu_skaicius"]))
        except (ValueError, TypeError):
            rows.append({"status": "no_match", "n_candidates": 0})
            continue
        res = match_row(row["atr_uzstatytas_plotas"], cat_key, cand_index)
        rows.append(res)

    df = pd.DataFrame(rows)
    n = len(df)
    counts = df["status"].value_counts()
    print(f"TIGHT tolerance ({RATIO_LO}-{RATIO_HI}x, margin={AMBIGUITY_LOG_MARGIN}) "
          f"three-way sensitivity check, n={n}")
    for k in ["confident", "ambiguous", "no_match"]:
        c = counts.get(k, 0)
        print(f"{k}: {c} ({c/n*100:.1f}%)")
    print("mean n_candidates (post-area-filter):", df["n_candidates"].mean())

    with open("analysis/output/three_way_tight_sensitivity_stats.txt", "w", encoding="utf-8") as f:
        f.write(f"TIGHT tolerance ({RATIO_LO}-{RATIO_HI}x, margin={AMBIGUITY_LOG_MARGIN}), n={n}\n")
        for k in ["confident", "ambiguous", "no_match"]:
            c = counts.get(k, 0)
            f.write(f"{k}: {c} ({c/n*100:.1f}%)\n")
    print("wrote analysis/output/three_way_tight_sensitivity_stats.txt")


if __name__ == "__main__":
    main()
