"""Current weather from Open-Meteo (free, no key) with a rule-based risk."""

from __future__ import annotations

import time

import httpx

_CACHE: dict[tuple[float, float], tuple[float, dict]] = {}
TTL_SECONDS = 900

# WMO weather interpretation codes (https://open-meteo.com/en/docs)
THUNDER = {95, 96, 99}
HEAVY_RAIN = {65, 67, 82}
FOG = {45, 48}


def weather_risk(cur: dict) -> dict:
    reasons, score = [], 0
    code = int(cur.get("weather_code") or 0)
    rain = float(cur.get("precipitation") or 0)
    gust = float(cur.get("wind_gusts_10m") or 0)
    temp = float(cur.get("temperature_2m") or 0)
    if code in THUNDER:
        score += 40
        reasons.append("Thunderstorm reported")
    if code in HEAVY_RAIN or rain >= 10:
        score += 30
        reasons.append(f"Heavy rain ({rain} mm in the last hour)")
    elif rain >= 2.5:
        score += 15
        reasons.append(f"Moderate rain ({rain} mm)")
    if gust >= 60:
        score += 25
        reasons.append(f"Strong wind gusts ({gust} km/h)")
    if code in FOG:
        score += 15
        reasons.append("Fog: reduced visibility")
    if temp >= 40:
        score += 20
        reasons.append(f"Extreme heat ({temp} °C)")
    level = "HIGH" if score >= 40 else "MEDIUM" if score >= 15 else "LOW"
    return {"weather_risk_score": min(100, score), "weather_risk_level": level, "reasons": reasons}


def current(lat: float, lon: float, client: httpx.Client | None = None) -> dict:
    key = (round(lat, 2), round(lon, 2))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL_SECONDS:
        return {**hit[1], "cached": True}
    params = {
        "latitude": key[0], "longitude": key[1], "timezone": "auto",
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,is_day",
    }
    try:
        resp = (client or httpx).get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8.0)
        resp.raise_for_status()
        cur = resp.json().get("current") or {}
    except Exception as exc:
        return {"available": False, "error": f"weather service unreachable ({type(exc).__name__})"}
    result = {"available": True, "current": cur, **weather_risk(cur),
              "attribution": "Weather data by Open-Meteo.com", "cached": False}
    _CACHE[key] = (time.time(), result)
    return result
