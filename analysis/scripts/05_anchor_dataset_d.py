"""Spatially anchor Dataset D (data.gov.lt #2838, real unikalus_nr + point
geometry) into Dataset B (Kaunas GRPK building footprint polygons) via
point-in-polygon. This is step 1 of the three-way matching experiment
proposed in PHASE2_KEY_SEARCH.md: categorical (A<->D) + spatial (D->B) +
area (A<->B) constraints combined instead of relying on any single one.

Both datasets are already in EPSG:3346 (LKS-94) -- confirmed by directly
comparing coordinate ranges, no reprojection needed.
"""
import pickle
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree


def main():
    with open("analysis/data/cache/buildings_with_seniunija.pkl", "rb") as f:
        b_records = pickle.load(f)

    b_polys = []
    b_valid_idx = []
    for i, r in enumerate(b_records):
        ring = r["ring0"]
        if len(ring) < 4:
            continue
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        b_polys.append(poly)
        b_valid_idx.append(i)
    print(f"B: {len(b_records)} records, {len(b_polys)} valid polygons indexed")

    tree = STRtree(b_polys)

    with open("analysis/data/cache/dataset_2838_kaunas_features.pkl", "rb") as f:
        d_features = pickle.load(f)
    print(f"D: {len(d_features)} point features")

    anchored = []
    n_zero, n_one, n_multi = 0, 0, 0
    for feat in d_features:
        x, y = feat["geometry"]["coordinates"]
        pt = Point(x, y)
        cand_local_idxs = tree.query(pt)  # candidates by bbox, may over-select
        hits = [b_valid_idx[j] for j in cand_local_idxs if b_polys[j].contains(pt)]
        if len(hits) == 0:
            n_zero += 1
            b_idx = None
        elif len(hits) == 1:
            n_one += 1
            b_idx = hits[0]
        else:
            n_multi += 1
            b_idx = hits[0]  # overlapping/duplicate footprints; take first, flag count
        props = feat["properties"]
        anchored.append({
            "unikalus_nr": props["unikalus_nr"],
            "obje_tipas": props["obje_tipas"],
            "pask_tipas": props["pask_tipas"],
            "aukstu_skaicius": props["aukstu_skaicius"],
            "statinio_kategorija": props.get("statinio_kategorija"),
            "b_idx": b_idx,
            "n_hits": len(hits),
        })

    n = len(d_features)
    print(f"\nanchor results (point-in-polygon into {len(b_polys)} B footprints):")
    print(f"  0 containing polygons (unanchored): {n_zero} ({n_zero/n*100:.1f}%)")
    print(f"  1 containing polygon  (anchored):    {n_one} ({n_one/n*100:.1f}%)")
    print(f"  2+ containing polygons (ambiguous):  {n_multi} ({n_multi/n*100:.1f}%)")
    print(f"  anchor rate (1 or more hits, using first): {(n_one+n_multi)/n*100:.1f}%")

    with open("analysis/data/cache/dataset_d_anchored.pkl", "wb") as f:
        pickle.dump(anchored, f)
    print("\nwrote analysis/data/cache/dataset_d_anchored.pkl")

    with open("analysis/output/dataset_d_anchor_stats.txt", "w", encoding="utf-8") as f:
        f.write(f"D features: {n}\n")
        f.write(f"unanchored (0 hits): {n_zero} ({n_zero/n*100:.1f}%)\n")
        f.write(f"anchored (1 hit): {n_one} ({n_one/n*100:.1f}%)\n")
        f.write(f"ambiguous (2+ hits): {n_multi} ({n_multi/n*100:.1f}%)\n")
        f.write(f"anchor rate (>=1 hit): {(n_one+n_multi)/n*100:.1f}%\n")
    print("wrote analysis/output/dataset_d_anchor_stats.txt")


if __name__ == "__main__":
    main()
