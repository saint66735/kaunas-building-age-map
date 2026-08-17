# Join-feasibility research

This folder is the research trail behind the [interactive map](../docs/) — the
investigation into whether Kaunas building footprints (geometry) can be joined
to their construction years at the individual-building level using public
Lithuanian government data.

**Short answer: no.** Read the two reports below for the full evidence trail.
The map itself uses the district-level result from Phase 1, plus a clearly
labeled statistical simulation for per-building detail (see
[`../docs/README.md`](../docs/README.md)).

## Reports

1. **[`PHASE1_JOIN_FEASIBILITY.md`](PHASE1_JOIN_FEASIBILITY.md)** — the main
   feasibility test. Confirms no shared ID between the construction-year
   dataset and the building-footprint dataset, builds a fuzzy area+district
   matcher anyway to quantify how bad the ambiguity is (0% confident matches
   at any tolerance), and recommends a district-level aggregate instead.
2. **[`PHASE2_KEY_SEARCH.md`](PHASE2_KEY_SEARCH.md)** — a deeper follow-up
   search across four more national-level sources (geoportal.lt, the
   national INSPIRE Buildings WFS, Registrų centras's own map viewer, and a
   deeper pass over the Spinta API) for a real exact join key. Finds a
   genuine official unique building number (`unikalus_nr`) in a dataset not
   originally in scope, but confirms it still doesn't solve the join.
3. **[`PHASE3_THREE_WAY_MATCH.md`](PHASE3_THREE_WAY_MATCH.md)** — builds and
   runs the three-way (categorical + spatial + area) matching idea Phase 2
   only sketched. A real, verified improvement over Phase 1 (0.6% confident
   vs. 0.0%), independently reproduced rather than assumed — but still far
   short of usable.

## Layout

```
scripts/    pipeline: fetch data, spatial-join districts, fuzzy match, plot
data/
  source/   the two raw government CSV exports used as pipeline input
  cache/    cached API responses (building geometry, district boundaries,
            schema samples, the unikalus_nr dataset) so scripts don't need
            to re-fetch everything to reproduce a run
output/     stats (CSV) and the two sanity-check plots (PNG) the scripts produce
evidence/   raw pages/responses backing Phase 2's per-source verdicts,
            grouped by source — see PHASE2_KEY_SEARCH.md for how each maps
            to its verdict
```

## Reproducing a run

```bash
python analysis/scripts/01_fetch_dataset_b.py
python analysis/scripts/02_assign_seniunija.py
python analysis/scripts/03_match.py
python analysis/scripts/03b_match_tight_sensitivity.py
python analysis/scripts/04_plots.py
python analysis/scripts/05_anchor_dataset_d.py
python analysis/scripts/06_three_way_match.py
python analysis/scripts/06b_three_way_tight_sensitivity.py
```

Run from the repo root — the scripts use paths relative to it.
