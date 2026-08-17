# Kaunas building-age join: Phase 3 three-way match (categorical + spatial + area)

Date: 2026-08-16/17. Follow-up to `PHASE2_KEY_SEARCH.md`'s proposed-but-untested
idea: instead of area+district alone (Phase 1's `PHASE1_JOIN_FEASIBILITY.md`,
0% confident), combine three independent constraints using the newly-found
`unikalus_nr` dataset (Dataset D, data.gov.lt #2838) as a bridge between
Dataset A (construction years) and Dataset B (building footprints).

**Verdict: still a no-go, but a real, verified improvement over the
area+district baseline.** 0.6% confident at realistic tolerance (up from
0.0%), 1.2% at an artificially tight best-case tolerance (up from 0.1%).
Roughly 2-10x better than Phase 1, and nowhere close to the 60-70% bar.

## Note on a pre-existing claim

`docs/README.md` (written by a different Claude session that built the map,
before this pass) asserts a similar experiment was already run: "category +
floor count, spatially anchored via point-in-polygon (92.4% anchor rate):
still only 0.3% confident... largest category... 16,010 candidates." No
script or raw output backing that claim exists anywhere in this repo — it's
a paragraph, not evidence. This pass **independently built and ran the
pipeline from scratch** rather than trust it. The real numbers below
(89.4% anchor rate, largest category 15,727 candidates, 0.6% confident) are
close enough to corroborate that a broadly similar experiment really was
run somewhere, but not identical — treat the numbers in this file as the
verified ones, since they come with the scripts and raw output that produced
them.

## Method

1. **Spatial anchor (`scripts/05_anchor_dataset_d.py`)**: point-in-polygon
   join of Dataset D's 49,487 Kaunas points (real `unikalus_nr` + coordinates,
   EPSG:3346) into Dataset B's 66,343 footprint polygons (same CRS, confirmed
   by direct coordinate-range comparison — no reprojection needed). For each
   D point, build the containing B polygon via `shapely.STRtree` +
   exact `.contains()` test.
   - **44,256 / 49,487 anchored (89.4%)** — a real footprint area now exists
     for each of these D features, which Dataset D alone never had.
   - 5,228 (10.6%) landed outside every B polygon (address point vs. footprint
     digitization mismatch, or the building simply isn't in Kaunas's ArcGIS
     layer under the same geometry).
   - 3 landed inside 2+ overlapping polygons (kept the first, negligible).
2. **Candidate index (`scripts/06_three_way_match.py`)**: grouped the 44,259
   anchored D-B pairs by their exact `(obje_tipas, pask_tipas,
   aukstu_skaicius)` triple — same NTR classifier codes on both the A and D
   side (confirmed in `PHASE2_KEY_SEARCH.md`). **244 distinct combinations**;
   the largest single combination (`obje_tipas=20, pask_tipas=110,
   aukstu_skaicius=1` — ordinary 1-story residential) alone covers **15,727**
   anchored buildings.
3. **Match**: for each Dataset A sample row (same 3,000-row sample, seed 42,
   as Phase 1 — directly comparable), filter to Dataset D candidates sharing
   its exact categorical triple, then rank by log-area distance between the
   anchored B polygon's `Shape_Area` and A's `atr_uzstatytas_plotas`, using
   the same tolerance band as Phase 1 (0.55x-2.6x ratio, ±8 m² absolute
   floor, 0.35 log-distance ambiguity margin — same A-vs-B area-definition
   skew applies here, since the area check is still A's attribute against
   B's geometry).
   - Categorical coverage is much better than district was: `obje_tipas`,
     `pask_tipas`, and `aukstu_skaicius` are **100% populated** in Dataset A
     (vs. district's 49%), so every sample row gets a categorical pool
     to search, not just half.

## Results

**Realistic tolerance** (n=3,000, same sample as Phase 1):

| status | count | % |
|---|---|---|
| confident | 19 | 0.6% |
| ambiguous | 2,944 | 98.1% |
| no_match | 37 | 1.2% |

Mean categorical-only pool size (before area filtering): 5,356. Median:
3,176. Sanity-checked the 19 confident matches directly — they're legitimate,
not coincidental: mostly rows with either an unusually large/distinctive
footprint area (e.g. 6,886 m², 4,832 m², 3,361 m² — few buildings that size
exist per category) or a small categorical pool to begin with (as low as 1-2
candidates), not the common ~50 m² garage/house sizes that dominate the
ambiguity everywhere else.

**Tight-tolerance sensitivity** (`scripts/06b_three_way_tight_sensitivity.py`,
0.9x-1.1x ratio, ±3 m², 0.15 margin — artificially strict best-case ceiling):

| status | count | % |
|---|---|---|
| confident | 37 | 1.2% |
| ambiguous | 2,769 | 92.3% |
| no_match | 194 | 6.5% |

## Comparison to Phase 1

| | Phase 1 (area + district) | Phase 3 (categorical + spatial + area) |
|---|---|---|
| realistic-tolerance confident | 0.0% | **0.6%** |
| tight-tolerance confident (ceiling) | 0.1% | **1.2%** |
| disambiguating signal coverage | district known for 49% of A | categorical triple known for 100% of A |

Real improvement — roughly 6-12x better than area+district alone — but the
underlying structural problem is unchanged: Kaunas has thousands of
near-identical small buildings (the single largest category, ordinary
1-story residential, alone covers 15,727 anchored candidates) and no
combination of publicly available attributes separates them into unique
matches. Adding a third independent constraint measurably helped; it did not
come close to solving it.

## Recommendation

Doesn't change Phase 1's recommendation. The district-level map (with the
per-building view clearly labeled as a statistical simulation) remains the
honest, buildable option. If per-building precision is still wanted, the
next-highest-leverage move is external to this repo: either RC acting on the
open data-need request (publishing `unikalus_nr` in Dataset A directly, or a
`dirbt_id`<->`unikalus_nr` crosswalk table), or RC's paid data extract.

## Files

- `scripts/05_anchor_dataset_d.py` — point-in-polygon spatial join, Dataset D
  points into Dataset B polygons
- `scripts/06_three_way_match.py` — main three-way matcher + stats
- `scripts/06b_three_way_tight_sensitivity.py` — tight-tolerance sensitivity check
- `data/cache/dataset_d_anchored.pkl` — Dataset D features with their
  anchored Dataset B index (or `None` if unanchored)
- `output/dataset_d_anchor_stats.txt` — spatial anchor rate
- `output/three_way_match_results_sample.csv` — per-row match results
- `output/three_way_match_stats.txt`, `output/three_way_tight_sensitivity_stats.txt`
