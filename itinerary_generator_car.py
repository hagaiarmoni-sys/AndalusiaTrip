"""
Car-Based Itinerary Generator for Andalusia Travel App
WITH OPTIMIZED ROUTE ALGORITHM (No Backtracking!)
"""

import streamlit as st
import math
import unicodedata
import json
import os
from collections import Counter
from urllib.parse import quote_plus
from text_norm import canonicalize_city, norm_key  # ✅ NEW: Import text normalization
# from semantic_merge import merge_city_pois  # ⚠️ DISABLED: Too aggressive, removing valid POIs

# ✅ NEW: Import weighted scoring and must-see landmarks
from must_see_landmarks import is_must_see, get_must_see_count, get_missing_must_sees
from weighted_poi_scoring import calculate_weighted_score, score_and_sort_pois

# ✅ NEW: Import day allocation for recommended days per city
try:
    from day_allocation import (
        allocate_days_for_route,
        parse_user_duration_requests,
        get_recommended_days_for_city,
        get_allocation_summary,
        get_max_intermediate_cities,  # NEW: For route building
    )
    DAY_ALLOCATION_AVAILABLE = True
    # print("✅ day_allocation module imported successfully")
except ImportError as e:
    DAY_ALLOCATION_AVAILABLE = False
    print(f"⚠️ day_allocation module not found: {e}")


# ============================================================================
# HIDDEN GEMS / ROUTE STOPS DATA
# ============================================================================

def load_hidden_gems():
    """Load hidden gems data for route stops between cities"""
    for path in ['data/andalusia_hidden_gems.json', 'andalusia_hidden_gems.json']:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
    return None

# Pre-defined route stops between major cities
# Format: (from_city, to_city): [list of stops with coordinates]
ROUTE_STOPS = {
    ('malaga', 'granada'): [
        {'name': 'Nerja Caves', 'type': 'attraction', 'detour_km': 15, 'time_min': 60,
         'lat': 36.7614, 'lon': -3.8447, 'highlight': 'Prehistoric cave paintings'},
        {'name': 'Frigiliana', 'type': 'village', 'detour_km': 10, 'time_min': 45,
         'lat': 36.7912, 'lon': -3.8947, 'highlight': 'Most beautiful village in Spain'},
    ],
    ('malaga', 'ronda'): [
        {'name': 'El Torcal de Antequera', 'type': 'nature', 'detour_km': 25, 'time_min': 90,
         'lat': 36.9539, 'lon': -4.5433, 'highlight': 'Surreal limestone formations'},
    ],
    ('malaga', 'cordoba'): [
        {'name': 'Antequera Dolmens', 'type': 'attraction', 'detour_km': 5, 'time_min': 45,
         'lat': 37.0236, 'lon': -4.5603, 'highlight': 'UNESCO prehistoric tombs'},
        {'name': 'El Torcal', 'type': 'nature', 'detour_km': 20, 'time_min': 60,
         'lat': 36.9539, 'lon': -4.5433, 'highlight': 'Otherworldly rock formations'},
    ],
    ('granada', 'cordoba'): [
        {'name': 'Priego de Córdoba', 'type': 'town', 'detour_km': 30, 'time_min': 60,
         'lat': 37.4383, 'lon': -4.1961, 'highlight': 'Best olive oil in Spain, baroque churches'},
        {'name': 'Zuheros', 'type': 'village', 'detour_km': 25, 'time_min': 45,
         'lat': 37.5453, 'lon': -4.3153, 'highlight': 'Cliffside village with caves'},
    ],
    ('cordoba', 'seville'): [
        {'name': 'Écija', 'type': 'town', 'detour_km': 10, 'time_min': 45,
         'lat': 37.5417, 'lon': -5.0828, 'highlight': 'City of towers, baroque churches'},
        {'name': 'Carmona', 'type': 'town', 'detour_km': 15, 'time_min': 60,
         'lat': 37.4714, 'lon': -5.6417, 'highlight': 'Roman necropolis, stunning views'},
    ],
    ('ronda', 'seville'): [
        {'name': 'Zahara de la Sierra', 'type': 'village', 'detour_km': 20, 'time_min': 45,
         'lat': 36.8403, 'lon': -5.3906, 'highlight': 'Turquoise reservoir, hilltop castle'},
        {'name': 'Olvera', 'type': 'village', 'detour_km': 15, 'time_min': 30,
         'lat': 36.9356, 'lon': -5.2678, 'highlight': 'Castle and church on hilltop'},
        {'name': 'Arcos de la Frontera', 'type': 'village', 'detour_km': 25, 'time_min': 45,
         'lat': 36.7511, 'lon': -5.8067, 'highlight': 'Perched above gorge, Parador hotel'},
    ],
    ('ronda', 'cadiz'): [
        {'name': 'Arcos de la Frontera', 'type': 'village', 'detour_km': 10, 'time_min': 45,
         'lat': 36.7511, 'lon': -5.8067, 'highlight': 'Dramatic white village on cliff'},
        {'name': 'Grazalema', 'type': 'village', 'detour_km': 15, 'time_min': 45,
         'lat': 36.7583, 'lon': -5.3667, 'highlight': 'Natural park, hiking, local cheeses'},
    ],
    ('seville', 'cadiz'): [
        {'name': 'Jerez de la Frontera', 'type': 'city', 'detour_km': 5, 'time_min': 90,
         'lat': 36.6850, 'lon': -6.1261, 'highlight': 'Sherry bodegas, horse shows'},
    ],
    ('malaga', 'cadiz'): [
        {'name': 'Ronda', 'type': 'city', 'detour_km': 30, 'time_min': 120,
         'lat': 36.7422, 'lon': -5.1667, 'highlight': 'Puente Nuevo, cliff houses'},
        {'name': 'Grazalema', 'type': 'village', 'detour_km': 20, 'time_min': 45,
         'lat': 36.7583, 'lon': -5.3667, 'highlight': 'Natural park, scenic drives'},
    ],
    ('granada', 'seville'): [
        {'name': 'Antequera', 'type': 'town', 'detour_km': 15, 'time_min': 60,
         'lat': 37.0194, 'lon': -4.5614, 'highlight': 'Dolmens, El Torcal nearby'},
        {'name': 'Écija', 'type': 'town', 'detour_km': 20, 'time_min': 45,
         'lat': 37.5417, 'lon': -5.0828, 'highlight': 'Baroque towers and palaces'},
    ],
    ('granada', 'ronda'): [
        {'name': 'Alhama de Granada', 'type': 'town', 'detour_km': 10, 'time_min': 45,
         'lat': 36.9908, 'lon': -3.9869, 'highlight': 'Thermal baths, gorge views'},
    ],
    ('seville', 'ronda'): [
        {'name': 'Arcos de la Frontera', 'type': 'village', 'detour_km': 20, 'time_min': 60,
         'lat': 36.7511, 'lon': -5.8067, 'highlight': 'Gateway to white villages'},
        {'name': 'Zahara de la Sierra', 'type': 'village', 'detour_km': 25, 'time_min': 45,
         'lat': 36.8403, 'lon': -5.3906, 'highlight': 'Swimming in turquoise reservoir'},
    ],
}


def get_route_stops(from_city, to_city, max_stops=2):
    """
    Get recommended stops between two cities.
    
    Args:
        from_city: Starting city (original name)
        to_city: Destination city (original name)
        max_stops: Maximum number of stops to return
    
    Returns:
        list: List of stop dicts with name, type, highlight, detour_km, time_min
    """
    from_norm = normalize_city_name(from_city)
    to_norm = normalize_city_name(to_city)
    
    # Try both directions
    key = (from_norm, to_norm)
    reverse_key = (to_norm, from_norm)
    
    stops = ROUTE_STOPS.get(key, []) or ROUTE_STOPS.get(reverse_key, [])
    
    if not stops:
        return []
    
    # Sort by detour distance (shortest first) and return top stops
    sorted_stops = sorted(stops, key=lambda x: x.get('detour_km', 999))
    return sorted_stops[:max_stops]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_city_name(city_name):
    """Normalize city name by removing accents and converting to lowercase"""
    if not city_name:
        return ""
    
    city_name = str(city_name)
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


def cities_match(city1, city2):
    """Check if two city names match (handling accents and aliases)"""
    if not city1 or not city2:
        return False
    
    norm1 = normalize_city_name(city1)
    norm2 = normalize_city_name(city2)
    
    if norm1 == norm2:
        return True
    
    # City aliases
    city_aliases = {
        'seville': {'seville', 'sevilla'},
        'cordoba': {'cordoba', 'córdoba'},
        'malaga': {'malaga', 'málaga'},
        'cadiz': {'cadiz', 'cádiz'},
        'jerez': {'jerez', 'jerez de la frontera'},
        'granada': {'granada'},
        'ronda': {'ronda'},
        'tarifa': {'tarifa'},
        'almeria': {'almeria', 'almería'},
        'antequera': {'antequera'},
        'marbella': {'marbella'},
        'nerja': {'nerja'}
    }
    
    for canonical, aliases in city_aliases.items():
        if norm1 in aliases and norm2 in aliases:
            return True
    
    # Partial match for longer names
    if len(norm1) > 3 and len(norm2) > 3 and (norm1 in norm2 or norm2 in norm1):
        return True
    
    return False


def parse_start_end(text, trip_type):
    """Parse start and end cities from text input"""
    if not text:
        return None, None
    
    parts = [p.strip() for p in text.split(" to ") if p.strip()]
    
    if len(parts) == 2:
        return parts[0], parts[1]
    
    if trip_type == "Circular":
        return text.strip(), text.strip()
    
    return text.strip(), None


def haversine_km(coord1, coord2, road_factor=1.3):
    """
    Calculate driving distance between two coordinates
    
    Args:
        coord1: Tuple (lat, lon) or coordinate dict
        coord2: Tuple (lat, lon) or coordinate dict
        road_factor: Multiplier for road distance vs straight line
    
    Returns:
        Distance in kilometers
    """
    # Handle different input formats
    if isinstance(coord1, tuple) and isinstance(coord2, tuple):
        lat1, lon1 = coord1
        lat2, lon2 = coord2
    elif isinstance(coord1, dict) and isinstance(coord2, dict):
        lat1 = coord1.get('latitude', coord1.get('lat', 0))
        lon1 = coord1.get('longitude', coord1.get('lng', coord1.get('lon', 0)))
        lat2 = coord2.get('latitude', coord2.get('lat', 0))
        lon2 = coord2.get('longitude', coord2.get('lng', coord2.get('lon', 0)))
    else:
        return None
    
    if not all([lat1, lon1, lat2, lon2]):
        return None
    
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c * road_factor
    
    return distance if distance < 10000 else None  # Sanity check




def calculate_driving_time(distance_km):
    """
    Calculate driving time in hours based on distance
    
    Args:
        distance_km: Distance in kilometers
    
    Returns:
        Driving time in hours
    """
    if distance_km < 30:
        # City driving: slower (40 km/h average)
        return distance_km / 40 + 0.25  # Add 15 min for traffic/parking
    elif distance_km < 100:
        # Regional roads: moderate (70 km/h average)
        return distance_km / 70 + 0.25
    else:
        # Highway: faster (100 km/h average)
        return distance_km / 100 + 0.5  # Add 30 min for rest stops

def google_maps_link(cities):
    """Generate Google Maps link for multi-city route"""
    if not cities or len(cities) < 2:
        return ""
    
    origin = cities[0]
    destination = cities[-1]
    waypoints = cities[1:-1] if len(cities) > 2 else []
    
    base_url = "https://www.google.com/maps/dir/"
    
    # Build URL
    parts = [quote_plus(str(origin))]
    for wp in waypoints:
        parts.append(quote_plus(str(wp)))
    parts.append(quote_plus(str(destination)))
    
    return base_url + "/".join(parts)


def filter_duplicate_pois(pois):
    """
    Remove duplicate POIs using place_id (most reliable) with name-based fallback
    """
    if not pois:
        return []
    
    import unicodedata
    
    seen_place_ids = set()
    seen_normalized_names = set()
    seen_landmark_keys = set()  # ✅ NEW: Track landmark variations
    unique = []
    
    # ✅ P2 FIX: Known landmark variations that are the same place
    # Key = canonical name, values = variations
    landmark_aliases = {
        'giralda': ['giralda', 'torre giralda', 'la giralda', 'giralda tower', 'giralda bell tower'],
        'alhambra': ['alhambra', 'la alhambra', 'alhambra palace', 'palacio de la alhambra'],
        'mezquita': ['mezquita', 'mezquita-catedral', 'mezquita catedral', 'mosque-cathedral', 'great mosque'],
        'alcazar_seville': ['real alcazar', 'alcazar de sevilla', 'alcazar sevilla', 'royal alcazar seville'],
        'alcazar_segovia': ['alcazar de segovia', 'alcazar segovia'],
        'alcazaba_malaga': ['alcazaba', 'alcazaba malaga', 'alcazaba de malaga'],
        'cathedral_seville': ['catedral de sevilla', 'seville cathedral', 'cathedral of seville'],
        'cathedral_granada': ['catedral de granada', 'granada cathedral', 'cathedral of granada'],
        'cathedral_malaga': ['catedral de malaga', 'malaga cathedral', 'cathedral of malaga'],
        'plaza_espana': ['plaza de espana', 'plaza espana', 'spain square'],
        'generalife': ['generalife', 'generalife gardens', 'jardines del generalife'],
        'divino_salvador': ['iglesia del divino salvador', 'divine savior church', 'eglise du divin sauveur', 'divino salvador'],
    }
    
    def get_landmark_key(name):
        """Check if name matches a known landmark and return its canonical key"""
        name_lower = name.lower().strip()
        # Remove accents
        name_lower = ''.join(
            c for c in unicodedata.normalize('NFD', name_lower)
            if unicodedata.category(c) != 'Mn'
        )
        
        for canonical, aliases in landmark_aliases.items():
            for alias in aliases:
                # Check if alias is contained in name or vice versa
                if alias in name_lower or name_lower in alias:
                    return canonical
                # Also check without spaces
                if alias.replace(' ', '') in name_lower.replace(' ', ''):
                    return canonical
        return None
    
    for poi in pois:
        place_id = poi.get('place_id')
        name = poi.get('name', '')
        
        # Priority 0: Check if it's a known landmark variation
        landmark_key = get_landmark_key(name)
        if landmark_key:
            if landmark_key in seen_landmark_keys:
                continue  # Skip - already have this landmark
            seen_landmark_keys.add(landmark_key)
            unique.append(poi)  # Add landmark and continue (don't check place_id)
            continue
        
        # Priority 1: Use place_id if available (100% reliable!)
        if place_id:
            if place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique.append(poi)
            # else: skip duplicate (same place_id)
            continue
        
        # Priority 2: Fallback to name-based deduplication (for POIs without place_id)
        name = name.lower().strip()
        
        if not name:
            continue
        
        # Remove accents first (fixes "Cádiz" vs "Cadiz")
        name = ''.join(
            c for c in unicodedata.normalize('NFD', name)
            if unicodedata.category(c) != 'Mn'
        )
        
        # Normalize name
        normalized = name
        
        # Remove common words
        words_to_remove = [
            'cathedral', 'catedral', 'mosque', 'mezquita',
            'church', 'iglesia', 'palace', 'palacio',
            'museum', 'museo', 'of', 'de', 'del', 'la', 'el',
            'the', '-', 'and', 'y', '(', ')', 'torre', 'tower'
        ]
        
        for word in words_to_remove:
            normalized = normalized.replace(word, '')
        
        # Remove extra spaces and special chars
        normalized = ''.join(c for c in normalized if c.isalnum())
        
        if normalized and normalized not in seen_normalized_names:
            seen_normalized_names.add(normalized)
            unique.append(poi)
    
    return unique

