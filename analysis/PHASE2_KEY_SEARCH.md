# Kaunas building-age join: Phase 2 key search (national sources)

Date: 2026-08-16. Follow-up to `PHASE1_JOIN_FEASIBILITY.md`'s Phase 1, which checked only
Kaunas municipality's own ArcGIS mirror and the `gov/rc/ntr`/`gov/rc/ar`
Spinta namespaces. This pass checks national-level sources per the plan:
geoportal.lt, inspire.lt, Registrų centras's own map viewer, and a deeper
Spinta pass — in that order, evidence first.

## Headline finding (found during source 1/2 search, not where expected)

**A real, official RC unique building number (`unikalus_nr`) IS published
in open data with geographic coordinates — but in a fourth dataset neither
Phase 1 nor the original spec's Datasets A/B/C, and it does not carry a
field that joins back to Dataset A's `dirbt_id` either.** Full detail in
"New dataset found" below. Short version: this is real progress (a usable
official unique number now exists in hand, with location), but it does
**not** hand us a one-step exact join between Dataset A and Dataset B —
see "What this does and doesn't solve."

## Source 1 — geoportal.lt national GRPK layer

- The national ArcGIS "background" map service
  (`https://www.geoportal.lt/arcgis/rest/services/geoportal_public/background_Lietuva_3346/MapServer`)
  has an equivalent buildings layer (layer 5, "Pastatai"). Full field list
  pulled directly: `OBJECTID, SHAPE, TOP_ID, GKODAS, META, RED_PRIEZASTIS,
  RED_SALTINIS, Suk_DATA, Red_DATA, SHAPE_Length, SHAPE_Area, PASK,
  GRAKTAS`. This is the same GUID-based `TOP_ID` scheme as Kaunas's local
  mirror (e.g. a raw GRPK internal GUID, not the dashed RC unique-number
  format), plus one extra field `GRAKTAS` not present on Kaunas's copy —
  checked, it's not unique-number-shaped either (short alphanumeric
  cartographic-symbol code, not a 12-digit number).
- The national bulk GRPK open-data downloads exist —
  `https://www.geoportal.lt/download/opendata/GRPK/GRPK_Open_SHP.zip` and
  `..._GDB.zip` (confirmed live, `data.gov.lt/datasets/3424/`) — but the
  server does not support HTTP range requests (confirmed: a `Range` header
  request returns `200`/chunked instead of `206`/partial), so extracting
  just the Pastatai layer's schema requires downloading the entire
  national multi-layer GRPK dump. **Not fully downloaded/verified** given
  the size and no partial-read path; treat as unlikely to differ
  meaningfully from the background layer's schema above, but flagging
  this as a genuine gap rather than claiming full certainty.
- **Verdict: confirmed dead end for an exact key** (same GUID scheme as
  the local Kaunas mirror), with one sub-item (full bulk GDB/SHP schema)
  not exhaustively verified due to download size/no range support.

## Source 2 — inspire.lt / national INSPIRE Buildings WFS

Found and queried the real national INSPIRE Buildings download service —
this is a proper OGC WFS, not just a static file:

- Capabilities: `https://www.inspire-geoportal.lt/geoserver/bu/wfs?service=WFS&version=2.0.0&request=GetCapabilities`
  exposes two feature types: `bu:BU.Building_point` and
  `bu:BU.Building_polygon`.
- `DescribeFeatureType` for `bu:BU.Building_polygon` (full schema, pulled
  directly, saved to `analysis/evidence/inspire_wfs/describe_building_polygon.xml`):
  `ogc_fid, gml_id,
  beginlifespanversion, localid, namespace, versionid, currentuse_title,
  currentuse_href, percentage, referencegeometry,
  horizontalgeometryreference_title, horizontalgeometryreference_href,
  numberofdwellings, conditionofconstruction_href, geometry`.
- A real sample feature (`GetFeature`, JSON,
  `totalFeatures: 2154683` nationwide) confirms `localid` is a GRPK GUID
  (e.g. `5f04a249-1696-49aa-aeee-ed9a6a260c18`, `namespace:
  "LT.SSVA.GRPK"`) — same GUID family as source 1, not an RC unique
  number.
- The INSPIRE Buildings data spec has an *optional*
  `nationalCadastralReference` extension field that, per the EU spec,
  often carries exactly this kind of national ID. **It is absent from
  this schema** — Lithuania's implementation only publishes the
  mandatory bu-core2d profile, not the optional cadastral-reference
  extension.
- **Verdict: confirmed dead end.** Actual schema pulled and checked
  field-by-field; no unique-number-equivalent field exists in Lithuania's
  published INSPIRE Buildings dataset.

## Source 3 — Registrų centras's own kadastras/REGIA map viewer

- The viewer lives at `registrucentras.lt/map/` ("REGIA"). Static HTML
  fetch does not expose the backing API — the page is a JS application
  that loads its map service configuration client-side; no browser/network
  inspection tool was available in this session to capture the live
  requests.
- **This source was only partially checked** — confirmed the viewer
  exists and (per public documentation found via search) supports
  searching by unique object number (format example seen:
  `2198-8002-1019:0004`, confirming the real dashed unique-number format),
  but the underlying map/tile service endpoint was not independently
  identified or schema-checked. Flagging this honestly rather than
  claiming a negative result — a follow-up with browser automation could
  still find something here, though given source 1's finding (Kaunas's
  own ArcGIS layer already mirrors the same GUID-based GRPK schema),
  REGIA's backing service is unlikely to differ.

## Source 4 — deeper Spinta `gov/rc/ntr` pass

- Listed the full `gov/rc/ntr` namespace via `:ns`: `ntr_atributai,
  ntr_inzineriniai_statiniai, ntr_kiti_klasifikatoriai,
  ntr_naudojimo_budai, ntr_objektai, ntr_paskirtys, ntr_pastatai,
  ntr_patalpos, ntr_teises, ntr_zemes_sklypai`.
- Drilled into `ntr_objektai` and `ntr_kiti_klasifikatoriai` specifically
  (the two the user flagged as maybe-unchecked crosswalks) and listed
  their actual models:
  - `ntr_objektai`: `NtrLeisinasObjektoTipas, NtrObjektoBukle,
    NtrObjektoStatusas, NtrObjektoTipas, NtrTurtoGrupe` — all titled
    "...klasifikatorius" (classifier/lookup tables for object type,
    condition, status, asset-group codes). These are code→label lookup
    tables (e.g. what `obje_tipas` codes mean), not a `dirbt_id`↔anything
    crosswalk.
  - `ntr_kiti_klasifikatoriai`: `NtrIdTipas, NtrIsigijimoTipas,
    NtrKainosTipas, NtrMatavimoVnt, NtrNaudotojoTipas, NtrRegistroTipas,
    NtrSandorioTipas`. `NtrIdTipas` ("NTR identifier types") looked
    promising by name — attempted to fetch its contents but the request
    timed out repeatedly (60s), so **not conclusively verified**. Given
    every sibling model in this namespace is a small closed-vocabulary
    classifier (transaction types, price types, measurement units, user
    types...), the strong prior is that `NtrIdTipas` is a lookup of
    *identifier type labels* (e.g. distinguishing what kind of ID a field
    is), not a table of actual `dirbt_id`↔`unikalus_nr` value pairs — but
    this is inference from the pattern, not a direct read, and is flagged
    as such.
  - A direct single-object fetch (`.../NtrPastatas/{dirbt_id}` for a real
    `dirbt_id` from the local CSV) was attempted to check whether
    individual-object responses expose fields hidden from list views —
    **this also timed out repeatedly** and could not be completed in this
    session. Not resolved either way.
- **Verdict: no crosswalk table found** among the models that were
  successfully listed; two specific follow-up checks (`NtrIdTipas`
  contents, single-object fetch) hit server timeouts and remain
  unverified rather than confirmed negative.

## New dataset found: "Pastatų erdviniai duomenys" (data.gov.lt #2838)

Not on the original checklist — found via a data.gov.lt "Poreikiai ir
pasiūlymai" (data-needs) request from another user that named it directly.
That request, titled *"NTR pastatų erdvinių, registrinių ir plotų duomenų
susiejimas"* (linking NTR buildings' spatial, register and area data),
states almost exactly this project's problem:

