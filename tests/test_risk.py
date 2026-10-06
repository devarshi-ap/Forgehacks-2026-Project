"""Tests for Module 1 (risk lookup).

These use a small made-up sample of the NRI table (tests/fixtures/nri_sample.csv)
and fake the geocoding calls, so they run offline and never depend on real APIs.
The sample numbers are invented for testing, not real FEMA values.

Sample counties and their expected top 3 (scores in brackets):
  Miami-Dade   hurricane (99.5), flood (98.0, coastal), heat (60.0)
  Los Angeles  earthquake (99.9), wildfire (98.0), landslide (95.0)
  Maricopa     heat (92.0), wildfire (75.0), flood (70.0)
  Orleans      hurricane (98.0), flood (96.0)   <- everything else is Very Low or unrated
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

import risk

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = Path(__file__).parent / "fixtures" / "nri_sample.csv"


@pytest.fixture
def nri():
    risk.load_nri.cache_clear()
    return risk.load_nri(SAMPLE)


def top(nri, fips, **kwargs) -> list[str]:
    """Hazard names for a sample county, in ranked order."""
    row = risk.find_county_row(nri, fips, None, None)
    return [r["hazard"] for r in risk.rank_hazards(row, **kwargs)]


def fake_geocoder(monkeypatch, place: dict, fips: str | None):
    monkeypatch.setattr(risk, "geocode", lambda _: place)
    monkeypatch.setattr(risk, "county_fips", lambda lat, lon: fips)


# ---- configuration: risk.py and download_nri.py must agree -----------------

def test_every_hazard_code_is_downloaded():
    """If risk.py uses a code that download_nri.py doesn't fetch, that hazard can never appear."""
    spec = importlib.util.spec_from_file_location("download_nri", ROOT / "scripts" / "download_nri.py")
    download_nri = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(download_nri)

    used = {code for codes in risk.HAZARD_CODES.values() for code in codes}
    legacy = {"RFLD"}  # older FEMA name for inland flooding; intentionally not downloaded
    missing = used - legacy - set(download_nri.HAZARDS)
    assert not missing, f"risk.py uses codes that download_nri.py doesn't download: {missing}"


def test_supported_hazards():
    assert set(risk.HAZARD_CODES) == {"hurricane", "flood", "heat", "earthquake", "landslide", "wildfire"}


# ---- rank_hazards ---------------------------------------------------------

def test_miami_top3_order(nri):
    assert top(nri, "12086") == ["hurricane", "flood", "heat"]


def test_los_angeles_new_hazards_can_outrank_flood(nri):
    assert top(nri, "06037") == ["earthquake", "wildfire", "landslide"]


def test_maricopa_wildfire_second(nri):
    assert top(nri, "04013") == ["heat", "wildfire", "flood"]


def test_flood_uses_worse_of_inland_and_coastal(nri):
    row = risk.find_county_row(nri, "12086", None, None)
    flood = next(r for r in risk.rank_hazards(row) if r["hazard"] == "flood")
    assert flood["score"] == 98.0  # coastal (98) beats inland (80)


def test_not_applicable_hurricane_is_skipped(nri):
    assert "hurricane" not in top(nri, "06037", n=6)


def test_very_low_and_unrated_risks_are_dropped(nri):
    # Orleans: heat/earthquake are Very Low, landslide/wildfire are "No Rating"
    assert top(nri, "22071", n=6) == ["hurricane", "flood"]


def test_n_limits_results(nri):
    assert len(top(nri, "06037", n=2)) == 2


def test_n_large_returns_all_rated_hazards(nri):
    # LA: earthquake, wildfire, landslide, flood, heat (hurricane is Not Applicable)
    assert top(nri, "06037", n=10) == ["earthquake", "wildfire", "landslide", "flood", "heat"]


def test_result_shape(nri):
    row = risk.find_county_row(nri, "04013", None, None)
    first = risk.rank_hazards(row)[0]
    assert first == {"haz