def compute_poi_quota(pace, total_pois, has_blockbuster=False):
    """
    Calculate how many POIs to select based on pace
    
    Args:
        pace: 'relaxed', 'medium', or 'fast'
        total_pois: Total available POIs in the city
        has_blockbuster: True if day includes major time-consuming attraction
    
    Returns:
        Number of POIs to select
    """
    # If day has blockbuster attraction (Alhambra, Alcázar, Cathedral)… fewer POIs
    if has_blockbuster:
        if pace == "relaxed":
            quota = min(3, total_pois)
        elif pace == "fast":
            quota = min(4, total_pois)
        else:  # medium
            quota = min(3, total_pois)
    else:
        # Normal days without blockbusters
        if pace == "relaxed":
            quota = min(5, total_pois)
        elif pace == "fast":
            quota = min(7, total_pois)
        else:  # medium
            quota = min(6, total_pois)

    # ✅ FIX: For cities with limited POIs (after filtering), be more generous
    # If total_pois is small (< 15), try to show at least half of them
    if total_pois < 15:
        quota = max(quota, min(total_pois // 2 + 1, total_pois))

    # Minimum 3 but don’t exceed available
    return max(3, min(quota, total_pois))


def has_blockbuster_attraction(pois):
    """
    Check if POI list contains a blockbuster attraction
    
    Blockbuster = attractions requiring 3+ hours (Alhambra, Alcázar, Cathedral, etc.)
    Uses visit_duration_hours from JSON data
    
    Args:
        pois: List of POI dicts with visit_duration_hours field
    
    Returns:
        True if any POI requires 3+ hours
    """
    for poi in pois:
        duration = poi.get('visit_duration_hours', 0)
        try:
            duration = float(duration)
            if duration >= 3.0:
                return True
        except (ValueError, TypeError):
            continue
    return False


    """
    Calculate how many POIs to select based on pace
    
    Args:
        pace: 'easy', 'medium', or 'fast'
        total_pois: Total available POIs
        has_blockbuster: True if day includes major time-consuming attraction
    
    Returns:
        Number of POIs to select
    """
    # If day has blockbuster attraction (Alhambra, Alcázar, Cathedral), limit POIs
    if has_blockbuster:
        if pace == "relaxed":
            quota = min(3, total_pois)  # 3 max with blockbuster
        elif pace == "fast":
            quota = min(4, total_pois)
        else:  # medium
            quota = min(3, total_pois)  # Conservative default
    else:
        # Normal days without blockbusters
        if pace == "relaxed":
            quota = min(5, total_pois)
        elif pace == "fast":
            quota = min(7, total_pois)  # Reduced from 8
        else:  # medium
            quota = min(6, total_pois)
    
    return max(3, min(quota, total_pois))


def apply_diversity(pois, quota, max_same_category):
    """
    ✅ UPDATED: Select POIs with category diversity using weighted scoring
    
    Changes from old version:
    - Uses weighted scoring instead of just rating
    - Prioritizes must-see landmarks and popular attractions
    - Still maintains category diversity
    - Still respects time limits
    """
    if not pois:
        return []
    
    # ✅ Calculate weighted scores for all POIs
    # This prioritizes landmarks with high popularity over obscure 5-star venues
    for poi in pois:
        city_name = poi.get('city_label', poi.get('city', ''))
        poi['weighted_score'] = calculate_weighted_score(poi, city_name)
    
    # ✅ Sort by weighted score (highest first)
    sorted_pois = sorted(pois, key=lambda x: x.get('weighted_score', 0), reverse=True)
    
    selected = []
    category_count = Counter()
    total_duration = 0
    max_duration_minutes = 8 * 60  # 8 hours max sightseeing per day
    
    for poi in sorted_pois:
        if len(selected) >= quota:
            break
        
        duration = poi.get('duration_minutes', 60)
        if total_duration + duration > max_duration_minutes:
            continue
        
        category = poi.get('category', 'Other')
        
        if category_count[category] < max_same_category:
            selected.append(poi)
            category_count[category] += 1
            total_duration += duration
    
    # If we haven't reached quota, add remaining POIs
    if len(selected) < quota:
        for poi in sorted_pois:
            if poi not in selected and len(selected) < quota:
                duration = poi.get('duration_minutes', 60)
                if total_duration + duration <= max_duration_minutes:
                    selected.append(poi)
                    total_duration += duration
    
    # ✅ NEW: Optimize POI order geographically (nearest-neighbor)
    selected = optimize_poi_order(selected)
    
    return selected


def optimize_poi_order(pois):
    """
    Optimize the order of POIs to minimize walking/driving distance.
    Uses nearest-neighbor algorithm starting from the first POI.
    
    Args:
        pois: List of POI dicts with lat/lon coordinates
    
    Returns:
        Reordered list of POIs for efficient visiting
    """
    if len(pois) <= 2:
        return pois
    
    def get_coords(poi):
        """Extract lat/lon from POI, checking multiple possible field names"""
        lat = poi.get('lat') or (poi.get('coordinates') or {}).get('lat')
        # Check both 'lng' and 'lon' for longitude
        lon = poi.get('lng') or poi.get('lon') or (poi.get('coordinates') or {}).get('lng') or (poi.get('coordinates') or {}).get('lon')
        return lat, lon
    
    # Check if we have coordinates
    pois_with_coords = [p for p in pois if all(get_coords(p))]
    pois_without_coords = [p for p in pois if not all(get_coords(p))]
    
    if len(pois_with_coords) <= 2:
        return pois  # Not enough coords to optimize
    
    # Nearest-neighbor algorithm
    remaining = pois_with_coords.copy()
    ordered = [remaining.pop(0)]  # Start with first POI
    
    while remaining:
        current = ordered[-1]
        current_lat, current_lon = get_coords(current)
        
        # Find nearest unvisited POI
        nearest = None
        nearest_dist = float('inf')
        
        for poi in remaining:
            poi_lat, poi_lon = get_coords(poi)
            
            # Simple Euclidean distance (good enough for city-scale)
            dist = ((current_lat - poi_lat) ** 2 + (current_lon - poi_lon) ** 2) ** 0.5
            
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = poi
        
        if nearest:
            ordered.append(nearest)
            remaining.remove(nearest)
    
    # Add POIs without coordinates at the end
    ordered.extend(pois_without_coords)
    
    return ordered


# ============================================================================
# OPTIMIZED ROUTE ALGORITHM
# ============================================================================

def optimize_route_andalusia(start_city, end_city, available_cities, centroids, city_name_map, days, parsed_requests, prefs):
    """
    OPTIMIZED ROUTE BUILDER - NO BACKTRACKING
    
    Algorithm:
    1. Filter out cities that cause huge detours (>100% longer)
    2. Score cities by importance + number of attractions
    3. Build route greedily: always pick nearest city that progresses toward destination
    
    Example:
        Input: Málaga to Seville, 8 days
        Output: Málaga → Ronda → Jerez → Cádiz → Córdoba → Antequera → Marbella → Seville
        Distance: ~881km (efficient, no backtracking!)
    """
    
    # Major cities importance scores
    MAJOR_CITIES = {
        'granada': 100, 'cordoba': 90, 'córdoba': 90,
        'seville': 95, 'sevilla': 95, 'cadiz': 85, 'cádiz': 85,
        'malaga': 80, 'málaga': 80, 'ronda': 70,
        'jerez': 65, 'tarifa': 55, 'marbella': 50,
        'antequera': 45, 'nerja': 40
    }
    
    # Parse user requests
    stay_duration = {}
    for city, duration in parsed_requests.get('stay_duration', {}).items():
        stay_duration[normalize_city_name(city)] = duration
    
    must_see_norms = [normalize_city_name(c) for c in parsed_requests.get('must_see_cities', [])]
    avoid_norms = [normalize_city_name(c) for c in parsed_requests.get('avoid_cities', [])]
    
    # Get coordinates
    start_name = city_name_map.get(start_city, start_city)
    end_name = city_name_map.get(end_city, end_city)
    start_coord = centroids.get(start_name)
    end_coord = centroids.get(end_name)
    
    if not start_coord or not end_coord:
        return []
    
    direct_distance = haversine_km(start_coord, end_coord)
    
    # ✅ FIX: Detect circular trip
    is_circular = (end_city == start_city)
    
    # Step 1: Filter and score all candidate cities
    candidates = []
    
    for city_norm, pois in available_cities.items():
        # Skip if should avoid or is start/end
        if city_norm in avoid_norms or city_norm == start_city or city_norm == end_city:
            continue
        
        # ✅ FIX: More lenient POI threshold
        # Major cities like Marbella should be included even with fewer POIs after filtering
        city_name = city_name_map.get(city_norm)
        
        if city_norm in MAJOR_CITIES:
            min_required_pois = 8  # Lenient for major cities (Marbella, Cádiz, etc.)
        else:
            min_required_pois = 12  # Stricter for small towns
        
        if len(pois) < min_required_pois:
            continue
        
        city_coord = centroids.get(city_name)
        
        if not city_coord:
            continue
        
        # Calculate detour: how much longer is it to go through this city?
        dist_start_to_city = haversine_km(start_coord, city_coord)
        dist_city_to_end = haversine_km(city_coord, end_coord)
        total_via_city = dist_start_to_city + dist_city_to_end
        
        # ✅ FIX: For circular trips, detour_ratio doesn't make sense (divide by 0)
        # Instead, just use distance from start as a proxy
        if is_circular:
            detour_ratio = 0  # Accept all cities for circular trips
        else:
            detour_ratio = total_via_city / direct_distance if direct_distance > 0 else 999
        
        # Exclude cities that add >200% to the journey (truly massive detours only)
        # This is very lenient - only excludes cities like Almería for Málaga→Seville
        if detour_ratio > 3.0 and city_norm not in must_see_norms:
            continue
        
        # Calculate score
        # ✅ FIX: Heavily prioritize cities with many attractions
        score = len(pois) * 3  # Triple weight for POI count
        
        if city_norm in MAJOR_CITIES:
            score += MAJOR_CITIES[city_norm]
        
        if city_norm in must_see_norms:
            score += 200  # Must-see gets huge bonus
        
        # Bonus for cities that are truly on the way (low detour)
        if detour_ratio < 1.2:
            score += 50
        
        candidates.append({
            'city_norm': city_norm,
            'city_name': city_name,
            'coord': city_coord,
            'score': score,
            'detour': detour_ratio
        })
    
    # Sort candidates by score (best first)
    candidates.sort(key=lambda x: -x['score'])
    
    # Step 2: Build route using greedy nearest neighbor WITH progress constraint
    # ✅ NEW: Use day allocation table to determine number of cities
    # Old logic: max_intermediate = days - 2 (10 days = 8 intermediate = 10 cities)
    # New logic: Use allocation table (10 days = 3 intermediate = 5 cities)
    
    # Check if user reduced city durations → need extra cities
    extra_cities = parsed_requests.get('extra_cities_needed', 0)
    
    if DAY_ALLOCATION_AVAILABLE:
        base_intermediate = get_max_intermediate_cities(days, is_circular)
        max_intermediate = base_intermediate + extra_cities
        
        if extra_cities > 0:
            st.info(f"📅 Day allocation: {base_intermediate + (1 if is_circular else 2)} base cities + {extra_cities} extra = {max_intermediate + (1 if is_circular else 2)} cities for {days}-day trip")
        else:
            st.info(f"📅 Day allocation: {max_intermediate + (1 if is_circular else 2)} cities for {days}-day trip")
    else:
        max_intermediate = days - 2 if end_city != start_city else days - 1
    
    
    route = [start_city]
    available = candidates[:]
    current_coord = start_coord
    dist_to_end = direct_distance
    
    for step in range(max_intermediate):
        if not available:
            st.write(f"⚠️ No more candidates available after {len(route)} cities")
            break
        
        best = None
        best_score = -float('inf')
        rejected_count = 0
        
        for candidate in available:
            dist_to_candidate = haversine_km(current_coord, candidate['coord'])
            dist_candidate_to_end = haversine_km(candidate['coord'], end_coord)
            
            # ✅ CRITICAL FIX: Skip cities that create drives > MAX_KM_PER_DAY
            # This prevents selecting distant cities that would later need intermediate stops
            MAX_SINGLE_DRIVE = prefs.get("max_km_per_day", 250)
            if dist_to_candidate > MAX_SINGLE_DRIVE and candidate['city_norm'] not in must_see_norms:
                rejected_count += 1
                continue  # Skip city - too far from current position
            
            # KEY: Only consider cities that progress toward destination
            # Very lenient for major cities, moderate for others
            # This ensures Granada, Córdoba, Ronda are included
            if candidate['city_norm'] in MAJOR_CITIES and candidate['score'] > 100:
                tolerance = 150  # Major cities get huge tolerance
            elif candidate['city_norm'] in MAJOR_CITIES:
                tolerance = 100  # Regular major cities
            else:
                tolerance = 50  # Small towns
            
            # ✅ FIX: Skip "progress" filter for circular trips
            if not is_circular:
                if dist_candidate_to_end > dist_to_end + tolerance and candidate['city_norm'] not in must_see_norms:
                    rejected_count += 1
                    continue  # This city doesn't progress toward destination
            
            # Score this candidate
            # REBALANCED: Prioritize city quality over pure geography
            # This ensures Granada, Córdoba are selected despite not being perfectly "on the way"
            nearby_score = max(0, 200 - dist_to_candidate)  # 0-200 points for distance
            
            # ✅ FIX: For circular trips, consider return to start in later steps
            if is_circular and step > max_intermediate / 2:
                # In second half of trip, prefer cities closer to start (completing the loop)
                dist_back_to_start = haversine_km(candidate['coord'], start_coord)
                progress = max(-50, (200 - dist_back_to_start))  # Closer to start = higher score
            else:
                progress = max(-50, (dist_to_end - dist_candidate_to_end) * 1.5)  # -50 to +200 points for progress
            
            quality = candidate['score']  # 0-200+ points for city quality
            
            # Weighted combination: 20% distance, 30% progress, 50% quality
            combined = (nearby_score * 0.2) + (progress * 0.3) + (quality * 0.5)
            
            if combined > best_score:
                best_score = combined
                best = candidate
        
        if best:
            route.append(best['city_norm'])
            current_coord = best['coord']
            dist_to_end = haversine_km(current_coord, end_coord)
            available.remove(best)
        else:
            # Fallback: If NO city passes the strict filter, just pick the highest-scored available city
            if available:
                best_fallback = max(available, key=lambda x: x['score'])
                route.append(best_fallback['city_norm'])
                current_coord = best_fallback['coord']
                dist_to_end = haversine_km(current_coord, end_coord)
                available.remove(best_fallback)
            else:
                st.write(f"  ❌ No cities available at all")
                break
    
    # Add end city (or return to start for circular)
    if end_city and end_city != start_city:
        route.append(end_city)
    elif is_circular:
        route.append(start_city)  # ✅ Close the loop by returning to start
        st.write(f"📍 Full route with return: {route}")
    
    # ===================================================================
    # NEW: POST-PROCESS ROUTE OPTIMIZATION (2-opt improvement)
    # ===================================================================
    def optimize_route_2opt(route, centroids, city_name_map):
        """
        Apply 2-opt optimization to reduce backtracking
        
        2-opt: Try swapping order of intermediate cities to reduce total distance
        """
        if len(route) <= 3:
            return route  # Too short to optimize
        
        improved = True
        iterations = 0
        max_iterations = 10
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            # Don't touch first and last cities
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # Calculate current distance
                    c1_name = city_name_map.get(route[i-1], route[i-1])
                    c2_name = city_name_map.get(route[i], route[i])
                    c3_name = city_name_map.get(route[j], route[j])
                    c4_name = city_name_map.get(route[j+1], route[j+1])
                    
                    c1_coord = centroids.get(c1_name)
                    c2_coord = centroids.get(c2_name)
                    c3_coord = centroids.get(c3_name)
                    c4_coord = centroids.get(c4_name)
                    
                    if not all([c1_coord, c2_coord, c3_coord, c4_coord]):
                        continue
                    
                    # Current edges: c1->c2 and c3->c4
                    current_dist = (haversine_km(c1_coord, c2_coord) + 
                                   haversine_km(c3_coord, c4_coord))
                    
                    # New edges if we reverse: c1->c3 and c2->c4
                    new_dist = (haversine_km(c1_coord, c3_coord) + 
                               haversine_km(c2_coord, c4_coord))
                    
                    # If reversing the segment improves distance, do it
                    if new_dist < current_dist - 1:  # -1 to avoid floating point issues
                        route[i:j+1] = reversed(route[i:j+1])
                        improved = True
                        break
                
                if improved:
                    break
        
        return route
    
    # Apply optimization
    route = optimize_route_2opt(route, centroids, city_name_map)
    
    # ===================================================================
    # ENFORCE MAX KM PER DAY - Insert intermediate cities if needed
    # ===================================================================
    MAX_KM_PER_DAY = prefs.get("max_km_per_day", 250)  # Use user preference (default 250)
    
    def check_and_fix_route(route, centroids, city_name_map, available_cities):
        """Check each leg and insert intermediate cities if distance > MAX_KM_PER_DAY
        
        Returns:
            tuple: (fixed_route, intermediate_cities_set)
        """
        fixed_route = [route[0]]
        intermediate_cities = set()  # Track which cities are just overnight stops
        
        for i in range(len(route) - 1):
            current_city = route[i]
            next_city = route[i + 1]
            
            # Get coordinates
            current_name = city_name_map.get(current_city, current_city)
            next_name = city_name_map.get(next_city, next_city)
            current_coord = centroids.get(current_name)
            next_coord = centroids.get(next_name)
            
            if not current_coord or not next_coord:
                fixed_route.append(next_city)
                continue
            
            distance = haversine_km(current_coord, next_coord)
            
            if distance > MAX_KM_PER_DAY:
                
                # Find best intermediate city
                best_intermediate = None
                best_max_leg = float('inf')
                
                for candidate_norm, pois in available_cities.items():
                    if candidate_norm in route or len(pois) < 3:
                        continue
                    
                    candidate_name = city_name_map.get(candidate_norm)
                    candidate_coord = centroids.get(candidate_name)
                    
                    if not candidate_coord:
                        continue
                    
                    dist_current_to_candidate = haversine_km(current_coord, candidate_coord)
                    dist_candidate_to_next = haversine_km(candidate_coord, next_coord)
                    
                    # Both legs must be under limit
                    if dist_current_to_candidate > MAX_KM_PER_DAY or dist_candidate_to_next > MAX_KM_PER_DAY:
                        continue
                    
                    # Find city that minimizes the maximum leg distance
                    max_leg = max(dist_current_to_candidate, dist_candidate_to_next)
                    
                    if max_leg < best_max_leg:
                        best_max_leg = max_leg
                        best_intermediate = {
                            'norm': candidate_norm,
                            'name': candidate_name,
                            'dist1': dist_current_to_candidate,
                            'dist2': dist_candidate_to_next
                        }
                
                if best_intermediate:
                    fixed_route.append(best_intermediate['norm'])
                    intermediate_cities.add(best_intermediate['norm'])  # Mark as intermediate
                else:
                    st.error(f"❌ Cannot find intermediate city to split {current_name}→{next_name}. "
                            f"This route may not be feasible with current constraints.")
            
            fixed_route.append(next_city)
        
        return fixed_route, intermediate_cities
    
    # ✅ FIX: Don't add intermediate stops - the route optimizer should avoid long drives
    # If a segment is too long, that means we need different cities, not intermediate stops
    intermediate_stops = set()
    
    MAX_RECOMMENDED_KM = prefs.get("max_km_per_day", 250)
    
    # Just warn about long segments but don't modify the route
    for i in range(len(route) - 1):
        city1_norm = route[i]
        city2_norm = route[i+1]
        city1_name = city_name_map.get(city1_norm, city1_norm)
        city2_name = city_name_map.get(city2_norm, city2_norm)
        coord1 = centroids.get(city1_name)
        coord2 = centroids.get(city2_name)
        
        if coord1 and coord2:
            distance = haversine_km(coord1, coord2)
            # Distance checked but no warning displayed
    
    return route, intermediate_stops



# ============================================================================
# STAR/HUB TRIP GENERATOR
# ============================================================================

def generate_star_hub_trip(base_city, days, prefs, attractions, hotels, restaurants=None):
    """
    Generate Star/Hub trip: Stay in one base city and take day trips
    
    Args:
        base_city: The base city to stay in
        days: Number of days
        prefs: User preferences dict
        attractions: All attractions
        hotels: All hotels
        restaurants: All restaurants (optional)
    
    Returns:
        dict with itinerary
    """
    
    
    # Get base city attractions
    base_city_norm = normalize_city_name(base_city)
    base_attractions = [a for a in attractions if normalize_city_name(a.get('city', '')) == base_city_norm]
    
    if not base_attractions:
        st.error(f"❌ No attractions found in {base_city}")
        return None
    
    # Build centroids for distance calculations
    centroids = {}
    for attr in attractions:
        city = attr.get('city')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        
        if city and lat and lon:
            if city not in centroids:
                centroids[city] = (float(lat), float(lon))
    
    base_coord = centroids.get(base_city)
    
    if not base_coord:
        st.error(f"❌ No coordinates found for {base_city}")
        return None
    
    # Find nearby cities for day trips (within reasonable driving distance)
    MAX_DAY_TRIP_KM = 150  # Maximum one-way distance for day trip
    
    nearby_cities = []
    city_attractions_map = {}
    
    for attr in attractions:
        city = attr.get('city')
        if not city or normalize_city_name(city) == base_city_norm:
            continue
        
        city_coord = centroids.get(city)
        if not city_coord:
            continue
        
        # Calculate distance from base
        distance = haversine_km(base_coord, city_coord)
        
        if distance <= MAX_DAY_TRIP_KM:
            city_norm = normalize_city_name(city)
            if city_norm not in city_attractions_map:
                city_attractions_map[city_norm] = {
                    'city': city,
                    'distance': distance,
                    'attractions': []
                }
            city_attractions_map[city_norm]['attractions'].append(attr)
    
    # Filter cities with enough attractions (at least 3 for a day trip)
    for city_norm, data in city_attractions_map.items():
        if len(data['attractions']) >= 3:
            nearby_cities.append(data)
    
    # Sort by combination of distance and quality
    nearby_cities.sort(key=lambda x: -len(x['attractions']) + x['distance']/10)
    
    st.write(f"📍 Found {len(nearby_cities)} cities within {MAX_DAY_TRIP_KM}km for day trips")
    
    # Build itinerary
    itinerary = []
    pace = prefs.get("pace", "medium")
    max_same_cat = prefs.get("max_same_category_per_day", 2)
    
    # Calculate how many days in base city vs day trips
    # ✅ FIX: User wants ONLY Day 1 in base city, all other days are different cities
    days_in_base = 1  # Only first day
    days_for_trips = days - 1  # All remaining days are day trips
    
    day_counter = 1
    
    # Start with 1 day in base city (Day 1 only)
    for i in range(days_in_base):
        city_attractions = [a for a in base_attractions]
        
        # Remove duplicates
        city_attractions = filter_duplicate_pois(city_attractions)
        
        # Select POIs for this day
        # Check for blockbuster attractions
        has_blockbuster = has_blockbuster_attraction(city_attractions)
        quota = compute_poi_quota(pace, len(city_attractions), has_blockbuster)
        selected_pois = apply_diversity(city_attractions, quota, max_same_cat)
        
        # Remove used attractions for next days
        base_attractions = [a for a in base_attractions if a not in selected_pois]
        
        itinerary.append({
            'day': day_counter,
            'city': base_city,
            'driving_km': 0,
            'driving_hours': 0,
            'cities': [{
                'city': base_city,
                'attractions': selected_pois
            }]
        })
        day_counter += 1
    
    # Day trips to nearby cities (ALL remaining days)
    for i in range(min(days_for_trips, len(nearby_cities))):
        day_trip = nearby_cities[i]
        trip_city = day_trip['city']
        trip_distance = day_trip['distance']
        trip_attractions = day_trip['attractions']
        
        # Remove duplicates
        trip_attractions = filter_duplicate_pois(trip_attractions)
        
        # Select POIs for day trip
        quota = compute_poi_quota(pace, len(trip_attractions))
        selected_pois = apply_diversity(trip_attractions, quota, max_same_cat)
        
        # Round trip distance (rounded to 1 decimal)
        total_km = round(trip_distance * 2, 1)
        driving_hours = round(calculate_driving_time(trip_distance) * 2, 1)  # Round trip
        
        itinerary.append({
            'day': day_counter,
            'city': trip_city,
            'is_day_trip': True,
            'base': base_city,  # ✅ FIX: Changed from 'base_city' to 'base'
            'driving_km': total_km,
            'driving_hours': driving_hours,
            'cities': [{
                'city': trip_city,
                'attractions': selected_pois
            }]
        })
        day_counter += 1
    
    # ✅ REMOVED: No more days at end in base city
    # User wants ONLY Day 1 in base, all others are different cities
    
    # ✅ REMOVED: No more days at end in base city
    # User wants ONLY Day 1 in base, all others are different cities
    
    # Get hotels for base city only
    base_city_hotels = [h for h in hotels if normalize_city_name(h.get('city', '')) == base_city_norm]
    
    # ✅ P1 FIX: Filter hotels by distance (max 15km from city center)
    base_attrs = [a for a in attractions if normalize_city_name(a.get('city', '')) == base_city_norm]
    if base_attrs:
        valid_coords = [(a.get('lat'), a.get('lon') or a.get('lng')) 
                       for a in base_attrs 
                       if a.get('lat') and (a.get('lon') or a.get('lng'))]
        if valid_coords:
            city_center_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
            city_center_lon = sum(c[1] for c in valid_coords) / len(valid_coords)
            
            def hotel_in_radius(hotel, max_km=15):
                h_lat = hotel.get('lat') or hotel.get('latitude')
                h_lon = hotel.get('lon') or hotel.get('lng') or hotel.get('longitude')
                if not h_lat or not h_lon:
                    return True
                dist = haversine_km((city_center_lat, city_center_lon), (h_lat, h_lon))
                return dist is not None and dist <= max_km
            
            base_city_hotels = [h for h in base_city_hotels if hotel_in_radius(h)]
    
    # Sort hotels by rating
    top_hotels = sorted(base_city_hotels, key=lambda x: x.get('rating', 0), reverse=True)[:3]
    
    # Add restaurants if available
    if restaurants:
        try:
            from restaurant_service import add_restaurants_to_itinerary
            itinerary = add_restaurants_to_itinerary(
                itinerary,
                restaurants,
                prefs.get('budget', 'mid-range'),
                prefs
            )
        except Exception as e:
            print(f"⚠️ Could not add restaurants: {e}")
    
    # Calculate summary
    visited_cities = [base_city]
    for day_data in itinerary:
        if day_data.get('is_day_trip'):
            city = day_data['city']
            if city not in visited_cities:
                visited_cities.append(city)
    
    total_driving_km = round(sum(day['driving_km'] for day in itinerary), 1)
    
    # Google Maps link
    day_trip_cities = [d['city'] for d in itinerary if d.get('is_day_trip')]
    maps_link = google_maps_link([base_city] + day_trip_cities)
    
    st.success(f"⭐ Star/Hub trip generated! Base: {base_city} | {len(day_trip_cities)} day trips | {total_driving_km:.0f}km total")
    
    return {
        'itinerary': itinerary,
        'ordered_cities': visited_cities,
        'hop_kms': [0] * (len(visited_cities) - 1),
        'total_km': total_driving_km,
        'maps_link': maps_link,
        'start_end_text': base_city,
        'days': days,
        'preferences': prefs,
        'trip_type': 'Star/Hub',
        'base_city': base_city,
        'base_hotels': top_hotels
    }


# ============================================================================
# MAIN TRIP GENERATION FUNCTION
# ============================================================================

def generate_simple_trip(start_end_text, days, prefs, trip_type, attractions, hotels, restaurants=None, start_date=None):
    """
    Generate car-based trip itinerary with optimized routing
    
    Args:
        restaurants: Optional list of restaurant data
        start_date: Optional trip start date for seasonal filtering
    
    Returns:
        dict with: itinerary, ordered_cities, hop_kms, maps_link
    """
    
    # ✅ NEW: Detect Star/Hub trip type
    is_star_hub = trip_type and ('star' in trip_type.lower() or 'hub' in trip_type.lower())
    
    if is_star_hub:
        # For Star/Hub, start_end_text is just the base city
        base_city = start_end_text.strip()
        
        # Build set of known cities
        known_cities = {(attr.get('city') or '').strip() for attr in attractions}
        known_cities.discard('')
        
        # Canonicalize base city
        base_city_canonical = canonicalize_city(base_city, known_cities)
        
        if not base_city_canonical:
            cities_list = ', '.join(sorted(known_cities)[:10])
            st.error(f"❌ Base city '{base_city}' not found in data")
            return None
        
        # Route to Star/Hub generator
        return generate_star_hub_trip(
            base_city_canonical,
            days,
            prefs,
            attractions,
            hotels,
            restaurants
        )
    
    # ✅ NEW: Build set of known cities from attractions
    known_cities = {(attr.get('city') or '').strip() for attr in attractions}
    known_cities.discard('')
    
    # ✅ NEW: Parse and canonicalize start/end cities
    start_city, end_city = parse_start_end(start_end_text, trip_type)
    
    if not start_city:
        st.error("❌ Please specify a start city")
        return None
    
    # ✅ NEW: Canonicalize city names to match dataset
    start_city_canonical = canonicalize_city(start_city, known_cities)
    end_city_canonical = canonicalize_city(end_city, known_cities) if end_city else None
    
    # ✅ NEW: Better error handling
    if not start_city_canonical:
        cities_list = ', '.join(sorted(known_cities)[:10])
        st.error(f"❌ Start city '{start_city}' not found in data")
        return None
    
    if end_city and not end_city_canonical:
        st.error(f"❌ End city '{end_city}' not found in data")
        return None
    
    # ✅ NEW: Use canonical names going forward
    start_city = start_city_canonical
    end_city = end_city_canonical
    
    # ✅ FILTER: Apply minimum rating filter (5.0 scale)
    min_rating = prefs.get('min_poi_rating', 0.0)
    original_total = len(attractions)
    
    if min_rating > 0:
        attractions = [a for a in attractions if (a.get('rating') or 0) >= min_rating]
        # print(f"📊 Rating filter ({min_rating}+ stars): {original_total} → {len(attractions)} POIs")
    
    # ✅ P1 FIX: Filter out hotels from attractions list
    hotel_keywords = ['hotel', 'hostel', 'hostal', 'aparthotel', 'parador', 'inn', 'motel', 'b&b', 'pension', 'pensión']
    def is_hotel_poi(poi):
        name = (poi.get('name') or '').lower()
        category = (poi.get('category') or '').lower()
        subcategory = (poi.get('subcategory') or '').lower()
        
        # Check if it's a hotel
        if 'hotel' in category or 'accommodation' in category or 'lodging' in category:
            return True
        for keyword in hotel_keywords:
            if keyword in name.lower():
                return True
        return False
    
    attractions = [a for a in attractions if not is_hotel_poi(a)]
    
    # ✅ P1 FIX: Filter out POIs with generic placeholder descriptions
    generic_phrases = [
        'a notable landmark attraction in the area',
        'is worth visiting to experience local culture',
        'a notable attraction in the area',
        'worth visiting to experience',
        'a notable museum attraction',
        'a notable historic site',
    ]
    def has_generic_description(poi):
        desc = (poi.get('description') or '').lower()
        if not desc or len(desc) < 50:  # Very short or no description
            return False  # Don't filter, just no description
        for phrase in generic_phrases:
            if phrase in desc:
                return True
        return False
    
    attractions = [a for a in attractions if not has_generic_description(a)]
    
    # ✅ NEW: Seasonal filtering - reduce beach POIs in winter months
    if start_date:
        trip_month = start_date.month if hasattr(start_date, 'month') else None
        
        if trip_month and trip_month in [11, 12, 1, 2, 3]:  # Nov-Mar = winter
            # Filter out beach-specific POIs in winter
            beach_keywords = ['beach', 'playa', 'swimming', 'water park', 'aquapark']
            
            def is_beach_poi(poi):
                name = (poi.get('name') or '').lower()
                category = (poi.get('category') or '').lower()
                subcategory = (poi.get('subcategory') or '').lower()
                description = (poi.get('description') or '').lower()
                
                # Check if it's primarily a beach attraction
                for keyword in beach_keywords:
                    if keyword in name or keyword in subcategory:
                        return True
                # Check category
                if 'beach' in category:
                    return True
                return False
            
            # Keep non-beach POIs + some beach POIs (in case user specifically wants them)
            non_beach = [a for a in attractions if not is_beach_poi(a)]
            beach_pois = [a for a in attractions if is_beach_poi(a)]
            
            # Keep only top 20% of beach POIs in winter (for context, not main attractions)
            beach_to_keep = beach_pois[:max(5, len(beach_pois) // 5)]
            
            attractions = non_beach + beach_to_keep
    
    # ✅ FILTER: Apply category filter (if specified)
    preferred_categories = prefs.get('poi_categories', [])
    if preferred_categories:
        # ✅ FIX: Use category mapping to match app UI categories to database categories
        from category_mapping import get_database_categories_for_filter
        
        # Convert app UI categories (e.g. "history") to database categories (e.g. "Historic Site")
        database_categories = get_database_categories_for_filter(preferred_categories)
        database_categories_lower = [cat.lower() for cat in database_categories]
        
        
        attractions_after_category = [a for a in attractions 
                      if a.get('category', '').lower() in database_categories_lower]
        
        # ⚠️ Safety check: Don't over-filter!
        if len(attractions_after_category) < 200:
            # Too restrictive, skip category filter
            pass
        else:
            attractions = attractions_after_category
    
    # ✅ Critical check: Ensure we have enough POIs
    if len(attractions) < 30:
        st.error(f"❌ Only {len(attractions)} attractions match your filters. Please adjust preferences:")
        return None
    
    # ✅ Critical check: Ensure start/end cities have POIs
    start_city_pois = [a for a in attractions if normalize_city_name(a.get('city', '')) == normalize_city_name(start_city)]
    if not start_city_pois:
        st.error(f"❌ No attractions found in {start_city} after filtering. Please adjust your preferences.")
        return None
    
    if end_city:
        end_city_pois = [a for a in attractions if normalize_city_name(a.get('city', '')) == normalize_city_name(end_city)]
        if not end_city_pois:
            st.error(f"❌ No attractions found in {end_city} after filtering. Please adjust your preferences.")
            return None
    
    
    # Build city coordinates map (centroids)
    centroids = {}
    for attr in attractions:
        city = attr.get('city')
        coords = attr.get('coordinates', {})
        lat = coords.get('latitude') or coords.get('lat')
        lon = coords.get('longitude') or coords.get('lng') or coords.get('lon')
        
        if city and lat and lon:
            if city not in centroids:
                centroids[city] = (float(lat), float(lon))
    
    # Group attractions by city (normalized)
    by_city_normalized = {}
    city_name_map = {}  # normalized -> original
    
    for attr in attractions:
        city = attr.get('city')
        if not city:
            continue
        
        city_norm = normalize_city_name(city)
        
        if city_norm not in city_name_map:
            city_name_map[city_norm] = city
        
        if city_norm not in by_city_normalized:
            by_city_normalized[city_norm] = []
        
        by_city_normalized[city_norm].append(attr)
    
    # Build route using optimized algorithm
    
    # Normalize for internal routing
    start_city_norm = normalize_city_name(start_city)
    end_city_norm = normalize_city_name(end_city) if end_city else None
    
    # ✅ NEW: Parse special requests for avoid/must-see cities
    notes = prefs.get('notes', '').lower()
    avoid_cities = []
    must_see_cities = []
    
    # Parse "avoid X" patterns
    import re
    avoid_patterns = [
        r'avoid\s+([a-záéíóúñ\s]+?)(?:\s*[,.]|$)',
        r'skip\s+([a-záéíóúñ\s]+?)(?:\s*[,.]|$)',
        r'no\s+([a-záéíóúñ\s]+?)(?:\s*[,.]|$)',
        r"don'?t\s+(?:go\s+to\s+|visit\s+)?([a-záéíóúñ\s]+?)(?:\s*[,.]|$)",
    ]
    for pattern in avoid_patterns:
        matches = re.findall(pattern, notes)
        for match in matches:
            city = match.strip()
            if city and len(city) > 2:
                avoid_cities.append(city)
                # print(f"🚫 User wants to avoid: {city}")
    
    # Parse "must see X" patterns
    must_see_patterns = [
        r'must\s+(?:see|visit)\s+([a-záéíóúñ\s]+?)(?:\s*[,.]|$)',
        r'definitely\s+(?:see|visit)\s+([a-záéíóúñ\s]+?)(?:\s*[,.]|$)',
        r'include\s+([a-záéíóúñ\s]+?)(?:\s*[,.]|$)',
    ]
    for pattern in must_see_patterns:
        matches = re.findall(pattern, notes)
        for match in matches:
            city = match.strip()
            if city and len(city) > 2:
                must_see_cities.append(city)
                # print(f"⭐ User must see: {city}")
    
    # ✅ NEW: Parse duration overrides BEFORE route optimization
    # to calculate if we need extra cities
    user_duration_overrides = {}
    extra_cities_needed = 0
    if DAY_ALLOCATION_AVAILABLE:
        user_duration_overrides = parse_user_duration_requests(prefs.get('notes', ''))
        if user_duration_overrides:
            # print(f"📅 User duration overrides: {user_duration_overrides}")
            
            # Calculate days saved by user reductions
            for city, user_days in user_duration_overrides.items():
                default_days = get_recommended_days_for_city(city, days)
                if default_days > user_days:
                    days_saved = default_days - user_days
                    extra_cities_needed += days_saved
                    # print(f"📅 {city}: reduced from {default_days} to {user_days} days → need {days_saved} more city days")
    
    parsed_requests = {
        'stay_duration': user_duration_overrides,
        'must_see_cities': must_see_cities,
        'avoid_cities': avoid_cities,
        'extra_cities_needed': extra_cities_needed,  # ✅ Pass to optimizer
    }
    
    route, intermediate_stops = optimize_route_andalusia(
        start_city_norm,
        end_city_norm,
        by_city_normalized,
        centroids,
        city_name_map,
        days,
        parsed_requests,
        prefs  # Add prefs parameter
    )
    
    if not route:
        st.error("❌ Could not generate route")
        return None
    
    # Convert to original city names
    ordered_cities = [city_name_map.get(c, c) for c in route]
    
    
    # ========================================================================
    # ✅ USE DAY ALLOCATION TABLE FOR MULTI-DAY CITY STAYS
    # ========================================================================
    
    # user_duration_overrides already parsed above before route optimization
    
    # Get day allocation for each city
    if DAY_ALLOCATION_AVAILABLE:
        # Remove duplicate consecutive cities for allocation (circular trips)
        unique_cities = []
        for city in ordered_cities:
            if not unique_cities or city != unique_cities[-1]:
                unique_cities.append(city)
        
        day_allocation = allocate_days_for_route(unique_cities, days, user_duration_overrides)
        # print(f"📅 Day allocation result: {day_allocation}")
        # print(get_allocation_summary(day_allocation, days))
    else:
        # Fallback: 1 day per city
        day_allocation = {city: 1 for city in ordered_cities}
    
    # Build day-by-day itinerary with MULTIPLE DAYS per important city
    itinerary = []
    pace = prefs.get("pace", "medium")
    max_same_cat = prefs.get("max_same_category_per_day", 2)
    day_counter = 1
    
    # ✅ FIX: For circular trips, detect if last city is return to start
    is_circular_trip = (len(route) >= 2 and route[0] == route[-1])
    start_city_for_hotels = city_name_map.get(route[0], route[0]) if is_circular_trip else None
    
    # Track which POIs have been used per city (for multi-day visits)
    used_pois_by_city = {}
    
    for i, city_norm in enumerate(route):
        city_original = city_name_map.get(city_norm, city_norm)
        
        # ✅ FIX: For circular trips, skip the last city (return to start)
        if is_circular_trip and i == len(route) - 1:
            continue
        
        # Get number of days for this city from allocation
        # Try multiple key formats (original name, normalized, with accents)
        days_in_city = day_allocation.get(city_original)
        if days_in_city is None:
            days_in_city = day_allocation.get(city_norm)
        if days_in_city is None:
            # Try case-insensitive match
            for alloc_city, alloc_days in day_allocation.items():
                if normalize_city_name(alloc_city) == normalize_city_name(city_original):
                    days_in_city = alloc_days
                    break
        if days_in_city is None:
            days_in_city = 1  # Default fallback
            print(f"⚠️ No allocation found for '{city_original}', defaulting to 1 day")
        
        # Skip cities with 0 days allocated
        if days_in_city <= 0:
            continue
        
        city_attrs = by_city_normalized.get(city_norm, [])
        
        # Initialize used POIs tracking for this city
        if city_original not in used_pois_by_city:
            used_pois_by_city[city_original] = set()
        
        # ✅ P2 FIX: Track landmark canonical names to prevent showing same landmark twice
        used_landmarks_by_city = {}
        landmark_aliases = {
            'giralda': ['giralda', 'torre giralda', 'la giralda'],
            'alhambra': ['alhambra', 'la alhambra', 'palacio de la alhambra'],
            'mezquita': ['mezquita', 'mezquita-catedral', 'mosque-cathedral'],
            'alcazar': ['real alcazar', 'alcazar de sevilla', 'alcazar', 'alcázar'],
            'alcazaba': ['alcazaba', 'alcazaba de malaga'],
            'cathedral': ['catedral', 'cathedral'],
            'plaza_espana': ['plaza de espana', 'plaza españa', 'plaza espana'],
            'generalife': ['generalife', 'jardines del generalife'],
        }
        
        def get_landmark_canonical(poi_name):
            """Get canonical landmark name if this is a known landmark"""
            import unicodedata
            # Strip accents for comparison
            name_lower = ''.join(
                c for c in unicodedata.normalize('NFD', poi_name.lower())
                if unicodedata.category(c) != 'Mn'
            )
            for canonical, aliases in landmark_aliases.items():
                for alias in aliases:
                    alias_clean = ''.join(
                        c for c in unicodedata.normalize('NFD', alias.lower())
                        if unicodedata.category(c) != 'Mn'
                    )
                    if alias_clean in name_lower:
                        return canonical
            return None
        
        # ✅ Sort and score all POIs for this city once
        all_city_pois = score_and_sort_pois(city_attrs, city_original)
        
        # Create multiple days for this city
        for day_in_city in range(days_in_city):
            # Get POIs not yet used in previous days
            def is_poi_available(p):
                name = p.get('name', '')
                # Check if name already used
                if name in used_pois_by_city[city_original]:
                    return False
                # Check if it's a landmark variation we already have
                landmark_key = get_landmark_canonical(name)
                if landmark_key and landmark_key in used_landmarks_by_city.get(city_original, set()):
                    return False
                return True
            
            available_pois = [p for p in all_city_pois if is_poi_available(p)]
            
            # If we've used all POIs, allow repeats from the full list
            if not available_pois:
                available_pois = all_city_pois
            
            # Select POIs for this day
            has_blockbuster = has_blockbuster_attraction(available_pois)
            quota = compute_poi_quota(pace, len(available_pois), has_blockbuster)
            selected = apply_diversity(available_pois, quota, max_same_cat)
            
            # Mark selected POIs as used (both name and landmark key)
            for poi in selected:
                poi_name = poi.get('name', '')
                used_pois_by_city[city_original].add(poi_name)
                # Also track landmark canonical name
                landmark_key = get_landmark_canonical(poi_name)
                if landmark_key:
                    if city_original not in used_landmarks_by_city:
                        used_landmarks_by_city[city_original] = set()
                    used_landmarks_by_city[city_original].add(landmark_key)
            
            # ✅ Check must-see landmark coverage (only on first day in city)
            major_cities = ['Granada', 'Seville', 'Córdoba', 'Málaga', 'Cádiz', 'Ronda']
            if city_original in major_cities and day_in_city == 0:
                must_see_count = get_must_see_count(selected, city_original)
                missing = get_missing_must_sees(selected, city_original)
                
                if missing and len(missing) > 2:
                    # Try to force-add top missing landmark
                    if len(selected) < quota:
                        for poi in available_pois:
                            poi_name = poi.get('name', '')
                            if any(m.lower() in poi_name.lower() for m in missing):
                                selected.append(poi)
                                used_pois_by_city[city_original].add(poi_name)
                                break
                elif must_see_count > 0:
                    st.success(f"✅ {city_original}: {must_see_count} must-see landmarks included")
            
            # Determine overnight city
            is_last_day_in_city = (day_in_city == days_in_city - 1)
            is_first_day_in_city = (day_in_city == 0)
            
            if is_circular_trip and i == len(route) - 2 and is_last_day_in_city:
                overnight_city = start_city_for_hotels
            else:
                overnight_city = city_original
            
            # ✅ NEW: Only show hotels on FIRST day in each city (like hub trips)
            # Include number of nights for booking
            if is_first_day_in_city:
                # Get hotels for the overnight city
                city_hotels = [h for h in hotels if cities_match(h.get("city", ""), overnight_city)]
                
                # ✅ P1 FIX: Filter hotels by distance (max 15km from city center)
                # Get city center coordinates from attractions
                city_attrs = [a for a in attractions if cities_match(a.get('city', ''), overnight_city)]
                if city_attrs:
                    # Calculate city center as average of attraction coords
                    valid_coords = [(a.get('lat'), a.get('lon') or a.get('lng')) 
                                   for a in city_attrs 
                                   if a.get('lat') and (a.get('lon') or a.get('lng'))]
                    if valid_coords:
                        city_center_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
                        city_center_lon = sum(c[1] for c in valid_coords) / len(valid_coords)
                        
                        # Filter hotels within 15km of city center
                        def hotel_within_radius(hotel, max_km=15):
                            h_lat = hotel.get('lat') or hotel.get('latitude')
                            h_lon = hotel.get('lon') or hotel.get('lng') or hotel.get('longitude')
                            if not h_lat or not h_lon:
                                return True  # Keep hotels without coords (can't verify)
                            
                            # Simple distance calculation
                            dist = haversine_km((city_center_lat, city_center_lon), (h_lat, h_lon))
                            return dist is not None and dist <= max_km
                        
                        city_hotels = [h for h in city_hotels if hotel_within_radius(h)]
                
                # Filter hotels with low ratings
                filtered_hotels = [h for h in city_hotels 
                                  if (h.get("guest_rating") or h.get("rating", 0) or 0) >= 7.0 
                                  or (h.get("guest_rating") or h.get("rating", 0) or 0) == 0]
                
                top_hotels = sorted(filtered_hotels, 
                                   key=lambda x: x.get("guest_rating") or x.get("rating", 0) or 0, 
                                   reverse=True)[:3]
                
                # Add number of nights to each hotel
                nights_in_city = days_in_city
                for h in top_hotels:
                    h['nights'] = nights_in_city
            else:
                # Not first day - no hotels to show (already booked)
                top_hotels = []
            
            # Get restaurants for this city
            city_restaurants = []
            if restaurants:
                city_restaurants = [r for r in restaurants if cities_match(r.get("city", ""), city_original)]
                
                # Filter restaurants with few reviews
                filtered_restaurants = []
                for r in city_restaurants:
                    reviews_count = r.get("reviews_count", 0) or r.get("user_ratings_total", 0)
                    
                    if reviews_count == 0:
                        topic = r.get("topic", "")
                        if topic:
                            parts = topic.split()
                            if parts and parts[0].isdigit():
                                reviews_count = int(parts[0])
                    
                    if reviews_count == 0 or reviews_count >= 20:
                        filtered_restaurants.append(r)
                
                top_restaurants = sorted(filtered_restaurants, key=lambda x: x.get("rating") or 0, reverse=True)
            else:
                top_restaurants = []
            
            # Vary restaurant selection for multi-day visits
            restaurant_offset = day_in_city * 2
            lunch_restaurant = top_restaurants[restaurant_offset] if len(top_restaurants) > restaurant_offset else None
            dinner_restaurant = top_restaurants[restaurant_offset + 1] if len(top_restaurants) > restaurant_offset + 1 else None
            
            # ✅ NEW: Get route stops for last day in city (when traveling to next city)
            route_stops = []
            if is_last_day_in_city and i < len(route) - 1:
                # Find next city in route
                next_city_norm = route[i + 1]
                next_city_original = city_name_map.get(next_city_norm, next_city_norm)
                
                # Skip if next city is same as current (circular return)
                if normalize_city_name(next_city_original) != normalize_city_name(city_original):
                    route_stops = get_route_stops(city_original, next_city_original, max_stops=2)
                    if route_stops:
                        pass  # Route stops found, will be added to day data
            
            itinerary.append({
                "day": day_counter,
                "city": city_original,
                "cities": [{"city": city_original, "attractions": selected}],
                "overnight_city": overnight_city,
                "hotels": top_hotels,
                "lunch_restaurant": lunch_restaurant,
                "dinner_restaurant": dinner_restaurant,
                "day_in_city": day_in_city + 1,  # Which day in this city (1, 2, 3...)
                "total_days_in_city": days_in_city,  # Total days in this city
                "route_stops": route_stops,  # ✅ NEW: Stops on the way to next city
                "is_travel_day": is_last_day_in_city and i < len(route) - 1,  # Flag for travel days
            })
            day_counter += 1
    
    # Renumber all days sequentially
    for i, day_data in enumerate(itinerary, 1):
        day_data['day'] = i
    
    # Calculate distances between cities
    hop_kms = []
    total_km = 0
    
    
    # ✅ FIX: Detect circular trip for distance calculation
    is_circular_route = (len(ordered_cities) >= 2 and 
                        normalize_city_name(ordered_cities[0]) == normalize_city_name(ordered_cities[-1]))
    
    # Calculate distances between consecutive cities
    # For circular trips, this will calculate all segments including return
    for i in range(len(ordered_cities) - 1):
        city1 = ordered_cities[i]
        city2 = ordered_cities[i + 1]
        c1 = centroids.get(city1)
        c2 = centroids.get(city2)
        
        
        if c1 and c2:
            dist = haversine_km(c1, c2)
            if dist and not math.isinf(dist):
                hop_kms.append(round(dist))
                total_km += dist
            else:
                hop_kms.append(None)
        else:
            hop_kms.append(None)
            if not c1:
                st.error(f"  - ❌ No coordinates found for city: **{city1}**")
                st.write(f"     Trying to look up '{city1}' in centroids...")
            if not c2:
                st.error(f"  - ❌ No coordinates found for city: **{city2}**")
                st.write(f"     Trying to look up '{city2}' in centroids...")
    
    # Generate Google Maps link
    maps_link = google_maps_link(ordered_cities)
    
    return {
        "itinerary": itinerary,
        "ordered_cities": ordered_cities,
        "hop_kms": hop_kms,
        "total_km": round(total_km, 1),
        "maps_link": maps_link,
        "day_allocation": day_allocation,  # ✅ NEW: Include day allocation for display
    }