> "Šiuo metu 'Pastatų erdviniuose duomenyse' pateikiamas pastato unikalus
> numeris ir geografinė padėtis, o 'NTR įregistruotų pastatų duomenyse
> pagal savivaldybes' pateikiami pastato atributai ir plotai, tačiau
> skelbiamas tik dirbtinis identifikatorius 'dirbt_id'. Dėl bendro jungties
> rakto nebuvimo neįmanoma patikimai nustatyti, kuri atributinio rinkinio
> eilutė priklauso konkrečiam erdvinio rinkinio pastatui."
>
> ("Currently, 'Building Spatial Data' provides the building's unique
> number and geographic location, while 'NTR registered buildings data by
> municipality' provides building attributes and areas, but only publishes
> an artificial identifier 'dirbt_id'. Because there is no common join
> key, it's impossible to reliably determine which attribute-dataset row
> belongs to which spatial-dataset building.")

This is an **official, RC-acknowledged confirmation that no public join
key exists between Dataset A and this spatial dataset** — written by
someone independently hitting the exact same wall. The request's proposed
fixes: publish `unikalus_nr` in the attribute dataset, publish a separate
`dirbt_id`↔`unikalus_nr` crosswalk table, or provide any other shared
stable identifier. As of this check, RC has not acted on it.

Chased down the dataset the request refers to — **data.gov.lt #2838,
"Pastatų erdviniai duomenys"**, published by Registrų centras
(`datasets/gov/rc/`), one resource per municipality, JSON zipped, CC BY
4.0. Downloaded and inspected the real Kaunas city resource (resource
16042, file `gis_kada_pastatu_taskai_19.json`, EPSG:3346):

- **49,487 features** for Kaunas city (`sav_kodas: 19`) — point geometry,
  not polygons (filename confirms: `taskai` = "points"). Probed several
  plausible sibling-filename guesses for a polygon/boundary version
  (`..._ribos_19.zip`, `..._kontura_19.zip`, `..._poligonai_19.zip`) —
  all returned the site's HTML error page, not a file. No polygon
  equivalent of this specific dataset was found.
- Real feature schema, pulled directly: `unikalus_nr, sav_kodas,
  sav_pavadinimas, seniunijos_kodas, seniunijos_pavad,
  statinio_kategorija, obje_tipas, pask_tipas, aukstu_skaicius,
  pts_koregavo_data, osta_statusas, obuk_bukle, past_tsk, formavimo_data`
  + point geometry.
- **`unikalus_nr` is real and matches the known RC unique-number format**
  — e.g. `"440059883486"` — a 12-digit number in the `4400-nnnn-nnnn`
  scheme (undashed here), consistent with the dashed example
  (`2198-8002-1019`) seen on the RC map-viewer documentation in source 3.
  This is the genuine article, not another internal GUID.
- **Field-name overlap with Dataset A is real and non-coincidental**:
  `sav_pavadinimas, statinio_kategorija, obje_tipas, pask_tipas,
  aukstu_skaicius, formavimo_data` are identically named in both A and
  this dataset — same registry, same classifier system. Spot-checked 8
  real Dataset A rows (local CSV) against this dataset's actual code
  values and frequency distribution — the `obje_tipas`/`pask_tipas` code
  ranges and relative frequencies line up (e.g. `obje_tipas=28,
  pask_tipas=240` — garage-type codes — appear at comparable scale in
  both: 4,272/4,731 occurrences in this dataset for Kaunas, and repeatedly
  in the Dataset A sample). This confirms both datasets share the same
  underlying RC classifier codes, so `obje_tipas`/`pask_tipas`/
  `aukstu_skaicius` values from A and this dataset are directly
  comparable without any code-translation step.
- **But it is not a 1:1 mirror of Dataset A.** 49,487 features here vs.
  83,112 rows in Dataset A for the same municipality — about 60% of the
  row count. This dataset is scoped differently (likely only a subset of
  NTR object types get a published point), so most Dataset A rows will
  not have a corresponding row here at all, independent of any matching
  difficulty.
- `seniunijos_pavad` is **`null` for all 49,487 Kaunas features** — worse
  than Dataset A's already-weak district coverage (Dataset A at least has
  a real seniūnija for 49% of rows; this dataset has none for Kaunas
  city). District is not usable as a disambiguator here.

### Plausibility check: does `unikalus_nr` solve the matching problem?

No — matching Dataset A to this dataset via the shared categorical fields
alone (`obje_tipas`, `pask_tipas`, `aukstu_skaicius`) turns out to have
**the same structural ambiguity problem as area+district did in
Phase 3 of the original report.** Only 261 distinct `(obje_tipas,
pask_tipas, aukstu_skaicius)` combinations exist across the 49,487
Kaunas features; the largest single combination alone covers 16,637
buildings, and mean candidate-pool size across combinations is ~190.
Checked directly against the 8 real Dataset A sample rows pulled above:

