# Dataset documentation

## Where the data lives
The live database `backend/tourist_safety.db` is **git-ignored** (it holds personal data) and therefore was **not available** to this work, which was done from the GitHub repository. All statements about its contents below come from the project-control evidence already in the repo (`docs/project-control/CHANGELOG.md`, `PROJECT_STATUS.md`, dated 2026-10-17) and from the seeding scripts. Run the read-only audit on the real file to confirm:

```bash
cd backend && python -m app.scripts.audit_db --json db_audit.json
```
or open **Dashboard → Dataset management** after starting the backend on that database.

## The 209 safety-zone records — reconciliation
| Group | Count | Evidence | Nature |
|---|---|---|---|
| `DEMO-KA-001` … `DEMO-KA-200` | 200 | `backend/app/seed_demo_zones.py` inserts exactly 200 with these names (seed 20261016), `RESTRICTED`, radii 100–500 m, near 30 Karnataka district centres, description "SYNTHETIC TEST DATA ONLY"; `activate_demo_zones.py` can activate them | **Synthetic test data — not real hazards** |
| `College Demo Zone 01` … `09` | 9 | Live API check 2026-10-17: IDs 201, 203, 205, 210–215; active, `RESTRICTED`, **200 m** radius | Demonstration zones around the SVIT campus |
| **Total** | **209** | `GET /zones` returned 209 on 2026-10-17 | |

**Conclusion:** the nine SVIT/College demo zones are **included in** the 209, not additional (200 + 9 = 209). The non-contiguous IDs (202, 204, 206–209 missing) suggest earlier rows were removed before the audit; nothing in this work deletes or renumbers zones.

### Radius discrepancy (reported, not changed)
The later specification asked for **50 m** College demo zones; the stored values were **200 m** at the last audit. Following the "do not silently modify" rule, nothing was changed. The data audit shows `college_demo_radii_found` and a warning note. To apply 50 m deliberately, an admin edits each zone in **Safety zones → Edit** (each change is audit-logged with the previous values).

### Overlaps
With 200 m radii, College demo zones whose centres are < 400 m apart overlap. `GET /api/v1/zones/overlaps` and the Dataset page list such pairs; review them — they are not auto-merged.

## Original KML source
`inspect_kml_dataset.py`, `export_kml_to_geojson.py`, `accurate_kml_boundary_analysis.py` and `shortlist_near_rajanukunte.py` read KML files from `backend/data/*.kml` (eco-sensitive zones / protected areas, source year 2022, marked `PENDING_OFFICIAL_REVIEW`, alerts disabled). **That `data/` folder and the KML files are not in the repository**, so the original geographic source could not be verified. No zone in the database is claimed to come from it.

To import real boundaries later: **Dataset management → Import** (GeoJSON or KML) → dry run → review → import (inactive, `PENDING_REVIEW`) → activate individually after verification. Record the source URL, publisher, licence and date in `docs/project-control/DATA_SOURCE_INVENTORY.csv`.

## Open datasets (downloaded 2026-11-02)
See [`datasets/README.md`](../datasets/README.md) and [`datasets/dataset_manifest.csv`](../datasets/dataset_manifest.csv): 42 of 42 source files downloaded and 37 of 37 processing outputs produced by the Datasets workflow. Analysis results are in [`datasets/analysis/report.md`](../datasets/analysis/report.md).

Key processing decisions:
* **Police units → districts.** KSP reports by police unit (commissionerates such as Bengaluru City, police districts, K.G.F., Railways). `datasets/scripts/crime.py` maps them explicitly to the 30 geoBoundaries 2021 polygons (Bengaluru City → Bangalore, Mysuru City + Dist → Mysore, K.G.F. → Kolar, Vijayanagara → Bellary, Bengaluru South → Ramanagara). Railways, CID and Coastal Security Police are statewide and excluded.
* **District risk index** = percentile-ranked registered crimes (55 %), heavy-rain days ≥ 64.5 mm (30 %) and heat days ≥ 40 °C (15 %). OSM police density is *not* an input because OSM police mapping is incomplete (e.g. 2 stations mapped in Vijayapura); it is reported separately as a coverage gap.
* **Open-data zones** (waterfalls, cliffs, protected areas) can be imported from the Dataset page; they are created inactive and `PENDING_REVIEW` and never alert tourists until verified.
* **No ML model** is trained: there are no geocoded incidents or labelled outcomes in any downloaded source.

## Historical incident datasets
`DATA_SOURCE_INVENTORY.csv` (project-control) lists the original candidates. The KSP crime tables (SRC-002/003 family) are now downloaded via OpenCity; NCRB, IMD and tourism statistics remain unavailable in machine-readable form.

## Tourist records
The six tourist accounts and their Gmail allow-list entries exist only in the local database. They are preserved by design: migrations are additive and backed up, and the copy script moves them to PostgreSQL unchanged. No Gmail address or personal detail appears in this repository or its documentation.
