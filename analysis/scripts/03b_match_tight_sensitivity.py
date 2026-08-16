"""Sensitivity check: same pipeline as 03_match.py but with a much tighter
area tolerance, to establish a best-case upper bound on confident-match rate
achievable with area+district alone (no other B-side attribute exists).
"""
import sys
import pickle
import random
import numpy as np
import pandas as pd

sys.path.insert(0, "analysis/scripts")
from load_dataset_a import load as load_a  # noqa: E402

SAMPLE_N = 3000
SEED = 42
RATIO_LO, RATIO_HI = 0.9, 1.1
ABS_SLACK = 3.0
AMBIGUITY_LOG_MARGIN = 0.15

named_kaunas_set = {
    "Akademijos sen.", "Aleksoto sen.", "Centro sen.", "Dainavos sen.",
    "Eigulių sen.", "Gričiupio sen.", "Panemunės sen.", "Petrašiūnų sen.",
    "Samylų sen.", "Vilijampolės sen.", "Šančių sen.", "Šilainių sen.",
    "Žaliakalnio sen.",
}


def build_b_index(b_records):
    groups = {}
    all_areas = []
    for i, r in enumerate(b_records):
        if r["Shape_Area"] is None or r["Shape_Area"] <= 0:
            continue
        la = np.log(r["Shape_Area"])
        sen = r["seniunija"]
        groups.setdefault(sen, []).append((la, i))
        all_areas.append((la, i))
    indexed = {}
    for k, v in groups.items():
        v.sort()
        indexed[k] = (np.array([x[0] for x in v]), np.array([x[1] for x in v]))
    all_areas.sort()
    indexed["__ALL__"] = (np.array([x[0] for x in all_areas]), np.array([x[1] for x in all_areas]))
    return indexed


def candidates_for(area_a, group):
    las, idxs = group
    lo = min(np.log(area_a * RATIO_LO), np.log(max(area_a - ABS_SLACK, 0.5)))
    hi = max(np.log(area_a * RATIO_HI), np.log(area_a + ABS_SLACK))
    left = np.searchsorted(las, lo, side="left")
    right = np.searchsorted(las, hi, side="right")
    if right <= left:
        return np.array([]), np.array([])
    cand_las = las[left:right]
    cand_idxs = idxs[left:right]
    dist = np.abs(cand_las - np.log(area_a))
    order = np.argsort(dist)
    return cand_idxs[order], dist[order]


def match_row(area_a, seniunija_a, b_index):
    if seniunija_a in named_kaunas_set and seniunija_a in b_index:
        group = b_index[seniunija_a]
        pool = "district"
    else:
        group = b_index["__ALL__"]
        pool = "citywide"
    cand_idxs, dists = candidates_for(area_a, group)
    if len(cand_idxs) == 0:
        return {"status": "no_match", "pool": pool, "n_candidates": 0}
    if len(cand_idxs) == 1 or dists[1] - dists[0] >= AMBIGUITY_LOG_MARGIN:
        return {"status": "confident", "pool": pool, "n_candidates": int(len(cand_idxs))}
    return {"status": "ambiguous", "pool": pool, "n_candidates": int(len(cand_idxs))}


def main():
    with open("analysis/data/cache/buildings_with_seniunija.pkl", "rb") as f:
        b_records = pickle.load(f)
    b_index = build_b_index(b_records)

    a = load_a()
    a = a[(a["stat_pabaigos_metai"].notna()) & (a["stat_pabaigos_metai"] >= 1700)
          & (a["stat_pabaigos_metai"] <= 2026) & (a["atr_uzstatytas_plotas"].notna())
          & (a["atr_uzstatytas_plotas"] > 0)].reset_index(drop=True)

    random.seed(SEED)
    sample_idx = random.sample(range(len(a)), min(SAMPLE_N, len(a)))
    sample = a.iloc[sample_idx].reset_index(drop=True)

    rows = []
    for _, row in sample.iterrows():
        res = match_row(row["atr_uzstatytas_plotas"], row["seniunijos_pavad"], b_index)
        rows.append(res | {"area": row["atr_uzstatytas_plotas"]})
    df = pd.DataFrame(rows)
    n = len(df)
    counts = df["status"].value_counts()
    print(f"TIGHT tolerance ({RATIO_LO}-{RATIO_HI}x, margin={AMBIGUITY_LOG_MARGIN}) sensitivity check, n={n}")
    for k in ["confident", "ambiguous", "no_match"]:
        c = counts.get(k, 0)
        print(f"{k}: {c} ({c/n*100:.1f}%)")
    print("mean n_candidates:", df["n_candidates"].mean())


if __name__ == "__main__":
    main()