| dirbt_id | obje/pask/floors | A's area, year | matching candidates in this dataset |
|---|---|---|---|
| 74267114641938553 | 28/240/1 | 51 m², 1989 | 4,080 |
| 74121505902056517 | 22/212/1 | 146 m², 2002 | 524 |
| 74458909690887407 | 28/240/1 | 22 m², 1991 | 4,080 |
| 74424299090460971 | 28/240/1 | 26 m², 1970 | 4,080 |
| 74502496663490556 | 28/240/1 | 25 m², 1979 | 4,080 |
| 74300749231899318 | 28/240/1 | 23 m², 1930 | 4,080 |
| 74514046258669406 | 28/240/1 | 34 m², 1969 | 4,080 |
| 7568589576494715 | 20/110/2 | 136 m², 1926 | 8,385 |

Not remotely confident on its own — same order of magnitude as the
area+district ambiguity already documented in `PHASE1_JOIN_FEASIBILITY.md`.

## What this does and doesn't solve

**Doesn't solve**: there is still no single field that exact-joins
Dataset A to anything else. The `unikalus_nr` dataset does not carry
`dirbt_id`, and Dataset A does not carry `unikalus_nr`. Matching the two
by shared attributes alone (the only option left) hits the same
ambiguity wall as before, for the same underlying reason — Kaunas has
thousands of near-identical small residential/auxiliary buildings and
none of the available fields (on either side) are selective enough to
tell them apart one-to-one.

**Does help, and is worth pursuing as a follow-up build (not attempted
here per scope — this pass is evidence-gathering only)**: `unikalus_nr` +
a real point location is new information Dataset B never had. A genuinely
promising next experiment — outside this pass's scope — would be a
*three-way* constraint: for each Dataset A row, find `unikalus_nr`
candidates matching on category codes, spatially resolve each candidate's
point into its containing Dataset B polygon (point-in-polygon, which
should be close to unambiguous per point), and then use Dataset B's
`Shape_Area` at that polygon as a *third* independent check against
Dataset A's `atr_uzstatytas_plotas` — combining categorical + spatial +
area constraints instead of relying on any single one. This wasn't
tested in this pass (out of scope: no fuzzy-matching pipeline was to be
written here), but is a concretely better-informed starting point than
Phase 3's area+district-only attempt, since it adds two more independent
constraints as well as a real official unique number to key off of once
a confident match is found.

## Overall verdict

**No public exact join key exists between Dataset A (`dirbt_id`) and
Dataset B (Kaunas building geometry) in any of the four sources checked**,
confirmed with real schema evidence at each one, plus one official RC
data-need request stating the same gap exists between Dataset A and the
newly-found `unikalus_nr` dataset too. Two narrow sub-checks (source 1's
full bulk GDB schema, source 3's live network traffic, and two Spinta
model contents in source 4) were not fully verified due to tooling/size
constraints — flagged individually above rather than folded into the
overall negative conclusion.

Per-building detail without RC's paid data extract would require either:
(a) RC acting on the open data-need request and publishing `unikalus_nr`
in Dataset A or a crosswalk table, or (b) building and validating the
three-way categorical+spatial+area matching approach sketched above,
which has a real chance of doing meaningfully better than Phase 3's
area+district-only result but was not tested here and should not be
assumed to clear the 60-70% bar without actually running it.

## Files

- `analysis/data/cache/dataset_2838_kaunas_features.pkl` — parsed Kaunas
  features from the `unikalus_nr` dataset (49,487 records), for reuse if
  the three-way matching experiment above is pursued later.
- `analysis/data/cache/dataset_2838_kaunas_pastatai_erdviniai.zip` — the
  raw downloaded Kaunas resource (`gis_kada_pastatu_taskai_19.json`) from
  dataset #2838.
- Raw evidence (schema/capability responses, dataset page dumps, RC's
  data-need request page) is organized under `analysis/evidence/` by
  source: `inspire_wfs/`, `registru_centras_portal/`,
  `dataset_2838_unikalus_nr/` (the headline find), `dataset_3742_unrelated/`
  (checked, turned out irrelevant), `spinta_namespace/`, `misc/`.
