# src/ingestion/download.py
"""
Download Sentinel-2 products from Copernicus Data Space via OData.
Downloads are saved to data/raw/ and tracked via DVC later.
"""
import os
import requests
from pathlib import Path
from tqdm import tqdm
from auth import get_access_token

RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
ODATA_DOWNLOAD_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"


def download_product(product_id: str, product_name: str) -> Path:
    """
    Download a single Sentinel-2 product by its OData ID.

    Args:
        product_id: The UUID from the search results e.g. 'a1b2c3...'
        product_name: Human-readable name used as the output filename

    Returns:
        Path to the downloaded .zip file
    """
    token = get_access_token()
    output_path = RAW_DATA_DIR / f"{product_name}.zip"

    if output_path.exists():
        print(f"⏭️  Already downloaded: {product_name}")
        return output_path

    url = f"{ODATA_DOWNLOAD_URL}({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"⬇️  Downloading: {product_name}")
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    total_bytes = int(response.headers.get("content-length", 0))
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f, tqdm(
        total=total_bytes, unit="B", unit_scale=True, desc=product_name[:40]
    ) as bar:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

    print(f"✅ Saved to: {output_path}")
    return output_path