# Kaunas — How the City Grew

An interactive map exploring how Kaunas, Lithuania grew over time — from the
oldest recorded building (1368) through 2026.

The whole thing is a single self-contained HTML file. No build step, no
server, no dependencies beyond Leaflet.js (loaded from a CDN). Open
`index.html` in a browser, or host it anywhere that serves static files
(GitHub Pages works out of the box).

## What it does

Two view modes, switchable at the top of the page:

- **Range** — drag a two-handled slider over a year window (e.g. 1950–1960)
  to see which districts (*seniūnijos*) grew fastest in that window. Shading
  reflects the share of each district's known building stock constructed in
  the selected years.
- **Growth (simulated)** — a cumulative "as of year X" animation that shows
  the built-up area expanding outward from the historic center over time,
  colony-style. Hit ▶ to watch it play out from 1368 to 2026.

Both modes share a "Show district shading overlay" toggle (off by default)
that layers the district-level aggregate coloring on top of the individual
building footprints — useful for seeing citywide/district patterns, but
turned off by default so the actual building shapes stay visible instead of
getting washed out in solid color at high coverage.

## Important limitation — read this before trusting a specific building's date

**Only the "Range" mode's district-level shading is built from real,
verified data.** There is no publicly available dataset that joins
individual buildings to their construction year in Lithuania's open data —
after a fairly thorough search (see "Data sources & how this was built"
below), the best available public data ties construction years to
*districts*, not individual buildings.

The "Growth (simulated)" mode's per-building animation is therefore a
**statistical simulation**: each of the 66,343 real building footprints is
randomly assigned a plausible construction year, sampled from its own
district's real year distribution (fixed random seed, so results are
reproducible). This means the citywide and per-district *timing* is
statistically accurate — Centro fills in first, Šilainiai (a mostly
Soviet/post-independence-era district) fills in last, matching known
history — but any single building's "appearance year" in that mode is
illustrative, not that building's actual verified construction year. A
disclaimer banner explaining this is available via its own checkbox in
Growth mode (off by default, so it doesn't clutter the view, but the
information is one click away).

## Data sources & how this was built

- **Construction years**: Registrų centras (Lithuania's state real estate
  registry), *"Nekilnojamojo turto registre įregistruotų pastatų duomenys
  pagal savivaldybes"* — via
  [data.gov.lt/datasets/1812](https://data.gov.lt/datasets/1812/),
  licensed **CC BY 4.0**. 83,110 valid dated rows for Kaunas city (one
  bogus placeholder "year 0" row excluded). Real years span 1368–2026.
  Only about 49% of rows carry a real district (*seniūnija*) name; the rest
  are logged only at municipality level and are included in citywide totals
  but can't be shown on the map by district.
- **Building footprints & seniūnija boundaries**: Kaunas city's ArcGIS/GRPK
  map service (`digital.kaunas.lt`, published by UAB "Kauno planas") —
  66,343 building footprint polygons and 11 seniūnija boundary polygons for
  Kaunas city, reprojected from EPSG:3346 (LKS-94) to WGS84.

  ⚠️ **Before publishing this publicly, verify the redistribution terms on
  this dataset specifically.** The construction-year data above is
  confirmed CC BY 4.0. The building-footprint geometry's reuse/
  redistribution license was not separately confirmed during development —
  it was only used for personal, non-published exploration up to this
  point. Check the ArcGIS service's terms of use (or reach out to UAB
  "Kauno planas" / Kaunas city directly) before shipping this to a public
  URL, since publishing bakes that geometry into a redistributed file
  rather than just displaying it live from their service.

### Why simulated, not real, per-building dates

A real per-building join was attempted three times and confirmed
structurally impossible with current public data (full evidence, scripts,
and raw output in [`../analysis/`](../analysis/)):

1. Fuzzy-matching buildings by footprint area + district: 0% confident
   matches at any reasonable tolerance.
2. Three-way match — category codes + floor count, spatially anchored via
   point-in-polygon into real building footprints (89.4% anchor rate), plus
   footprint area as a third independent check: **0.6% confident** (1.2% at
   an artificially tight best-case tolerance). A real, verified improvement
   over (1) — roughly 6-12x — but still nowhere near usable. The single
   largest category alone (ordinary 1-story residential buildings) covers
   15,727 anchored candidates with continuously overlapping footprint
   areas — no combination of available attributes separates them into
   unique matches.

Checked and ruled out: national GRPK layer, INSPIRE Buildings WFS,
Registrų centras's own map viewer, and a deeper search of the data.gov.lt
namespace tree — none expose a shared ID between the two datasets. An
official Registrų centras data-need request confirms this gap is known and
unresolved on their end too. A paid bulk data channel exists
(~€0.15–0.25/record from Registrų centras) but was priced out as
disproportionate for a hobby project (~€12,000–21,000 for full Kaunas
coverage).

## Running locally / deploying

It's one file — there's nothing to build.

```bash
# open directly
open index.html          # macOS
xdg-open index.html      # Linux

# or serve it (recommended, avoids any local file:// CORS quirks)
python3 -m http.server 8000
# then visit http://localhost:8000
```

**GitHub Pages**: push `index.html` to a repo, enable Pages in the repo
settings (serve from the root of `main`, or from a `docs/` folder), and
it's live at `https://<username>.github.io/<repo>/`.

Note the file is ~8MB — that's the embedded building geometry and
year-distribution data, simplified and compressed as much as reasonably
possible while keeping the map interactive. Large for a single HTML file,
but well within GitHub's per-file limits.

## License

The code in this repository (the HTML/CSS/JS in `index.html`, excluding
the embedded data) is released under the MIT License — see `LICENSE`.

The embedded construction-year data is CC BY 4.0 (Registrų centras, via
data.gov.lt) — attribution is included in the page footer and above; keep
it if you redistribute or fork this.

The embedded building-footprint geometry's license should be independently
confirmed before public redistribution (see the warning above).
