import os
import math
import logging
from typing import List, Dict, Any, Optional
import googlemaps
from dotenv import load_dotenv

from backend.models import Doctor, DoctorSearchRequest

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Google Maps client safely
API_KEY = os.getenv("PLACES_API_KEY")
gmaps_client = None

if API_KEY:
    # Clean leading/trailing whitespace, quotes, or carriage returns from secret mounting
    API_KEY = API_KEY.strip().strip('"').strip("'").strip()

if API_KEY:
    try:
        gmaps_client = googlemaps.Client(key=API_KEY)
        logger.info("Google Maps Places API client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Google Maps client: {e}")
else:
    logger.warning("PLACES_API_KEY environment variable is missing. Nearby searches will use fallback cache.")

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculates the Haversine distance in kilometers between two GPS coordinates.
    """
    R = 6371.0 # Radius of the Earth in km
    
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2)
         
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance, 2)

# Fallback templates disabled
FALLBACK_DOCTOR_TEMPLATES = {}




def search_nearby_doctors(request: DoctorSearchRequest) -> List[Doctor]:
    """
    Queries Google Places Nearby Search for real doctors based on specialist type, location, radius, and rating bounds.
    Never uses any mock fallback data. Returns an empty list if no matching doctors are found.
    """
    if not gmaps_client:
        logger.warning("googlemaps client is not initialized.")
        return []
        
    specialist_display = request.specialist_type.replace("_", " ").title()
    query_keyword = f"{specialist_display} doctor"
    
    # Radius in meters (request.radius_km to meters)
    radius_meters = int(request.radius_km * 1000)
    user_location = (request.lat, request.lng)
    
    logger.info(f"===> [OUTGOING API CALL: Google Places Nearby Search] Keyword: '{query_keyword}' | Location: {user_location} | Radius: {request.radius_km} km | Rating Bounds: [{request.min_rating}-{request.max_rating}]")
    
    try:
        # Perform Nearby Search
        places_result = gmaps_client.places_nearby(
            location=user_location,
            radius=radius_meters,
            keyword=query_keyword,
            type="doctor"
        )
        
        raw_results = places_result.get("results", [])
        logger.info(f"<=== [INCOMING API RESPONSE: Google Places Nearby Search] Raw Places Count: {len(raw_results)}")
        
        # Collect and pre-filter candidates near the coordinates
        candidates = []
        for p in raw_results:
            geometry = p.get("geometry", {})
            loc = geometry.get("location", {})
            doc_lat = loc.get("lat")
            doc_lng = loc.get("lng")
            
            if doc_lat is None or doc_lng is None:
                continue
                
            distance = haversine_distance(request.lat, request.lng, doc_lat, doc_lng)
            
            # Skip if result is outside of search radius
            if distance > request.radius_km:
                continue
                
            # Filter based on rating range
            rating = p.get("rating", 4.0)
            if rating < request.min_rating or rating > request.max_rating:
                continue
                
            candidates.append((p, distance))
            
        logger.info(f"Filtered to {len(candidates)} candidate doctors matching radius and rating criteria.")
            
        # Sort candidates: rating (descending), then distance (ascending) as a tie-breaker
        candidates.sort(key=lambda item: (-item[0].get("rating", 4.0), item[1]))
        
        # Limit to top candidates to optimize latency and minimize Place Details API transaction costs
        top_candidates = candidates[:request.max_results]
        
        doctors_list = []
        for p, distance in top_candidates:
            place_id = p.get("place_id")
            rating = p.get("rating", 4.0)
            
            # Extract coordinates for the current doctor
            geometry = p.get("geometry", {})
            loc = geometry.get("location", {})
            lat = loc.get("lat")
            lng = loc.get("lng")
            
            import urllib.parse
            encoded_name = urllib.parse.quote(p.get("name", "Doctor"))
            
            # Formulate the correct Google Maps directions URL
            if place_id:
                directions_url = f"https://www.google.com/maps/dir/?api=1&destination={encoded_name}&destination_place_id={place_id}"
            elif lat is not None and lng is not None:
                directions_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
            else:
                directions_url = f"https://www.google.com/maps/search/?api=1&query={encoded_name}"
            
            # Default address fallback values
            address = p.get("vicinity") or p.get("formatted_address")
            phone_number = None
            
            # Fetch complete formatted address and contact phone number using Place Details API
            if place_id:
                try:
                    logger.info(f"Fetching complete details for place_id: {place_id}")
                    details = gmaps_client.place(
                        place_id=place_id,
                        fields=["formatted_address", "formatted_phone_number"]
                    )
                    details_result = details.get("result", {})
                    if details_result.get("formatted_address"):
                        address = details_result.get("formatted_address")
                    if details_result.get("formatted_phone_number"):
                        phone_number = details_result.get("formatted_phone_number")
                except Exception as detail_err:
                    logger.warning(f"Failed to fetch Place Details for {place_id}: {detail_err}")
            
            # Clean compound plus_code fallback if address is still missing
            if not address:
                compound_code = p.get("plus_code", {}).get("compound_code")
                if compound_code:
                    parts = compound_code.split(" ", 1)
                    if len(parts) > 1 and "+" in parts[0]:
                        address = parts[1]
                    else:
                        address = compound_code
            if not address:
                address = "Mumbai, Maharashtra, India"
                
            doctors_list.append(
                Doctor(
                    name=p.get("name", "Unknown Doctor"),
                    specialty_tag=specialist_display,
                    distance_km=distance,
                    rating=rating,
                    address=address,
                    phone_number=phone_number,
                    directions_url=directions_url
                )
            )
            
        return doctors_list
        
    except Exception as e:
        logger.error(f"Error querying Google Places API: {e}.")
        return []


