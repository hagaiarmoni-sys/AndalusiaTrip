"""
Trip Validation System - ENHANCED
Prevents impossible or conflicting trip configurations
+ Data existence validation for cities
"""

import streamlit as st
from datetime import timedelta
from text_norm import canonicalize_city, norm_key

# ═══════════════════════════════════════════════════════════
# CONSTRAINTS CONFIGURATION
# ═══════════════════════════════════════════════════════════

TRIP_CONSTRAINTS = {
    'min_days': 3,
    'max_days': 21,
    'max_circular_days': 14,
    'min_attractions_per_day': 2,
    'max_attractions_per_day': 6,
    'max_driving_per_day_km': 250,
}

# ═══════════════════════════════════════════════════════════
# ✅ NEW: DATA EXISTENCE VALIDATION
# ═══════════════════════════════════════════════════════════

def extract_known_cities(attractions_data):
    """
    Extract all unique cities from attractions data
    
    Returns: set of city names in database
    """
    if not attractions_data:
        return set()
    
    cities = set()
    for attr in attractions_data:
        city = attr.get('city', '').strip()
        if city:
            cities.add(city)
    
    return cities


def validate_city_exists(city_name, known_cities, context=""):
    """
    Check if a city exists in the database
    
    Args:
        city_name: User-provided city name
        known_cities: Set of cities in database
        context: Where this city is used (e.g., "start city", "avoid list")
    
    Returns:
        (exists: bool, canonical_name: str or None, suggestion: str or None)
    """
    if not city_name or not city_name.strip():
        return False, None, None
    
    # Try to canonicalize (handles accents, aliases, typos)
    canonical = canonicalize_city(city_name, known_cities)
    
    if canonical:
        return True, canonical, None
    
    # Not found - provide helpful suggestions
    city_key = norm_key(city_name)
    
    # Find similar cities (fuzzy match)
    suggestions = []
    for known in known_cities:
        known_key = norm_key(known)
        
        # Check if user input is substring of known city
        if city_key in known_key or known_key in city_key:
            suggestions.append(known)
        
        # Check for single character difference (typo)
        if len(city_key) == len(known_key):
            diff_count = sum(c1 != c2 for c1, c2 in zip(city_key, known_key))
            if diff_count <= 2:  # Allow 1-2 character difference
                suggestions.append(known)
    
    if suggestions:
        suggestion_text = f"Did you mean: {', '.join(suggestions[:3])}?"
    else:
        # Show some popular cities
        popular = ['Málaga', 'Seville', 'Granada', 'Córdoba', 'Ronda', 'Cádiz']
        available_popular = [c for c in popular if c in known_cities]
        if available_popular:
            suggestion_text = f"Available cities include: {', '.join(available_popular[:5])}"
        else:
            suggestion_text = "Please check the city name"
    
    return False, None, suggestion_text


