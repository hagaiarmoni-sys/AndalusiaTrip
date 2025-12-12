"""
Compound Attractions Handler
Ensures attractions that are part of the same complex are grouped on the same day.
"""

import json
from pathlib import Path
import os

# Load compound attractions configuration
# Try multiple possible locations
POSSIBLE_PATHS = [
    Path(__file__).parent / "data" / "compound_attractions.json",  # Same dir as handler, in data/
    Path(__file__).parent / "compound_attractions.json",           # Same dir as handler
    Path("/data/compound_attractions.json"),                       # Absolute /data path
    Path("data/compound_attractions.json"),                        # Relative data/ path
]

COMPOUND_CONFIG = {}
COMPOUND_CONFIG_PATH = None

for path in POSSIBLE_PATHS:
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                COMPOUND_CONFIG = json.load(f)
            COMPOUND_CONFIG_PATH = path
            print(f"✅ Loaded compound attractions from: {path}")
            break
        except Exception as e:
            print(f"⚠️ Error loading {path}: {e}")
            continue

if not COMPOUND_CONFIG:
    print(f"⚠️ Warning: compound_attractions.json not found in any of these locations:")
    for path in POSSIBLE_PATHS:
        print(f"   - {path}")
    print(f"   Compound attraction grouping disabled.")


def get_compound_groups(city):
    """
    Get all compound attraction groups for a city.
    
    Args:
        city (str): City name (e.g., "Granada", "Seville")
    
    Returns:
        list: List of compound groups, each containing attraction names that must be grouped
    
    Example:
        >>> get_compound_groups("Granada")
        [
            {
                'name': 'Alhambra Complex',
                'core': 'The Alhambra',
                'attractions': ['The Alhambra', 'Generalife', 'Palace of Charles V', ...],
                'must_group': True
            }
        ]
    """
    if city not in COMPOUND_CONFIG:
        return []
    
    groups = []
    for group_name, config in COMPOUND_CONFIG[city].items():
        if 'included_attractions' in config:
            groups.append({
                'name': group_name,
                'core': config.get('core_attraction'),
                'attractions': config['included_attractions'],
                'excluded': config.get('excluded_attractions', []),
                'must_group': config.get('must_visit_together', False),
                'visit_duration': config.get('visit_duration_hours', 2),
                'neighborhood': config.get('neighborhood', '')
            })
    
    return groups


def find_compound_group(poi_name, city):
    """
    Find which compound group a POI belongs to.
    
    Args:
        poi_name (str): Name of the POI
        city (str): City name
    
    Returns:
        dict or None: Compound group info if POI belongs to a group, None otherwise
    """
    groups = get_compound_groups(city)
    
    for group in groups:
        # Check if POI is in the included list
        if poi_name in group['attractions']:
            return group
        
        # Check if POI name contains any of the attraction names (partial match)
        for attraction in group['attractions']:
            if attraction.lower() in poi_name.lower() or poi_name.lower() in attraction.lower():
                return group
    
    return None


def group_pois_by_compound(pois, city):
    """
    Group POIs by their compound attractions.
    
    Args:
        pois (list): List of POI dictionaries with 'name' keys
        city (str): City name
    
    Returns:
        dict: {
            'grouped': {group_name: [poi1, poi2, ...]},
            'standalone': [poi1, poi2, ...]
        }
    """
    grouped = {}
    standalone = []
    
    for poi in pois:
        poi_name = poi.get('name', '')
        group = find_compound_group(poi_name, city)
        
        if group and group['must_group']:
            group_name = group['name']
            if group_name not in grouped:
                grouped[group_name] = []
            grouped[group_name].append(poi)
        else:
            standalone.append(poi)
    
    return {
        'grouped': grouped,
        'standalone': standalone
    }


