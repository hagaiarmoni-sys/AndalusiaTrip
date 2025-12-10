"""
Day Allocation Module for Andalusia Travel App

Uses recommended days per city based on trip length.
Allows user overrides via special requests.
"""

# ============================================================================
# RECOMMENDED DAYS PER CITY TABLE
# Based on travel expert recommendations
# ============================================================================

# Format: city -> {trip_length: days}
# Use tuples for ranges like (2, 3) meaning "2-3 days"
RECOMMENDED_DAYS = {
    'seville': {
        5: 2,
        7: (2, 3),
        10: 3,
        14: (3, 4),
    },
    'granada': {
        5: 2,
        7: 2,
        10: (2, 3),
        14: 3,
    },
    'cordoba': {
        5: 1,
        7: 1,
        10: (1, 2),
        14: 2,
    },
    'malaga': {
        5: 0,  # Skip for 5-day trips
        7: 1,
        10: 2,
        14: 3,
    },
    'ronda': {
        5: 0,
        7: 1,
        10: (1, 2),
        14: 2,
    },
    'white_villages': {  # Includes Arcos, Zahara, Grazalema, Setenil, etc.
        5: 0,
        7: 0,
        10: (1, 2),
        14: (2, 3),
    },
    'cadiz': {
        5: 0,
        7: 0,
        10: 0,
        14: (1, 2),
    },
    'jerez': {
        5: 0,
        7: 0,
        10: 0,
        14: (1, 2),
    },
}

# Notes for each trip length
TRIP_NOTES = {
    5: "Focus on Seville + Granada, Córdoba as day trip",
    7: "Add Málaga for culture + coast",
    10: "Include Ronda + Setenil or Grazalema",
    14: "Full circuit: cities + countryside + Cádiz/Jerez",
}


def get_optimal_city_count(total_days, start_city=None, end_city=None):
    """
    Calculate how many unique cities should be in the route based on trip length.
    
    This replaces the old 'days - 2' logic with allocation-table-aware city selection.
    
    Args:
        total_days: Total trip duration
        start_city: Starting city (normalized)
        end_city: Ending city (normalized)
    
    Returns:
        int: Recommended number of unique cities (including start and end)
    """
    # Get trip bracket
    bracket = get_trip_bracket(total_days)
    
    # Count how many cities get allocated days in this bracket
    cities_with_days = 0
    for city, allocations in RECOMMENDED_DAYS.items():
        if city == 'white_villages':
            continue  # Count actual white village cities separately
        days = allocations.get(bracket, 0)
        if isinstance(days, tuple):
            days = days[0]  # Use minimum
        if days > 0:
            cities_with_days += 1
    
    # Add 1 for white villages if they get days (count as 1 city)
    wv_days = RECOMMENDED_DAYS.get('white_villages', {}).get(bracket, 0)
    if isinstance(wv_days, tuple):
        wv_days = wv_days[0]
    if wv_days > 0:
        cities_with_days += 1
    
    # Ensure at least start and end cities
    min_cities = 2 if start_city != end_city else 1
    
    return max(cities_with_days, min_cities)


# Recommended city counts by trip length (pre-calculated for efficiency)
OPTIMAL_CITY_COUNTS = {
    5: 3,   # Seville, Granada, Córdoba
    7: 4,   # + Málaga or Ronda
    10: 5,  # + Ronda + maybe white village
    14: 7,  # Full circuit with Cádiz/Jerez
}


def get_max_intermediate_cities(total_days, is_circular=False):
    """
    Get the maximum number of intermediate cities (excluding start/end) for route building.
    
    Args:
        total_days: Total trip duration
        is_circular: Whether this is a circular trip (same start/end)
    
    Returns:
        int: Maximum intermediate cities to add
    """
    bracket = get_trip_bracket(total_days)
    optimal = OPTIMAL_CITY_COUNTS.get(bracket, 5)
    
    if is_circular:
        # Circular: start city is also end city, so intermediate = optimal - 1
        return optimal - 1
    else:
        # Point-to-point: intermediate = optimal - 2 (exclude start and end)
        return optimal - 2


# Cities that count as "White Villages"
WHITE_VILLAGE_CITIES = {
    'arcos de la frontera', 'arcos', 'zahara de la sierra', 'zahara',
    'grazalema', 'setenil de las bodegas', 'setenil', 'olvera',
    'frigiliana', 'mijas', 'casares', 'vejer de la frontera', 'vejer'
}

# Aliases for city name matching
CITY_ALIASES = {
    'sevilla': 'seville',
    'córdoba': 'cordoba',
    'málaga': 'malaga',
    'cádiz': 'cadiz',
    'jerez de la frontera': 'jerez',
}


def normalize_city_for_allocation(city_name: str) -> str:
    """Normalize city name for allocation lookup"""
    if not city_name:
        return ""
    
    city_lower = city_name.lower().strip()
    
    # Check aliases
    if city_lower in CITY_ALIASES:
        return CITY_ALIASES[city_lower]
    
    # Check if it's a white village
    if city_lower in WHITE_VILLAGE_CITIES:
        return 'white_villages'
    
    return city_lower


def get_trip_bracket(days: int) -> int:
    """
    Get the trip length bracket for lookup
    
    Args:
        days: Total trip days
        
    Returns:
        Bracket (5, 7, 10, or 14)
    """
    if days <= 5:
        return 5
    elif days <= 7:
        return 7
    elif days <= 10:
        return 10
    else:
        return 14


def get_recommended_days_for_city(city_name: str, total_trip_days: int, use_max: bool = False) -> int:
    """
    Get recommended number of days for a city based on trip length
    
    Args:
        city_name: City name
        total_trip_days: Total trip length
        use_max: If True, return max of range; if False, return min
        
    Returns:
        Recommended days (0 means skip this city)
    """
    city_norm = normalize_city_for_allocation(city_name)
    bracket = get_trip_bracket(total_trip_days)
    
    if city_norm not in RECOMMENDED_DAYS:
        # Unknown city - default to 1 day
        return 1
    
    city_data = RECOMMENDED_DAYS[city_norm]
    
    if bracket not in city_data:
        # Find closest bracket
        available = sorted(city_data.keys())
        bracket = min(available, key=lambda x: abs(x - bracket))
    
    days = city_data.get(bracket, 1)
    
    # Handle ranges
    if isinstance(days, tuple):
        return days[1] if use_max else days[0]
    
    return days


