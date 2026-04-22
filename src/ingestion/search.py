# src/ingestion/search.py
"""
Search the Copernicus OData catalog for Sentinel-2 L2A tiles.
Filters by bounding box, date range, and cloud cover.
"""
import requests
from auth import get_access_token

ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

def search_sentinel2(
    lon: float,
    lat: float,
    start_date: str,
    end_date: str,
    max_cloud_pct: int = 20,
    max_results: int = 5,
) -> list[dict]:
    """
    Search for Sentinel-2 L2A products near a point.

    Args:
        lon: Longitude of area of interest (e.g. 8.68 for Frankfurt)
        lat: Latitude of area of interest (e.g. 50.11 for Frankfurt)
        start_date: ISO format string e.g. '2024-06-01T00:00:00.000Z'
        end_date:   ISO format string e.g. '2024-06-30T00:00:00.000Z'
        max_cloud_pct: Maximum cloud cover percentage (0-100)
        max_results: Maximum number of results to return

    Returns:
        List of product metadata dicts
    """
    token = get_access_token()

    filter_query = (
        f"Collection/Name eq 'SENTINEL-2' "
        f"and OData.CSC.Intersects(area=geography'SRID=4326;POINT({lon} {lat})') "
        f"and ContentDate/Start gt {start_date} "
        f"and ContentDate/Start lt {end_date} "
        f"and Attributes/OData.CSC.DoubleAttribute/any("
        f"att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value lt {max_cloud_pct}.0)"
    )

    response = requests.get(
        ODATA_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "$filter": filter_query,
            "$top": max_results,
            "$orderby": "ContentDate/Start desc",
        },
    )
    response.raise_for_status()

    products = response.json().get("value", [])
    print(f"✅ Found {len(products)} Sentinel-2 L2A products.")
    return products


def print_results(products: list[dict]) -> None:
    """Pretty-print search results."""
    for i, p in enumerate(products, 1):
        cloud = next(
            (a["Value"] for a in p.get("Attributes", [])
             if a.get("Name") == "cloudCover"), "N/A"
        )
        print(f"  {i}. {p['Name']}")
        print(f"     Date: {p['ContentDate']['Start'][:10]}")
        print(f"     Cloud: {cloud}%  |  Size: {p.get('ContentLength', 0) / 1e6:.0f} MB")
        print(f"     ID: {p['Id']}")
        print()