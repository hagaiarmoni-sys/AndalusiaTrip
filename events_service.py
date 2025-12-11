# Events Service for Andalusia Trip Planner
# Uses FREE APIs to find events during user's trip

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ============================================================================
# TIER 1: JUNTA DE ANDALUCÍA API (100% FREE FOREVER)
# ============================================================================

def get_junta_events(city: str, start_date: str, end_date: str) -> List[Dict]:
    """
    Get official events from Junta de Andalucía Open Data
    
    API: https://www.juntadeandalucia.es/datosabiertos/portal/api/3/action/datastore_search
    Format: start_date and end_date as "YYYY-MM-DD"
    
    Returns list of events with:
    - name
    - date
    - location
    - description
    - type
    """
    
    # Resource ID for Junta events
    resource_id = "d94fb9e3-f5c8-457e-9833-9067d6fa811e"  # JSON endpoint
    
    url = "https://www.juntadeandalucia.es/datosabiertos/portal/api/3/action/datastore_search"
    
    try:
        params = {
            'resource_id': resource_id,
            'limit': 100  # Get up to 100 events
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('result', {}).get('records', [])
            
            # Filter by date range and city
            filtered_events = []
            for record in records:
                event_date_str = record.get('fecha_inicio', '')
                event_city = record.get('municipio', '')
                
                # Parse date
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    start = datetime.strptime(start_date, '%Y-%m-%d')
                    end = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    # Check if event is during trip
                    if start <= event_date <= end:
                        # Check if event is in this city (fuzzy match)
                        if city.lower() in event_city.lower():
                            filtered_events.append({
                                'name': record.get('titulo', 'Event'),
                                'date': event_date_str,
                                'location': event_city,
                                'description': record.get('descripcion', ''),
                                'type': 'Cultural',
                                'source': 'Junta de Andalucía',
                                'url': record.get('enlace', '')
                            })
                except:
                    continue
            
            return filtered_events
    
    except Exception as e:
        print(f"⚠️ Error fetching Junta events: {e}")
        return []
    
    return []


# ============================================================================
# TIER 2: EVENTBRITE API (1,000 free requests/day)
# ============================================================================

def get_eventbrite_events(city: str, start_date: str, end_date: str, api_token: str) -> List[Dict]:
    """
    Get events from Eventbrite API
    
    Sign up: https://www.eventbrite.com/platform/api
    Free tier: 1,000 requests/day
    
    Args:
        api_token: Your Eventbrite private token
    """
    
    if not api_token or api_token == "YOUR_TOKEN_HERE":
        print("⚠️ Eventbrite API token not configured")
        return []
    
    url = "https://www.eventbriteapi.com/v3/events/search/"
    
    try:
        # Convert dates to ISO format
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        params = {
            'location.address': f'{city}, Andalusia, Spain',
            'start_date.range_start': start_dt.strftime('%Y-%m-%dT00:00:00'),
            'start_date.range_end': end_dt.strftime('%Y-%m-%dT23:59:59'),
            'expand': 'venue',
            'sort_by': 'date'
        }
        
        headers = {
            'Authorization': f'Bearer {api_token}'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            events_list = []
            
            for event in data.get('events', []):
                events_list.append({
                    'name': event.get('name', {}).get('text', 'Event'),
                    'date': event.get('start', {}).get('local', '')[:10],
                    'location': city,
                    'description': event.get('description', {}).get('text', '')[:200] + '...',
                    'type': 'Event',
                    'source': 'Eventbrite',
                    'url': event.get('url', ''),
                    'is_free': event.get('is_free', False)
                })
            
            return events_list
        
    except Exception as e:
        print(f"⚠️ Error fetching Eventbrite events: {e}")
        return []
    
    return []


# ============================================================================
# TIER 3: CURATED DATABASE (Backup - Always works)
# ============================================================================

# Major annual festivals in Andalusia
CURATED_FESTIVALS = [
    # === MAY FESTIVALS (Tier 1 - Major) ===
    {
        'name': 'Feria del Caballo (Horse Fair)',
        'city': 'Jerez de la Frontera',
        'month': 5,
        'week': 1,  # First week of May
        'duration': 7,
        'type': 'Festival',
        'tier': 'tier_1',
        'description': "Spain's most important horse fair with equestrian shows, sherry, and flamenco"
    },
    {
        'name': 'Festival de los Patios',
        'city': 'Córdoba',
        'month': 5,
        'week': 1,  # First 2 weeks of May
        'duration': 14,
        'type': 'Cultural',
        'tier': 'tier_1',
        'description': 'UNESCO-listed festival where locals open their flower-filled patios for free'
    },
    {
        'name': 'Cruces de Mayo',
        'city': 'Córdoba',
        'month': 5,
        'week': 1,
        'duration': 4,
        'type': 'Festival',
        'tier': 'tier_2',
        'description': 'Neighborhoods compete to create the most beautiful flower-covered crosses'
    },
    {
        'name': 'Cruces de Mayo',
        'city': 'Granada',
        'month': 5,
        'week': 1,  # Around May 3rd
        'duration': 3,
        'type': 'Festival',
        'tier': 'tier_2',
        'description': 'Decorated crosses in plazas with music, dancing, and tapas'
    },
    # === APRIL FESTIVALS ===
    {
        'name': 'Feria de Abril',
        'city': 'Seville',
        'month': 4,
        'week': 3,  # 3rd week of April
        'duration': 6,
        'type': 'Festival',
        'tier': 'tier_1',
        'description': 'The most famous festival in Seville with flamenco, food, and casetas'
    },
    # === SEMANA SANTA ===
    {
        'name': 'Semana Santa (Holy Week)',
        'city': 'Granada',
        'month': 3,  # Or 4, depends on Easter
        'week': 2,
        'duration': 7,
        'type': 'Religious',
        'tier': 'tier_1',
        'description': 'Spectacular Holy Week processions through the streets'
    },
    {
        'name': 'Semana Santa (Holy Week)',
        'city': 'Seville',
        'month': 3,  # Or 4, depends on Easter
        'week': 2,
        'duration': 7,
        'type': 'Religious',
        'tier': 'tier_1',
        'description': 'One of Spain\'s most impressive Holy Week celebrations'
    },
    {
        'name': 'Semana Santa (Holy Week)',
        'city': 'Málaga',
        'month': 3,  # Or 4, depends on Easter
        'week': 2,
        'duration': 7,
        'type': 'Religious',
        'tier': 'tier_1',
        'description': 'Famous Holy Week processions with spectacular thrones'
    },
    {
        'name': 'Semana Santa (Holy Week)',
        'city': 'Córdoba',
        'month': 3,  # Or 4, depends on Easter
        'week': 2,
        'duration': 7,
        'type': 'Religious',
        'tier': 'tier_1',
        'description': 'Beautiful processions through historic streets'
    },
    {
        'name': 'Festival Internacional de Música y Danza',
        'city': 'Granada',
        'month': 6,
        'week': 3,
        'duration': 30,
        'type': 'Music',
        'description': 'International music and dance festival at the Alhambra'
    },
    {
        'name': 'Bienal de Flamenco',
        'city': 'Seville',
        'month': 9,
        'week': 2,
        'duration': 30,
        'type': 'Flamenco',
        'description': 'Biennial flamenco festival (even years only)'
    },
    {
        'name': 'Carnaval de Cádiz',
        'city': 'Cádiz',
        'month': 2,
        'week': 2,
        'duration': 10,
        'type': 'Carnival',
        'description': 'One of Spain\'s most famous carnivals with satirical songs'
    },
    {
        'name': 'Festival de Jerez',
        'city': 'Jerez de la Frontera',
        'month': 2,
        'week': 4,
        'duration': 14,
        'type': 'Flamenco',
        'description': 'Major flamenco festival attracting artists worldwide'
    },
    {
        'name': 'Feria de Málaga',
        'city': 'Málaga',
        'month': 8,
        'week': 2,
        'duration': 9,
        'type': 'Festival',
        'description': 'Summer fair with music, dancing, and fireworks'
    },
    {
        'name': 'Romería del Rocío',
        'city': 'Almonte',
        'month': 5,
        'week': 4,
        'duration': 3,
        'type': 'Religious',
        'description': 'Massive pilgrimage to El Rocío sanctuary'
    },
    {
        'name': 'Noche en Blanco',
        'city': 'Málaga',
        'month': 5,
        'week': 2,
        'duration': 1,
        'type': 'Cultural',
        'description': 'All-night cultural activities throughout the city'
    },
    {
        'name': 'Noche en Blanco',
        'city': 'Seville',
        'month': 10,
        'week': 2,
        'duration': 1,
        'type': 'Cultural',
        'description': 'All-night cultural activities throughout the city'
    },
    {
        'name': 'Feria de Córdoba',
        'city': 'Córdoba',
        'month': 5,
        'week': 4,
        'duration': 9,
        'type': 'Festival',
        'description': 'May fair with flamenco, food, and traditional celebrations'
    },
    {
        'name': 'Festival de Teatro de Málaga',
        'city': 'Málaga',
        'month': 3,
        'week': 1,
        'duration': 14,
        'type': 'Theater',
        'description': 'International theater festival'
    },
    {
        'name': 'Feria de Granada',
        'city': 'Granada',
        'month': 6,
        'week': 1,
        'duration': 7,
        'type': 'Festival',
        'description': 'Corpus Christi fair with traditional celebrations'
    },
    {
        'name': 'Noche de San Juan',
        'city': 'Málaga',
        'month': 6,
        'week': 4,
        'duration': 1,
        'type': 'Festival',
        'description': 'Midsummer festival with beach bonfires'
    },
    {
        'name': 'Noche de San Juan',
        'city': 'Cádiz',
        'month': 6,
        'week': 4,
        'duration': 1,
        'type': 'Festival',
        'description': 'Midsummer celebrations on the beach'
    },

    {
        'name': 'Festival Internacional de Música y Danza',
        'city': 'Granada',
        'month': 6,
        'week': 3,
        'duration': 30,
        'type': 'Music',
        'description': 'International music and dance festival at the Alhambra'
    },
    {
        'name': 'Bienal de Flamenco',
        'city': 'Seville',
        'month': 9,
        'week': 2,
        'duration': 30,
        'type': 'Flamenco',
        'description': 'Biennial flamenco festival (even years only)'
    },
    {
        'name': 'Carnaval de Cádiz',
        'city': 'Cádiz',
        'month': 2,
        'week': 2,
        'duration': 10,
        'type': 'Carnival',
        'description': 'One of Spain\'s most famous carnivals with satirical songs'
    },
    {
        'name': 'Festival de Jerez',
        'city': 'Jerez de la Frontera',
        'month': 2,
        'week': 4,
        'duration': 14,
        'type': 'Flamenco',
        'description': 'Major flamenco festival attracting artists worldwide'
    },
    {
        'name': 'Feria de Málaga',
        'city': 'Málaga',
        'month': 8,
        'week': 2,
        'duration': 9,
        'type': 'Festival',
        'description': 'Summer fair with music, dancing, and fireworks'
    },
    {
        'name': 'Romería del Rocío',
        'city': 'Almonte',
        'month': 5,
        'week': 4,
        'duration': 3,
        'type': 'Religious',
        'description': 'Massive pilgrimage to El Rocío sanctuary'
    }
]

def get_curated_events(city: str, start_date: str, end_date: str) -> List[Dict]:
    """
    Check curated database of major festivals
    
    This is a fallback that always works, no API needed!
    """
    import unicodedata
    
    def normalize_city(name: str) -> str:
        """Remove accents and lowercase for comparison"""
        # Normalize unicode and remove accents
        normalized = unicodedata.normalize('NFD', name)
        without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return without_accents.lower()
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    matching_events = []
    
    for festival in CURATED_FESTIVALS:
        # Estimate festival dates (approximate)
        festival_year = start_dt.year
        festival_month = festival['month']
        festival_week = festival['week']
        
        # Estimate start day (week 1 = day 1, week 2 = day 8, etc.)
        estimated_day = (festival_week - 1) * 7 + 1
        
        try:
            festival_start = datetime(festival_year, festival_month, estimated_day)
            festival_end = festival_start + timedelta(days=festival['duration'])
            
            # Check if festival overlaps with trip
            if (festival_start <= end_dt and festival_end >= start_dt):
                # Check if city matches (normalized for accents)
                city_norm = normalize_city(city)
                festival_city_norm = normalize_city(festival['city'])
                if city_norm in festival_city_norm or festival_city_norm in city_norm or ('jerez' in city_norm and 'jerez' in festival_city_norm):
                    matching_events.append({
                        'name': festival['name'],
                        'date': festival_start.strftime('%Y-%m-%d'),
                        'city': festival['city'],
                        'location': festival['city'],
                        'description': festival['description'],
                        'type': festival['type'],
                        'tier': festival.get('tier', 'tier_2'),
                        'source': 'Curated',
                        'duration': festival['duration']
                    })
        except:
            continue
    
    # Sort by tier (tier_1 first) then date
    tier_order = {'tier_1': 0, 'tier_2': 1, 'tier_3': 2}
    matching_events.sort(key=lambda x: (tier_order.get(x.get('tier', 'tier_3'), 3), x.get('date', '')))
    
    return matching_events


# ============================================================================
# MAIN FUNCTION: Get all events
# ============================================================================

def get_events_for_trip(city: str, start_date: str, end_date: str, 
                       eventbrite_token: Optional[str] = None) -> List[Dict]:
    """
    Get all events during the trip using multiple sources
    
    Args:
        city: City name (e.g., "Granada")
        start_date: Trip start "YYYY-MM-DD"
        end_date: Trip end "YYYY-MM-DD"
        eventbrite_token: Optional Eventbrite API token
    
    Returns:
        List of events sorted by date
    """
    
    all_events = []
    
    # Tier 1: Official government events (always try first)
    junta_events = get_junta_events(city, start_date, end_date)
    all_events.extend(junta_events)
    
    # Tier 2: Eventbrite (if token provided)
    if eventbrite_token:
        eventbrite_events = get_eventbrite_events(city, start_date, end_date, eventbrite_token)
        all_events.extend(eventbrite_events)
    
    # Tier 3: Curated festivals (always check)
    curated_events = get_curated_events(city, start_date, end_date)
    all_events.extend(curated_events)
    
    # Remove duplicates (by name)
    seen_names = set()
    unique_events = []
    for event in all_events:
        name_lower = event['name'].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_events.append(event)
    
    # Sort by date
    unique_events.sort(key=lambda x: x.get('date', ''))
    
    
    return unique_events


# ============================================================================
# TEST FUNCTION
# ============================================================================

if __name__ == "__main__":
    # Test the service
    city = "Granada"
    start = "2026-06-15"
    end = "2026-06-22"
    
    print("=" * 80)
    print(f"🎉 TESTING EVENTS SERVICE")
    print(f"City: {city}")
    print(f"Dates: {start} to {end}")
    print("=" * 80)
    
    events = get_events_for_trip(city, start, end)
    
    print(f"\n📅 EVENTS FOUND:\n")
    for event in events:
        print(f"• {event['date']} - {event['name']}")
        print(f"  📍 {event['location']} | Type: {event['type']}")
        print(f"  {event['description'][:80]}...")
        print()