def validate_cities_existence(params, attractions_data):
    """
    Validate that all referenced cities exist in database
    
    Returns: (errors, warnings)
    """
    errors = []
    warnings = []
    
    if not attractions_data:
        warnings.append("⚠️ No attractions data available - cannot verify city names")
        return errors, warnings
    
    # Extract known cities
    known_cities = extract_known_cities(attractions_data)
    
    if not known_cities:
        warnings.append("⚠️ Could not extract city list from attractions data")
        return errors, warnings
    
    # Validate start city
    start_city = params.get('start_city', '')
    if start_city:
        exists, canonical, suggestion = validate_city_exists(start_city, known_cities, "start city")
        if not exists:
            errors.append(f"❌ Start city '{start_city}' not found in database. {suggestion}")
        elif canonical != start_city:
            warnings.append(f"ℹ️ Start city '{start_city}' recognized as '{canonical}'")
    
    # Validate end city (if not circular/hub trip)
    end_city = params.get('end_city', '')
    trip_type = params.get('trip_type', 'point_to_point')
    
    if end_city and trip_type not in ['circular', 'hub']:
        exists, canonical, suggestion = validate_city_exists(end_city, known_cities, "end city")
        if not exists:
            errors.append(f"❌ End city '{end_city}' not found in database. {suggestion}")
        elif canonical != end_city:
            warnings.append(f"ℹ️ End city '{end_city}' recognized as '{canonical}'")
    
    # Validate cities to include
    cities_to_include = params.get('cities_to_include', [])
    for city in cities_to_include:
        if not city or not city.strip():
            continue
        
        exists, canonical, suggestion = validate_city_exists(city, known_cities, "cities to visit")
        if not exists:
            warnings.append(f"⚠️ City '{city}' not in database. {suggestion}")
        elif canonical != city:
            warnings.append(f"ℹ️ '{city}' recognized as '{canonical}'")
    
    # Validate cities to avoid
    cities_to_avoid = params.get('cities_to_avoid', [])
    for city in cities_to_avoid:
        if not city or not city.strip():
            continue
        
        exists, canonical, suggestion = validate_city_exists(city, known_cities, "avoid list")
        if not exists:
            warnings.append(f"⚠️ City to avoid '{city}' not in our database (will be ignored). {suggestion}")
        elif canonical != city:
            warnings.append(f"ℹ️ '{city}' recognized as '{canonical}'")
    
    return errors, warnings


# ═══════════════════════════════════════════════════════════
# ORIGINAL VALIDATION FUNCTIONS (unchanged)
# ═══════════════════════════════════════════════════════════

def validate_trip_duration(days, trip_type='point_to_point'):
    """Validate trip duration is within acceptable range"""
    errors = []
    warnings = []
    
    min_days = TRIP_CONSTRAINTS['min_days']
    max_days = TRIP_CONSTRAINTS['max_days']
    
    if days < min_days:
        errors.append(f"❌ Trip too short! Minimum {min_days} days required.")
    
    if trip_type == 'circular' and days > TRIP_CONSTRAINTS['max_circular_days']:
        warnings.append(f"⚠️ Circular trips work best with ≤{TRIP_CONSTRAINTS['max_circular_days']} days. Consider point-to-point instead.")
    
    if days > max_days:
        errors.append(f"❌ Trip too long! Maximum {max_days} days allowed.")
    
    return errors, warnings


def validate_city_conflicts(start_city, end_city, cities_to_include, cities_to_avoid):
    """Check for conflicts between selected cities and avoid list"""
    errors = []
    warnings = []
    
    def normalize(city):
        if not city:
            return ""
        return city.lower().strip()
    
    start_norm = normalize(start_city)
    end_norm = normalize(end_city)
    avoid_norm = [normalize(c) for c in cities_to_avoid]
    include_norm = [normalize(c) for c in cities_to_include]
    
    if start_norm in avoid_norm:
        errors.append(f"❌ Conflict: Start city '{start_city}' is in your AVOID list!")
    
    if end_city and end_norm in avoid_norm:
        errors.append(f"❌ Conflict: End city '{end_city}' is in your AVOID list!")
    
    for city in cities_to_include:
        if normalize(city) in avoid_norm:
            errors.append(f"❌ Conflict: You want to visit '{city}' but it's in your AVOID list!")
    
    if start_city and end_city and start_norm == end_norm:
        warnings.append(f"⚠️ Start and end cities are the same. Consider using 'Circular' or 'Hub' trip type instead.")
    
    return errors, warnings


def validate_special_requests(special_requests, start_city, end_city, cities_to_include):
    """Parse special requests and check for conflicts"""
    errors = []
    warnings = []
    
    if not special_requests:
        return errors, warnings
    
    text_lower = special_requests.lower()
    avoid_keywords = ['avoid', 'skip', 'no', "don't visit", 'exclude', 'not interested']
    cities_mentioned = [start_city] + ([end_city] if end_city else []) + cities_to_include
    
    for city in cities_mentioned:
        if not city:
            continue
        city_lower = city.lower()
        
        for keyword in avoid_keywords:
            if keyword in text_lower and city_lower in text_lower:
                city_pos = text_lower.find(city_lower)
                keyword_pos = text_lower.find(keyword)
                
                if abs(city_pos - keyword_pos) < 30:
                    if city == start_city:
                        errors.append(f"❌ Conflict: You want to AVOID '{city}' but it's your START city!")
                    elif city == end_city:
                        errors.append(f"❌ Conflict: You want to AVOID '{city}' but it's your END city!")
                    elif city in cities_to_include:
                        errors.append(f"❌ Conflict: You want to AVOID '{city}' but you also want to VISIT it!")
    
    return errors, warnings


