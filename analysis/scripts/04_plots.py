"""Two sanity-check visuals:
1. District-level choropleth: median construction year per seniunija (from
   Dataset A's reliable district-labelled subset), draped over the real
   seniunija boundary polygons (layer 82) -- a geographically valid result
   even though building-level matching failed.
2. Illustrative scatter of a few hundred "best-guess" (nearest log-area,
   loose tolerance) building-level matches from the sample, colored by
   decade, explicitly labeled as unreliable/for-illustration since >99% of
   sample rows were ambiguous.
"""
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
import matplotlib.cm as cm

KAUNAS_CITY_SENIUNIJOS = {
    "Akademijos sen.", "Aleksoto sen.", "Centro sen.", "Dainavos sen.",
    "Eigulių sen.", "Gričiupio sen.", "Panemunės sen.", "Petrašiūnų sen.",
    "Samylų sen.", "Vilijampolės sen.", "Šančių sen.", "Šilainių sen.",
    "Žaliakalnio sen.",
}


def plot_choropleth():
    with open("analysis/data/cache/seniunijos_raw.json", encoding="utf-8") as f:
        sen_feats = json.load(f)
    med = pd.read_csv("analysis/output/median_year_by_seniunija.csv", index_col=0)["stat_pabaigos_metai"]

    fig, ax = plt.subplots(figsize=(9, 9))
    patches = []
    colors = []
    vmin, vmax = 1930, 2010
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = matplotlib.colormaps["viridis"]

    for feat in sen_feats:
        name = feat["attributes"]["SEN_PAV"]
        if name not in KAUNAS_CITY_SENIUNIJOS:
            continue
        year = med.get(name)
        for ring in feat["geometry"]["rings"]:
            if len(ring) < 4:
                continue
            pts = np.array(ring)
            patches.append(MplPolygon(pts, closed=True))
            colors.append(year if year is not None and not np.isnan(year) else vmin)

    pc = PatchCollection(patches, array=np.array(colors), cmap=cmap, norm=norm,
                          edgecolor="white", linewidth=0.6)
    ax.add_collection(pc)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xlabel("Easting, LKS-94 (m)")
    ax.set_ylabel("Northing, LKS-94 (m)")
    ax.set_title("Kaunas: median building construction year by seniunija\n(Dataset A aggregate, district-level only)")
    cbar = fig.colorbar(pc, ax=ax, shrink=0.75)
    cbar.set_label("Median stat_pabaigos_metai")
    fig.tight_layout()
    fig.savefig("analysis/output/choropleth_median_year_by_seniunija.png", dpi=150)
    print("wrote analysis/output/choropleth_median_year_by_seniunija.png")


def plot_illustrative_scatter():
    with open("analysis/data/cache/buildings_with_seniunija.pkl", "rb") as f:
        b_records = pickle.load(f)
    b_by_objid = {r["OBJECTID"]: r for r in b_records}

    df = pd.read_csv("analysis/output/match_results_sample.csv")
    df = df.dropna(subset=["b_OBJECTID", "b_cx", "b_cy"])
    # Take up to 400 rows, preferring the least-ambiguous (lowest n_candidates)
    df = df.sort_values("n_candidates").head(400)

    decades = (df["stat_pabaigos_metai"] // 10 * 10).astype(int)
    fig, ax = plt.subplots(figsize=(9, 9))
    uniq_decades = sorted(decades.unique())
    cmap = matplotlib.colormaps["plasma"].resampled(len(uniq_decades))
    dec_to_color = {d: cmap(i) for i, d in enumerate(uniq_decades)}
    colors = decades.map(dec_to_color)

    ax.scatter(df["b_cx"], df["b_cy"], c=list(colors), s=18, alpha=0.85, edgecolor="k", linewidth=0.2)
    ax.set_aspect("equal")
    ax.set_xlabel("Easting, LKS-94 (m)")
    ax.set_ylabel("Northing, LKS-94 (m)")
    ax.set_title(
        "Illustrative only: 400 lowest-ambiguity 'best-guess' building matches by decade\n"
        "NOT validated -- >99% of the full sample had multiple equally plausible candidates"
    )
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=dec_to_color[d],
                           markeredgecolor="k", markersize=8, label=f"{d}s") for d in uniq_decades]
    ax.legend(handles=handles, title="Decade", loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
    fig.tight_layout()
    fig.savefig("analysis/output/illustrative_scatter_best_guess.png", dpi=150)
    print("wrote analysis/output/illustrative_scatter_best_guess.png")


if __name__ == "__main__":
    plot_choropleth()
    plot_illustrative_scatter()
