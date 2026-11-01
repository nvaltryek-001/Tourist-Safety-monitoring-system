# Geofencing

* **Shapes:** circles (centre + radius, Haversine distance) and GeoJSON Polygon/MultiPolygon (ray-casting point-in-polygon with holes).
* **Classification** (`services/geofence.evaluate`): `DANGER` inside a `RESTRICTED`/`HIGH_RISK` zone or a zone with `risk_level=HIGH`; `CAUTION` within 1.5 × radius of such a zone or inside a `MEDIUM`-risk zone; otherwise `SAFE` (meaning "no known zone hazard", never a guarantee). An open SOS overrides to `SOS`. Only **active** zones are evaluated.
* **Entry/exit:** the set of zones a tourist is inside is reconstructed from the newest `geofence_events` per zone; differences produce `ENTER`/`EXIT` rows, a tourist warning and an admin notification for restricted entries, and a `geofence.event` WebSocket message.
* **Validation:** coordinates range-checked; polygons must be closed, ≥4 positions, not self-intersecting; radius 0 < r ≤ 100 km.
* **Overlaps:** `GET /api/v1/zones/overlaps` (centre distance < sum of radii, latitude-sorted pruning). Overlaps are reported, never auto-merged, because some may be intentional.
* **Import/export:** GeoJSON and KML (Point → circle with `radius_meters` property or 200 m default; Polygon kept as geometry). Dry run first; duplicates by name + 6-decimal coordinates are skipped; imports are inactive and `PENDING_REVIEW` unless "activate" is chosen; DTD/ENTITY KML is refused; 5 MB / 5 000 feature limits.
