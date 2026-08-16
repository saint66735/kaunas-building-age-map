# Kaunas — How the City Grew

An interactive map of Kaunas, Lithuania exploring how the city grew over
time, built from open Lithuanian government data.

**Live map: https://saint66735.github.io/kaunas-building-age-map/**

## What's in this repo

- **[`docs/`](docs/)** — the map itself. A single self-contained HTML file
  (Leaflet.js), served via GitHub Pages from this folder. See
  [`docs/README.md`](docs/README.md) for what it shows, its two view modes,
  and — importantly — which parts are real data vs. statistical simulation.
- **[`analysis/`](analysis/)** — the research behind it: whether individual
  buildings can be joined to their construction year using public data
  (verdict: not at the individual-building level, only district-level), the
  scripts and cached data that back that finding, and a deeper search for a
  real join key across several national data sources. See
  [`analysis/README.md`](analysis/README.md).

## Data sources

- Construction years: Registrų centras (Lithuania's state real estate
  registry), via [data.gov.lt](https://data.gov.lt/datasets/1812/) — CC BY 4.0.
- Building footprints & district boundaries: Kaunas city's ArcGIS/GRPK map
  service (`digital.kaunas.lt`, UAB "Kauno planas"). Redistribution terms
  for this specific layer are not yet independently confirmed — see the
  warning in `docs/README.md`.
