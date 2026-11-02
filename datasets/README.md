# SafeTrail open datasets

Everything here is produced by scripts in `datasets/scripts/` and the **Datasets** GitHub workflow (`.github/workflows/datasets.yml`), which downloads, processes, analyses and commits the results. Every source is listed with URL, licence, download date and record count in [`dataset_manifest.csv`](dataset_manifest.csv).

| Folder | Contents |
|---|---|
| `raw/` | Original downloads, unmodified (large files gzip-compressed) + `fetch_log.json` of every attempt |
| `processed/` | Cleaned tables: facilities CSV, daily weather CSV, normalised crime/rainfall CSVs, study-area roads |
| `application_data/` | What the backend serves: GeoJSON layers, KML, `analysis_summary.json`, `district_risk.geojson` |
| `analysis/` | `report.md`, charts (PNG) and result tables (CSV) |
| `synthetic_test_data/` | The 200 `DEMO-KA-*` synthetic zones, regenerated from `seed_demo_zones.py` and labelled synthetic |

## Sources (all downloaded: 42/42)
| Source | Publisher | Licence | What we use |
|---|---|---|---|
| OpenStreetMap (Overpass API) | © OpenStreetMap contributors | ODbL 1.0 | 7,664 emergency facilities (374 police, 3,610 hospitals, 2,345 clinics, 63 fire stations, 1,272 pharmacies), 283 named attractions, 59 protected areas, 204 waterfalls/cliffs, 29,398 road segments around SVIT |
| geoBoundaries gbOpen IND ADM1/ADM2 (2021) | geoBoundaries (source: lgdirectory.gov.in) | ODbL 1.0 | 30 Karnataka district polygons |
| Karnataka State Police crime tables 2022, 2024, 2025 | KSP via OpenCity (data.opencity.in) | Public Domain | District-wise registered crimes, 2024 crime heads, 2022 road accidents |
| KSNDMC district rainfall 2020–2025 | KSNDMC via OpenCity | Public Domain | Official annual rainfall vs normal |
| Open-Meteo Historical Weather (ERA5) | Open-Meteo.com | CC BY 4.0 | 21,930 district-days of temperature, rain, wind (2024–2025) |

Not downloadable as machine-readable data (recorded as `NOT_DOWNLOADED` in the manifest): NCRB *Crime in India* (PDF/XLSX behind an interactive site), Ministry of Tourism statistics (PDF), IMD station data (request-only).

## Re-run
```bash
python datasets/scripts/fetch_all.py            # downloads (needs internet)
python datasets/scripts/process.py              # clean + convert
python datasets/scripts/analyze.py              # report + charts (pip install matplotlib)
```
