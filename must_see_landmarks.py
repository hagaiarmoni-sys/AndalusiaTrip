"""
Must-see landmarks database for major Andalusian cities.
Ensures world-famous attractions are prioritized in itineraries.
"""

MUST_SEE_LANDMARKS = {
    "Granada": [
        "Alhambra",
        "Generalife",
        "Albaicín",
        "Cathedral",
        "Royal Chapel",
        "Sacromonte",
        "Mirador de San Nicolás",
        "Science Park"
    ],
    "Seville": [
        "Cathedral",
        "Alcázar",
        "Plaza de España",
        "Torre del Oro",
        "Metropol Parasol",
        "Plaza de Toros",
        "Barrio Santa Cruz",
        "Maria Luisa Park"
    ],
    "Córdoba": [
        "Mezquita",
        "Mosque-Cathedral",
        "Jewish Quarter",
        "Alcázar de los Reyes Cristianos",
        "Roman Bridge",
        "Medina Azahara",
        "Synagogue",
        "Palacio de Viana"
    ],
    "Málaga": [
        "Alcazaba",
        "Gibralfaro Castle",
        "Picasso Museum",
        "Cathedral",
        "Roman Theatre",
        "Centre Pompidou",
        "Carmen Thyssen Museum",
        "Port"
    ],
    "Cádiz": [
        "Cathedral",
        "Torre Tavira",
        "Roman Theatre",
        "Santa Catalina Castle",
        "San Sebastian Castle",
        "La Caleta Beach",
        "Plaza de España",
        "Old Town"
    ],
    "Ronda": [
        "Puente Nuevo",
        "Plaza de Toros",
        "Old Town",
        "Arab Baths",
        "Mondragón Palace",
        "Tajo Gorge"
    ],
    "Jerez de la Frontera": [
        "Alcázar",
        "Cathedral",
        "Royal Andalusian School of Equestrian Art",
        "Bodegas",
        "Old Town"
    ],
    "Marbella": [
        "Old Town",
        "Orange Square",
        "Puerto Banús",
        "Beach Promenade"
    ],
    "Nerja": [
        "Nerja Caves",
        "Balcón de Europa",
        "Beaches"
    ],
    "Antequera": [
        "Dolmens",
        "Alcazaba",
        "El Torcal"
    ],
    "Tarifa": [
        "Old Town",
        "Castle",
        "Beaches",
        "Whale Watching"
    ],
    "Gibraltar": [
        "Rock of Gibraltar",
        "St. Michael's Cave",
        "Apes' Den",
        "Europa Point"
    ],
    "Úbeda": [
        "Vázquez de Molina Square",
        "Chapel of El Salvador",
        "Renaissance Buildings"
    ],
    "Baeza": [
        "Cathedral",
        "Plaza del Pópulo",
        "Renaissance Architecture"
    ],
    "Almería": [
        "Alcazaba",
        "Cathedral",
        "Cable Inglés",
        "Beaches"
    ]
}


def is_must_see(poi_name, city_name):
    """
    Check if a POI is a must-see landmark for the given city.
    
    Args:
        poi_name: Name of the POI
        city_name: Name of the city
        
    Returns:
        bool: True if the POI is a must-see landmark
    """
    if city_name not in MUST_SEE_LANDMARKS:
        return False
    
    landmarks = MUST_SEE_LANDMARKS[city_name]
    poi_lower = poi_name.lower()
    
    # Check for substring matches (e.g., "Alhambra Palace" matches "Alhambra")
    return any(landmark.lower() in poi_lower for landmark in landmarks)


def get_must_see_count(pois, city_name):
    """
    Count how many must-see landmarks are included in a list of POIs.
    
    Args:
        pois: List of POI dictionaries
        city_name: Name of the city
        
    Returns:
        int: Number of must-see landmarks found
    """
    if city_name not in MUST_SEE_LANDMARKS:
        return 0
    
    count = 0
    for poi in pois:
        if is_must_see(poi.get('name', ''), city_name):
            count += 1
    
    return count


def get_missing_must_sees(pois, city_name):
    """
    Get list of must-see landmarks that are missing from the POI list.
    
    Args:
        pois: List of POI dictionaries
        city_name: Name of the city
        
    Returns:
        list: Names of missing must-see landmarks
    """
    if city_name not in MUST_SEE_LANDMARKS:
        return []
    
    included_names = [poi.get('name', '').lower() for poi in pois]
    missing = []
    
    for landmark in MUST_SEE_LANDMARKS[city_name]:
        landmark_found = any(landmark.lower() in name for name in included_names)
        if not landmark_found:
            missing.append(landmark)
    
    return missing


def get_city_landmarks(city_name):
    """
    Get the list of must-see landmarks for a city.
    
    Args:
        city_name: Name of the city
        
    Returns:
        list: List of landmark names, or empty list if city not found
    """
    return MUST_SEE_LANDMARKS.get(city_name, [])