def allocate_days_for_route(ordered_cities: list, total_days: int, user_overrides: dict = None) -> dict:
    """
    Allocate days to each city in the route based on recommendations
    
    Args:
        ordered_cities: List of cities in route order
        total_days: Total trip length
        user_overrides: Dict of {city: days} for user-specified durations
        
    Returns:
        Dict of {city: days}
    """
    user_overrides = user_overrides or {}
    
    allocation = {}
    
    # First pass: Get recommended days for each city
    for city in ordered_cities:
        city_norm = normalize_city_for_allocation(city)
        
        # Check for user override
        if city_norm in user_overrides:
            allocation[city] = user_overrides[city_norm]
        elif city.lower() in user_overrides:
            allocation[city] = user_overrides[city.lower()]
        else:
            # Use table recommendation
            allocation[city] = get_recommended_days_for_city(city, total_days)
    
    # Calculate total allocated days
    total_allocated = sum(allocation.values())
    
    # Adjust if over/under budget
    if total_allocated != total_days:
        diff = total_days - total_allocated
        
        if diff > 0:
            # Need to add days - distribute to cities in route
            # Priority: major cities that haven't reached their max
            priority_order = ['granada', 'seville', 'cordoba', 'malaga', 'ronda', 'cadiz', 'jerez']
            
            # Get cities we can add to (not user-overridden, below max)
            available_cities = []
            for city in ordered_cities:
                city_norm = normalize_city_for_allocation(city)
                city_lower = city.lower()
                if city_lower not in (user_overrides or {}) and city_norm not in (user_overrides or {}):
                    if allocation[city] < 4:  # Max 4 days per city
                        available_cities.append(city)
            
            # Sort by priority
            def get_priority(c):
                cn = normalize_city_for_allocation(c)
                return priority_order.index(cn) if cn in priority_order else 999
            
            available_cities.sort(key=get_priority)
            
            # Distribute days round-robin to avoid inflating one city too much
            city_idx = 0
            for _ in range(diff):
                if not available_cities:
                    break
                
                # Find next city that can accept a day
                attempts = 0
                while attempts < len(available_cities):
                    city = available_cities[city_idx % len(available_cities)]
                    if allocation[city] < 4:
                        allocation[city] += 1
                        city_idx += 1
                        break
                    city_idx += 1
                    attempts += 1
        
        elif diff < 0:
            # Need to remove days - remove from least important cities first
            priority_order = ['seville', 'granada', 'cordoba', 'malaga', 'ronda']
            
            for _ in range(abs(diff)):
                for city in reversed(ordered_cities):
                    city_norm = normalize_city_for_allocation(city)
                    
                    # Don't reduce below 1 day for cities in route
                    # Don't reduce user-overridden cities
                    if allocation[city] > 1 and city_norm not in (user_overrides or {}) and city.lower() not in (user_overrides or {}):
                        # Don't reduce priority cities unless necessary
                        if city_norm not in priority_order:
                            allocation[city] -= 1
                            break
                else:
                    # Must reduce a priority city
                    for city in reversed(ordered_cities):
                        if allocation[city] > 1 and city.lower() not in (user_overrides or {}):
                            allocation[city] -= 1
                            break
    
    return allocation


def get_cities_for_trip_length(total_days: int, start_city: str = None, end_city: str = None) -> list:
    """
    Get recommended cities to visit based on trip length
    
    Args:
        total_days: Total trip days
        start_city: Starting city (will be included)
        end_city: Ending city (will be included)
        
    Returns:
        List of recommended cities in suggested order
    """
    bracket = get_trip_bracket(total_days)
    
    # Get cities with non-zero days for this bracket
    recommended = []
    
    for city, brackets in RECOMMENDED_DAYS.items():
        if city == 'white_villages':
            continue  # Handle separately
            
        days = brackets.get(bracket, 0)
        if isinstance(days, tuple):
            days = days[0]  # Use minimum
        
        if days > 0:
            recommended.append((city.title(), days))
    
    # Sort by days (most important first)
    recommended.sort(key=lambda x: -x[1])
    
    cities = [c[0] for c in recommended]
    
    # Ensure start/end cities are included
    if start_city:
        start_norm = start_city.title()
        if start_norm not in cities:
            cities.insert(0, start_norm)
    
    if end_city and end_city != start_city:
        end_norm = end_city.title()
        if end_norm not in cities:
            cities.append(end_norm)
    
    return cities


