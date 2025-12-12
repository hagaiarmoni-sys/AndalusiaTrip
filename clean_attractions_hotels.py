"""
Clean Attractions JSON - Remove Hotels/Lodging
Based on manual review of andalusia_attractions_filtered.json
"""

import json
from pathlib import Path

# Hotels/lodging to REMOVE from attractions
HOTELS_TO_REMOVE = [
    # Antequera
    "Arte de Cozina",
    "Convento de la Magdalena",
    "Hotel Fuente del Sol",
    
    # Carmona
    "Parador de Carmona",
    
    # Cádiz
    "Apartments Plaza de la Luz",
    "Hotel Boutique Convento Cádiz",
    "Hotel Monte Puertatierra",
    "Parador de Cádiz",
    
    # Córdoba
    "Hotel NH Collection Amistad Córdoba",
    
    # Frigiliana/Torrox
    "Iberostar Waves Málaga Playa",
    
    # Granada
    "Camping Las Lomas",
    "Casa del Capitel Nazarí",
    "Corrala de Santiago",
    "ECO Hostel",
    "Edificio de la Lonja de Granada",
    "Hospes Palacio de los Patos",
    "Hotel Alhambra Palace",
    "Hotel NH Collection Granada Victoria",
    "Hotel Palacio de Santa Ines, siglo XVI",
    
    # Huelva
    "Hacienda Montija Hotel",
    "Hotel Nuevo Portil",
    
    # Jaén
    "Parador de Jaén",
    
    # Jerez
    "Barceló Montecastillo Golf",
    "Hipotels Sherry Park",
    
    # Marbella
    "Don Carlos Marbella",
    "El Fuerte Marbella",
    "Hotel Don Pepe Gran Meliá",
    "Hotel Los Monteros SPA & Golf Resort 5GL",
    "Marbella Club Golf Resort",
    "Marriott's Marbella Beach Resort",
    
    # Málaga
    "Barceló Málaga",
    "Hotel Molina Lario",
    
    # Nerja
    "Hotel Villa Flamenca",
    "Parador de Nerja",
    
    # Osuna
    "Palace of the Marques de la Gomera",
    
    # Ronda
    "Camping El Sur",
    "Hotel Colón",
    "Hotel San Francisco – Ronda",
    
    # Seville
    "Bécquer Hotel",
    "CoolRooms Palacio Villapanés 5 GL",
    "H10 Corregidor Boutique Hotel",
    "Hospes Las Casas del Rey de Baeza",
    "Hotel Casa 1800 Seville",
    "Petit Palace Santa Cruz",
    "Torre de la Plata",
    
    # Tarifa
    "Hostal El Levante",
    "Hotel Hurricane",
    "Hotel La Torre, Tarifa",
    "Mesón de Sancho",
    "Tres mares",
    
    # Vejer/Conil
    "Camping Caños de Meca",
    "Conilsol",
    "FERGUS Conil Park",
    "Hipotels Flamenco Conil",
    "Hipotels Gran Conil",
    "Hotel Andalussia",
    "Hotel Fuerte Conil-Resort",
    "Hotel La Casa del Califa de Vejer",
    "Hotel Pradillo Conil",
    
    # Úbeda
    "Cetina Palacio de Los Salcedo",
    "Hotel Álvaro de Torres Boutique",
]

# Non-attractions to REMOVE
NON_ATTRACTIONS = [
    "Europe Luxury Cars",  # Car rental
    "PC PLASMA – Tu Tienda Informática",  # Computer shop
]

# Keep this one (it's a real attraction)
KEEP = [
    "Úbeda Renaissance Quarter"
]

def clean_attractions_file(input_path, output_path=None):
    """
    Remove hotels and non-attractions from attractions JSON
    
    Args:
        input_path: Path to andalusia_attractions_filtered.json
        output_path: Path to save cleaned file (default: adds _cleaned suffix)
    """
    # Load data
    with open(input_path, 'r', encoding='utf-8') as f:
        attractions = json.load(f)
    
    print(f"Original attractions count: {len(attractions)}")
    
    # Identify items to remove
    to_remove_names = set(HOTELS_TO_REMOVE + NON_ATTRACTIONS)
    
    # Also remove anything with 'lodging' in google_types (but keep explicit KEEP list)
    removed = []
    cleaned = []
    
    for attr in attractions:
        name = attr.get('name', '')
        google_types = attr.get('google_types', [])
        
        # Check if should be kept (explicit whitelist)
        if name in KEEP:
            cleaned.append(attr)
            continue
        
        # Check if should be removed (explicit blacklist)
        if name in to_remove_names:
            removed.append({
                'name': name,
                'city': attr.get('city'),
                'reason': 'manual_list'
            })
            continue
        
        # Check if lodging type
        if 'lodging' in google_types:
            removed.append({
                'name': name,
                'city': attr.get('city'),
                'reason': 'lodging_type'
            })
            continue
        
        # Otherwise keep it
        cleaned.append(attr)
    
    # Save cleaned file
    if output_path is None:
        input_path_obj = Path(input_path)
        output_path = input_path_obj.parent / f"{input_path_obj.stem}_cleaned{input_path_obj.suffix}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    # Report
    print(f"\n{'='*80}")
    print(f"CLEANUP COMPLETE")
    print(f"{'='*80}")
    print(f"Original count: {len(attractions)}")
    print(f"Removed count:  {len(removed)}")
    print(f"Final count:    {len(cleaned)}")
    print(f"\nSaved to: {output_path}")
    
    # Show what was removed
    print(f"\n{'='*80}")
    print(f"REMOVED ITEMS BY CITY")
    print(f"{'='*80}")
    
    from collections import defaultdict
    by_city = defaultdict(list)
    for item in removed:
        by_city[item['city']].append(item['name'])
    
    for city, names in sorted(by_city.items()):
        print(f"\n{city} ({len(names)} removed):")
        for name in sorted(names):
            print(f"  - {name}")
    
    return cleaned, removed


if __name__ == "__main__":
    # Example usage
    input_file = "/mnt/user-data/uploads/andalusia_attractions_filtered.json"
    output_file = "/mnt/user-data/outputs/andalusia_attractions_cleaned.json"
    
    cleaned, removed = clean_attractions_file(input_file, output_file)
    
    print(f"\n{'='*80}")
    print(f"VERIFICATION")
    print(f"{'='*80}")
    
    # Count by category
    from collections import Counter
    categories = Counter(attr.get('category') for attr in cleaned)
    print("\nAttractions by category:")
    for cat, count in categories.most_common(15):
        print(f"  {cat:30s}: {count:3d}")
