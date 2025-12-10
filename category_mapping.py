"""
Category Mapping for Andalusia Travel App

Maps database POI categories (from JSON) to app UI categories (from multiselect).

This ensures that when users select "history" in preferences, they get POIs
that are categorized as "Historic Site", "Monument", etc. in the database.
"""

# Database → App UI category mapping
CATEGORY_MAPPING = {
    # History-related
    "Historic Site": "history",
    "Historic Quarter": "history",
    "Historic Towns": "history",
    "Monument": "history",
    "Cultural Site": "history",
    
    # Architecture
    "Architecture": "architecture",
    "Palace": "palaces",
    "Castle": "castles",
    
    # Museums & Art
    "Museum": "museums",
    "Gallery": "art",
    
    # Religious
    "Religious Site": "religious",
    "Church": "religious",
    "Cathedral": "religious",
    "Monastery": "religious",
    "Mosque": "religious",
    
    # Nature
    "Natural Site": "nature",
    "Natural Park": "nature",
    "Natural Reserve": "nature",
    "Mountain": "nature",
    "Park": "parks",
    "Gardens": "gardens",
    "Garden": "gardens",
    
    # Beaches & Coast
    "Beach": "beaches",
    
    # Views & Landmarks
    "Viewpoint": "viewpoints",
    "Landmark": "viewpoints",  # Many landmarks are viewpoints
    
    # Neighborhoods
    "Neighborhood": "neighborhoods",
    "White Village": "neighborhoods",
    "Quarter": "neighborhoods",
    
    # Markets & Food
    "Market": "markets",
    "Shop": "markets",
    
    # Activities
    "Entertainment": "entertainment",
    "Activity": "activities",
    "Tour": "activities",
    
    # Fallback - anything not mapped goes to a generic category
    "Unknown": "other",
}

# Reverse mapping: App UI → Database categories
# This allows us to query "what database categories match 'history'?"
APP_TO_DATABASE = {}
for db_cat, app_cat in CATEGORY_MAPPING.items():
    if app_cat not in APP_TO_DATABASE:
        APP_TO_DATABASE[app_cat] = []
    APP_TO_DATABASE[app_cat].append(db_cat)


def normalize_poi_category(db_category):
    """
    Convert database category to app UI category.
    
    Args:
        db_category: Category from JSON database (e.g. "Historic Site")
    
    Returns:
        App UI category (e.g. "history")
    """
    if not db_category:
        return "other"
    
    # Try exact match first
    if db_category in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[db_category]
    
    # Try case-insensitive match
    for db_cat, app_cat in CATEGORY_MAPPING.items():
        if db_cat.lower() == db_category.lower():
            return app_cat
    
    # Unknown category - return as-is but lowercase
    return db_category.lower()


def get_database_categories_for_filter(app_categories):
    """
    Convert app UI category filters to database category filters.
    
    Args:
        app_categories: List of app UI categories (e.g. ["history", "museums"])
    
    Returns:
        List of database categories (e.g. ["Historic Site", "Monument", "Museum"])
    """
    database_categories = []
    
    for app_cat in app_categories:
        app_cat_lower = app_cat.lower()
        if app_cat_lower in APP_TO_DATABASE:
            database_categories.extend(APP_TO_DATABASE[app_cat_lower])
    
    return database_categories


def apply_category_filter(attractions, preferred_app_categories):
    """
    Filter attractions by app UI categories.
    
    Args:
        attractions: List of POI dicts with 'category' field
        preferred_app_categories: List of app UI categories (e.g. ["history", "museums"])
    
    Returns:
        Filtered list of attractions
    """
    if not preferred_app_categories:
        return attractions  # No filter
    
    # Get corresponding database categories
    db_categories = get_database_categories_for_filter(preferred_app_categories)
    db_categories_lower = [cat.lower() for cat in db_categories]
    
    # Filter attractions
    filtered = []
    for attraction in attractions:
        db_cat = attraction.get('category', '')
        if db_cat.lower() in db_categories_lower:
            filtered.append(attraction)
    
    return filtered


# For debugging: show the mapping
if __name__ == "__main__":
    print("DATABASE → APP CATEGORY MAPPING:")
    print("=" * 70)
    for db_cat, app_cat in sorted(CATEGORY_MAPPING.items()):
        print(f"{db_cat:30s} → {app_cat}")
    
    print("\n" + "=" * 70)
    print("APP → DATABASE CATEGORIES:")
    print("=" * 70)
    for app_cat, db_cats in sorted(APP_TO_DATABASE.items()):
        print(f"\n{app_cat}:")
        for db_cat in db_cats:
            print(f"  - {db_cat}")
    
    print("\n" + "=" * 70)
    print("EXAMPLE USAGE:")
    print("=" * 70)
    
    # Example 1: Normalize database category
    print("\nnormalize_poi_category('Historic Site') →", normalize_poi_category('Historic Site'))
    print("normalize_poi_category('Natural Park') →", normalize_poi_category('Natural Park'))
    
    # Example 2: Get database categories for filter
    app_prefs = ["history", "nature", "museums"]
    print(f"\nUser selects: {app_prefs}")
    print(f"Database categories to query: {get_database_categories_for_filter(app_prefs)}")
