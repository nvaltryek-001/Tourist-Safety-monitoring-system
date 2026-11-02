"""Explainable safety intelligence.

Design (see docs/AI_INTELLIGENCE.md):

1. Feature extraction  – ``extract_features`` turns a tourist's recent
   location history into movement features.
2. Rule-based checks   – ``rule_checks`` produce advisories with evidence.
3. Anomaly detection   – ``route_deviation`` compares the newest position to
   the tourist's *own* recent movement corridor (robust z-score on distance
   from the median centre). It refuses to run with too few points.
4. Risk scoring        – ``score`` combines advisories into a 0–100 score
   with every contributing reason listed.
5. Aggregates          – zone risk, incident trends, hazard report.

Every output is labelled ``AI_ADVISORY``: it is a prompt for a human to look,
never a confirmed emergency. ``confidence`` is reported as ``None`` because
the project does not have labelled outcome data to calibrate against; the
rules are evaluated by unit tests on constructed scenarios instead.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.services.geofence import distance_meters

ADVISORY = "AI_ADVISORY"
MIN_POINTS_FOR_DEVIATION = 8
STATIONARY_RADIUS_M = 50
STATIONARY_MINUTES = 45
DEVIATION_Z = 3.5
DEVIATION_MIN_M = 1000
REPEAT_RESTRICTED_COUNT = 2
REPEAT_WINDOW_HOURS = 24
STALE_MINUTES = 30
HIGH_SPEED_MPS = 45  # ~160 km/h: likely GPS glitch or unusual transport


@dataclass
class Point:
    latitude: float
    longitude: float
    recorded_at: datetime
    accuracy: float | None = None


@dataclass
class Advisory:
    code: str
    risk_level: str  # LOW / MEDIUM / HIGH
    reason: str
    evidence: dict
    recommended_action: str
    weight: int
    kind: str = ADVISORY
    confidence: float | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "kind": self.kind,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------- 1. features
def extract_features(points: list[Point]) -> dict:
    pts = sorted(points, key=lambda p: _utc(p.recorded_at))
    features = {
        "point_count": len(pts),
        "total_distance_m": 0.0,
        "max_speed_mps": 0.0,
        "stationary_minutes": 0.0,
        "last_seen": _utc(pts[-1].recorded_at).isoformat() if pts else None,
        "mean_accuracy_m": None,
    }
    if not pts:
        return features
    accuracies = [p.accuracy for p in pts if p.accuracy is not None]
    if accuracies:
        features["mean_accuracy_m"] = round(statistics.fmean(accuracies), 1)
    for a, b in zip(pts, pts[1:]):
        d = distance_meters(a.latitude, a.longitude, b.latitude, b.longitude)
        features["total_distance_m"] += d
        seconds = (_utc(b.recorded_at) - _utc(a.recorded_at)).total_seconds()
        if seconds > 0:
            features["max_speed_mps"] = max(features["max_speed_mps"], d / seconds)
    # stationary: how long the latest points stayed within STATIONARY_RADIUS_M
    anchor = pts[-1]
    start = anchor.recorded_at
    for p in reversed(pts):
        if distance_meters(anchor.latitude, anchor.longitude, p.latitude, p.longitude) > STATIONARY_RADIUS_M:
            break
        start = p.recorded_at
    features["stationary_minutes"] = round((_utc(anchor.recorded_at) - _utc(start)).total_seconds() / 60, 1)
    features["total_distance_m"] = round(features["total_distance_m"], 1)
    features["max_speed_mps"] = round(features["max_speed_mps"], 2)
    return features


# ---------------------------------------------------------- 3. anomaly
def route_deviation(points: list[Point]) -> dict | None:
    """Robust z-score of the newest point's distance from the median centre
    of the earlier points. Returns None when there is not enough data."""
    pts = sorted(points, key=lambda p: _utc(p.recorded_at))
    if len(pts) < MIN_POINTS_FOR_DEVIATION:
        return None
    history, latest = pts[:-1], pts[-1]
    c_lat = statistics.median(p.latitude for p in history)
    c_lon = statistics.median(p.longitude for p in history)
    dists = [distance_meters(c_lat, c_lon, p.latitude, p.longitude) for p in history]
    med = statistics.median(dists)
    mad = statistics.median(abs(d - med) for d in dists) or 1.0
    latest_d = distance_meters(c_lat, c_lon, latest.latitude, latest.longitude)
    z = 0.6745 * (latest_d - med) / mad
    return {
        "distance_from_corridor_m": round(latest_d, 1),
        "corridor_median_m": round(med, 1),
        "robust_z": round(z, 2),
        "is_anomalous": z >= DEVIATION_Z and latest_d - med >= DEVIATION_MIN_M,
        "points_used": len(history),
    }


# ---------------------------------------------------------- 2. rules
def rule_checks(
    points: list[Point],
    geofence_events: list[dict],
    now: datetime | None = None,
    open_sos: int = 0,
) -> tuple[list[Advisory], dict]:
    now = _utc(now or datetime.now(timezone.utc))
    features = extract_features(points)
    advisories: list[Advisory] = []

    if open_sos:
        advisories.append(Advisory(
            "OPEN_SOS", "HIGH", "Tourist has an open SOS alert (confirmed emergency workflow).",
            {"open_sos": open_sos}, "Follow the SOS command-centre workflow.", 60,
        ))

    if not points:
        advisories.append(Advisory(
            "NO_LOCATION", "LOW", "No location has been shared yet.", {},
            "Ask the tourist to enable location sharing in the app.", 5,
        ))
    else:
        last = _utc(max(p.recorded_at for p in points))
        stale = (now - last).total_seconds() / 60
        if stale > STALE_MINUTES:
            advisories.append(Advisory(
                "STALE_LOCATION", "MEDIUM" if stale < 180 else "HIGH",
                f"No location update for {int(stale)} minutes.",
                {"minutes_since_last_update": int(stale), "last_seen": last.isoformat()},
                "Check connectivity / contact the tourist.", 15 if stale < 180 else 25,
            ))

    if features["stationary_minutes"] >= STATIONARY_MINUTES:
        advisories.append(Advisory(
            "PROLONGED_STATIONARY", "MEDIUM",
            f"Tourist stayed within {STATIONARY_RADIUS_M} m for {features['stationary_minutes']} minutes.",
            {"stationary_minutes": features["stationary_minutes"]},
            "Check in with the tourist if this location is unexpected.", 15,
        ))

    if features["max_speed_mps"] >= HIGH_SPEED_MPS:
        advisories.append(Advisory(
            "UNUSUAL_SPEED", "LOW",
            "Implausibly fast movement between two fixes (possible GPS glitch or unusual transport).",
            {"max_speed_mps": features["max_speed_mps"]},
            "Treat location with caution; verify on next update.", 5,
        ))

    window_start = now - timedelta(hours=REPEAT_WINDOW_HOURS)
    recent_entries = [
        e for e in geofence_events
        if e.get("event_type") == "ENTER" and _utc(e["created_at"]) >= window_start
    ]
    restricted = [e for e in recent_entries if e.get("zone_type") in {"RESTRICTED", "HIGH_RISK"}]
    if restricted:
        latest = max(restricted, key=lambda e: _utc(e["created_at"]))
        advisories.append(Advisory(
            "HIGH_RISK_ENTRY", "HIGH" if latest.get("zone_type") == "RESTRICTED" else "MEDIUM",
            f"Entered {latest.get('zone_name') or 'a restricted zone'} in the last {REPEAT_WINDOW_HOURS} h.",
            {"zone_id": latest.get("zone_id"), "zone_name": latest.get("zone_name"),
             "entered_at": _utc(latest["created_at"]).isoformat()},
            "Send a safety advisory and monitor the tourist's next updates.", 25,
        ))
    if len(restricted) >= REPEAT_RESTRICTED_COUNT:
        advisories.append(Advisory(
            "REPEATED_RESTRICTED_ENTRY", "HIGH",
            f"{len(restricted)} restricted-zone entries in {REPEAT_WINDOW_HOURS} h.",
            {"entries": len(restricted), "zones": sorted({e.get('zone_name') or '' for e in restricted})},
            "Contact the tourist; consider officer follow-up.", 20,
        ))

    deviation = route_deviation(points)
    if deviation and deviation["is_anomalous"]:
        advisories.append(Advisory(
            "ROUTE_DEVIATION", "MEDIUM",
            "Latest position is far outside the tourist's recent movement corridor.",
            deviation, "Confirm the tourist's plans / active trip.", 15,
        ))
    features["route_deviation"] = deviation
    return advisories, features


# ---------------------------------------------------------- 4. scoring
def score(advisories: list[Advisory]) -> dict:
    total = min(100, sum(a.weight for a in advisories))
    level = "LOW"
    if total >= 60:
        level = "CRITICAL"
    elif total >= 35:
        level = "HIGH"
    elif total >= 15:
        level = "MEDIUM"
    return {
        "risk_score": total,
        "risk_level": level,
        "kind": ADVISORY,
        "confidence": None,
        "confidence_note": "Rule-based score; not statistically calibrated (no labelled outcome data).",
        "reasons": [a.reason for a in advisories],
    }


def assess_tourist(points, geofence_events, open_sos=0, now=None) -> dict:
    advisories, features = rule_checks(points, geofence_events, now=now, open_sos=open_sos)
    return {
        **score(advisories),
        "advisories": [a.as_dict() for a in advisories],
        "features": features,
    }


# ---------------------------------------------------------- 5. aggregates
def zone_risk(zones: list[dict], geofence_events: list[dict], sos_points: list[dict]) -> list[dict]:
    entries = Counter(e["zone_id"] for e in geofence_events if e.get("event_type") == "ENTER")
    out = []
    for z in zones:
        sos_inside = sum(
            1 for s in sos_points
            if s.get("latitude") is not None
            and distance_meters(z["latitude"], z["longitude"], s["latitude"], s["longitude"]) <= z["radius_meters"]
        )
        base = {"RESTRICTED": 30, "HIGH_RISK": 25, "CAUTION": 10}.get(z["zone_type"], 0)
        base += {"HIGH": 20, "MEDIUM": 10}.get((z.get("risk_level") or "").upper(), 0)
        value = min(100, base + 5 * entries.get(z["id"], 0) + 15 * sos_inside)
        out.append({
            "zone_id": z["id"],
            "zone_name": z["name"],
            "zone_type": z["zone_type"],
            "entries": entries.get(z["id"], 0),
            "sos_within_zone": sos_inside,
            "risk_index": value,
            "explanation": f"type/risk base {base}, +5 per entry, +15 per SOS inside",
        })
    return sorted(out, key=lambda r: r["risk_index"], reverse=True)


def incident_trends(alerts: list[dict], days: int = 30, now: datetime | None = None) -> dict:
    now = _utc(now or datetime.now(timezone.utc))
    start = (now - timedelta(days=days - 1)).date()
    per_day = defaultdict(int)
    by_status = Counter()
    by_type = Counter()
    response_minutes = []
    for a in alerts:
        created = _utc(a["created_at"])
        by_status[a.get("status") or "OPEN"] += 1
        by_type[a.get("alert_type") or "GENERAL"] += 1
        if created.date() >= start:
            per_day[created.date().isoformat()] += 1
        if a.get("acknowledged_at"):
            response_minutes.append((_utc(a["acknowledged_at"]) - created).total_seconds() / 60)
    series = []
    for i in range(days):
        day = (start + timedelta(days=i)).isoformat()
        series.append({"date": day, "count": per_day.get(day, 0)})
    return {
        "window_days": days,
        "daily": series,
        "by_status": dict(by_status),
        "by_type": dict(by_type),
        "total": len(alerts),
        "median_ack_minutes": round(statistics.median(response_minutes), 1) if response_minutes else None,
        "acknowledged_count": len(response_minutes),
    }


def hazard_report(zone_rows: list[dict], trends: dict, tourist_assessments: list[dict]) -> dict:
    high = [t for t in tourist_assessments if t["risk_level"] in {"HIGH", "CRITICAL"}]
    return {
        "kind": ADVISORY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": (
            f"{len(high)} tourist(s) currently need attention; "
            f"{trends['total']} SOS alerts on record; "
            f"top risk zone: {zone_rows[0]['zone_name'] if zone_rows else 'n/a'}."
        ),
        "tourists_needing_attention": high,
        "top_zones": zone_rows[:10],
        "trends": trends,
        "limitations": [
            "Rule-based and explainable; not a trained predictive model.",
            "Too few tourists/incidents exist to train or validate an ML model honestly.",
            "Synthetic DEMO-KA zones are test data and must not drive real decisions.",
        ],
    }


# ---------------------------------------------------------- 6. operational analytics
MIN_EVENTS_FOR_HOTSPOTS = 5


def grid_hotspots(points: list[dict], cell_m: float = 500, min_count: int = 2) -> dict:
    """Grid-density hotspots over real event coordinates (SOS alerts / zone entries).

    Each point: {"latitude", "longitude", "kind", "created_at"}. Cells are about
    cell_m x cell_m metres. Returns cells with >= min_count events, ranked.
    Refuses to label anything a hotspot when there are too few events.
    """
    pts = [p for p in points if p.get("latitude") is not None and p.get("longitude") is not None]
    if len(pts) < MIN_EVENTS_FOR_HOTSPOTS:
        return {"status": "INSUFFICIENT_DATA", "events": len(pts), "min_events": MIN_EVENTS_FOR_HOTSPOTS, "cells": [],
                "note": f"At least {MIN_EVENTS_FOR_HOTSPOTS} located events are needed before hotspots are reported."}
    import math

    dlat = cell_m / 111_320
    cells: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for p in pts:
        dlon = cell_m / (111_320 * max(0.2, math.cos(math.radians(p["latitude"]))))
        cells[(int(p["latitude"] // dlat), int(p["longitude"] // dlon))].append(p)
    out = []
    for members in cells.values():
        if len(members) < min_count:
            continue
        lat = statistics.fmean(m["latitude"] for m in members)
        lon = statistics.fmean(m["longitude"] for m in members)
        out.append({
            "latitude": round(lat, 6), "longitude": round(lon, 6), "count": len(members),
            "by_kind": dict(Counter(m.get("kind", "EVENT") for m in members)),
            "first": min(_utc(m["created_at"]) for m in members).isoformat(),
            "last": max(_utc(m["created_at"]) for m in members).isoformat(),
        })
    out.sort(key=lambda c: -c["count"])
    return {"status": "OK", "events": len(pts), "cell_m": cell_m, "min_count": min_count, "cells": out,
            "note": "Density of SafeTrail's own recorded events; not a crime prediction."}


def _pct(values: list[float], q: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 1)
    return round(statistics.quantiles(values, n=100, method="inclusive")[q - 1], 1)


def response_times(alerts: list[dict]) -> dict:
    """Minutes from SOS creation to acknowledgement and to resolution."""
    ack, res = [], []
    by_type: dict[str, list[float]] = defaultdict(list)
    by_officer: dict[str, list[float]] = defaultdict(list)
    outcomes = Counter()
    for a in alerts:
        created = _utc(a["created_at"])
        if a.get("acknowledged_at"):
            m = (_utc(a["acknowledged_at"]) - created).total_seconds() / 60
            ack.append(m)
            by_type[a.get("alert_type") or "GENERAL"].append(m)
        if a.get("resolved_at") and a.get("status") == "RESOLVED":
            m = (_utc(a["resolved_at"]) - created).total_seconds() / 60
            res.append(m)
            if a.get("officer"):
                by_officer[a["officer"]].append(m)
            outcomes[a.get("resolution_outcome") or "UNSPECIFIED"] += 1
    return {
        "alerts": len(alerts),
        "acknowledged": len(ack),
        "resolved": len(res),
        "ack_minutes": {"median": _pct(ack, 50), "p90": _pct(ack, 90)},
        "resolve_minutes": {"median": _pct(res, 50), "p90": _pct(res, 90)},
        "ack_median_by_type": {k: _pct(v, 50) for k, v in sorted(by_type.items())},
        "resolve_median_by_officer": {k: _pct(v, 50) for k, v in sorted(by_officer.items())},
        "outcomes": dict(outcomes),
    }


def zone_activity(events: list[dict]) -> list[dict]:
    """Entries, exits, unique tourists and median dwell time per zone from ENTER/EXIT pairs."""
    per_zone: dict[int, dict] = {}
    open_entries: dict[tuple[str, int], datetime] = {}
    for e in sorted(events, key=lambda x: _utc(x["created_at"])):
        z = per_zone.setdefault(e["zone_id"], {"zone_id": e["zone_id"], "zone_name": e.get("zone_name"), "zone_type": e.get("zone_type"),
                                               "entries": 0, "exits": 0, "tourists": set(), "dwell": []})
        key = (e["tourist_code"], e["zone_id"])
        if e["event_type"] == "ENTER":
            z["entries"] += 1
            z["tourists"].add(e["tourist_code"])
            open_entries[key] = _utc(e["created_at"])
        else:
            z["exits"] += 1
            started = open_entries.pop(key, None)
            if started:
                z["dwell"].append((_utc(e["created_at"]) - started).total_seconds() / 60)
    rows = []
    for z in per_zone.values():
        rows.append({"zone_id": z["zone_id"], "zone_name": z["zone_name"], "zone_type": z["zone_type"], "entries": z["entries"],
                     "exits": z["exits"], "unique_tourists": len(z["tourists"]), "median_dwell_minutes": _pct(z["dwell"], 50),
                     "currently_inside": sum(1 for (_, zid) in open_entries if zid == z["zone_id"])})
    return sorted(rows, key=lambda r: -r["entries"])


def movement_summary(points_by_tourist: dict[str, list[Point]]) -> list[dict]:
    rows = []
    for code, pts in points_by_tourist.items():
        f = extract_features(pts)
        dev = route_deviation(pts)
        rows.append({"tourist_code": code, "points": f["point_count"], "distance_km": round(f["total_distance_m"] / 1000, 2),
                     "max_speed_kmh": round(f["max_speed_mps"] * 3.6, 1), "stationary_minutes": f["stationary_minutes"],
                     "route_deviation": bool(dev and dev["is_anomalous"]), "last_seen": f["last_seen"]})
    return sorted(rows, key=lambda r: -r["distance_km"])
