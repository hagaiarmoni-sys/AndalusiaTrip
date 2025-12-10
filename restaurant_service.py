"""
Restaurant Service for Andalusia Travel App
Recommends lunch and dinner restaurants NEAR the POIs being visited
"""

import unicodedata
import math
from typing import List, Dict, Optional


def normalize_city_name(city_name):
    """Normalize city name by removing accents and converting to lowercase"""
    if not city_name:
        return ""
    city_name = str(city_name)
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


def cities_match(city1, city2):
    """Check if two city names match (ignoring accents and case)"""
    return normalize_city_name(city1) == normalize_city_name(city2)


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates in kilometers
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    
    try:
        R = 6371.0  # Earth radius in km
        
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    except:
        return float('inf')


def get_poi_center(pois):
    """
    Calculate the geographic center of a list of POIs
    
    Args:
        pois: List of POI dicts with coordinates
    
    Returns:
        Tuple of (avg_lat, avg_lon) or None if no valid coordinates
    """
    valid_coords = []
    
    for poi in pois:
        coords = poi.get('coordinates', {})
        lat = coords.get('lat') or coords.get('latitude')
        lon = coords.get('lon') or coords.get('lng') or coords.get('longitude')
        
        if lat is not None and lon is not None:
            try:
                valid_coords.append((float(lat), float(lon)))
            except:
                continue
    
    if not valid_coords:
        return None
    
    avg_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
    avg_lon = sum(c[1] for c in valid_coords) / len(valid_coords)
    
    return (avg_lat, avg_lon)


def categorize_restaurant_by_time(restaurant):
    """
    Categorize restaurant as suitable for lunch, dinner, or both
    Based on cuisine type, price range, and ambiance
    """
    name = restaurant.get('name', '').lower()
    cuisine = restaurant.get('cuisine', '').lower()
    price_range = restaurant.get('price_range', '$')
    
    # Keywords that suggest lunch spots
    lunch_keywords = ['tapas', 'cafe', 'cafeteria', 'market', 'mercado', 'bistro', 'casual']
    
    # Keywords that suggest fine dining (dinner)
    dinner_keywords = ['fine dining', 'gourmet', 'michelin', 'starred', 'upscale', 'elegant']
    
    # Check name and cuisine
    is_casual = any(keyword in name or keyword in cuisine for keyword in lunch_keywords)
    is_fine = any(keyword in name or keyword in cuisine for keyword in dinner_keywords)
    
    # Price-based classification
    if price_range in ['$$$', '$$$$']:
        is_fine = True
    elif price_range == '$':
        is_casual = True
    
    if is_fine:
        return 'dinner'
    elif is_casual:
        return 'lunch'
    else:
        return 'both'  # Can work for both meals


def get_restaurants_near_pois(city, all_restaurants, pois, max_distance_km=1.5):
    """
    Get restaurants near the POIs being visited (NOT just in the city)
    
    Args:
        city: City name (string)
        all_restaurants: List of all restaurant dicts
        pois: List of POI dicts for the day
        max_distance_km: Maximum distance from POIs (default 1.5km walking distance)
    
    Returns:
        List of restaurant dicts near the POIs, sorted by distance
    """
    
    # Get POI center point
    poi_center = get_poi_center(pois)
    
    if not poi_center:
        # Fallback: just return restaurants in the city
        return get_restaurants_for_city(city, all_restaurants)
    
    center_lat, center_lon = poi_center
    
    # Find restaurants near POIs
    nearby_restaurants = []
    
    for restaurant in all_restaurants:
        restaurant_city = restaurant.get('city', '')
        
        # Must be in same city
        if not cities_match(restaurant_city, city):
            continue
        
        # Get restaurant coordinates
        coords = restaurant.get('coordinates', {})
        rest_lat = coords.get('lat') or coords.get('latitude')
        rest_lon = coords.get('lon') or coords.get('lng') or coords.get('longitude')
        
        if rest_lat is None or rest_lon is None:
            continue
        
        # Calculate distance from POI center
        distance = haversine_km(center_lat, center_lon, rest_lat, rest_lon)
        
        # Only include if within walking distance
        if distance <= max_distance_km:
            restaurant_copy = restaurant.copy()
            restaurant_copy['distance_from_pois'] = round(distance, 2)
            nearby_restaurants.append(restaurant_copy)
    
    # Sort by distance (closest first)
    nearby_restaurants.sort(key=lambda x: x.get('distance_from_pois', 999))
    
    return nearby_restaurants


