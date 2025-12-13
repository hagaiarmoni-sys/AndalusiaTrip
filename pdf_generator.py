"""
Advanced PDF Generator for Andalusia Travel App
Features: Photos, Colors, Hyperlinks, styled like the Word document
"""

from fpdf import FPDF
from datetime import datetime, timedelta
import os
import io
from urllib.parse import quote_plus
from poi_cards_pdf import render_poi_cards

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PHOTOS_DIR = os.path.join(DATA_DIR, 'photos')

# Colors (R, G, B)
COLOR_PRIMARY = (41, 128, 185)    # Blue
COLOR_ACCENT = (231, 76, 60)      # Red
COLOR_DAY_HEADER = (243, 156, 18) # Orange/Yellow
COLOR_TEXT = (52, 73, 94)         # Dark Grey
COLOR_LIGHT = (127, 140, 141)     # Light Grey
COLOR_HOTEL = (46, 204, 113)      # Green
COLOR_FOOD = (230, 126, 34)       # Orange
COLOR_ATTR = (155, 89, 182)       # Purple

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_text(text, max_length=300):
    """Clean text for PDF - handle special characters"""
    if not text:
        return ""
    text = str(text)
    
    # Replace problematic characters
    replacements = {
        "'": "'", "'": "'", "–": "-", "—": "-", 
        """: '"', """: '"', "€": "EUR ", "…": "...",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ñ": "n", "ç": "c", "°": " deg",
        "★": "*", "☆": "*", "●": "*", "•": "*",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Encode to latin-1, replacing unknown chars
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text


def get_photo_path(attr):
    """Find photo using same logic as Word generator"""
    # 1. Try local_photo_path
    if attr.get('local_photo_path'):
        rel_path = attr['local_photo_path'].replace('\\', '/')
        if os.path.isabs(rel_path):
            full_path = rel_path
        else:
            # Try relative to DATA_DIR
            full_path = os.path.join(DATA_DIR, rel_path)
            if not os.path.exists(full_path):
                # Try just the filename in PHOTOS_DIR
                filename = os.path.basename(rel_path)
                full_path = os.path.join(PHOTOS_DIR, filename)
        
        if os.path.exists(full_path):
            return full_path

    # 2. Try place_id
    if attr.get('place_id'):
        photo_filename = f"{attr['place_id']}.jpg"
        full_path = os.path.join(PHOTOS_DIR, photo_filename)
        if os.path.exists(full_path):
            return full_path
    
    # 3. Try name-based filename
    name = attr.get('name', '')
    if name:
        # Try various filename formats
        for ext in ['.jpg', '.jpeg', '.png']:
            # Try exact name
            test_path = os.path.join(PHOTOS_DIR, f"{name}{ext}")
            if os.path.exists(test_path):
                return test_path
            # Try normalized name
            norm_name = name.lower().replace(' ', '_').replace("'", "")
            test_path = os.path.join(PHOTOS_DIR, f"{norm_name}{ext}")
            if os.path.exists(test_path):
                return test_path

    return None


# ============================================================================
# PDF CLASS
# ============================================================================

class TravelPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(*COLOR_LIGHT)
            self.cell(0, 10, 'Andalusia Road Trip Planner', align='C')
            self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*COLOR_LIGHT)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title, color):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*color)
        self.multi_cell(0, 10, safe_text(title, 100))
        self.ln(2)
        
    def section_title(self, title, color):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*color)
        self.multi_cell(0, 8, safe_text(title, 80))
        self.ln(1)

    def add_link(self, text, url, color=COLOR_PRIMARY):
        """Add a clickable hyperlink using write()"""
        if not url:
            return
        self.set_font('Helvetica', 'U', 10)
        self.set_text_color(*color)
        self.write(6, safe_text(text, 70), url)
        self.ln(7)
        self.set_text_color(*COLOR_TEXT)

    def add_photo(self, photo_path, max_width=100):
        """Add a photo, centered, with error handling"""
        if not photo_path or not os.path.exists(photo_path):
            return False
        try:
            # Center the image (A4 width is 210mm, minus margins)
            x_pos = (210 - max_width) / 2
            self.image(photo_path, x=x_pos, w=max_width)
            self.ln(3)
            return True
        except Exception as e:
            # Image failed to load - skip silently
            return False


# ============================================================================
# MAIN BUILDER
# ============================================================================

