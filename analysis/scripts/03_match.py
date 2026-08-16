"""Core matching pipeline: join a sample of Dataset A (construction years) rows
to Dataset B (building polygons) using seniunija (where A has one) + footprint
area as a fuzzy key. No exact shared ID exists between A and B (confirmed in
Phase 1), and B carries no floor-count-equivalent field, so area (in log space,
to absorb the systematic A-vs-B area definitional skew) plus district is the
whole signal available.
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

# Tolerance band for B_area / A_area ratio. Derived from the percentile
# comparison in Phase 2 (B's Shape_Area runs ~1.3x-2.6x larger than A's
# atr_uzstatytas_plotas across the interquartile range) -- generous on the
# high side, present on the low side too since some A structures may exceed
# their GRPK footprint parent polygon slice.
RATIO_LO, RATIO_HI = 0.55, 2.6
ABS_SLACK = 8.0  # m^2, absolute floor so tiny buildings aren't over-constrained

# "confident" requires the best candidate to be clearly better than the runner-up
AMBIGUITY_LOG_MARGIN = 0.35  # in log-area distance units


def build_b_index(b_records):
    """Group B records by seniunija; also build one 'ALL' group. Each group is
    stored as (sorted_log_area array, parallel index array into b_records)."""
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
        las = np.array([x[0] for x in v])
        idxs = np.array([x[1] for x in v])
        indexed[k] = (las, idxs)

    all_areas.sort()
    indexed["__ALL__"] = (
        np.array([x[0] for x in all_areas]),
        np.array([x[1] for x in all_areas]),
    )
    return indexed


def candidates_for(area_a, group):
    las, idxs = group
    lo = np.log(area_a * RATIO_LO)
    hi = np.log(area_a * RATIO_HI)
    # widen with absolute slack converted at the boundary
    lo = min(lo, np.log(max(area_a - ABS_SLACK, 0.5)))
    hi = max(hi, np.log(area_a + ABS_SLACK))
    left = np.searchsorted(las, lo, side="left")
    right = np.searchsorted(las, hi, side="right")
    if right <= left:
        return np.array([]), np.array([])
    cand_las = las[left:right]
    cand_idxs = idxs[left:right]
    dist = np.abs(cand_las - np.log(area_a))
    order = np.argsort(dist)
    return cand_idxs[order], dist[order]


def match_row(area_a, seniunija_a, b_index, named_kaunas_set):
    if seniunija_a in named_kaunas_set and seniunija_a in b_index:
        group = b_index[seniunija_a]
        pool = "district"
    else:
        group = b_index["__ALL__"]
        pool = "citywide"
    cand_idxs, dists = candidates_for(area_a, group)
    if len(cand_idxs) == 0:
        return {"status": "no_match", "pool": pool, "n_candidates": 0}
    if len(cand_idxs) == 1:
        return {"status": "confident", "pool": pool, "n_candidates": 1,
                "best_idx": cand_idxs[0], "best_dist": dists[0]}
    # 2+ candidates: confident only if best is clearly better than runner-up
    if dists[1] - dists[0] >= AMBIGUITY_LOG_MARGIN:
        return {"status": "confident", "pool": pool, "n_candidates": int(len(cand_idxs)),
                "best_idx": cand_idxs[0], "best_dist": dists[0]}
    return {"status": "ambiguous", "pool": pool, "n_candidates": int(len(cand_idxs)),
            "best_idx": cand_idxs[0], "best_dist": dists[0]}


def main():
    named_kaunas_set = {
        "Akademijos sen.", "Aleksoto sen.", "Centro sen.", "Dainavos sen.",
        "Eigulių sen.", "Gričiupio sen.", "Panemunės sen.", "Petrašiūnų sen.",
        "Samylų sen.", "Vilijampolės sen.", "Šančių sen.", "Šilainių sen.",
        "Žaliakalnio sen.",
    }

    with open("analysis/data/cache/buildings_with_seniunija.pkl", "rb") as f:
        b_records = pickle.load(f)
    b_index = build_b_index(b_records)

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
        res = match_row(row["atr_uzstatytas_plotas"], row["seniunijos_pavad"], b_index, named_kaunas_set)
        out = {
            "dirbt_id": row["dirbt_id"],
            "seniunijos_pavad": row["seniunijos_pavad"],
            "atr_uzstatytas_plotas": row["atr_uzstatytas_plotas"],
            "stat_pabaigos_metai": row["stat_pabaigos_metai"],
            "aukstu_skaicius": row["aukstu_skaicius"],
            "status": res["status"],
            "pool": res["pool"],
            "n_candidates": res.get("n_candidates", 0),
        }
        if "best_idx" in res:
            b = b_records[res["best_idx"]]
            out.update({
                "b_OBJECTID": b["OBJECTID"],
                "b_TOP_ID": b["TOP_ID"],
                "b_Shape_Area": b["Shape_Area"],
                "b_seniunija": b["seniunija"],
                "b_cx": b["cx"],
                "b_cy": b["cy"],
                "log_area_dist": res["best_dist"],
            })
        out_rows.append(out)

    result = pd.DataFrame(out_rows)
    result.to_csv("analysis/output/match_results_sample.csv", index=False, encoding="utf-8")
    print("wrote analysis/output/match_results_sample.csv")

    # ---- headline stats ----
    n = len(result)
    counts = result["status"].value_counts()
    print("\n=== overall ===")
    for k in ["confident", "ambiguous", "no_match"]:
        c = counts.get(k, 0)
        print(f"{k}: {c} ({c/n*100:.1f}%)")

    print("\n=== by pool (district-known vs citywide/Kauno m.) ===")
    for pool_name, g in result.groupby("pool"):
        cc = g["status"].value_counts()
        tot = len(g)
        line = f"{pool_name} (n={tot}): "
        line += ", ".join(f"{k}={cc.get(k,0)}({cc.get(k,0)/tot*100:.1f}%)" for k in ["confident", "ambiguous", "no_match"])
        print(line)

    print("\n=== by seniunija (district-known rows only) ===")
    named = result[result["pool"] == "district"]
    rows_out = []
    for sen, g in named.groupby("seniunijos_pavad"):
        cc = g["status"].value_counts()
        tot = len(g)
        rows_out.append({
            "seniunija": sen, "n": tot,
            "confident_pct": round(cc.get("confident", 0) / tot * 100, 1),
            "ambiguous_pct": round(cc.get("ambiguous", 0) / tot * 100, 1),
            "no_match_pct": round(cc.get("no_match", 0) / tot * 100, 1),
        })
    district_df = pd.DataFrame(rows_out).sort_values("n", ascending=False)
    district_df.to_csv("analysis/output/match_by_district.csv", index=False, encoding="utf-8")
    print(district_df.to_string(index=False))


if __name__ == "__main__":
    main()
