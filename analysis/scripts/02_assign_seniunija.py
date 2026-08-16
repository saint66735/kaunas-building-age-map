"""Assign each Dataset B building polygon to a seniunija by point-in-polygon
test of its centroid against the Kaunas seniunija boundary layer (layer 82).

Only the seniunijos that belong to Kaunas MIESTO (city) savivaldybe are kept --
layer 82 also carries Kaunas RAJONO (district) seniunijos (Garliava, Domeikava,
Karmelava, etc.) since it's a wider planning-area layer. The Kaunas-city set is
determined empirically as the intersection of names appearing in both Dataset A
(seniunijos_pavad) and layer 82 (SEN_PAV).
"""
import json
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
import pickle

KAUNAS_CITY_SENIUNIJOS = {
    "Akademijos sen.", "Aleksoto sen.", "Centro sen.", "Dainavos sen.",
    "Eigulių sen.", "Gričiupio sen.", "Panemunės sen.", "Petrašiūnų sen.",
    "Samylų sen.", "Vilijampolės sen.", "Šančių sen.", "Šilainių sen.",
    "Žaliakalnio sen.",
}


def main():
    with open("analysis/data/seniunijos_raw.json", encoding="utf-8") as f:
        sen_feats = json.load(f)

    sen_polys = []
    sen_names = []
    for feat in sen_feats:
        name = feat["attributes"]["SEN_PAV"]
        if name not in KAUNAS_CITY_SENIUNIJOS:
            continue
        rings = feat["geometry"]["rings"]
        # esri polygon: first ring = outer (or could have multiple parts/holes);
        # build as a single (multi)polygon via shapely from the rings list.
        from shapely.geometry import Polygon, MultiPolygon
        polys = [Polygon(r) for r in rings if len(r) >= 4]
        geom = polys[0] if len(polys) == 1 else MultiPolygon([(p.exterior.coords, []) for p in polys])
        sen_polys.append(geom)
        sen_names.append(name)

    print(f"kept {len(sen_polys)} seniunija polygon features across {len(set(sen_names))} names")

    tree = STRtree(sen_polys)

    with open("analysis/data/buildings_raw.json", encoding="utf-8") as f:
        bld_feats = json.load(f)

    from shapely.geometry import Polygon as ShpPolygon

    results = []
    unassigned = 0
    for feat in bld_feats:
        attrs = feat["attributes"]
        rings = feat["geometry"]["rings"]
        if not rings:
            continue
        outer = rings[0]
        if len(outer) < 4:
            continue
        poly = ShpPolygon(outer)
        c = poly.centroid
        idxs = tree.query(c)
        sen = None
        for i in idxs:
            if sen_polys[i].contains(c):
                sen = sen_names[i]
                break
        if sen is None:
            unassigned += 1
        results.append({
            "OBJECTID": attrs["OBJECTID"],
            "TOP_ID": attrs["TOP_ID"],
            "PASK": attrs.get("PASK"),
            "Shape_Area": attrs["Shape_Area"],
            "cx": c.x,
            "cy": c.y,
            "seniunija": sen,
            "n_rings": len(rings),
            "ring0": outer,
        })

    print(f"buildings total {len(results)}, unassigned to any Kaunas-city seniunija: {unassigned}")

    with open("analysis/data/buildings_with_seniunija.pkl", "wb") as f:
        pickle.dump(results, f)

    from collections import Counter
    c = Counter(r["seniunija"] for r in results)
    with open("analysis/output/b_seniunija_counts.txt", "w", encoding="utf-8") as f:
        for name, cnt in c.most_common():
            f.write(f"{name}\t{cnt}\n")
    print("wrote analysis/output/b_seniunija_counts.txt")


if __name__ == "__main__":
    main()
