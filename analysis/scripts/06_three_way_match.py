"""Three-way matching experiment (categorical + spatial + area), proposed
as future work in PHASE2_KEY_SEARCH.md after Phase 3's area+district-only
attempt came back at 0% confident.

For each Dataset A row:
  1. Categorical: filter Dataset D candidates to those sharing A's exact
     (obje_tipas, pask_tipas, aukstu_skaicius) -- same NTR classifier codes
     on both sides (confirmed in PHASE2_KEY_SEARCH.md).
  2. Spatial: each surviving D candidate is already anchored to one
     Dataset B footprint polygon via point-in-polygon (05_anchor_dataset_d.py,
     89.4% anchor rate) -- this gives a real footprint area for that
     candidate, which Dataset D alone never had.
  3. Area: rank/filter those anchored candidates by log-area distance
     between the anchored B polygon's Shape_Area and A's
     atr_uzstatytas_plotas, using the same tolerance band as
     03_match.py (same A-vs-B area-definition skew applies here, since
     the area check is still A-attribute vs B-geometry).

Same SAMPLE_N/SEED as 03_match.py so results are directly comparable to
the original area+district-only baseline.
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
RATIO_LO, RATIO_HI = 0.55, 2.6
ABS_SLACK = 8.0
AMBIGUITY_LOG_MARGIN = 0.35


def build_candidate_index(anchored, b_records):
    """Group anchored D features by (obje_tipas, pask_tipas, aukstu_skaicius),
    each entry carrying its anchored B polygon's Shape_Area (sorted by
    log-area for fast range queries, same pattern as 03_match.py)."""
    groups = {}
    n_no_area = 0
    for a in anchored:
        if a["b_idx"] is None:
            continue
        b = b_records[a["b_idx"]]
        area = b["Shape_Area"]
        if area is None or area <= 0:
            n_no_area += 1
            continue
        key = (a["obje_tipas"], a["pask_tipas"], a["aukstu_skaicius"])
        groups.setdefault(key, []).append((np.log(area), area, a["unikalus_nr"], a["b_idx"]))
    print(f"candidate index: {len(groups)} distinct (obje,pask,floors) categorical keys, "
          f"{n_no_area} anchored D features dropped for missing/zero B area")
    indexed = {}
    for k, v in groups.items():
        v.sort()
        indexed[k] = v
    return indexed


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
        return {"status": "no_match", "n_candidates": 0, "n_categorical_pool": 0}
    ranked = candidates_for(area_a, entries)
    n_cat_pool = len(entries)
    if len(ranked) == 0:
        return {"status": "no_match", "n_candidates": 0, "n_categorical_pool": n_cat_pool}
    if len(ranked) == 1:
        best = ranked[0]
        return {"status": "confident", "n_candidates": 1, "n_categorical_pool": n_cat_pool,
                "best_unikalus_nr": best[0][2], "best_area": best[0][1], "best_dist": best[1]}
    dists = [d for _, d in ranked]
    if dists[1] - dists[0] >= AMBIGUITY_LOG_MARGIN:
        best = ranked[0]
        return {"status": "confident", "n_candidates": len(ranked), "n_categorical_pool": n_cat_pool,
                "best_unikalus_nr": best[0][2], "best_area": best[0][1], "best_dist": dists[0]}
    best = ranked[0]
    return {"status": "ambiguous", "n_candidates": len(ranked), "n_categorical_pool": n_cat_pool,
            "best_unikalus_nr": best[0][2], "best_area": best[0][1], "best_dist": dists[0]}


def main():
    with open("analysis/data/cache/dataset_d_anchored.pkl", "rb") as f:
        anchored = pickle.load(f)
    with open("analysis/data/cache/buildings_with_seniunija.pkl", "rb") as f:
        b_records = pickle.load(f)
    cand_index = build_candidate_index(anchored, b_records)

    a = load_a()
    a = a[(a["stat_pabaigos_metai"].notna())
          & (a["stat_pabaigos_metai"] >= 1700)
          & (a["stat_pabaigos_metai"] <= 2026)
          & (a["atr_uzstatytas_plotas"].notna())
          & (a["atr_uzstatytas_plotas"] > 0)].reset_index(drop=True)
    print("Dataset A rows after basic year/area sanity filter:", len(a))

    random.seed(SEED)
    sample_idx = random.sample(range(len(a)), min(SAMPLE_N, len(a)))
    sample = a.iloc[sample_idx].reset_index(drop=True)
    print("sample size:", len(sample))

    out_rows = []
    for _, row in sample.iterrows():
        try:
            cat_key = (int(row["obje_tipas"]), int(row["pask_tipas"]), int(row["aukstu_skaicius"]))
        except (ValueError, TypeError):
            out_rows.append({
                "dirbt_id": row["dirbt_id"], "status": "no_match",
                "n_candidates": 0, "n_categorical_pool": 0,
                "reason": "unparseable categorical key",
            })
            continue
        res = match_row(row["atr_uzstatytas_plotas"], cat_key, cand_index)
        out = {
            "dirbt_id": row["dirbt_id"],
            "seniunijos_pavad": row["seniunijos_pavad"],
            "obje_tipas": cat_key[0], "pask_tipas": cat_key[1], "aukstu_skaicius": cat_key[2],
            "atr_uzstatytas_plotas": row["atr_uzstatytas_plotas"],
            "stat_pabaigos_metai": row["stat_pabaigos_metai"],
            "status": res["status"],
            "n_candidates": res["n_candidates"],
            "n_categorical_pool": res["n_categorical_pool"],
        }
        if "best_unikalus_nr" in res:
            out.update({
                "best_unikalus_nr": res["best_unikalus_nr"],
                "best_b_area": res["best_area"],
                "log_area_dist": res["best_dist"],
            })
        out_rows.append(out)

    result = pd.DataFrame(out_rows)
    result.to_csv("analysis/output/three_way_match_results_sample.csv", index=False, encoding="utf-8")
    print("wrote analysis/output/three_way_match_results_sample.csv")

    n = len(result)
    counts = result["status"].value_counts()
    print("\n=== overall (three-way: categorical + spatial-anchor + area) ===")
    for k in ["confident", "ambiguous", "no_match"]:
        c = counts.get(k, 0)
        print(f"{k}: {c} ({c/n*100:.1f}%)")
    print("\nmean categorical-only pool size:", result["n_categorical_pool"].mean())
    print("median categorical-only pool size:", result["n_categorical_pool"].median())

    with open("analysis/output/three_way_match_stats.txt", "w", encoding="utf-8") as f:
        f.write(f"n={n}\n")
        for k in ["confident", "ambiguous", "no_match"]:
            c = counts.get(k, 0)
            f.write(f"{k}: {c} ({c/n*100:.1f}%)\n")
        f.write(f"mean categorical pool size: {result['n_categorical_pool'].mean():.1f}\n")
        f.write(f"median categorical pool size: {result['n_categorical_pool'].median():.1f}\n")
    print("wrote analysis/output/three_way_match_stats.txt")


if __name__ == "__main__":
    main()
