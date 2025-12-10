"""
Community Itineraries Service
Provides curated itinerary recommendations and trip planning guidance
based on the andalusia_community_itineraries_enriched.json data
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# ============================================================================
# DATA LOADING
# ============================================================================

_ITINERARIES_CACHE = None
_RECOMMENDED_DAYS_CACHE = None

def load_community_itineraries(filepath: str = "andalusia_community_itineraries_enriched.json") -> Dict:
    """
    Load community itineraries with caching
    
    Returns:
        Dict with keys: version, itineraries, recommended_days_per_city, sources
    """
    global _ITINERARIES_CACHE
    
    if _ITINERARIES_CACHE is not None:
        return _ITINERARIES_CACHE
    
    # Try multiple locations - data/ subfolder first (most common)
    possible_paths = [
        f"data/{filepath}",  # Most likely location
        filepath,
        os.path.join(os.path.dirname(__file__), "data", filepath),
        os.path.join(os.path.dirname(__file__), filepath),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    _ITINERARIES_CACHE = json.load(f)
                # print(f"✅ Loaded community itineraries from {path}")
                # print(f"   Version: {_ITINERARIES_CACHE.get('version', '?')}")
                # print(f"   Itineraries: {len(_ITINERARIES_CACHE.get('itineraries', []))}")
                return _ITINERARIES_CACHE
            except Exception as e:
                print(f"❌ Error loading {path}: {e}")
    
    print(f"⚠️ Community itineraries file not found")
    return {"version": "0", "itineraries": [], "recommended_days_per_city": {}}


def get_recommended_days_per_city() -> Dict:
    """
    Get recommended days per city table
    
    Returns:
        Dict like:
        {
            "Seville": {"5_day": 2, "7_day": "2-3", "10_day": 3, "14_day": "3-4", "notes": "..."},
            "Granada": {...},
            ...
        }
    """
    data = load_community_itineraries()
    return data.get("recommended_days_per_city", {})


# ============================================================================
# ITINERARY FILTERING & MATCHING
# ============================================================================

def get_all_itineraries() -> List[Dict]:
    """Get all available itineraries"""
    data = load_community_itineraries()
    return data.get("itineraries", [])


def filter_itineraries(
    duration_days: Optional[int] = None,
    duration_range: Optional[Tuple[int, int]] = None,
    trip_type: Optional[str] = None,
    cities: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    budget_level: Optional[str] = None,
    first_time: Optional[bool] = None,
    family_friendly: Optional[bool] = None,
    max_results: int = 10
) -> List[Dict]:
    """
    Filter itineraries by various criteria
    
    Args:
        duration_days: Exact number of days
        duration_range: Tuple of (min_days, max_days)
        trip_type: "Point-to-point", "Circular", "Star/Hub", etc.
        cities: List of cities that must be included
        tags: List of tags to match (e.g., ["culture", "beach", "food"])
        budget_level: "budget", "mid-range", "luxury"
        first_time: True if user is first-time visitor
        family_friendly: True if traveling with family
        max_results: Maximum number of results to return
        
    Returns:
        List of matching itineraries, sorted by relevance
    """
    itineraries = get_all_itineraries()
    results = []
    
    for itin in itineraries:
        score = 100  # Start with perfect score, deduct for mismatches
        
        # Duration matching
        itin_days = itin.get("duration_days", 0)
        
        if duration_days:
            diff = abs(itin_days - duration_days)
            if diff == 0:
                score += 20  # Exact match bonus
            elif diff <= 1:
                score += 10  # Close match
            elif diff <= 2:
                pass  # OK
            else:
                score -= diff * 5  # Penalize large differences
        
        if duration_range:
            min_d, max_d = duration_range
            if min_d <= itin_days <= max_d:
                score += 10
            else:
                continue  # Skip if outside range
        
        # Trip type matching
        if trip_type:
            itin_type = itin.get("type", "").lower()
            trip_type_lower = trip_type.lower()
            
            # Map common variations
            type_mapping = {
                "point-to-point": ["linear", "point-to-point", "one-way"],
                "circular": ["circular", "loop", "round"],
                "star/hub": ["star", "hub", "hub & spoke", "base"]
            }
            
            matched = False
            for key, variations in type_mapping.items():
                if trip_type_lower in key or key in trip_type_lower:
                    if any(v in itin_type for v in variations):
                        matched = True
                        score += 15
                        break
            
            if not matched and trip_type_lower in itin_type:
                score += 10
        
        # Cities matching
        if cities:
            itin_cities = [c.lower() for c in itin.get("cities_visited", [])]
            matched_cities = sum(1 for c in cities if c.lower() in itin_cities)
            if matched_cities > 0:
                score += matched_cities * 10
            else:
                score -= 20  # Penalize if no cities match
        
        # Tags matching
        if tags:
            itin_tags = [t.lower() for t in itin.get("tags", [])]
            matched_tags = sum(1 for t in tags if t.lower() in itin_tags)
            score += matched_tags * 5
        
        # Budget matching
        if budget_level:
            itin_budget = itin.get("budget_level", "").lower()
            if budget_level.lower() in itin_budget or itin_budget in budget_level.lower():
                score += 10
        
        # Profile fit matching
        profile = itin.get("profile_fit", {})
        
        if first_time is not None and profile.get("first_time") == first_time:
            score += 15
        
        if family_friendly is not None and profile.get("family_friendly") == family_friendly:
            score += 15
        
        # Add to results with score
        results.append((score, itin))
    
    # Sort by score (descending) and return top results
    results.sort(key=lambda x: x[0], reverse=True)
    return [itin for score, itin in results[:max_results]]


def get_itinerary_by_id(itinerary_id: str) -> Optional[Dict]:
    """Get a specific itinerary by ID"""
    itineraries = get_all_itineraries()
    for itin in itineraries:
        if itin.get("id") == itinerary_id:
            return itin
    return None


def get_similar_itineraries(itinerary_id: str, max_results: int = 3) -> List[Dict]:
    """Get itineraries similar to the given one"""
    source_itin = get_itinerary_by_id(itinerary_id)
    if not source_itin:
        return []
    
    return filter_itineraries(
        duration_range=(source_itin.get("duration_days", 7) - 2, 
                       source_itin.get("duration_days", 7) + 2),
        tags=source_itin.get("tags", [])[:3],
        max_results=max_results + 1  # +1 to exclude self
    )


# ============================================================================
# TRIP PLANNING HELPERS
# ============================================================================

def get_recommended_duration(cities: List[str]) -> Dict:
    """
    Get recommended trip duration based on cities to visit
    
    Args:
        cities: List of city names
        
    Returns:
        Dict with recommended durations and breakdown
    """
    days_table = get_recommended_days_per_city()
    
    if not cities or not days_table:
        return {
            "minimum": 5,
            "recommended": 7,
            "comfortable": 10,
            "breakdown": {},
            "notes": []
        }
    
    # Normalize city names
    def normalize(name):
        import unicodedata
        nfd = unicodedata.normalize('NFD', str(name))
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower().strip()
    
    breakdown = {}
    notes = []
    
    for city in cities:
        city_norm = normalize(city)
        
        for table_city, days_info in days_table.items():
            if normalize(table_city) == city_norm:
                # Use 7-day recommendation as base
                rec_days = days_info.get("7_day", 1)
                
                # Handle range like "2-3"
                if isinstance(rec_days, str) and "-" in rec_days:
                    parts = rec_days.split("-")
                    rec_days = float(parts[0])  # Use lower bound
                
                breakdown[city] = {
                    "days": float(rec_days),
                    "notes": days_info.get("notes", "")
                }
                
                if days_info.get("notes"):
                    notes.append(f"{city}: {days_info['notes']}")
                break
    
    # Calculate totals
    total_days = sum(info["days"] for info in breakdown.values())
    
    # Add travel days (roughly 0.5 day per city transition)
    travel_days = max(0, len(cities) - 1) * 0.5
    
    return {
        "minimum": max(3, int(total_days * 0.7)),
        "recommended": int(total_days + travel_days),
        "comfortable": int(total_days * 1.3 + travel_days),
        "breakdown": breakdown,
        "notes": notes,
        "travel_days": travel_days
    }


def validate_trip_duration(days: int, cities: List[str]) -> Tuple[bool, str]:
    """
    Validate if trip duration is reasonable for selected cities
    
    Returns:
        Tuple of (is_valid, message)
    """
    rec = get_recommended_duration(cities)
    
    if days < rec["minimum"]:
        return (False, 
                f"⚠️ {days} days is too short for {', '.join(cities)}. "
                f"Minimum recommended: {rec['minimum']} days.")
    
    if days < rec["recommended"]:
        return (True, 
                f"💡 {days} days is tight. Recommended: {rec['recommended']} days for a comfortable pace.")
    
    if days > rec["comfortable"] * 1.5:
        return (True, 
                f"💡 {days} days is generous! Consider adding more cities or slower pace.")
    
    return (True, f"✅ {days} days is good for your selected cities.")


# ============================================================================
# ITINERARY FORMATTING FOR UI
# ============================================================================

def format_itinerary_summary(itin: Dict) -> Dict:
    """
    Format itinerary for display in UI cards
    
    Returns:
        Dict with formatted fields for display
    """
    # Build cities string
    cities = itin.get("cities_visited", [])
    if len(cities) <= 4:
        cities_str = " → ".join(cities)
    else:
        cities_str = f"{cities[0]} → ... → {cities[-1]} ({len(cities)} cities)"
    
    # Get highlight tags
    tags = itin.get("tags", [])[:4]
    
    # Get cost estimate
    costs = itin.get("estimated_total_cost_per_person", {})
    cost_str = ""
    if costs:
        mid = costs.get("mid_range", costs.get("budget", 0))
        if mid:
            cost_str = f"~€{mid}/person"
    
    # Get source info
    source = itin.get("source", "Community")
    if len(source) > 30:
        source = source[:27] + "..."
    
    # Profile badges
    badges = []
    profile = itin.get("profile_fit", {})
    if profile.get("first_time"):
        badges.append("👋 First Timer")
    if profile.get("family_friendly"):
        badges.append("👨‍👩‍👧 Family")
    if profile.get("culture_focused"):
        badges.append("🏛️ Culture")
    if profile.get("adventure_focused"):
        badges.append("🥾 Adventure")
    if profile.get("relaxation_focused"):
        badges.append("🏖️ Relaxation")
    
    return {
        "id": itin.get("id", ""),
        "name": itin.get("name", "Unnamed Itinerary"),
        "duration": itin.get("duration_days", 0),
        "type": itin.get("type", "Mixed"),
        "cities_str": cities_str,
        "cities_list": cities,
        "tags": tags,
        "cost_str": cost_str,
        "source": source,
        "badges": badges[:3],  # Limit badges
        "highlights": itin.get("highlights", [])[:3],
        "daily_plan": itin.get("daily_plan", [])
    }


def get_itinerary_quick_view(itin: Dict) -> str:
    """
    Get a quick text overview of an itinerary
    
    Returns:
        Markdown-formatted string
    """
    summary = format_itinerary_summary(itin)
    
    lines = [
        f"### {summary['name']}",
        f"**{summary['duration']} days** | {summary['type']} | {summary['cities_str']}",
        ""
    ]
    
    if summary['tags']:
        lines.append("🏷️ " + " · ".join(summary['tags']))
    
    if summary['badges']:
        lines.append(" ".join(summary['badges']))
    
    if summary['cost_str']:
        lines.append(f"💰 {summary['cost_str']}")
    
    if summary['highlights']:
        lines.append("")
        lines.append("**Highlights:**")
        for h in summary['highlights']:
            lines.append(f"• {h}")
    
    return "\n".join(lines)


# ============================================================================
# DAILY PLAN EXTRACTION
# ============================================================================

def extract_daily_plan_for_generator(itin: Dict) -> List[Dict]:
    """
    Extract daily plan in a format suitable for the trip generator
    
    Returns:
        List of dicts with city, pois, activities for each day
    """
    daily_plan = itin.get("daily_plan", [])
    result = []
    
    for day in daily_plan:
        day_data = {
            "day": day.get("day_number", day.get("day", 0)),
            "city": day.get("city_or_region", day.get("city", "")),
            "overnight": day.get("overnight", day.get("city_or_region", "")),
            "poi_ids": day.get("poi_ids_for_day", day.get("poi_ids", [])),
            "activities": day.get("activities", []),
            "driving_km": day.get("driving_km", 0),
            "driving_minutes": day.get("driving_minutes", 0),
            "title": day.get("title", "")
        }
        result.append(day_data)
    
    return result


def get_cities_from_itinerary(itin: Dict) -> List[str]:
    """Extract ordered list of cities from itinerary"""
    cities_visited = itin.get("cities_visited", [])
    if cities_visited:
        return cities_visited
    
    # Fallback: extract from daily plan
    daily_plan = itin.get("daily_plan", [])
    cities = []
    for day in daily_plan:
        city = day.get("city_or_region", day.get("city", ""))
        if city and city not in cities:
            cities.append(city)
    
    return cities


# ============================================================================
# STATISTICS & METADATA
# ============================================================================

def get_itineraries_stats() -> Dict:
    """Get statistics about available itineraries"""
    itineraries = get_all_itineraries()
    
    if not itineraries:
        return {"total": 0}
    
    durations = [i.get("duration_days", 0) for i in itineraries]
    types = {}
    all_tags = {}
    all_cities = set()
    
    for itin in itineraries:
        # Count types
        t = itin.get("type", "Unknown")
        types[t] = types.get(t, 0) + 1
        
        # Count tags
        for tag in itin.get("tags", []):
            all_tags[tag] = all_tags.get(tag, 0) + 1
        
        # Collect cities
        all_cities.update(itin.get("cities_visited", []))
    
    return {
        "total": len(itineraries),
        "duration_range": (min(durations), max(durations)) if durations else (0, 0),
        "avg_duration": sum(durations) / len(durations) if durations else 0,
        "types": types,
        "top_tags": sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:10],
        "cities_covered": sorted(all_cities)
    }


# ============================================================================
# MAIN - For testing
# ============================================================================

if __name__ == "__main__":
    # Test loading
    data = load_community_itineraries()
    print(f"\n{'='*60}")
    print("COMMUNITY ITINERARIES SERVICE TEST")
    print(f"{'='*60}")
    
    stats = get_itineraries_stats()
    print(f"\nStats: {stats['total']} itineraries")
    print(f"Duration range: {stats['duration_range'][0]}-{stats['duration_range'][1]} days")
    print(f"Types: {stats['types']}")
    print(f"Top tags: {stats['top_tags'][:5]}")
    
    # Test filtering
    print(f"\n{'='*60}")
    print("FILTER TEST: 7-day trips with Granada")
    print(f"{'='*60}")
    
    results = filter_itineraries(
        duration_days=7,
        cities=["Granada"],
        max_results=3
    )
    
    for itin in results:
        print(f"\n{itin['name']} ({itin['duration_days']}d)")
        print(f"  Cities: {', '.join(itin.get('cities_visited', []))}")
    
    # Test recommended duration
    print(f"\n{'='*60}")
    print("RECOMMENDED DURATION: Seville, Granada, Córdoba")
    print(f"{'='*60}")
    
    rec = get_recommended_duration(["Seville", "Granada", "Córdoba"])
    print(f"Minimum: {rec['minimum']} days")
    print(f"Recommended: {rec['recommended']} days")
    print(f"Comfortable: {rec['comfortable']} days")
    print(f"Breakdown: {rec['breakdown']}")
