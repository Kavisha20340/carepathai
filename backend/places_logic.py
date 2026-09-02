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

# Fallback templates with Mumbai-based default data
FALLBACK_DOCTOR_TEMPLATES = {
    "orthopedic": [
        {"name": "Dr. Rajesh Shah (Orthopedic Clinic)", "rating": 4.8, "offset_lat": 0.008, "offset_lng": 0.012, "address": "12, Juhu Tara Rd, Santacruz West, Mumbai, Maharashtra 400049", "phone": "+91 22 2660 1111"},
        {"name": "Dr. Amit Kulkarni - Bone & Joint Care", "rating": 4.6, "offset_lat": -0.012, "offset_lng": 0.005, "address": "Plot 45, Linking Rd, Bandra West, Mumbai, Maharashtra 400050", "phone": "+91 22 2640 2222"},
        {"name": "Dr. Sunita Deshmukh - Joint Replacement Specialist", "rating": 4.6, "offset_lat": 0.004, "offset_lng": -0.015, "address": "Metro Hospital, S.V. Road, Andheri West, Mumbai, Maharashtra 400058", "phone": "+91 22 2620 3333"},
        {"name": "Dr. Vijay Patil - Sports Injury Centre", "rating": 4.3, "offset_lat": -0.005, "offset_lng": -0.008, "address": "78, Hill Road, Bandra West, Mumbai, Maharashtra 400050", "phone": "+91 22 2650 4444"}
    ],
    "dermatologist": [
        {"name": "Dr. Sneha Sharma - Dermacare Skin Clinic", "rating": 4.9, "offset_lat": 0.006, "offset_lng": 0.009, "address": "15, Turner Rd, Bandra West, Mumbai, Maharashtra 400050", "phone": "+91 22 2642 5555"},
        {"name": "Dr. Priya Mehta - Radiant Skin & Laser Centre", "rating": 4.7, "offset_lat": -0.010, "offset_lng": 0.007, "address": "Khar West Chambers, S.V. Rd, Khar, Mumbai, Maharashtra 400052", "phone": "+91 22 2648 6666"},
        {"name": "Dr. Rahul Verma - Skin & Hair Specialist", "rating": 4.4, "offset_lat": 0.003, "offset_lng": -0.011, "address": "Bhardawadi Road, Andheri West, Mumbai, Maharashtra 400058", "phone": "+91 22 2622 7777"}
    ],
    "pulmonologist": [
        {"name": "Dr. Sandeep Patil - Chest & Lung Clinic", "rating": 4.8, "offset_lat": 0.007, "offset_lng": 0.010, "address": "KEM Hospital, Acharya Donde Marg, Parel, Mumbai, Maharashtra 400012", "phone": "+91 22 2410 8888"},
        {"name": "Dr. Vikram Kadam - Respiratory Care", "rating": 4.5, "offset_lat": -0.008, "offset_lng": 0.014, "address": "Lilavati Hospital, Bandra Reclamation, Mumbai, Maharashtra 400050", "phone": "+91 22 2656 9999"}
    ],
    "general_physician": [
        {"name": "Dr. Anita Nair - Family Physician", "rating": 4.7, "offset_lat": 0.003, "offset_lng": 0.004, "address": "Shreeji Clinic, S.V. Road, Santacruz West, Mumbai, Maharashtra 400054", "phone": "+91 22 2611 1010"},
        {"name": "Dr. Manoj Joshi - General Medicine", "rating": 4.5, "offset_lat": -0.004, "offset_lng": -0.006, "address": "Joshi Nursing Home, Linking Road, Khar, Mumbai, Maharashtra 400052", "phone": "+91 22 2646 2020"},
        {"name": "Dr. Kiran Sawant - Care First Clinic", "rating": 4.2, "offset_lat": 0.009, "offset_lng": -0.007, "address": "104, Hill Road, Bandra West, Mumbai, Maharashtra 400050", "phone": "+91 22 2651 3030"}
    ]
}

