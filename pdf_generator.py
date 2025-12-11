"""
Advanced PDF Generator for Andalusia Travel App
Features: Photos, Colors, Hyperlinks, styled like the Word document
"""

from fpdf import FPDF
from datetime import datetime, timedelta
import os
import io
from urllib.parse import quote_plus

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
    
    # Date handling
    start_date = None
    if result and result.get('start_date'):
        start_date = result['start_date']
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except:
                start_date = None

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
        
        # Day in city info
        if total_days_in_city > 1:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(*COLOR_LIGHT)
            pdf.cell(0, 5, f'Day {day_in_city} of {total_days_in_city} in {city}', new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # ---------------------------------------------------------
        # Daily Google Maps Link (from itinerary)
        # ---------------------------------------------------------
        day_map_url = day.get('google_maps_url')
        if day_map_url:
            pdf.add_link("Open Today's Route in Google Maps", day_map_url, COLOR_PRIMARY)
        
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

        pdf.ln(3)

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
        # EVENTS (if any for this day)
        # ---------------------------------------------------------
        events = day.get('events', [])
        if events:
            pdf.ln(3)
            pdf.section_title('EVENTS & FESTIVALS', (142, 68, 173))  # Purple
            pdf.ln(1)
            
            for event in events[:3]:
                event_name = safe_text(event.get('name', 'Event'), 50)
                
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
                event_date = event.get('date', '') or event.get('dates', '')
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
                hotel_name = hotel.get('name', 'Hotel')
                if 'Hotels in' in hotel_name:
                    continue
                
                hotel_name_display = safe_text(hotel_name, 50)
                
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
                
                # Booking link with FULL hotel name and city
                hotel_search = quote_plus(f"{hotel_name} {overnight}"[:80])
                if checkin_str and checkout_str:
                    booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}&checkin={checkin_str}&checkout={checkout_str}"
                    link_text = f"Book {hotel_name_display} ({nights} nights)"
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
                    
                    # Google Maps link
                    lat = restaurant.get('lat')
                    lon = restaurant.get('lon') or restaurant.get('lng')
                    if lat and lon:
                        rest_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.add_link('View on Google Maps', rest_url, COLOR_FOOD)
                    
                    pdf.ln(1)

    # ========================================================================
    # TRAVEL TIPS PAGE
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('ESSENTIAL TRAVEL TIPS', COLOR_PRIMARY)
    pdf.ln(3)
    
    tips = [
        ('Spanish Schedule', 'Lunch is typically 2-4pm, Dinner starts at 9pm or later. Many restaurants are closed 4-8pm.'),
        ('Book Ahead', 'Alhambra, Alcazar, and Cathedral tours require advance booking - sometimes 2-3 weeks ahead!'),
        ('Cash is King', 'Small towns, markets, and traditional tapas bars often prefer or only accept cash.'),
        ('Free Tapas', 'In Granada, many bars give you a FREE tapa with every drink you order!'),
        ('Monday Closures', 'Many museums and attractions are closed on Mondays. Plan accordingly.'),
        ('Summer Heat', 'June-August temperatures can exceed 40C. Plan indoor activities for midday hours.'),
        ('Siesta Time', 'Small shops typically close 2-5pm, though tourist areas often stay open.'),
    ]
    
    for title, desc in tips:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_x(pdf.get_x() + 5)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(3)

    # ========================================================================
    # OUTPUT
    # ========================================================================
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer
