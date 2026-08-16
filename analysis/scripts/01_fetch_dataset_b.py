"""Fetch full Dataset B (GRPK building polygons) and the seniunija boundary layer
from Kaunas city's ArcGIS MapServer. Saves raw geometry (EPSG:3346 / LKS-94) as JSON.
"""
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://digital.kaunas.lt/arcgis/rest/services/Miesto_planavimas/BP_2026_m_esama_bukle/MapServer"


def fetch_page(layer_id, out_fields, offset, page_size):
    params = {
        "where": "1=1",
        "outFields": out_fields,
        "returnGeometry": "true",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": page_size,
    }
    r = requests.get(f"{BASE}/{layer_id}/query", params=params, timeout=60)
    r.raise_for_status()
    d = r.json()
    if "error" in d:
        raise RuntimeError(d["error"])
    return d.get("features", [])


def fetch_layer_paginated(layer_id, out_fields, page_size=100, total=None, workers=10):
    if total is None:
        r = requests.get(
            f"{BASE}/{layer_id}/query",
            params={"where": "1=1", "returnCountOnly": "true", "f": "json"},
            timeout=30,
        )
        total = r.json()["count"]
    offsets = list(range(0, total, page_size))
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_page, layer_id, out_fields, off, page_size): off for off in offsets}
        done = 0
        for fut in as_completed(futs):
            off = futs[fut]
            results[off] = fut.result()
            done += 1
            if done % 50 == 0 or done == len(offsets):
                print(f"layer {layer_id}: {done}/{len(offsets)} pages fetched")
    features = []
    for off in offsets:
        features.extend(results[off])
    return features


def main():
    # Seniunija boundaries (small layer, fetch whole)
    sen_feats = fetch_layer_paginated(82, "OBJECTID,SEN_PAV,SEN_KODAS,SAV_KODAS", page_size=1000)
    with open("analysis/data/cache/seniunijos_raw.json", "w", encoding="utf-8") as f:
        json.dump(sen_feats, f, ensure_ascii=False)
    print("seniunijos features:", len(sen_feats))

    # Buildings (66,343 expected). Server hard-caps maxRecordCount at 100.
    bld_feats = fetch_layer_paginated(
        101, "OBJECTID,TOP_ID,GKODAS,PASK,Shape_Area,Shape_Length", page_size=100
    )
    with open("analysis/data/cache/buildings_raw.json", "w", encoding="utf-8") as f:
        json.dump(bld_feats, f, ensure_ascii=False)
    print("building features:", len(bld_feats))


if __name__ == "__main__":
    main()