def validate_date_range(start_date, end_date):
    """Validate date range is reasonable"""
    errors = []
    warnings = []
    
    if end_date <= start_date:
        errors.append(f"❌ End date must be AFTER start date!")
        return errors, warnings
    
    days = (end_date - start_date).days + 1
    
    err, warn = validate_trip_duration(days)
    errors.extend(err)
    warnings.extend(warn)
    
    from datetime import datetime
    months_ahead = (start_date.year - datetime.now().year) * 12 + (start_date.month - datetime.now().month)
    
    if months_ahead > 24:
        warnings.append(f"⚠️ Trip is {months_ahead} months away. Plans may need adjustment closer to the date.")
    
    return errors, warnings


def validate_pace_and_days(pace, days):
    """Check if pace is appropriate for trip length"""
    warnings = []
    
    if pace == 'relaxed' and days < 5:
        warnings.append(f"⚠️ 'Relaxed' pace works best with 5+ days. Consider 'Medium' pace for {days}-day trip.")
    
    if pace == 'fast' and days > 10:
        warnings.append(f"⚠️ 'Fast' pace can be exhausting for {days}-day trip. Consider 'Medium' or 'Relaxed' pace.")
    
    return warnings


# ═══════════════════════════════════════════════════════════
# ✅ ENHANCED: Master validation with data existence checks
# ═══════════════════════════════════════════════════════════

def validate_all_parameters(params, attractions_data=None):
    """
    Master validation function - checks everything including data existence
    
    params = {
        'start_date': date,
        'end_date': date,
        'start_city': str,
        'end_city': str,
        'trip_type': str,
        'cities_to_include': list,
        'cities_to_avoid': list,
        'special_requests': str,
        'pace': str
    }
    
    attractions_data: Optional list of attractions to validate cities against
    
    Returns: (all_errors, all_warnings, is_valid)
    """
    all_errors = []
    all_warnings = []
    
    # Extract parameters
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    start_city = params.get('start_city', '')
    end_city = params.get('end_city', '')
    trip_type = params.get('trip_type', 'point_to_point')
    cities_to_include = params.get('cities_to_include', [])
    cities_to_avoid = params.get('cities_to_avoid', [])
    special_requests = params.get('special_requests', '')
    pace = params.get('pace', 'medium')
    
    # Calculate days
    if start_date and end_date:
        days = (end_date - start_date).days + 1
    else:
        days = 7
    
    # ✅ NEW: Validate city existence FIRST (before other checks)
    if attractions_data:
        errors, warnings = validate_cities_existence(params, attractions_data)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
    
    # Run original validations
    errors, warnings = validate_date_range(start_date, end_date)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    errors, warnings = validate_city_conflicts(start_city, end_city, cities_to_include, cities_to_avoid)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    errors, warnings = validate_special_requests(special_requests, start_city, end_city, cities_to_include)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    warnings = validate_pace_and_days(pace, days)
    all_warnings.extend(warnings)
    
    is_valid = len(all_errors) == 0
    
    return all_errors, all_warnings, is_valid


def display_validation_results(errors, warnings):
    """Display validation errors and warnings in Streamlit UI"""
    if errors:
        st.error("### 🚫 Cannot Generate Trip - Please Fix These Issues:")
        for error in errors:
            st.error(error)
        return False
    
    if warnings:
        st.warning("### ⚠️ Suggestions:")
        for warning in warnings:
            st.warning(warning)
    
    return True