def build_pdf(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, parsed_requests, is_car_mode=False, result=None):
    pdf = TravelPDF()
    
    # Date handling - support date, datetime, and string
    start_date = None
    if result and result.get('start_date'):
        raw_date = result['start_date']
        # Debug
        print(f"[PDF] Raw start_date: {raw_date}, type: {type(raw_date)}")
        
        # Convert string to date
        if isinstance(raw_date, str):
            try:
                start_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
            except:
                try:
                    start_date = datetime.strptime(raw_date, "%d/%m/%Y").date()
                except:
                    start_date = None
        # If it's already a date or datetime
        elif hasattr(raw_date, 'year'):
            start_date = raw_date
        
        print(f"[PDF] Processed start_date: {start_date}, type: {type(start_date)}")
    
    # Get all events from result
    all_events = []
    if result:
        all_events = result.get('events', []) or result.get('seasonal_events', []) or []
        print(f"[PDF] Found {len(all_events)} events in result")

    trip_type = prefs.get('trip_type', 'Point-to-point') if prefs else 'Point-to-point'
    is_hub_trip = trip_type == 'Star/Hub'

    # ========================================================================
    # COVER PAGE
    # ========================================================================
    pdf.add_page()
    pdf.ln(30)
    
    # Title
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 15, 'ANDALUSIA', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', 'B', 26)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(0, 12, 'ROAD TRIP', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Route
    if ordered_cities:
        pdf.set_font('Helvetica', '', 14)
        pdf.set_text_color(*COLOR_TEXT)
        route_text = ' - '.join([safe_text(c, 20) for c in ordered_cities[:6]])
        pdf.cell(0, 8, route_text, align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Duration
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 8, f'{days} Days of Adventure', align='C', new_x="LMARGIN", new_y="NEXT")
    
    # Dates
    if start_date:
        try:
            end_date = start_date + timedelta(days=days-1)
            date_str = f"{start_date.strftime('%d %B')} - {end_date.strftime('%d %B %Y')}"
            pdf.set_font('Helvetica', '', 12)
            pdf.cell(0, 8, date_str, align='C', new_x="LMARGIN", new_y="NEXT")
        except:
            pass
    
    pdf.ln(15)
    
    # Full route link
    if maps_link:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(*COLOR_HOTEL)
        pdf.cell(0, 8, 'VIEW COMPLETE ROUTE:', align='C', new_x="LMARGIN", new_y="NEXT")
        
        # Centered clickable link
        pdf.set_font('Helvetica', 'U', 11)
        pdf.set_text_color(*COLOR_PRIMARY)
        link_text = 'Open in Google Maps'
        link_width = pdf.get_string_width(link_text) + 10
        pdf.set_x((210 - link_width) / 2)
        pdf.write(8, link_text, maps_link)
        pdf.ln(10)

    # ========================================================================
    # EVENTS SECTION (if any events during the trip)
    # ========================================================================
    if all_events:
        pdf.add_page()
        pdf.chapter_title('EVENTS DURING YOUR TRIP', (142, 68, 173))  # Purple
        pdf.ln(3)
        
        pdf.set_font('Helvetica', 'I', 10)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(0, 6, f'Found {len(all_events)} special events happening during your visit!', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        for event in all_events:
            # Event name
            event_name = safe_text(event.get('name', '') or event.get('title', 'Event'), 60)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(*COLOR_TEXT)
            pdf.cell(0, 7, event_name, new_x="LMARGIN", new_y="NEXT")
            
            # Event location/city
            event_city = event.get('city', '') or event.get('location', '')
            if event_city:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(*COLOR_LIGHT)
                pdf.cell(0, 5, f'Location: {safe_text(event_city, 40)}', new_x="LMARGIN", new_y="NEXT")
            
            # Event dates
            event_dates = event.get('dates', '') or event.get('date', '') or event.get('event_date', '')
            if event_dates:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(*COLOR_LIGHT)
                pdf.cell(0, 5, f'Dates: {safe_text(str(event_dates), 50)}', new_x="LMARGIN", new_y="NEXT")
            
            # Event description
            event_desc = event.get('description', '')
            if event_desc:
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(*COLOR_TEXT)
                pdf.multi_cell(0, 5, safe_text(event_desc, 200))
            
            # Event URL if available
            event_url = event.get('url', '') or event.get('link', '') or event.get('website', '')
            if event_url:
                pdf.add_link('More Information', event_url, COLOR_PRIMARY)
            
            pdf.ln(4)

    # ========================================================================
    # DAILY ITINERARY
    # ========================================================================
    
    for day in itinerary:
        pdf.add_page()
        
        day_num = day.get('day', 0)
        city = safe_text(day.get('city', 'Unknown'), 30)
        overnight = safe_text(day.get('overnight_city', city), 30)
        day_in_city = day.get('day_in_city', 1)
        total_days_in_city = day.get('total_days_in_city', 1)
        
        # Calculate date
        current_date_obj = None
        date_str = ""
        if start_date:
            try:
                current_date_obj = start_date + timedelta(days=day_num - 1)
                date_str = f" - {current_date_obj.strftime('%a, %d %b')}"
            except:
                pass

        # Day header
        pdf.chapter_title(f"DAY {day_num}: {city.upper()}{date_str}", COLOR_DAY_HEADER)
        
        # Day in city info (always show)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*COLOR_LIGHT)
        if total_days_in_city > 1:
            pdf.cell(0, 5, f'Day {day_in_city} of {total_days_in_city} in {city}', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)  # Consistent spacing after header

        # ---------------------------------------------------------
        # Daily Google Maps Link - Use name+city search (same as restaurants)
        # ---------------------------------------------------------
        waypoints = []
        seen_names = set()  # Track unique names to avoid duplicates
        
        for city_stop in day.get('cities', []):
            for attr in city_stop.get('attractions', []):
                attr_name = attr.get('name', '')
                if attr_name and attr_name not in seen_names:
                    seen_names.add(attr_name)
                    attr_city = city_stop.get('city', city)
                    # Build search query: "Attraction Name City"
                    search_query = f"{attr_name} {attr_city}".strip()
                    waypoints.append(search_query)
        
        # Limit to 10 waypoints (Google Maps limit)
        if len(waypoints) > 10:
            waypoints = waypoints[:10]
        
        day_map_url = None
        if waypoints:
            if len(waypoints) == 1:
                # Single destination - use search API
                day_map_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(waypoints[0])}"
            else:
                # Multiple waypoints - use directions API with name-based waypoints
                # Join all locations with " / " separator for directions
                origin = waypoints[0]
                destination = waypoints[-1]
                
                # Build URL with origin, destination, and middle waypoints
                day_map_url = f"https://www.google.com/maps/dir/?api=1&origin={quote_plus(origin)}&destination={quote_plus(destination)}&travelmode=walking"
                
                # Add middle waypoints if any
                if len(waypoints) > 2:
                    middle = waypoints[1:-1]
                    waypoints_param = "|".join(middle)
                    day_map_url += f"&waypoints={quote_plus(waypoints_param)}"
        
        if day_map_url:
            pdf.add_link("Open Today's Route in Google Maps", day_map_url, COLOR_PRIMARY)
            pdf.ln(2)  # Add spacing after route link
        
        # ---------------------------------------------------------
        # YouTube Video Link (first day in city only)
        # ---------------------------------------------------------
        if day_in_city == 1:
            video_added = False
            try:
                from youtube_helper import get_video_for_city
                videos = get_video_for_city(city, max_videos=1)
                if videos and len(videos) > 0:
                    video = videos[0]
                    video_title = safe_text(video.get('title', f'{city} Travel Guide'), 45)
                    video_url = video.get('watch_url', '')
                    if video_url:
                        pdf.add_link(f"Watch: {video_title}", video_url, COLOR_ACCENT)
                        video_added = True
            except:
                pass
            
            if not video_added:
                query = quote_plus(f"{city} Spain travel guide 4K")
                fallback_url = f"https://www.youtube.com/results?search_query={query}"
                pdf.add_link(f"Watch {city} Travel Videos", fallback_url, COLOR_ACCENT)

        pdf.ln(4)  # Increased spacing before highlights section

        # ---------------------------------------------------------
        # ATTRACTIONS WITH PHOTOS (NO individual Google Maps links)
        # ---------------------------------------------------------
        cities_data = day.get('cities', [])
        if not cities_data:
            cities_data = [{'city': city, 'attractions': day.get('attractions', [])}]
        
        for city_stop in cities_data:
            attractions = city_stop.get('attractions', [])
            if attractions:
                pdf.section_title("TODAY'S HIGHLIGHTS", COLOR_ATTR)
                pdf.ln(1)
                
                # NEW: render POIs as compact cards (rounded photos) - implemented in poi_cards_pdf.py
                
                try:
                
                    render_poi_cards(
                
                        pdf=pdf,
                
                        pois=attractions[:6],
                
                        get_photo_path=get_photo_path,
                
                        safe_text=safe_text,
                
                        theme={"text": COLOR_TEXT, "light": COLOR_LIGHT, "accent": COLOR_ATTR, "primary": COLOR_PRIMARY},
                
                        cards_per_page=3,
                
                        max_cards=6,
                
                    )
                
                except Exception:
                
                    # Fallback: previous simple list rendering (keeps PDF generation robust)
                
                                    
                
                                    for idx, attr in enumerate(attractions[:6], 1):
                
                                        attr_name = safe_text(attr.get('name', 'Attraction'), 60)
                
                                        
                
                                        # Attraction name
                
                                        pdf.set_font('Helvetica', 'B', 12)
                
                                        pdf.set_text_color(*COLOR_TEXT)
                
                                        pdf.cell(0, 8, f'{idx}. {attr_name}', new_x="LMARGIN", new_y="NEXT")
                
                                        
                
                                        # PHOTO
                
                                        photo_path = get_photo_path(attr)
                
                                        if photo_path:
                
                                            pdf.add_photo(photo_path, max_width=90)
                
                                        
                
                                        # Description
                
                                        description = attr.get('description', '')
                
                                        if description:
                
                                            pdf.set_font('Helvetica', '', 10)
                
                                            pdf.set_text_color(*COLOR_TEXT)
                
                                            pdf.multi_cell(0, 5, safe_text(description, 300))
                
                                        
                
                                        # Details (rating, duration, price)
                
                                        details = []
                
                                        if attr.get('rating'):
                
                                            details.append(f"Rating: {attr['rating']}")
                
                                        duration = attr.get('recommended_duration') or attr.get('duration')
                
                                        if duration:
                
                                            details.append(f"Time: {duration}")
                
                                        if attr.get('price'):
                
                                            details.append(f"Cost: {attr['price']}")
                
                                        
                
                                        if details:
                
                                            pdf.set_font('Helvetica', 'I', 9)
                
                                            pdf.set_text_color(*COLOR_LIGHT)
                
                                            pdf.cell(0, 6, ' | '.join(details), new_x="LMARGIN", new_y="NEXT")
                
                                        
                
                                        pdf.ln(3)

        # ---------------------------------------------------------
        # EVENTS (check multiple possible locations)
        # ---------------------------------------------------------
        events = day.get('events', [])
        
        # Also check if events are in city_stop
        if not events:
            for city_stop in day.get('cities', []):
                city_events = city_stop.get('events', [])
                if city_events:
                    events = city_events
                    break
        
        # Also check result for events matching this day/city
        if not events and result:
            all_events = result.get('events', [])
            if all_events:
                # Filter events for this city
                city_lower = city.lower()
                events = [e for e in all_events if city_lower in str(e.get('city', '')).lower() 
                          or city_lower in str(e.get('location', '')).lower()]
        
        if events:
            pdf.ln(3)
            pdf.section_title('EVENTS & FESTIVALS', (142, 68, 173))  # Purple
            pdf.ln(1)
            
            for event in events[:3]:
                event_name = safe_text(event.get('name', '') or event.get('title', 'Event'), 50)
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(*COLOR_TEXT)
                pdf.cell(0, 6, f'* {event_name}', new_x="LMARGIN", new_y="NEXT")
                
                # Event details
                event_desc = event.get('description', '')
                if event_desc:
                    pdf.set_font('Helvetica', '', 9)
                    pdf.set_text_color(*COLOR_TEXT)
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.multi_cell(0, 5, safe_text(event_desc, 150))
                
                # Event date/time
                event_date = event.get('date', '') or event.get('dates', '') or event.get('event_date', '')
                if event_date:
                    pdf.set_font('Helvetica', 'I', 8)
                    pdf.set_text_color(*COLOR_LIGHT)
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.cell(0, 5, f'Date: {event_date}', new_x="LMARGIN", new_y="NEXT")
                
                pdf.ln(2)

        # ---------------------------------------------------------
        # HOTELS
        # ---------------------------------------------------------
        hotels = day.get('hotels', [])
        if hotels and day_in_city == 1 and not is_hub_trip:
            pdf.ln(3)
            pdf.section_title('WHERE TO STAY', COLOR_HOTEL)
            pdf.ln(1)
            
            # Calculate dates
            checkin_str = ""
            checkout_str = ""
            nights = total_days_in_city
            if current_date_obj:
                try:
                    checkout_date = current_date_obj + timedelta(days=nights)
                    checkin_str = current_date_obj.strftime('%Y-%m-%d')
                    checkout_str = checkout_date.strftime('%Y-%m-%d')
                except:
                    pass
            
            # Show stay info
            if checkin_str and checkout_str:
                pdf.set_font('Helvetica', 'I', 9)
                pdf.set_text_color(*COLOR_LIGHT)
                stay_info = f"{nights} night{'s' if nights > 1 else ''}: {current_date_obj.strftime('%d %b')} - {checkout_date.strftime('%d %b %Y')}"
                pdf.cell(0, 5, stay_info, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
            
            for hotel in hotels[:3]:
                hotel_name_raw = hotel.get('name', 'Hotel')
                if 'Hotels in' in hotel_name_raw:
                    continue
                
                hotel_name_display = safe_text(hotel_name_raw, 50)
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(*COLOR_TEXT)
                pdf.cell(0, 6, f'* {hotel_name_display}', new_x="LMARGIN", new_y="NEXT")
                
                # Address
                address = hotel.get('address', '')
                if address:
                    pdf.set_font('Helvetica', 'I', 8)
                    pdf.set_text_color(*COLOR_LIGHT)
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.cell(0, 5, safe_text(address, 60), new_x="LMARGIN", new_y="NEXT")
                
                # Booking link - use RAW hotel name for URL (not safe_text)
                # Get city name without safe_text processing for URL
                overnight_raw = day.get('overnight_city', '') or day.get('city', '')
                hotel_search = quote_plus(f"{hotel_name_raw} {overnight_raw}"[:100])
                
                if checkin_str and checkout_str:
                    booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}&checkin={checkin_str}&checkout={checkout_str}"
                    link_text = f"Book {hotel_name_display} ({nights} night{'s' if nights > 1 else ''})"
                else:
                    booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}"
                    link_text = f"Book {hotel_name_display}"
                
                pdf.set_x(pdf.get_x() + 5)
                pdf.add_link(link_text, booking_url, COLOR_HOTEL)
                pdf.ln(1)

        # ---------------------------------------------------------
        # RESTAURANTS
        # ---------------------------------------------------------
        lunch = day.get('lunch_restaurant')
        dinner = day.get('dinner_restaurant')
        
        if lunch or dinner:
            pdf.ln(3)
            pdf.section_title('WHERE TO EAT', COLOR_FOOD)
            pdf.ln(1)
            
            for meal_type, restaurant in [('Lunch', lunch), ('Dinner', dinner)]:
                if restaurant:
                    rest_name = safe_text(restaurant.get('name', 'Restaurant'), 50)
                    
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.set_text_color(*COLOR_TEXT)
                    pdf.cell(0, 6, f'{meal_type}: {rest_name}', new_x="LMARGIN", new_y="NEXT")
                    
                    # Google Maps link - prefer place_id, fallback to name search
                    place_id = restaurant.get('place_id')
                    if place_id:
                        # Use place_id for accurate location
                        rest_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(rest_name)}&query_place_id={place_id}"
                    else:
                        # Fallback: search by name + city (more accurate than coordinates)
                        city = restaurant.get('city', '')
                        search_query = f"{rest_name} {city}".strip()
                        rest_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(search_query)}"
                    
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.add_link('View on Google Maps', rest_url, COLOR_FOOD)
                    
                    pdf.ln(1)

        # ---------------------------------------------------------
        # STOPS ALONG THE WAY (scenic detours on travel days)
        # ---------------------------------------------------------
        route_stops = day.get('route_stops', [])
        if route_stops:
            pdf.ln(3)
            pdf.section_title('STOPS ALONG THE WAY', COLOR_PRIMARY)
            pdf.ln(1)
            
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(*COLOR_LIGHT)
            pdf.cell(0, 5, 'Recommended stops when driving to your next destination', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
            for stop in route_stops:
                stop_name = safe_text(stop.get('name', 'Unknown'), 40)
                stop_type = stop.get('type', 'stop').replace('_', ' ').title()
                highlight = stop.get('highlight', '')
                detour_km = stop.get('detour_km', 0)
                time_min = stop.get('time_min', 30)
                
                # Stop name and type
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(*COLOR_TEXT)
                pdf.cell(0, 6, f"{stop_name} ({stop_type})", new_x="LMARGIN", new_y="NEXT")
                
                # Highlight
                if highlight:
                    pdf.set_font('Helvetica', 'I', 9)
                    pdf.set_text_color(*COLOR_ACCENT)
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.cell(0, 5, f"* {safe_text(highlight, 50)}", new_x="LMARGIN", new_y="NEXT")
                
                # Time and detour info
                pdf.set_font('Helvetica', '', 9)
                pdf.set_text_color(*COLOR_LIGHT)
                pdf.set_x(pdf.get_x() + 5)
                pdf.cell(0, 5, f"~{time_min} min visit | +{detour_km}km detour", new_x="LMARGIN", new_y="NEXT")
                
                # Google Maps link for the stop
                stop_place_id = stop.get('place_id')
                if stop_place_id:
                    stop_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(stop_name)}&query_place_id={stop_place_id}"
                else:
                    stop_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(stop_name + ' Spain')}"
                pdf.set_x(pdf.get_x() + 5)
                pdf.add_link('View on Google Maps', stop_url, COLOR_PRIMARY)
                
                pdf.ln(2)

    # ========================================================================
    # MUST-TRY ANDALUSIAN DISHES
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('MUST-TRY ANDALUSIAN DISHES', COLOR_FOOD)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.multi_cell(0, 5, "Andalusian cuisine is a delicious blend of Mediterranean and Moorish influences. Don't leave without trying these iconic dishes!")
    pdf.ln(4)
    
    dishes = [
        ('Gazpacho', 'Cold tomato soup, perfect for hot days - originated right here in Andalusia'),
        ('Salmorejo', 'Thick, creamy cold soup from Cordoba, topped with egg and jamon'),
        ('Jamon Iberico', 'Premium cured ham from acorn-fed pigs - the best in Spain!'),
        ('Pescaito Frito', 'Fried fish platter, a coastal specialty in Malaga and Cadiz'),
        ('Rabo de Toro', 'Oxtail stew, traditional in Cordoba (especially after bullfights)'),
        ('Tortilla Espanola', 'Classic Spanish potato omelet - simple but delicious'),
        ('Espeto de Sardinas', 'Grilled sardines on a stick, Malaga beach specialty'),
        ('Flamenquin', 'Rolled pork filled with ham and cheese, breaded and fried'),
        ('Pringa', 'Slow-cooked meat sandwich, popular in Seville'),
        ('Churros con Chocolate', 'Fried dough with thick hot chocolate for dipping'),
        ('Sherry Wine', 'From Jerez - try fino, manzanilla, or sweet Pedro Ximenez'),
        ('Ajo Blanco', 'Cold white soup with almonds and grapes, from Malaga'),
    ]
    
    for name, desc in dishes:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*COLOR_FOOD)
        pdf.cell(0, 6, f"{name}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(2)
    
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 6, 'MEAL TIMING IN SPAIN:', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*COLOR_TEXT)
    meal_times = [
        'Breakfast: 8-10am (coffee & pastry)',
        'Lunch: 2-4pm (main meal of the day!)',
        'Tapas: 8-10pm (pre-dinner snacks)',
        'Dinner: 9pm-midnight (yes, really!)',
    ]
    for meal in meal_times:
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {meal}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(3)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.multi_cell(0, 5, "Pro tip: When in doubt, follow the locals! If a restaurant is full of Spanish families at 10pm, you're in the right place.")

    # ========================================================================
    # ROAD TRIP ESSENTIALS
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('ROAD TRIP ESSENTIALS', COLOR_PRIMARY)
    pdf.ln(3)
    
    # Driving in Spain
    pdf.section_title('Driving in Spain 101', COLOR_PRIMARY)
    pdf.ln(1)
    driving_tips = [
        'Drive on the RIGHT side of the road',
        'Speed limits: 120 km/h (highways), 90 km/h (rural), 50 km/h (cities)',
        'Right-of-way: Traffic from right has priority',
        'Using phones while driving is ILLEGAL (200 euro fine!)',
        'Blood alcohol limit: 0.5g/l (0.25g/l for new drivers)',
        'Children under 135cm MUST use car seats',
        'Required: 2 warning triangles, reflective vest, spare tire',
        'Headlights required in tunnels and at night',
    ]
    for tip in driving_tips:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {tip}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(3)
    pdf.section_title('Tolls & Fuel', COLOR_PRIMARY)
    pdf.ln(1)
    fuel_tips = [
        'Autopistas (AP-) are TOLL roads, Autovias (A-) are FREE',
        'Most toll booths accept credit cards (Visa/Mastercard)',
        'Typical tolls: Malaga-Seville ~15-20 euros',
        'Gas stations (gasolineras) are frequent on highways',
        'Fuel types: Gasolina 95 (regular), Gasolina 98 (premium), Diesel',
        'Apps: Google Maps or Waze for cheapest fuel nearby',
    ]
    for tip in fuel_tips:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {tip}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(3)
    pdf.section_title('Parking Guide', COLOR_PRIMARY)
    pdf.ln(1)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.multi_cell(0, 5, "Parking in historic centers can be tricky! Here's what the colors mean:")
    pdf.ln(1)
    parking_tips = [
        'BLUE zones: Pay & display (limited time, usually 2-4h)',
        'GREEN zones: Resident parking ONLY - avoid these!',
        'WHITE lines: Free parking (rare in city centers)',
        'YELLOW lines: No parking/stopping zones',
        'Public lots: 15-25 euros/day in city centers',
        'Hotel parking: 10-20 euros/night (ask when booking)',
        'Best strategy: Park outside old town, walk or taxi in',
        'Useful apps: Parclick, ElParking, Parkopedia',
        'NEVER leave valuables visible in car!',
    ]
    for tip in parking_tips:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {tip}", new_x="LMARGIN", new_y="NEXT")
    
    # Car Rental Tips
    pdf.add_page()
    pdf.section_title('Car Rental Insider Tips', COLOR_PRIMARY)
    pdf.ln(1)
    rental_tips = [
        'Book online in advance = 30-50% cheaper!',
        'Most rentals require 21+ (sometimes 25+)',
        'Credit card required for deposit (debit often not accepted)',
        'Consider full insurance (CDW + theft protection)',
        'Bring: Valid license, passport, credit card',
        'International Driving Permit: Recommended for non-EU licenses',
        '"Full to full" policy is standard (return with full tank)',
        'Manual transmission is default - automatic costs MORE',
        'GPS: 5-10 euros/day, or just use your phone',
        'Photograph ANY existing damage before leaving lot!',
    ]
    for tip in rental_tips:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {tip}", new_x="LMARGIN", new_y="NEXT")

    # ========================================================================
    # ESSENTIAL TRAVEL TIPS
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('ESSENTIAL TRAVEL TIPS', COLOR_PRIMARY)
    pdf.ln(3)
    
    tips = [
        ('Spanish Schedule', 'Lunch 2-4pm, Dinner 9pm+. Many restaurants closed 4-8pm. Embrace the siesta!'),
        ('Book Ahead', 'Alhambra, Alcazar, Cathedral tours need 2-3 weeks advance booking!'),
        ('Best Season', 'Spring (April-May) or Fall (September-October) for perfect weather'),
        ('Cash is King', 'Small towns, markets, and tapas bars often prefer cash'),
        ('Learn Spanish', 'Even basic phrases go a long way! Locals really appreciate it'),
        ('Free Tapas', 'In Granada, many bars give FREE tapas with drinks!'),
        ('Monday Closures', 'Many museums closed Mondays - plan accordingly'),
        ('Get Data', 'Local SIM or international plan for navigation & translations'),
        ('Comfy Shoes', 'Cobblestone streets everywhere - sneakers are your friend'),
        ('Summer Heat', 'June-August = 40C+. Plan indoor activities for midday'),
        ('Tap Water', 'Safe to drink, but locals prefer bottled'),
        ('Siesta Time', 'Small shops close 2-5pm (tourist areas stay open)'),
    ]
    
    for title, desc in tips:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(2)

    # ========================================================================
    # PACKING CHECKLIST
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('PACKING CHECKLIST', COLOR_PRIMARY)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.multi_cell(0, 5, "Pack smart for your Andalusian adventure! Here's everything you need:")
    pdf.ln(3)
    
    pdf.section_title('Clothing', COLOR_PRIMARY)
    pdf.ln(1)
    clothing = [
        'Comfortable walking shoes (10-20km per day!)',
        'Sandals or flip-flops for beach/hotel',
        'Light, breathable clothing (cotton/linen)',
        'Light jacket for evenings (even in summer)',
        'Modest clothes for churches (covered shoulders/knees)',
        'Swimsuit for beaches or hotel pools',
        'Hat or cap for sun protection',
    ]
    for item in clothing:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {item}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    pdf.section_title('Essentials', COLOR_PRIMARY)
    pdf.ln(1)
    essentials = [
        'Sunscreen SPF 30+ (Andalusian sun is STRONG!)',
        'Sunglasses with UV protection',
        'Reusable water bottle',
        'Day backpack for sightseeing',
        'Power adapter (Type C/F for Spain)',
        'Portable phone charger',
        'Copy of passport & travel insurance',
        'Prescription meds + basic first aid',
    ]
    for item in essentials:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {item}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    pdf.section_title('Nice to Have', COLOR_PRIMARY)
    pdf.ln(1)
    nice_to_have = [
        'Light rain jacket (spring/fall)',
        'Spanish phrasebook or translation app',
        'Camera with good storage',
        'Smart-casual outfit for nice dinners',
        'Small lock for hotel lockers',
        'Earplugs (Spanish cities = noisy at night!)',
        'Hand sanitizer and wet wipes',
    ]
    for item in nice_to_have:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"- {item}", new_x="LMARGIN", new_y="NEXT")

    # ========================================================================
    # SURVIVAL SPANISH
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('SURVIVAL SPANISH', COLOR_PRIMARY)
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.multi_cell(0, 5, "Basic Spanish will make your trip SO much better! Practice these:")
    pdf.ln(3)
    
    phrases = [
        ('Hola / Buenos dias', 'Hello / Good morning'),
        ('Gracias / Muchas gracias', 'Thank you / Thank you very much'),
        ('Por favor', 'Please'),
        ('De nada', "You're welcome"),
        ('Habla ingles?', 'Do you speak English?'),
        ('No entiendo', "I don't understand"),
        ('Cuanto cuesta?', 'How much does it cost?'),
        ('La cuenta, por favor', 'The bill, please'),
        ('Donde esta...?', 'Where is...?'),
        ('Una mesa para dos', 'A table for two'),
        ('Salud!', 'Cheers!'),
        ('Perdon / Disculpe', 'Excuse me / Sorry'),
        ('Si / No', 'Yes / No'),
        ('Adios / Hasta luego', 'Goodbye / See you later'),
        ('Ayuda!', 'Help!'),
        ('Necesito un medico', 'I need a doctor'),
    ]
    
    for spanish, english in phrases:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(80, 6, spanish)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.cell(0, 6, f"= {english}", new_x="LMARGIN", new_y="NEXT")

    # ========================================================================
    # EMERGENCY CONTACTS
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('EMERGENCY CONTACTS', (220, 53, 69))
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.multi_cell(0, 5, "Save these numbers in your phone BEFORE you travel!")
    pdf.ln(3)
    
    emergencies = [
        ('ALL EMERGENCIES (EU-wide)', '112', 'Police, medical, fire - works everywhere in Europe'),
        ('National Police', '091', 'For crimes, theft, lost documents'),
        ('Medical Emergency', '061', 'Ambulance and medical assistance'),
        ('Fire Department', '080', 'Fire emergencies'),
        ('Local Police', '092', 'Non-emergency local police'),
        ('Tourist Information', '902 200 120', 'Tourism information hotline'),
    ]
    
    for name, number, desc in emergencies:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color((220, 53, 69))
        pdf.cell(0, 6, f"{name}: {number}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, desc, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    
    pdf.ln(3)
    pdf.section_title('Embassy Contacts (Madrid)', COLOR_PRIMARY)
    pdf.ln(1)
    embassies = [
        ('US Embassy', '+34 91 587 2200'),
        ('UK Embassy', '+34 91 714 6300'),
        ('Canadian Embassy', '+34 91 382 8400'),
        ('Australian Embassy', '+34 91 353 6600'),
        ('Irish Embassy', '+34 91 436 4093'),
    ]
    for name, phone in embassies:
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.cell(0, 5, f"{name}: {phone}", new_x="LMARGIN", new_y="NEXT")

    # ========================================================================
    # FINAL PAGE
    # ========================================================================
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 15, 'HAVE AN AMAZING', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 15, 'ADVENTURE!', new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 12)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 8, '"Travel is the only thing you buy that makes you richer."', new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.ln(15)
    pdf.set_font('Helvetica', '', 11)
    pdf.multi_cell(0, 6, "Enjoy every moment in beautiful Andalusia!\nMake memories, take photos, eat tapas, and embrace the adventure.", align='C')
    
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(0, 6, '#AndalusiaRoadTrip #TravelSpain #Wanderlust', new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.ln(15)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(0, 6, 'Generated with love by Your Personal Travel Planner', new_x="LMARGIN", new_y="NEXT", align='C')

    # ========================================================================
    # OUTPUT
    # ========================================================================
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer
