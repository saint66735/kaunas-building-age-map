# Kaunas building-age map: join feasibility test

Date: 2026-08-16

## Goal

Determine whether construction-year data (Dataset A, Registrų centras NTR
export) can be joined to building footprint geometry (Dataset B, Kaunas
GRPK/ArcGIS) at the individual-building level, well enough to drive a
per-building color-by-decade map.

**Verdict: no.** Per-building matching is not viable with the data
currently available. A district-level (seniūnija) aggregate is viable and
looks geographically sane — that's the fallback recommendation.

## Phase 1 — key discovery

> **Follow-up note (2026-08-16):** a deeper national-source key search was
> run after this report — checking geoportal.lt's national GRPK layer,
> Lithuania's INSPIRE Buildings WFS, Registrų centras's own map viewer, and
> a deeper Spinta pass. It found a real official RC unique building number
> (`unikalus_nr`) published with coordinates in a dataset not covered
> below, but confirmed it still does not exact-join to Dataset A. Full
> evidence and verdict in `PHASE2_KEY_SEARCH.md`.


Checked for a real shared identifier before writing any fuzzy-matching code,
since a real key would have made this trivial:

- **ArcGIS layer 101 field schema** (`analysis/data/cache/layer101_meta.json`):
  fields are `OBJECTID, Shape, TOP_ID, GKODAS, META, RED_PRIEZA, RED_SALTIN,
  PASK, SHAPE_Leng, Suk_DATA, Red_DATA, Shape_Length, Shape_Area`. `TOP_ID`
  is a raw GUID (e.g. `06EC2A22-2355-40BE-BB99-EE0F7A2F6ECF`) — a GRPK
  cadastre-layer internal identifier, not the Registrų centras "unikalus
  numeris" (which has the dashed-digit-group format `nnnn-nnnn-nnnn`).
  `GKODAS` and the other fields carry no resemblance to that format either.
- **Full ArcGIS MapServer layer listing** (`analysis/data/cache/mapserver_meta.json`):
  no seniūnija boundary layer or address-point layer lives in this service
  alongside the building layer (the seniūnija boundaries used below came
  from a separate service). No bridging table to RC unique numbers.
- **Raw Spinta JSON for `ntr_pastatai`** (`analysis/data/cache/ntrpastatas_sample.json`):
  exposes `id` (matches the CSV's `dirbt_id` — internal Spinta row ID, not an
  RC unique number) and `seniunija._id`, but **no address field and no
  geometry reference of any kind**. This closes off Dataset C (Pastatas /
  AdresoTaskas) as a bridge regardless of its own data-availability issues,
  because Dataset A never carries an address to join C against in the first
  place — the address bridge only helps connect B and C to each other, not
  A to either of them.
- Traced the theoretical C-side bridge anyway for completeness:
  `Pastatas.aob_kodas._id` → `gov/rc/ar/adresai/Adresas.aob_kodas` (integer)
  → `AdresoTaskas`. `AdresoTaskas` currently returns `count()=0` on every
  query form tried — the schema exists but no rows are loaded upstream at
  data.gov.lt right now. Moot given the point above, but worth knowing if
  Dataset C is revisited later.
