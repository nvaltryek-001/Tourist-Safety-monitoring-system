# AI safety intelligence

Implemented in `backend/app/services/intelligence.py` (pure Python, unit-tested).

## Pipeline
| Stage | Function | Output |
|---|---|---|
| Feature extraction | `extract_features` | point count, distance, max speed, stationary minutes, mean accuracy, last seen |
| Rule-based checks | `rule_checks` | advisories: `OPEN_SOS`, `NO_LOCATION`, `STALE_LOCATION`, `PROLONGED_STATIONARY` (≥45 min within 50 m), `UNUSUAL_SPEED` (≥45 m/s), `HIGH_RISK_ENTRY`, `REPEATED_RESTRICTED_ENTRY` (≥2 in 24 h) |
| Anomaly detection | `route_deviation` | robust z-score (median/MAD) of the newest point's distance from the tourist's own recent corridor; flags z ≥ 3.5 **and** ≥ 1 km; refuses to run with < 8 points |
| Risk scoring | `score` | 0–100 sum of rule weights → LOW / MEDIUM / HIGH / CRITICAL with every reason listed |
| Zone risk | `zone_risk` | type/risk base + 5 per entry + 15 per SOS inside, with the formula shown |
| Trends | `incident_trends` | daily SOS series, by status/type, median time-to-acknowledge |
| Hazard report | `hazard_report` | summary, tourists needing attention, top zones, explicit limitations |

Every advisory includes `risk_level`, `reason`, `evidence`, `recommended_action`, `timestamp`, `kind: "AI_ADVISORY"` and `confidence: null`.

## Why no trained model
The system holds six tourists and five SOS records and no labelled outcomes. Training Isolation Forest or any classifier on that would produce numbers with no statistical meaning, and fabricated training data would be dishonest. The explainable baseline is designed so a model can later replace `route_deviation` or `score` once real labelled data exists; the API shape stays the same.

## Evaluation
Rules are evaluated with constructed scenarios in `tests/test_pure_logic.py` (stationary, far jump vs. insufficient points, repeated restricted entries, stale and missing location, trend and zone-index arithmetic). These verify behaviour, not real-world precision/recall, which cannot be measured without labelled incidents.

## Advisory vs emergency
Dashboards label advisories "AI advisory — not a confirmed emergency". Only an SOS created by the tourist (or staff on their behalf) is an emergency.