def get_restaurants_for_city(city, all_restaurants):
    """
    Get all restaurants for a specific city (fallback when no POI coordinates)
    
    Args:
        city: City name (string)
        all_restaurants: List of all restaurant dicts
    
    Returns:
        List of restaurant dicts for the city
    """
    city_restaurants = []
    
    for restaurant in all_restaurants:
        restaurant_city = restaurant.get('city', '')
        if cities_match(restaurant_city, city):
            city_restaurants.append(restaurant)
    
    return city_restaurants


def select_restaurants_for_day(city, all_restaurants, pois, budget='mid-range', preferences=None):
    """
    Select lunch and dinner restaurants NEAR the POIs being visited
    
    Args:
        city: City name
        all_restaurants: List of all restaurant dicts from JSON
        pois: List of POI dicts being visited this day
        budget: 'budget', 'mid-range', or 'luxury'
        preferences: Dict with user preferences (cuisine preferences, etc.)
    
    Returns:
        Dict with 'lunch' and 'dinner' restaurant recommendations
    """
    if preferences is None:
        preferences = {}
    
    # ✅ KEY CHANGE: Get restaurants NEAR the POIs, not just in the city
    nearby_restaurants = get_restaurants_near_pois(city, all_restaurants, pois, max_distance_km=1.5)
    
    if not nearby_restaurants:
        # Fallback: get all city restaurants if none near POIs
        nearby_restaurants = get_restaurants_for_city(city, all_restaurants)
    
    if not nearby_restaurants:
        return {
            'lunch': None,
            'dinner': None
        }
    
    # Budget mapping to price ranges
    budget_map = {
        'budget': ['$', '$$'],
        'mid-range': ['$$', '$$$'],
        'luxury': ['$$$', '$$$$']
    }
    
    allowed_prices = budget_map.get(budget, ['$$', '$$$'])
    
    # Filter by budget
    filtered = [r for r in nearby_restaurants if r.get('price_range') in allowed_prices]
    
    # If too few after filtering, use all nearby restaurants
    if len(filtered) < 2:
        filtered = nearby_restaurants
    
    # Categorize restaurants
    lunch_suitable = []
    dinner_suitable = []
    both_suitable = []
    
    for restaurant in filtered:
        category = categorize_restaurant_by_time(restaurant)
        
        if category == 'lunch':
            lunch_suitable.append(restaurant)
        elif category == 'dinner':
            dinner_suitable.append(restaurant)
        else:  # both
            both_suitable.append(restaurant)
    
    # Sort by rating AND distance (prefer closer restaurants)
    def sort_key(r):
        rating = r.get('rating') or 0
        distance = r.get('distance_from_pois', 999)
        # Score: higher rating is better, lower distance is better
        return (rating * 10 - distance)
    
    lunch_suitable.sort(key=sort_key, reverse=True)
    dinner_suitable.sort(key=sort_key, reverse=True)
    both_suitable.sort(key=sort_key, reverse=True)
    filtered_sorted = sorted(filtered, key=sort_key, reverse=True)
    
    # Select lunch restaurant
    lunch_restaurant = None
    if lunch_suitable:
        lunch_restaurant = lunch_suitable[0]
    elif both_suitable:
        lunch_restaurant = both_suitable[0]
    elif filtered_sorted:
        lunch_restaurant = filtered_sorted[0]
    
    # Select dinner restaurant (different from lunch)
    dinner_restaurant = None
    if dinner_suitable:
        dinner_restaurant = dinner_suitable[0]
    elif len(both_suitable) > 1:
        # Use second option from both_suitable
        dinner_restaurant = both_suitable[1]
    elif both_suitable and both_suitable[0] != lunch_restaurant:
        dinner_restaurant = both_suitable[0]
    elif len(filtered_sorted) > 1:
        # Pick a different restaurant from filtered list
        for r in filtered_sorted:
            if r != lunch_restaurant:
                dinner_restaurant = r
                break
    
    # If still no dinner restaurant, use any available (even if same as lunch)
    if not dinner_restaurant and filtered_sorted:
        dinner_restaurant = filtered_sorted[1] if len(filtered_sorted) > 1 else filtered_sorted[0]
    
    return {
        'lunch': lunch_restaurant,
        'dinner': dinner_restaurant
    }


