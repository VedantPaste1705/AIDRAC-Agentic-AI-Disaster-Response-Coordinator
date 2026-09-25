#!/usr/bin/env python3
"""
Geographic data loader for Indian locations.

This script downloads and imports Indian geographic data from GeoNames
into the locations table. GeoNames provides a comprehensive gazetteer
with city, district, and state information for India.

Usage:
    python load_geonames.py [--data-file PATH] [--limit N]

The script expects a GeoNames dump file (e.g., IN.txt from geonames.org)
or will download it automatically if not provided.

GeoNames data format (tab-separated):
    geonameid, name, asciiname, alternatenames, latitude, longitude,
    feature class, feature code, country code, cc2, admin1 code,
    admin2 code, admin3 code, admin4 code, population, elevation,
    dem, timezone, modification date

Feature codes we care about:
    PPL (populated place), PPLA (seat of first-order admin),
    PPLA2 (seat of second-order admin), PPLA3 (seat of third-order admin),
    ADM1 (first-order admin), ADM2 (second-order admin), ADM3 (third-order admin)
"""

import argparse
import asyncio
import csv
import gzip
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.location import Location

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("aidrac.load_geonames")

GEONAMES_IN_URL = "http://download.geonames.org/export/dump/IN.zip"
GEONAMES_FEATURE_CODES = {
    "PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLF", "PPLG", "PPLL",
    "PPLR", "PPLS", "PPLW", "PPLX", "PPLA5",
    "ADM1", "ADM2", "ADM3", "ADM4"
}

INDIAN_STATES = {
    "AN": "Andaman and Nicobar Islands",
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CH": "Chandigarh",
    "CT": "Chhattisgarh",
    "DN": "Dadra and Nagar Haveli and Daman and Diu",
    "DD": "Daman and Diu",
    "DL": "Delhi",
    "GA": "Goa",
    "GJ": "Gujarat",
    "HR": "Haryana",
    "HP": "Himachal Pradesh",
    "JK": "Jammu and Kashmir",
    "JH": "Jharkhand",
    "KA": "Karnataka",
    "KL": "Kerala",
    "LA": "Ladakh",
    "LD": "Lakshadweep",
    "MP": "Madhya Pradesh",
    "MH": "Maharashtra",
    "MN": "Manipur",
    "ML": "Meghalaya",
    "MZ": "Mizoram",
    "NL": "Nagaland",
    "OR": "Odisha",
    "PB": "Punjab",
    "PY": "Puducherry",
    "RJ": "Rajasthan",
    "SK": "Sikkim",
    "TN": "Tamil Nadu",
    "TG": "Telangana",
    "TR": "Tripura",
    "UP": "Uttar Pradesh",
    "UT": "Uttarakhand",
    "WB": "West Bengal",
}

INDIAN_STATES_REVERSE = {v.lower(): k for k, v in INDIAN_STATES.items()}


def _normalize_name(name: str) -> str:
    import re
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


