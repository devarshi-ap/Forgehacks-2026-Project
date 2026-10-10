"""
One-time setup: download FEMA's National Risk Index county table to data/nri_counties.csv.

    python scripts/download_nri.py

Uses FEMA's public ArcGIS service for the NRI (no key needed) and keeps only the
columns this project uses, so the CSV is small enough to commit to the repo.
That way the app never depends on FEMA's servers during the demo.
"""

from pathlib import Path

import pandas as pd
import requests

URL = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
    "National_Risk_Index_Counties/FeatureServer/0/query"
)

"""
Hazard acronyms for FEMA:
HRCN = Hurricane
IFLD = Inland Flooding
CFLD = Coastal Flooding
HWAV = Heat Wave
ERQK = Earthquake
LNDS = Landslide
WFIR = Wildfire

Field acronyms for FEMA:
STCOFIPS = 5-digit county code (ie. 12086 for Miami-Dade County)
STATE = full name of the U.S. State (ie. "California")
STATEABBRV = two-letter postal abbreviation of the state (ie. "CA")
COUNTY = full name of the county (ie. "Miami-Dade")
RISK_SCORE = numeric value (0-100) representing a community's relative risk to natural hazards
RISK_RATING = qualitative text classification of Risk_Score (ie. Very Low, Relatively Low, Relatively Moderate, Relatively High, or Very High)
"""
HAZARDS = ["HRCN", "IFLD", "CFLD", "HWAV", "ERQK", "LNDS", "WFIR"]
FIELDS = ["STCOFIPS", "STATE", "STATEABBRV", "COUNTY", "RISK_SCORE", "RISK_RATNG"] + [
    f"{h}_{s}" for h in HAZARDS for s in ("RISKS", "RISKR")
]
PAGE = 1000
OUT = Path(__file__).resolve().parent.parent / "data" / "nri_counties.csv"


def main() -> None:
    rows, offset = [], 0
    while True:
        resp = requests.get(
            URL,
            params={
                "where": "1=1",
                "outFields": ",".join(FIELDS),
                "returnGeometry": "false",
                "orderByFields": "STCOFIPS",
                "resultOffset": offset,
                "resultRecordCount": PAGE,
                "f": "json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise SystemExit(f"ArcGIS error: {data['error']}")
        batch = [f["attributes"] for f in data.get("features", [])]
        rows += batch
        print(f"Downloaded {len(rows)} counties...")
        if not batch or not data.get("exceededTransferLimit"):
            break
        offset += len(batch)

    df = pd.DataFrame(rows)
    df["STCOFIPS"] = df["STCOFIPS"].astype(str).str.zfill(5)
    OUT.parent.mkdir(exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Saved {len(df)} counties to {OUT}")


if __name__ == "__main__":
    main()
