"""
Car-Based Itinerary Generator for Andalusia Travel App
WITH OPTIMIZED ROUTE ALGORITHM (No Backtracking!)
"""

import streamlit as st
import math
import unicodedata
from collections import Counter
from urllib.parse import quote_plus
from text_norm import canonicalize_city, norm_key # ✅ NEW: Import text normalization
# from semantic_merge import merge_city_pois # ⚠️ DISABLED: Too aggressive, removing valid POIs

# ✅ NEW: Import weighted scoring and must-see landmarks
from must_see_landmarks import is_must_see, get_must_see_count, get_missing_must_sees
from weighted_poi_scoring import calculate_weighted_score, score_and_sort_pois


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
    
    R = 6371 # Earth radius in km
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c * road_factor
    
    return distance if distance < 10000 else None # Sanity check




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
        return distance_km / 40 + 0.25 # Add 15 min for traffic/parking
    elif distance_km < 100:
        # Regional roads: moderate (70 km/h average)
        return distance_km / 70 + 0.25
    else:
        # Highway: faster (100 km/h average)
        return distance_km / 100 + 0.5 # Add 30 min for rest stops

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
    """Remove duplicate POIs based on name similarity"""
    if not pois:
        return []
    
    seen_normalized = set()
    unique = []
    
    # Translation map for common city name variations
    name_translations = {
        'sevilla': 'seville',
        'córdoba': 'cordoba',
        'málaga': 'malaga',
        'cádiz': 'cadiz'
    }
    
    for poi in pois:
        name = poi.get('name', '').lower().strip()
        
        if not name:
            continue
        
        # Normalize name (remove common building type words)
        normalized = name
        
        # Remove common words
        words_to_remove = [
            'cathedral', 'catedral', 'mosque', 'mezquita',
            'church', 'iglesia', 'palace', 'palacio',
            'museum', 'museo', 'of', 'de', 'del', 'la', 'el',
            'the', '-', 'and', 'y'
        ]
        
        for word in words_to_remove:
            normalized = normalized.replace(word, '')
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        # Apply translations
        for spanish, english in name_translations.items():
            normalized = normalized.replace(spanish, english)
        
        # Remove all spaces for final comparison
        normalized = normalized.replace(' ', '')
        
        if normalized and normalized not in seen_normalized:
            seen_normalized.add(normalized)
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
        else: # medium
            quota = min(3, total_pois)
    else:
        # Normal days without blockbusters
        if pace == "relaxed":
            quota = min(5, total_pois)
        elif pace == "fast":
            quota = min(7, total_pois)
        else: # medium
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
            quota = min(3, total_pois) # 3 max with blockbuster
        elif pace == "fast":
            quota = min(4, total_pois)
        else: # medium
            quota = min(3, total_pois) # Conservative default
    else:
        # Normal days without blockbusters
        if pace == "relaxed":
            quota = min(5, total_pois)
        elif pace == "fast":
            quota = min(7, total_pois) # Reduced from 8
        else: # medium
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
    max_duration_minutes = 8 * 60 # 8 hours max sightseeing per day
    
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
    
    return selected