async def load_geonames(data_file: Optional[str] = None, limit: Optional[int] = None) -> int:
    """Load GeoNames data for India into the database."""
    if data_file and os.path.exists(data_file):
        txt_path = data_file
        logger.info("Using provided data file: %s", txt_path)
    else:
        txt_path = await _download_and_extract_geonames()

    logger.info("Loading GeoNames data from: %s", txt_path)

    count = 0
    batch_size = 1000
    batch: list[Location] = []

    async with async_session_factory() as session:
        async with session.begin():
            with open(txt_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    if limit and count >= limit:
                        break

                    if len(row) < 19:
                        continue

                    try:
                        geonameid = int(row[0])
                        name = row[1].strip()
                        asciiname = row[2].strip()
                        alternatenames = row[3].strip()
                        latitude = float(row[4])
                        longitude = float(row[5])
                        feature_class = row[6]
                        feature_code = row[7]
                        country_code = row[8]
                        admin1_code = row[10] if len(row) > 10 else ""
                        admin2_code = row[11] if len(row) > 11 else ""
                        admin3_code = row[12] if len(row) > 12 else ""

                        if feature_code not in GEONAMES_FEATURE_CODES:
                            continue

                        if country_code != "IN":
                            continue

                        state_name = INDIAN_STATES.get(admin1_code, "")
                        district_name = admin2_code

                        aliases = alternatenames if alternatenames else None

                        normalized_name = _normalize_name(name)
                        if not normalized_name:
                            continue

                        location = Location(
                            name=name,
                            normalized_name=normalized_name,
                            latitude=latitude,
                            longitude=longitude,
                            type=feature_code,
                            state=state_name if state_name else None,
                            district=district_name if district_name else None,
                            country="India",
                            aliases=aliases,
                        )
                        batch.append(location)
                        count += 1

                        if len(batch) >= batch_size:
                            session.add_all(batch)
                            await session.flush()
                            logger.info("Loaded %d locations...", count)
                            batch.clear()

                    except (ValueError, IndexError) as e:
                        logger.debug("Skipping row: %s", e)
                        continue

            if batch:
                session.add_all(batch)
                await session.flush()
                logger.info("Loaded %d locations (final batch)", count)

        logger.info("Successfully loaded %d Indian locations from GeoNames", count)
        return count


async def _download_and_extract_geonames() -> str:
    """Download and extract GeoNames India data."""
    import zipfile
    import tempfile

    temp_dir = Path(tempfile.gettempdir()) / "aidrac_geonames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    zip_path = temp_dir / "IN.zip"
    txt_path = temp_dir / "IN.txt"

    if txt_path.exists():
        logger.info("Using cached GeoNames file: %s", txt_path)
        return str(txt_path)

    logger.info("Downloading GeoNames India data from %s...", GEONAMES_IN_URL)
    urllib.request.urlretrieve(GEONAMES_IN_URL, zip_path)
    logger.info("Downloaded to %s", zip_path)

    logger.info("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    if not txt_path.exists():
        raise FileNotFoundError(f"Expected IN.txt not found in {temp_dir}")

    logger.info("Extracted to %s", txt_path)
    return str(txt_path)


async def add_manual_locations(session: AsyncSession) -> int:
    """Add important Indian cities manually to ensure coverage."""
    manual_locations = [
        # Major metros
        ("Mumbai", "Mumbai", 19.0760, 72.8777, "PPLA", "Maharashtra", "Mumbai City"),
        ("Delhi", "Delhi", 28.6139, 77.2090, "PPLC", "Delhi", "New Delhi"),
        ("Bengaluru", "Bengaluru", 12.9716, 77.5946, "PPLA", "Karnataka", "Bengaluru Urban"),
        ("Chennai", "Chennai", 13.0827, 80.2707, "PPLA", "Tamil Nadu", "Chennai"),
        ("Kolkata", "Kolkata", 22.5726, 88.3639, "PPLA", "West Bengal", "Kolkata"),
        ("Hyderabad", "Hyderabad", 17.3850, 78.4867, "PPLA", "Telangana", "Hyderabad"),
        ("Pune", "Pune", 18.5204, 73.8567, "PPLA2", "Maharashtra", "Pune"),
        ("Ahmedabad", "Ahmedabad", 23.0225, 72.5714, "PPLA2", "Gujarat", "Ahmedabad"),
        ("Surat", "Surat", 21.1702, 72.8311, "PPL", "Gujarat", "Surat"),
        ("Jaipur", "Jaipur", 26.9124, 75.7873, "PPLA", "Rajasthan", "Jaipur"),
        ("Lucknow", "Lucknow", 26.8467, 80.9462, "PPLA", "Uttar Pradesh", "Lucknow"),
        ("Kanpur", "Kanpur", 26.4499, 80.3319, "PPL", "Uttar Pradesh", "Kanpur Nagar"),
        ("Nagpur", "Nagpur", 21.1458, 79.0882, "PPLA2", "Maharashtra", "Nagpur"),
        ("Indore", "Indore", 22.7196, 75.8577, "PPLA2", "Madhya Pradesh", "Indore"),
        ("Thane", "Thane", 19.2183, 72.9781, "PPL", "Maharashtra", "Thane"),
        ("Bhopal", "Bhopal", 23.2599, 77.4126, "PPLA", "Madhya Pradesh", "Bhopal"),
        ("Visakhapatnam", "Visakhapatnam", 17.6868, 83.2185, "PPLA2", "Andhra Pradesh", "Visakhapatnam"),
        ("Pimpri-Chinchwad", "Pimpri-Chinchwad", 18.6298, 73.7997, "PPL", "Maharashtra", "Pune"),
        ("Patna", "Patna", 25.5941, 85.1376, "PPLA", "Bihar", "Patna"),
        ("Vadodara", "Vadodara", 22.3072, 73.1812, "PPLA2", "Gujarat", "Vadodara"),
        ("Ghaziabad", "Ghaziabad", 28.6692, 77.4538, "PPL", "Uttar Pradesh", "Ghaziabad"),
        ("Ludhiana", "Ludhiana", 30.9010, 75.8573, "PPL", "Punjab", "Ludhiana"),
        ("Agra", "Agra", 27.1767, 78.0081, "PPL", "Uttar Pradesh", "Agra"),
        ("Nashik", "Nashik", 19.9975, 73.7898, "PPLA2", "Maharashtra", "Nashik"),
        ("Faridabad", "Faridabad", 28.4089, 77.3178, "PPL", "Haryana", "Faridabad"),
        ("Meerut", "Meerut", 28.9845, 77.7064, "PPL", "Uttar Pradesh", "Meerut"),
        ("Rajkot", "Rajkot", 22.3039, 70.8022, "PPLA2", "Gujarat", "Rajkot"),
        ("Kalyan-Dombivli", "Kalyan-Dombivli", 19.2437, 73.1355, "PPL", "Maharashtra", "Thane"),
        ("Vasai-Virar", "Vasai-Virar", 19.4919, 72.8054, "PPL", "Maharashtra", "Palghar"),
        ("Varanasi", "Varanasi", 25.3176, 82.9739, "PPL", "Uttar Pradesh", "Varanasi"),
        ("Srinagar", "Srinagar", 34.0837, 74.7973, "PPLA", "Jammu and Kashmir", "Srinagar"),
        ("Aurangabad", "Aurangabad", 19.8762, 75.3433, "PPLA2", "Maharashtra", "Aurangabad"),
        ("Dhanbad", "Dhanbad", 23.7957, 86.4304, "PPL", "Jharkhand", "Dhanbad"),
        ("Amritsar", "Amritsar", 31.6340, 74.8723, "PPL", "Punjab", "Amritsar"),
        ("Navi Mumbai", "Navi Mumbai", 19.0330, 73.0297, "PPL", "Maharashtra", "Raigad"),
        ("Allahabad", "Allahabad", 25.4358, 81.8463, "PPL", "Uttar Pradesh", "Prayagraj"),
        ("Ranchi", "Ranchi", 23.3441, 85.3096, "PPLA", "Jharkhand", "Ranchi"),
        ("Howrah", "Howrah", 22.5958, 88.2636, "PPL", "West Bengal", "Howrah"),
        ("Coimbatore", "Coimbatore", 11.0168, 76.9558, "PPLA2", "Tamil Nadu", "Coimbatore"),
        ("Jabalpur", "Jabalpur", 23.1815, 79.9864, "PPLA2", "Madhya Pradesh", "Jabalpur"),
        ("Gwalior", "Gwalior", 26.2183, 78.1828, "PPL", "Madhya Pradesh", "Gwalior"),
        ("Vijayawada", "Vijayawada", 16.5062, 80.6480, "PPLA2", "Andhra Pradesh", "Krishna"),
        ("Jodhpur", "Jodhpur", 26.2389, 73.0243, "PPLA2", "Rajasthan", "Jodhpur"),
        ("Madurai", "Madurai", 9.9252, 78.1198, "PPLA2", "Tamil Nadu", "Madurai"),
        ("Raipur", "Raipur", 21.2514, 81.6296, "PPLA", "Chhattisgarh", "Raipur"),
        ("Kota", "Kota", 25.2138, 75.8648, "PPL", "Rajasthan", "Kota"),
        ("Guwahati", "Guwahati", 26.1445, 91.7362, "PPLA", "Assam", "Kamrup Metropolitan"),
        ("Chandigarh", "Chandigarh", 30.7333, 76.7794, "PPLA", "Chandigarh", "Chandigarh"),
        ("Solapur", "Solapur", 17.6599, 75.9064, "PPL", "Maharashtra", "Solapur"),
        ("Hubli-Dharwad", "Hubli-Dharwad", 15.3647, 75.1240, "PPL", "Karnataka", "Dharwad"),
        ("Bareilly", "Bareilly", 28.3670, 79.4304, "PPL", "Uttar Pradesh", "Bareilly"),
        ("Mysore", "Mysore", 12.2958, 76.6394, "PPLA2", "Karnataka", "Mysuru"),
        ("Tiruppur", "Tiruppur", 11.1085, 77.3411, "PPLA2", "Tamil Nadu", "Tiruppur"),
        ("Gurgaon", "Gurgaon", 28.4595, 77.0266, "PPL", "Haryana", "Gurugram"),
        ("Aligarh", "Aligarh", 27.8974, 78.0880, "PPL", "Uttar Pradesh", "Aligarh"),
        ("Jalandhar", "Jalandhar", 31.3260, 75.5762, "PPL", "Punjab", "Jalandhar"),
        ("Bhubaneswar", "Bhubaneswar", 20.2961, 85.8245, "PPLA", "Odisha", "Khordha"),
        ("Salem", "Salem", 11.6643, 78.1460, "PPLA2", "Tamil Nadu", "Salem"),
        ("Warangal", "Warangal", 17.9784, 79.5941, "PPLA2", "Telangana", "Warangal Urban"),
        ("Guntur", "Guntur", 16.3067, 80.4365, "PPLA2", "Andhra Pradesh", "Guntur"),
        ("Bhiwandi", "Bhiwandi", 19.2813, 73.0489, "PPL", "Maharashtra", "Thane"),
        ("Saharanpur", "Saharanpur", 29.9680, 77.5552, "PPL", "Uttar Pradesh", "Saharanpur"),
        ("Gorakhpur", "Gorakhpur", 26.7606, 83.3732, "PPLA2", "Uttar Pradesh", "Gorakhpur"),
        ("Bikaner", "Bikaner", 28.0229, 73.3119, "PPLA2", "Rajasthan", "Bikaner"),
        ("Amravati", "Amravati", 20.9374, 77.7796, "PPLA2", "Maharashtra", "Amravati"),
        ("Noida", "Noida", 28.5355, 77.3910, "PPL", "Uttar Pradesh", "Gautam Buddha Nagar"),
        ("Jamshedpur", "Jamshedpur", 22.8046, 86.1861, "PPL", "Jharkhand", "East Singhbhum"),
        ("Bhilai", "Bhilai", 21.1938, 81.3509, "PPL", "Chhattisgarh", "Durg"),
        ("Cuttack", "Cuttack", 20.4625, 85.8828, "PPL", "Odisha", "Cuttack"),
        ("Firozabad", "Firozabad", 27.1592, 78.3957, "PPL", "Uttar Pradesh", "Firozabad"),
        ("Kochi", "Kochi", 9.9312, 76.2673, "PPLA2", "Kerala", "Ernakulam"),
        ("Nellore", "Nellore", 14.4426, 79.9865, "PPLA2", "Andhra Pradesh", "Sri Potti Sriramulu Nellore"),
        ("Bhavnagar", "Bhavnagar", 21.7645, 72.1519, "PPLA2", "Gujarat", "Bhavnagar"),
        ("Dehradun", "Dehradun", 30.3165, 78.0322, "PPLA", "Uttarakhand", "Dehradun"),
        ("Durgapur", "Durgapur", 23.5204, 87.3119, "PPL", "West Bengal", "Paschim Bardhaman"),
        ("Asansol", "Asansol", 23.6739, 86.9524, "PPL", "West Bengal", "Paschim Bardhaman"),
        ("Rourkela", "Rourkela", 22.2604, 84.8536, "PPL", "Odisha", "Sundargarh"),
        ("Nanded", "Nanded", 19.1383, 77.3210, "PPLA2", "Maharashtra", "Nanded"),
        ("Kolhapur", "Kolhapur", 16.7050, 74.2433, "PPLA2", "Maharashtra", "Kolhapur"),
        ("Ajmer", "Ajmer", 26.4499, 74.6399, "PPLA2", "Rajasthan", "Ajmer"),
        ("Akola", "Akola", 20.7002, 77.0082, "PPLA2", "Maharashtra", "Akola"),
        ("Gulbarga", "Gulbarga", 17.3297, 76.8343, "PPLA2", "Karnataka", "Kalaburagi"),
        ("Jamnagar", "Jamnagar", 22.4707, 70.0577, "PPLA2", "Gujarat", "Jamnagar"),
        ("Ujjain", "Ujjain", 23.1765, 75.7885, "PPLA2", "Madhya Pradesh", "Ujjain"),
        ("Loni", "Loni", 28.7500, 77.2800, "PPL", "Uttar Pradesh", "Ghaziabad"),
        ("Siliguri", "Siliguri", 26.7271, 88.3953, "PPL", "West Bengal", "Darjeeling"),
        ("Jhansi", "Jhansi", 25.4484, 78.5685, "PPLA2", "Uttar Pradesh", "Jhansi"),
        ("Ulhasnagar", "Ulhasnagar", 19.2215, 73.1645, "PPL", "Maharashtra", "Thane"),
        ("Jammu", "Jammu", 32.7266, 74.8570, "PPLA", "Jammu and Kashmir", "Jammu"),
        ("Sangli-Miraj", "Sangli-Miraj", 16.8524, 74.5815, "PPL", "Maharashtra", "Sangli"),
        ("Mangalore", "Mangalore", 12.9141, 74.8560, "PPLA2", "Karnataka", "Dakshina Kannada"),
        ("Erode", "Erode", 11.3410, 77.7172, "PPLA2", "Tamil Nadu", "Erode"),
        ("Belgaum", "Belgaum", 15.8497, 74.4977, "PPLA2", "Karnataka", "Belagavi"),
        ("Ambattur", "Ambattur", 13.1143, 80.1548, "PPL", "Tamil Nadu", "Chennai"),
        ("Tirunelveli", "Tirunelveli", 8.7139, 77.7567, "PPLA2", "Tamil Nadu", "Tirunelveli"),
        ("Malegaon", "Malegaon", 20.5579, 74.5287, "PPL", "Maharashtra", "Nashik"),
        ("Gaya", "Gaya", 24.7914, 84.9994, "PPL", "Bihar", "Gaya"),
        ("Jalgaon", "Jalgaon", 21.0077, 75.5626, "PPLA2", "Maharashtra", "Jalgaon"),
        ("Udaipur", "Udaipur", 24.5854, 73.7125, "PPLA2", "Rajasthan", "Udaipur"),
        ("Maheshtala", "Maheshtala", 22.5030, 88.2480, "PPL", "West Bengal", "South 24 Parganas"),
    ]

    added = 0
    for name, asciiname, lat, lng, ftype, state, district in manual_locations:
        normalized = _normalize_name(name)
        result = await session.execute(
            select(Location).where(Location.normalized_name == normalized)
        )
        existing = result.scalar_one_or_none()
        if existing:
            continue

        location = Location(
            name=name,
            normalized_name=normalized,
            latitude=lat,
            longitude=lng,
            type=ftype,
            state=state,
            district=district,
            country="India",
            aliases=asciiname if asciiname != name else None,
        )
        session.add(location)
        added += 1

    await session.flush()
    logger.info("Added %d manual locations", added)
    return added


async def main():
    parser = argparse.ArgumentParser(description="Load Indian geographic data from GeoNames")
    parser.add_argument("--data-file", help="Path to GeoNames IN.txt file")
    parser.add_argument("--limit", type=int, help="Limit number of records to load")
    parser.add_argument("--manual-only", action="store_true", help="Only add manual locations")
    args = parser.parse_args()

    async with async_session_factory() as session:
        if not args.manual_only:
            await load_geonames(args.data_file, args.limit)

        await add_manual_locations(session)
        await session.commit()

    logger.info("Geographic data loading complete")


if __name__ == "__main__":
    asyncio.run(main())