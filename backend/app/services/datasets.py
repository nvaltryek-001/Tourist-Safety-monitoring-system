"""Locate and read the processed open datasets (datasets/application_data)."""

from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]

LAYERS = {
    "districts": "karnataka_districts.geojson",
    "protected_areas": "protected_areas.geojson",
    "attractions": "tourist_attractions.geojson",
    "facilities": "emergency_facilities.geojson",
    "natural_hazards": "natural_hazards.geojson",
    "district_risk": "district_risk.geojson",
}


def data_dir() -> Path | None:
    candidates = [os.getenv("DATASETS_DIR"), BACKEND.parent / "datasets" / "application_data", BACKEND / "app" / "data"]
    for c in candidates:
        if c and Path(c).is_dir() and any(Path(c).iterdir()):
            return Path(c)
    return None


def layer_path(name: str) -> Path | None:
    base = data_dir()
    filename = LAYERS.get(name)
    if not base or not filename:
        return None
    path = base / filename
    return path if path.exists() else None


@lru_cache(maxsize=16)
def _read_json(path: str, mtime: float):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_json(path: Path):
    return _read_json(str(path), path.stat().st_mtime)


def manifest() -> list[dict]:
    root = BACKEND.parent / "datasets" / "dataset_manifest.csv"
    if not root.exists():
        base = data_dir()
        root = base / "dataset_manifest.csv" if base else root
    if not root.exists():
        return []
    with root.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def analysis_summary() -> dict | None:
    base = data_dir()
    if not base:
        return None
    path = base / "analysis_summary.json"
    return read_json(path) if path.exists() else None
