# src/ingestion/search.py
import requests
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from auth import get_access_token

ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

def search_sentinel2(lon, lat, start_date, end_date, max_cloud_pct=20, max_results=5):
    token = get_access_token()

    filter_query = (
        f"Collection/Name eq 'SENTINEL-2'"
        f" and OData.CSC.Intersects(area=geography'SRID=4326;POINT({lon} {lat})')"
        f" and ContentDate/Start gt {start_date}"
        f" and ContentDate/Start lt {end_date}"
        f" and Attributes/OData.CSC.DoubleAttribute/any("
        f"att:att/Name eq 'cloudCover'"
        f" and att/OData.CSC.DoubleAttribute/Value lt {float(max_cloud_pct)})"
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
    print(f"HTTP Status: {response.status_code}")
    response.raise_for_status()

    products = response.json().get("value", [])
    print(f"✅ Found {len(products)} products.")
    return products

def print_results(products):
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