def ensure_compound_integrity(selected_pois, available_pois, city):
    """
    Ensure compound attractions are complete. If any part of a compound is selected,
    add all other parts from the same compound.
    
    Args:
        selected_pois (list): Currently selected POIs for a day
        available_pois (list): All available POIs that can be added
        city (str): City name
    
    Returns:
        list: Updated selected_pois with complete compound groups
    """
    groups = get_compound_groups(city)
    
    for group in groups:
        if not group['must_group']:
            continue
        
        # Check if any POI from this compound is selected
        group_pois_in_selection = []
        for poi in selected_pois:
            if poi.get('name') in group['attractions']:
                group_pois_in_selection.append(poi)
        
        # If we have at least one, add all missing ones from the compound
        if group_pois_in_selection:
            # Find all POIs from this compound in available_pois
            for attraction_name in group['attractions']:
                # Skip if already selected
                if any(p.get('name') == attraction_name for p in selected_pois):
                    continue
                
                # Find in available_pois and add
                for poi in available_pois:
                    if poi.get('name') == attraction_name:
                        selected_pois.append(poi)
                        print(f"  ✅ Added '{attraction_name}' to complete {group['name']}")
                        break
    
    return selected_pois


def split_pois_into_days(all_pois, city, num_days, quota_per_day):
    """
    Intelligently split POIs into multiple days, respecting compound attractions.
    
    Args:
        all_pois (list): All POIs for this city
        city (str): City name
        num_days (int): Number of days in this city
        quota_per_day (int): Target number of POIs per day
    
    Returns:
        list: [day1_pois, day2_pois, ...] where each is a list of POIs
    """
    grouped_data = group_pois_by_compound(all_pois, city)
    groups = grouped_data['grouped']
    standalone = grouped_data['standalone']
    
    # Initialize days
    days = [[] for _ in range(num_days)]
    day_counts = [0] * num_days
    
    # Step 1: Assign compound groups (entire group goes to one day)
    for group_name, group_pois in groups.items():
        # Find day with most capacity
        best_day_idx = min(range(num_days), key=lambda i: day_counts[i])
        
        # Add entire group to this day
        days[best_day_idx].extend(group_pois)
        day_counts[best_day_idx] += len(group_pois)
        
        print(f"  📦 Assigned {group_name} ({len(group_pois)} POIs) to Day {best_day_idx + 1}")
    
    # Step 2: Distribute standalone POIs
    for poi in standalone:
        # Find day with most capacity (but prefer keeping it under quota)
        best_day_idx = min(range(num_days), key=lambda i: day_counts[i])
        
        days[best_day_idx].append(poi)
        day_counts[best_day_idx] += 1
    
    # Step 3: Balance if needed (move standalone POIs between days)
    # This is a simple balancing - can be improved
    
    return days


def get_neighborhood_tags(city):
    """
    Get neighborhood groupings for a city.
    
    Args:
        city (str): City name
    
    Returns:
        dict: {neighborhood_name: [attraction_names]}
    """
    neighborhoods = COMPOUND_CONFIG.get('neighborhoods', {})
    return neighborhoods.get(city, {})


def suggest_poi_order_by_neighborhood(pois, city):
    """
    Suggest an order for POIs based on neighborhood grouping.
    POIs in the same neighborhood should be adjacent in the order.
    
    Args:
        pois (list): List of POI dictionaries
        city (str): City name
    
    Returns:
        list: Reordered POIs grouped by neighborhood
    """
    neighborhoods = get_neighborhood_tags(city)
    
    # Group POIs by neighborhood
    neighborhood_groups = {n: [] for n in neighborhoods.keys()}
    unmatched = []
    
    for poi in pois:
        poi_name = poi.get('name', '')
        matched = False
        
        for neighborhood, attractions in neighborhoods.items():
            if poi_name in attractions:
                neighborhood_groups[neighborhood].append(poi)
                matched = True
                break
        
        if not matched:
            unmatched.append(poi)
    
    # Combine: neighborhoods first, then unmatched
    ordered_pois = []
    for neighborhood, pois_in_neighborhood in neighborhood_groups.items():
        ordered_pois.extend(pois_in_neighborhood)
    
    ordered_pois.extend(unmatched)
    
    return ordered_pois