def parse_user_duration_requests(special_requests: str) -> dict:
    """
    Parse user's special requests for specific city durations
    
    Examples:
        "Must see Seville for 3 days" -> {'seville': 3}
        "Stay in Granada 4 nights" -> {'granada': 4}
        "2 days in Ronda" -> {'ronda': 2}
        "Seville for only one day" -> {'seville': 1}
        
    Args:
        special_requests: Free-text special requests
        
    Returns:
        Dict of {city: days}
    """
    import re
    
    if not special_requests:
        return {}
    
    overrides = {}
    text = special_requests.lower()
    
    # Convert word numbers to digits (order matters - longer phrases first!)
    word_to_num = [
        ('only one', '1'),
        ('just one', '1'),
        ('a single', '1'),
        ('single', '1'),
        ('one', '1'),
        ('two', '2'),
        ('three', '3'),
        ('four', '4'),
        ('five', '5'),
        ('six', '6'),
        ('seven', '7'),
        ('eight', '8'),
        ('nine', '9'),
        ('ten', '10'),
        # Don't include 'a' alone - it breaks 'day' → 'd1y'
    ]
    
    for word, num in word_to_num:
        text = text.replace(word, num)
    
    # Known city names to search for
    cities = ['seville', 'sevilla', 'granada', 'cordoba', 'córdoba', 'malaga', 'málaga',
              'ronda', 'cadiz', 'cádiz', 'jerez', 'marbella', 'nerja', 'tarifa', 'antequera']
    
    # Pattern: "X days in CITY" or "CITY for X days" or "stay in CITY X days/nights"
    patterns = [
        r'(\d+)\s*days?\s*(?:in|at)\s*(\w+)',  # "3 days in Seville"
        r'(\w+)\s*(?:for|:)\s*(?:only\s*)?(\d+)\s*days?',  # "Seville for 3 days" or "Seville for only 1 day"
        r'stay\s*(?:in|at)?\s*(\w+)\s*(?:for)?\s*(\d+)\s*(?:days?|nights?)',  # "stay in Granada 4 nights"
        r'(\w+)\s*(\d+)\s*(?:days?|nights?)',  # "Granada 4 days"
        r'spend\s*(\d+)\s*days?\s*(?:in|at)\s*(\w+)',  # "spend 3 days in Seville"
        r'(\w+)\s*for\s*(?:only\s*)?(\d+)\s*day',  # "Seville for only 1 day"
        r'only\s*(\d+)\s*days?\s*(?:in|at|for)\s*(\w+)',  # "only 1 day in Seville"
        r'(\w+)\s*(?:just|only)\s*(\d+)\s*days?',  # "Seville just 1 day"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Determine which group is city and which is number
            if match[0].isdigit():
                days = int(match[0])
                city = match[1]
            else:
                city = match[0]
                if match[1].isdigit():
                    days = int(match[1])
                else:
                    continue  # Skip if no valid number
            
            # Check if it's a known city
            city_lower = city.lower()
            for known_city in cities:
                if known_city.startswith(city_lower) or city_lower.startswith(known_city[:4]):
                    # Normalize the city name
                    city_norm = normalize_city_for_allocation(known_city)
                    if city_norm:
                        overrides[city_norm] = days
                    break
    
    return overrides


def get_allocation_summary(allocation: dict, total_days: int) -> str:
    """
    Get a human-readable summary of the day allocation
    
    Args:
        allocation: Dict of {city: days}
        total_days: Total trip days
        
    Returns:
        Summary string
    """
    lines = [f"📅 Day Allocation ({total_days}-day trip):"]
    
    for city, days in allocation.items():
        lines.append(f"  • {city}: {days} day{'s' if days != 1 else ''}")
    
    total = sum(allocation.values())
    if total != total_days:
        lines.append(f"  ⚠️ Total: {total} days (expected {total_days})")
    
    return "\n".join(lines)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    # Test allocation
    print("=== Testing Day Allocation ===\n")
    
    # Test 7-day trip
    cities = ['Málaga', 'Granada', 'Córdoba', 'Seville']
    allocation = allocate_days_for_route(cities, 7)
    print(get_allocation_summary(allocation, 7))
    
    print()
    
    # Test 10-day trip
    cities = ['Málaga', 'Granada', 'Córdoba', 'Ronda', 'Seville']
    allocation = allocate_days_for_route(cities, 10)
    print(get_allocation_summary(allocation, 10))
    
    print()
    
    # Test with user override
    cities = ['Málaga', 'Granada', 'Seville']
    overrides = parse_user_duration_requests("Must see Seville for 4 days")
    print(f"User overrides: {overrides}")
    allocation = allocate_days_for_route(cities, 7, overrides)
    print(get_allocation_summary(allocation, 7))
