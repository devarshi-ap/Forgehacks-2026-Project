"""
Module 1: Risk lookup
=====================
Mini-problem: given a location, what are the biggest disaster risks there?

    >>> get_top_risks("Miami, FL")
    {
      "location": {"name": "Miami", "county": "Miami-Dade", "state": "FL", "fips": "12086"},
      "risks": [
        {"hazard": "hurricane", "score": 99.9, "rating": "Very High"},
        {"hazard": "flood",     "score": 99.7, "rating": "Very High"},
        {"hazard": "heat",      "score": 61.2, "rating": "Relatively Moderate"}
      ]
    }
    (numbers above are illustrative)

How it works (no AI here; this is plain code on purpose):
  1. Location text -> latitude/longitude      (Open-Meteo geocoding, free, no key)
  2. Latitude/longitude -> county FIPS code    (FCC Area API, free, no key)
  3. County FIPS -> hazard risk scores         (FEMA National Risk Index, local CSV)
  4. Keep the hazards StormSignal supports, sort by score, return the top N.

About the scores: each NRI hazard score is a national percentile (0-100).
A hurricane score of 95 means "this county's hurricane risk is higher than
95% of U.S. counties". So the top risks are the hazards this county is
unusually exposed to compared with the rest of the country.

Run it from the terminal:
    python -m stormsignal.risk "Miami, FL"
    python -m stormsignal.risk 77002
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests

NRI_CSV = Path(__file__).parent / "data" / "nri_counties.csv"

# StormSignal hazard name -> NRI hazard codes.
# Flood combines inland/riverine and coastal flooding; we keep whichever is worse.
# (Newer NRI releases call inland flooding IFLD; older ones call it RFLD.)
HAZARD_CODES: dict[str, list[str]] = {
    "hurricane": ["HRCN"],
    "flood": ["IFLD", "RFLD", "CFLD"], # might remove RFLD
    "heat": ["HWAV"],
    "earthquake": ["ERQK"],
    "landslide": ["LNDS"],
    "wildfire": ["WFIR"],
}

# NRI rating labels, from most to least severe.
RATING_ORDER = [
    "Very High",
    "Relatively High",
    "Relatively Moderate",
    "Relatively Low",
    "Very Low",
]

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
    "PR": "Puerto Rico",
}

HTTP_TIMEOUT = 10  # seconds
HEADERS = {"User-Agent": "StormSignal (ForgeHacks 2026 student project)"}


class LocationNotFound(Exception):
    """Raised when we can't turn the user's text into a U.S. county."""


# --------------------------------------------------------------------------
# Step 1 + 2: location text -> county
# --------------------------------------------------------------------------

def geocode(location: str) -> dict:
    """'Miami, FL' or '77002' -> {name, lat, lon, state_name, county_name}."""
    text = location.strip()
    if not text:
        raise LocationNotFound("Please enter a city or ZIP code.")

    # Split "City, ST" so we can filter by state (Open-Meteo searches names only).
    city, state_name = text, None
    if "," in text:
        city, state_part = [p.strip() for p in text.split(",", 1)]
        state_part = state_part.split()[0] if state_part else ""
        state_name = US_STATES.get(state_part.upper(), state_part.title() or None)

    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 10, "countryCode": "US", "language": "en", "format": "json"},
        headers=HEADERS,
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []

    if state_name:
        results = [r for r in results if r.get("admin1", "").lower() == state_name.lower()]
    if not results:
        raise LocationNotFound(f"Couldn't find '{location}' in the U.S. Try 'City, ST' or a ZIP code.")

    best = results[0]  # Open-Meteo sorts by relevance/population
    return {
        "name": best["name"],
        "lat": best["latitude"],
        "lon": best["longitude"],
        "state_name": best.get("admin1"),
        "county_name": best.get("admin2"),
    }


def county_fips(lat: float, lon: float) -> str | None:
    """Latitude/longitude -> 5-digit county FIPS code (e.g. '12086'), or None."""
    try:
        resp = requests.get(
            "https://geo.fcc.gov/api/census/area",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers=HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
        return results[0]["county_fips"] if results else None
    except (requests.RequestException, KeyError, ValueError):
        return None  # caller falls back to matching the county by name


# --------------------------------------------------------------------------
# Step 3: county -> NRI row
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_nri(path: str | Path = NRI_CSV) -> pd.DataFrame:
    """Load the National Risk Index county table (cached after the first call)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m stormsignal.risk.download_nri` once to create it."
        )
    df = pd.read_csv(path, dtype={"STCOFIPS": str})
    df["STCOFIPS"] = df["STCOFIPS"].str.zfill(5)
    return df


def _normalize_county(name: str) -> str:
    name = (name or "").lower()
    for suffix in (" county", " parish", " borough", " census area", " municipality", " city and borough"):
        name = name.removesuffix(suffix)
    return name.replace("saint ", "st. ").strip()


def find_county_row(nri: pd.DataFrame, fips: str | None, state_name: str | None,
                    county_name: str | None) -> pd.Series:
    """Find the county's NRI row by FIPS code, falling back to state + county name."""
    if fips:
        match = nri[nri["STCOFIPS"] == fips]
        if not match.empty:
            return match.iloc[0]

    if state_name and county_name:
        target = _normalize_county(county_name)
        in_state = nri[nri["STATE"].str.lower() == state_name.lower()]
        match = in_state[in_state["COUNTY"].map(_normalize_county) == target]
        if not match.empty:
            return match.iloc[0]

    raise LocationNotFound("Found the place, but not its county in FEMA's risk data.")


# --------------------------------------------------------------------------
# Step 4: NRI row -> top hazards
# --------------------------------------------------------------------------

def _hazard_score(row: pd.Series, codes: list[str]) -> tuple[float, str] | None:
    """Best (score, rating) across the NRI codes for one StormSignal hazard."""
    best = None
    for code in codes:
        score_col, rating_col = f"{code}_RISKS", f"{code}_RISKR"
        if score_col not in row.index:
            continue  # e.g. this CSV has IFLD, not RFLD
        score = row[score_col]
        rating = row.get(rating_col)
        if pd.isna(score) or rating not in RATING_ORDER:
            continue  # "No Rating", "Not Applicable", "Insufficient Data", blank
        if best is None or score > best[0]:
            best = (float(score), str(rating))
    return best


def rank_hazards(row: pd.Series, n: int = 3, min_rating: str = "Relatively Low") -> list[dict]:
    """Sort supported hazards by NRI score and keep the top n.

    Hazards rated below `min_rating` are dropped, so a county with only two real
    risks returns two, not two plus a "Very Low" filler.
    """
    cutoff = RATING_ORDER.index(min_rating)
    ranked = []
    for hazard, codes in HAZARD_CODES.items():
        result = _hazard_score(row, codes)
        if result and RATING_ORDER.index(result[1]) <= cutoff:
            ranked.append({"hazard": hazard, "score": round(result[0], 1), "rating": result[1]})
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:n]


# --------------------------------------------------------------------------
# Public function: this is what the rest of StormSignal calls
# --------------------------------------------------------------------------

def get_top_risks(location: str, n: int = 3, nri_path: str | Path = NRI_CSV) -> dict:
    """Location text -> county + its top n disaster risks."""
    place = geocode(location)
    fips = county_fips(place["lat"], place["lon"])
    row = find_county_row(load_nri(nri_path), fips, place["state_name"], place["county_name"])
    return {
        "location": {
            "name": place["name"],
            "county": row["COUNTY"],
            "state": row["STATEABBRV"],
            "fips": row["STCOFIPS"],
        },
        "risks": rank_hazards(row, n=n),
    }


def main(argv: list[str]) -> int:
    import json

    query = " ".join(argv[1:]) or "Miami, FL"
    try:
        print(json.dumps(get_top_risks(query), indent=2))
    except LocationNotFound as e:
        print(f"Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