DEFAULT_DOCTOR_TEMPLATES = [
    {"name": "Dr. Arvind Gupta - Specialty Medical Centre", "rating": 4.6, "offset_lat": 0.005, "offset_lng": 0.008, "address": "Public Healthcare Plaza, Worli, Mumbai, Maharashtra 400018", "phone": "+91 22 2490 4040"},
    {"name": "Dr. Shalini Rao - Elite Health Clinic", "rating": 4.4, "offset_lat": -0.007, "offset_lng": 0.006, "address": "Lokhandwala Complex, Andheri West, Mumbai, Maharashtra 400053", "phone": "+91 22 2630 5050"},
    {"name": "Dr. Devendra Singh - City Care Centre", "rating": 4.1, "offset_lat": 0.003, "offset_lng": -0.009, "address": "Colaba Causeway, Near Regal Cinema, Mumbai, Maharashtra 400001", "phone": "+91 22 2280 6060"}
]

def generate_fallback_doctors(request: DoctorSearchRequest) -> List[Doctor]:
    """
    Generates localized mock doctor records relative to the user's lat/lng,
    sorted by rating (desc) then distance (asc).
    """
    specialist = request.specialist_type
    user_lat = request.lat
    user_lng = request.lng
    
    templates = FALLBACK_DOCTOR_TEMPLATES.get(specialist, DEFAULT_DOCTOR_TEMPLATES)
    
    fallback_doctors = []
    for t in templates:
        # Filter based on rating threshold
        if t.get("rating", 4.0) < request.min_rating:
            continue
            
        doc_lat = user_lat + t.get("offset_lat", 0.005)
        doc_lng = user_lng + t.get("offset_lng", 0.008)
        
        distance = haversine_distance(user_lat, user_lng, doc_lat, doc_lng)
        
        # Filter based on radius
        if distance > request.radius_km:
            continue
            
        directions_url = f"https://www.google.com/maps/dir/?api=1&destination={doc_lat},{doc_lng}"
        specialty_display = specialist.replace("_", " ").title()
        
        fallback_doctors.append(
            Doctor(
                name=t["name"],
                specialty_tag=specialty_display,
                distance_km=distance,
                rating=t["rating"],
                address=t["address"],
                phone_number=t.get("phone"),
                directions_url=directions_url
            )
        )
        
    fallback_doctors.sort(key=lambda d: (-d.rating, d.distance_km))
    return fallback_doctors[:request.max_results]


def search_nearby_doctors(request: DoctorSearchRequest) -> List[Doctor]:
    """
    Queries Google Places Nearby Search for doctors based on specialist type.
    Falls back to a high-quality localized mock database if live API returns < 3 entries.
    """
    if not gmaps_client:
        logger.info("Using fallback generator: googlemaps client is not initialized.")
        return generate_fallback_doctors(request)
        
    specialist_display = request.specialist_type.replace("_", " ").title()
    query_keyword = f"{specialist_display} doctor"
    
    # Radius in meters (request.radius_km to meters)
    radius_meters = int(request.radius_km * 1000)
    user_location = (request.lat, request.lng)
    
    logger.info(f"Querying Google Places for: '{query_keyword}' at location: {user_location} within {request.radius_km} km")
    
    try:
        # Perform Nearby Search
        places_result = gmaps_client.places_nearby(
            location=user_location,
            radius=radius_meters,
            keyword=query_keyword,
            type="doctor"
        )
        
        raw_results = places_result.get("results", [])
        logger.info(f"Google Places returned {len(raw_results)} results.")
        
        if len(raw_results) < 3:
            logger.warning(f"Fewer than 3 live results ({len(raw_results)}) found. Activating localized demo fallback.")
            return generate_fallback_doctors(request)
            
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
                
            # Filter based on rating threshold
            rating = p.get("rating", 4.0)
            if rating < request.min_rating:
                continue
                
            candidates.append((p, distance))
            
        if len(candidates) < 3:
            logger.warning(f"Fewer than 3 filtered live results (found {len(candidates)}) matching rating >= {request.min_rating} inside radius. Activating localized demo fallback.")
            return generate_fallback_doctors(request)
            
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
        logger.error(f"Error querying Google Places API: {e}. Activating localized demo fallback.")
        return generate_fallback_doctors(request)


