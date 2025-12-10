"""
Weighted POI scoring system that prioritizes popular landmarks over obscure high-rated venues.
Combines rating, review volume, and landmark importance.
"""

import math
from must_see_landmarks import is_must_see


def calculate_weighted_score(poi, city_name=None):
    """
    Calculate a weighted score for a POI that balances rating, popularity, and importance.
    
    Formula: score = (rating × √reviews) + popularity_bonus + must_see_bonus
    
    This ensures that:
    - A 4.5★ with 10,000 reviews scores higher than 5.0★ with 30 reviews
    - Must-see landmarks get priority regardless of rating
    - Popular attractions are favored over obscure venues
    
    Args:
        poi: POI dictionary with 'rating', 'reviews_count', 'name' fields
        city_name: Optional city name to check for must-see landmarks
        
    Returns:
        float: Weighted score (higher is better)
    """
    # Extract values with safe defaults
    rating = poi.get('rating', 0)
    if rating is None:
        rating = 0
    
    reviews_count = poi.get('reviews_count', 0)
    if reviews_count is None:
        reviews_count = 0
    
    poi_name = poi.get('name', '')
    
    # Base score: rating × √review_count
    # The square root prevents review count from dominating but still gives weight to popularity
    base_score = rating * math.sqrt(reviews_count)
    
    # Popularity bonus: Extra points for high review volumes
    popularity_bonus = 0
    if reviews_count > 5000:
        popularity_bonus = 20
    elif reviews_count > 1000:
        popularity_bonus = 10
    elif reviews_count > 500:
        popularity_bonus = 5
    
    # Must-see bonus: Massive boost for iconic landmarks
    must_see_bonus = 0
    if city_name and is_must_see(poi_name, city_name):
        must_see_bonus = 50  # Strong boost to ensure must-sees are always included
    
    # Importance tier bonus: Boost for high-importance categories
    importance = poi.get('importance', 0)
    if importance is None:
        importance = 0
    
    importance_bonus = 0
    if importance >= 9:  # Top-tier attractions
        importance_bonus = 15
    elif importance >= 7:  # Major attractions
        importance_bonus = 8
    elif importance >= 5:  # Moderate attractions
        importance_bonus = 3
    
    # Calculate total score
    total_score = base_score + popularity_bonus + must_see_bonus + importance_bonus
    
    return total_score


def score_and_sort_pois(pois, city_name=None):
    """
    Score all POIs and return them sorted by weighted score (highest first).
    
    Args:
        pois: List of POI dictionaries
        city_name: Optional city name for must-see landmark checking
        
    Returns:
        list: POIs sorted by weighted score, each with added 'weighted_score' field
    """
    # Calculate scores
    for poi in pois:
        poi['weighted_score'] = calculate_weighted_score(poi, city_name)
    
    # Sort by score (highest first)
    sorted_pois = sorted(pois, key=lambda x: x['weighted_score'], reverse=True)
    
    return sorted_pois


def filter_low_quality_pois(pois, min_reviews=10, min_rating=3.5):
    """
    Filter out POIs that are too new or poorly rated to trust.
    
    Args:
        pois: List of POI dictionaries
        min_reviews: Minimum number of reviews required (default: 10)
        min_rating: Minimum rating required (default: 3.5)
        
    Returns:
        list: Filtered POIs
    """
    filtered = []
    
    for poi in pois:
        rating = poi.get('rating', 0)
        reviews_count = poi.get('reviews_count', 0)
        
        # Handle None values
        if rating is None:
            rating = 0
        if reviews_count is None:
            reviews_count = 0
        
        # Keep POI if it meets quality thresholds
        if rating >= min_rating and reviews_count >= min_reviews:
            filtered.append(poi)
    
    return filtered


def get_top_pois_by_score(pois, city_name=None, top_n=10, min_reviews=10):
    """
    Get the top N POIs by weighted score, filtering out low-quality venues.
    
    Args:
        pois: List of POI dictionaries
        city_name: Optional city name for must-see landmark checking
        top_n: Number of top POIs to return
        min_reviews: Minimum review count threshold
        
    Returns:
        list: Top N POIs sorted by weighted score
    """
    # Filter out low-quality POIs
    quality_pois = filter_low_quality_pois(pois, min_reviews=min_reviews)
    
    # Score and sort
    scored_pois = score_and_sort_pois(quality_pois, city_name)
    
    # Return top N
    return scored_pois[:top_n]


def explain_score(poi, city_name=None):
    """
    Generate a human-readable explanation of a POI's weighted score.
    Useful for debugging and understanding why certain POIs are prioritized.
    
    Args:
        poi: POI dictionary
        city_name: Optional city name
        
    Returns:
        str: Explanation of the score breakdown
    """
    score = calculate_weighted_score(poi, city_name)
    rating = poi.get('rating', 0) or 0
    reviews = poi.get('reviews_count', 0) or 0
    importance = poi.get('importance', 0) or 0
    name = poi.get('name', 'Unknown')
    
    base = rating * math.sqrt(reviews)
    
    explanation = f"{name}: {score:.1f} points\n"
    explanation += f"  Base (rating × √reviews): {rating} × √{reviews} = {base:.1f}\n"
    
    if reviews > 5000:
        explanation += f"  Popularity bonus: +20 (>{reviews} reviews)\n"
    elif reviews > 1000:
        explanation += f"  Popularity bonus: +10 (>{reviews} reviews)\n"
    
    if city_name and is_must_see(name, city_name):
        explanation += f"  Must-see bonus: +50 (iconic landmark)\n"
    
    if importance >= 9:
        explanation += f"  Importance bonus: +15 (tier {importance})\n"
    elif importance >= 7:
        explanation += f"  Importance bonus: +8 (tier {importance})\n"
    
    return explanation