- `dirbt_id` (Dataset A's only row identifier) is a 17-digit number
  (e.g. `65178183482725541`) that doesn't match the RC unique-number format
  and isn't referenced by anything on the B or C side. Confirmed to be an
  internal Spinta row ID, not a usable key.

**Conclusion: no exact/shared identifier exists between Dataset A and
Dataset B in any of the public schemas checked.** The only usable Dataset
A attributes for matching are area (`atr_uzstatytas_plotas`), floor count
(`aukstu_skaicius`), and district name (`seniunijos_pavad`, populated for
only ~51% of rows — see below). Dataset B has no floor-count-equivalent
field at all, so district + area is the entire fuzzy signal available.

## Phase 2 — pipeline

- Fetched all **66,343** Dataset B building polygons from the ArcGIS
  MapServer (paginated at the server's 100-record page cap) —
  `analysis/scripts/01_fetch_dataset_b.py`, raw output cached in
  `analysis/data/cache/buildings_raw.json`.
- Fetched the Kaunas city seniūnija boundary layer and spatially assigned
  each of the 66,343 B polygons to one of the 13 real seniūnijos by
  centroid-in-polygon — `analysis/scripts/02_assign_seniunija.py`. Only 2
  of 66,343 buildings were unassigned, confirming the geometry and
  boundaries agree on scope. Per-district counts: `analysis/output/b_seniunija_counts.txt`.
- Loaded Dataset A (83,112 rows) from the local pipe-delimited CSV,
  parsing decimal-comma numerics — `analysis/scripts/load_dataset_a.py`.
  **51% of rows (42,353 / 83,112) have `seniunijos_pavad = "Kauno m."`**
  (the municipality-level catch-all, not a real district), which halves
  the value of district as a disambiguating filter for over half the
  dataset. District counts: `analysis/output/seniunijos_a_counts.csv`.
- **Area-field sanity check**: Dataset B's `Shape_Area` is **not**
  directly comparable to Dataset A's `atr_uzstatytas_plotas`. Across the
  interquartile range, B's area runs systematically **1.3x–2.6x larger**
  than A's for what should be the same footprint — most likely because
  GRPK (B) sometimes digitizes an entire physically-attached structure as
  one polygon where NTR (A) registers it as several separate legal
  buildings. This required a wide, asymmetric log-space tolerance band
  (0.55x–2.6x, plus an absolute ±8 m² floor for small buildings) rather
  than a tight ratio check — `analysis/scripts/03_match.py`.
- Matching strategy actually used: for each Dataset A sample row, restrict
  to Dataset B buildings in the same seniūnija if A's district is known
  (else search citywide), then rank B candidates by log-area distance to
  A's footprint. A match is "confident" only if the best candidate is
  clearly closer than the runner-up (log-distance margin ≥ 0.35); otherwise
  "ambiguous" if ≥2 candidates pass the tolerance band, or "no_match" if
  none do.
- The originally-planned point-in-polygon anchor via Dataset C address
  points was not usable — see Phase 1 — so this is area+district fuzzy
  matching only, not the spatial-containment-first approach in the
  original spec.

## Phase 3 — hard numbers

Sample: 3,000 rows drawn from Dataset A (seed 42), matched against all
66,343 Dataset B candidates.

**Generous tolerance (0.55x–2.6x area ratio, the realistic operating
point given the confirmed area-definition mismatch):**

| status | count | % |
|---|---|---|
| confident | 0 | 0.0% |
| ambiguous | 2,982 | 99.4% |
| no_match | 18 | 0.6% |

By pool: district-known rows (n=1,419) — 0.0% confident, 100% ambiguous.
Citywide/"Kauno m." rows (n=1,581) — 0.0% confident, 98.9% ambiguous, 1.1%
no_match. Per-district breakdown (district-known rows only, all 11 real
seniūnijos represented): **every single district independently comes out
at 0.0% confident, 100.0% ambiguous** — see `analysis/output/match_by_district.csv`.

**Tight tolerance sensitivity check (0.9x–1.1x area ratio, an artificially
strict best-case ceiling that would reject many true matches given the
confirmed area skew)** — `analysis/scripts/03b_match_tight_sensitivity.py`:
still only **0.1% confident**, with a mean candidate pool of ~1,783
buildings per query even at this unrealistically tight tolerance.

**This is a structural finding, not a tuning problem.** Kaunas's median
building footprint is ~58 m², a size shared by thousands of buildings per
district (garages, sheds, small houses, apartment-block sections). Area +
district alone cannot separate them, at any reasonable tolerance, and
there is no second attribute on the B side (no floor count, no address, no
year) to break ties. Scaling from the 3,000-row sample to the full 83k
dataset would not change this conclusion — the ambiguity is a property of
the B-side candidate density, not the sample size.

**Go/no-go against the user's ~60–70% "workable" bar: no-go**, by a wide
margin (0% vs. a 60-70% target).

## Phase 4 — visual sanity checks

- `analysis/output/choropleth_median_year_by_seniunija.png` — median
  `stat_pabaigos_metai` per seniūnija from Dataset A, drawn over the real
  seniūnija boundary polygons (no per-building join involved, this is a
  pure aggregate). **Geographically sane**: historic center (Centro,
  Šančių) is darkest/oldest (median ~1935-1940), outer districts
  (Šilainių, Dainavos, the Naujosios Vilnios / Zapyškio periphery) are
  brightest/newest (median 1980s-2020s) — consistent with Kaunas's known
  growth pattern outward from the Old Town/center.
- `analysis/output/illustrative_scatter_best_guess.png` — the 400
  *least-ambiguous* individual "best-guess" matches from the sample,
  plotted at their B-polygon centroid and colored by decade, explicitly
  labeled as illustrative/not validated. **Shows no geographic coherence**
  — decades are randomly interspersed across the city with no discernible
  pattern, which is the visual confirmation of the 0% confident-match
  finding: these "best guesses" are not real matches, just the least-bad
  arbitrary picks.

## Recommendation

1. **Don't build a per-building join** with the current public datasets —
   it's not a tolerance/heuristic problem, it's a data problem (no shared
   ID, and no second disambiguating B-side attribute).
2. **Build the prototype at seniūnija (district) granularity instead.**
   The Phase 4 choropleth shows this is honest, immediately buildable
   (Dataset A aggregates cleanly by district; the seniūnija boundary layer
   is already fetched), and tells a real, geographically sane story about
   how Kaunas grew. This unblocks the "time slider showing how the city
   grew" idea at a coarser resolution than originally hoped.
3. **For real building-level detail later**, the highest-value next step
   is finding an actual RC "unikalus numeris" field exposed on some
   national geoportal building layer (e.g. GeoLitas / Kadastras.lt / the
   national inspire.lt building download instead of Kaunas's local ArcGIS
   layer) — that would be an exact join instead of a fuzzy one, and would
   sidestep this entire area-ambiguity problem. Better fuzzy heuristics on
   the current B layer won't help; the ambiguity is structural.

## Files

- `scripts/01_fetch_dataset_b.py` — fetch & cache all Dataset B polygons
- `scripts/02_assign_seniunija.py` — spatial join B polygons → seniūnija
- `scripts/load_dataset_a.py` — parse the local pipe/decimal-comma CSV
- `scripts/03_match.py` — main fuzzy match + stats (generous tolerance)
- `scripts/03b_match_tight_sensitivity.py` — tight-tolerance sensitivity check
- `scripts/04_plots.py` — Phase 4 visuals
- `data/source/` — the two raw government exports (Dataset A CSV, Dataset C CSV)
- `data/cache/` — cached raw API responses (mapserver/layer metadata, building
  geometry, seniūnija boundaries, Dataset A/B linked pickle)
- `output/` — CSV stats, per-district breakdown, the two PNGs
