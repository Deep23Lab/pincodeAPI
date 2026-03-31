from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import requests
import io
import os
from app.firebase import db
from app.utils.haversine import calculate_haversine_distance
from google.cloud import firestore

router = APIRouter()

# Collection name 
COLLECTION_NAME = "service_centers"

@router.get("/sync-data")
async def sync_data():
    """
    Sync data from Google Sheets to Firestore.
    CSV export link: https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise HTTPException(status_code=500, detail="GOOGLE_SHEET_ID not set in .env")

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Read with pandas 
        # Columns expected: Pincode, Service Centre Name, Address, Phone Number, State, Partner, Latitude (lat), Longitude (lng)
        # Note: CSV might have different headers, so we'll sanitize if necessary.
        df = pd.read_csv(io.StringIO(response.text))
        
        # Rename columns if they don't match Firestore fields 
        # Fields: pincode, name, address, phone, state, partner, lat, lng
        # Mapping: 
        # Pincode -> pincode
        # Service Centre Name -> name
        # Address -> address
        # Phone Number -> phone
        # State -> state
        # Partner -> partner
        # Latitude (lat) -> lat
        # Longitude (lng) -> lng
        
        column_map = {
            "Pincode": "pincode",
            "Service Centre Name": "name",
            "Address": "address",
            "Phone Number": "phone",
            "State": "state",
            "Partner": "partner",
            "Latitude (lat)": "lat",
            "Longitude (lng)": "lng"
        }
        
        # Filter columns that exist
        df = df.rename(columns=column_map)
        
        # Firestore batch upload 
        batch = db.batch()
        count = 0
        
        # Delete existing data (optional, but requested each row as a doc)
        # We could use the pincode-name combo or just random IDs. 
        # For full sync, we might want to clear or update. 
        # Let's clear old entries if needed, or just overwrite by ID if we have a stable ID.
        
        for index, row in df.iterrows():
            # Create a document handle 
            # Use random ID or something stable? 
            # Pincode is not unique (multiple centers in one pincode).
            doc_ref = db.collection(COLLECTION_NAME).document()
            
            # Prepare data 
            # Handle NaN/None values from pandas 
            data = {
                "pincode": str(row.get("pincode", "")),
                "name": str(row.get("name", "")),
                "address": str(row.get("address", "")),
                "phone": str(row.get("phone", "")),
                "state": str(row.get("state", "")),
                "partner": str(row.get("partner", "")),
                "lat": float(row.get("lat", 0.0)) if pd.notna(row.get("lat")) else 0.0,
                "lng": float(row.get("lng", 0.0)) if pd.notna(row.get("lng")) else 0.0,
            }
            
            batch.set(doc_ref, data)
            count += 1
            
            # Firestore batch limit is 500 
            if count % 500 == 0:
                batch.commit()
                batch = db.batch()
                
        batch.commit()
        
        return {"status": "success", "synced_count": count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_pincode(pincode: str = Query(..., description="6-digit pincode")):
    """
    Search by Pincode. Exact first, then fallback to nearest distance.
    """
    pincode = str(pincode).strip()
    
    # 1. Exact Match 
    query = db.collection(COLLECTION_NAME).where("pincode", "==", pincode).stream()
    exact_results = []
    for doc in query:
        res = doc.to_dict()
        res["id"] = doc.id
        exact_results.append(res)
        
    if exact_results:
        return {"status": "found", "type": "exact", "results": exact_results}
        
    # 2. Nearest Search logic 
    user_lat, user_lng = None, None

    # PRIORITY 1: Find "nearest pincode" from Firestore dataset and use its lat/lng 
    # This means find any document with a pincode as close as possible to the input 
    # to serve as a reference point for distance calculation.
    try:
        # Search for pincode >= input or <= input 
        # Since pincodes are strings, we'll search alphabetically 
        higher_query = db.collection(COLLECTION_NAME).order_by("pincode").where("pincode", ">=", pincode).limit(1).stream()
        lower_query = db.collection(COLLECTION_NAME).order_by("pincode", direction=firestore.Query.DESCENDING).where("pincode", "<=", pincode).limit(1).stream()
        
        neighbor = None
        for doc in higher_query:
            neighbor = doc.to_dict()
            break 
        if not neighbor:
            for doc in lower_query:
                neighbor = doc.to_dict()
                break
        
        if neighbor:
            user_lat = neighbor.get("lat")
            user_lng = neighbor.get("lng")
            print(f"Using neighbor pincode {neighbor.get('pincode')} as reference for {pincode}")

    except Exception as e:
        print(f"Numerical proximity search failed: {e}")

    # PRIORITY 2: Fallback to Google Geocoding if neighbor search didn't provide coords 
    # (Or if we want more accuracy than just the neighbor's location)
    if user_lat is None or user_lng is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={pincode}+India&key={api_key}"
            try:
                geo_res = requests.get(geo_url).json()
                if geo_res.get("status") == "OK":
                    location = geo_res["results"][0]["geometry"]["location"]
                    user_lat = location["lat"]
                    user_lng = location["lng"]
            except Exception as e:
                print(f"Geocoding error: {e}")

    # If geocoding didn't work, maybe use the first 3 or 4 digits of pincode to find "nearby" centers 
    # and take the average lat/lng? 
    # Or just use the numerical closest (which is a bit unreliable).
    # Since I don't have a full pincode database, I'll rely on the Google Geocoding or an error if missing.
    
    if user_lat is None or user_lng is None:
        # Emergency fallback: maybe search for similar pincodes?
        # But for now, returning empty or error if no way to geocode.
        # However, let's try to query ALL centers and find if any *prefix* matches to get a rough Lat/Lng?
        # That's too complex. Let's return only if we have coordinates.
        raise HTTPException(status_code=404, detail="Pincode not found and could not determine location coordinates.")

    # Fetch ALL service centers 
    all_centers_query = db.collection(COLLECTION_NAME).stream()
    all_centers = []
    for doc in all_centers_query:
        center = doc.to_dict()
        center["id"] = doc.id
        
        # Calculate distance 
        lat2 = center.get("lat")
        lng2 = center.get("lng")
        
        if lat2 is not None and lng2 is not None:
            dist = calculate_haversine_distance(user_lat, user_lng, lat2, lng2)
            center["distance"] = round(dist, 2)
            all_centers.append(center)
            
    # Sort by distance 
    all_centers.sort(key=lambda x: x["distance"])
    
    # Top 3
    top_3 = all_centers[:3]
    
    return {"status": "found", "type": "nearest", "results": top_3, "user_coordinates": {"lat": user_lat, "lng": user_lng}}