def get_fallback_restaurant(city, meal_type='lunch'):
    """
    Create a fallback restaurant placeholder when no data available
    """
    meal_suggestions = {
        'lunch': {
            'name': f'Local Tapas Bar in {city}',
            'cuisine': 'Spanish Tapas',
            'description': 'Explore local tapas bars near your morning attractions. Ask locals for recommendations!',
            'price_range': '$$',
            'meal_time': 'Lunch (2-4pm)'
        },
        'dinner': {
            'name': f'Traditional Restaurant in {city}',
            'cuisine': 'Andalusian',
            'description': 'Discover authentic Andalusian cuisine in the old town. Dinner typically starts around 9pm.',
            'price_range': '$$',
            'meal_time': 'Dinner (9-11pm)'
        }
    }
    
    return meal_suggestions.get(meal_type, meal_suggestions['lunch'])


def add_restaurants_to_itinerary(itinerary, all_restaurants, budget='mid-range', preferences=None):
    """
    Add restaurant recommendations NEAR POIs to each day in the itinerary
    """
    for day in itinerary:
        city = day.get('city', '')
        
        # Get POIs for the day
        all_pois = []
        for city_stop in day.get('cities', []):
            all_pois.extend(city_stop.get('attractions', []))
        
        # Get restaurant recommendations NEAR the POIs
        restaurants = select_restaurants_for_day(city, all_restaurants, all_pois, budget, preferences)
        
        # Add to day
        lunch = restaurants['lunch'] if restaurants['lunch'] else get_fallback_restaurant(city, 'lunch')
        dinner = restaurants['dinner'] if restaurants['dinner'] else get_fallback_restaurant(city, 'dinner')
        
        day['lunch_restaurant'] = lunch
        day['dinner_restaurant'] = dinner
    
    return itinerary


def format_restaurant_info(restaurant, meal_type='lunch'):
    """Format restaurant information for display"""
    if not restaurant:
        return "No restaurant data available"
    
    name = restaurant.get('name', 'Unknown')
    cuisine = restaurant.get('cuisine', 'Local')
    rating = restaurant.get('rating')
    price = restaurant.get('price_range', '$$')
    distance = restaurant.get('distance_from_pois')
    
    info_parts = [f"**{name}**"]
    
    details = []
    if rating:
        details.append(f"⭐ {rating}/10")
    details.append(f"💶 {price}")
    details.append(f"🍽️ {cuisine}")
    if distance is not None:
        details.append(f"📍 {distance}km from attractions")
    
    if details:
        info_parts.append(" · ".join(details))
    
    if restaurant.get('description'):
        info_parts.append(restaurant['description'])
    
    return "\n".join(info_parts)


def get_restaurant_tips(meal_type='lunch'):
    """Get general restaurant tips for Andalusia"""
    tips = {
        'lunch': [
            "Spanish lunch is typically 2-4pm, the main meal of the day",
            "Many restaurants offer 'menú del día' (daily menu) for great value",
            "Tapas bars are perfect for a lighter lunch",
            "Reservations usually not needed for lunch"
        ],
        'dinner': [
            "Dinner starts late in Spain - restaurants fill up after 9pm",
            "Book popular restaurants in advance, especially on weekends",
            "Tapas hopping is a fun way to experience multiple places",
            "Don't rush - Spanish dinners are leisurely affairs"
        ]
    }
    
    return tips.get(meal_type, [])