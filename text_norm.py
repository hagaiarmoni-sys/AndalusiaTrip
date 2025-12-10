# coding: utf-8
"""
Text normalization utilities for handling accents and city name variations
"""
import unicodedata
import re

def strip_accents(s):
    """Remove accents from string"""
    if not s:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def norm_key(s):
    """Normalize string for comparison: lowercase, no accents, single spaces"""
    s = strip_accents(s).lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

# Common aliases - using ASCII names that we'll convert
CITY_ALIASES = {
    "malaga": "Malaga",  # Will be matched to Málaga in dataset
    "cordoba": "Cordoba",  # Will be matched to Córdoba in dataset  
    "cadiz": "Cadiz",  # Will be matched to Cádiz in dataset
    "sevilla": "Seville",
    "granada": "Granada",
    "ronda": "Ronda",
    "marbella": "Marbella",
    "jerez": "Jerez de la Frontera",
}

def canonicalize_city(user_city, known_city_labels):
    """
    Convert user input to canonical city name from dataset
    
    Args:
        user_city: City name from user input (e.g., "malaga", "Málaga", "MALAGA")
        known_city_labels: Set of actual city names in your dataset
    
    Returns:
        Canonical city name or None if not found
    """
    if not user_city:
        return None
    
    # Normalize the user input
    key = norm_key(user_city)
    
    # 1) Check alias map first (this gives us ASCII versions)
    if key in CITY_ALIASES:
        alias_result = CITY_ALIASES[key]
        # Now match the alias result against known cities
        alias_key = norm_key(alias_result)
        for label in known_city_labels:
            if norm_key(label) == alias_key:
                return label
        # If alias doesn't match, continue to step 2
    
    # 2) Direct exact match (case/accent/space insensitive)
    for label in known_city_labels:
        if norm_key(label) == key:
            return label
    
    # 3) Gentle fallback: prefix match (helps with typos)
    for label in known_city_labels:
        if norm_key(label).startswith(key):
            return label
    
    return None
