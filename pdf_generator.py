"""
PDF Generator for Andalusia Travel App
Uses fpdf2 for reliable hyperlink support across all platforms.
"""

from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os
from urllib.parse import quote_plus

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_text(text, max_length=200):
    """Truncate text to prevent overflow and clean characters"""
    if not text:
        return ""
    text = str(text)
    # Replace common non-latin-1 characters
    replacements = {
        "'": "'", "–": "-", "—": "-", """: '"', """: '"',
        "…": "...", "•": "*", "→": "->", "←": "<-",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ñ": "n", "ç": "c",
        "°": " degrees",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Encode/decode to strip remaining unhandleable chars
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text


# ============================================================================
# CUSTOM PDF CLASS
# ============================================================================

class TravelPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)
        
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, 'Andalusia Road Trip Planner', align='C')
            self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def chapter_title(self, title, color=(41, 128, 185)):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*color)
        self.multi_cell(0, 10, safe_text(title, 100))
        self.ln(2)
        
    def section_title(self, title, color=(52, 73, 94)):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*color)
        self.multi_cell(0, 8, safe_text(title, 80))
        self.ln(1)
        
    def add_link_cell(self, text, url, color=(41, 128, 185), icon=""):
        """Add clickable hyperlink using write() for proper link support"""
        if not url:
            return
        
        # Icon (if provided)
        if icon:
            self.set_font('Helvetica', '', 10)
            self.set_text_color(0, 0, 0)
            self.write(6, icon + " ")
        
        # Clickable link text - use write() which properly supports links
        self.set_font('Helvetica', 'U', 10)
        self.set_text_color(*color)
        self.write(6, safe_text(text, 70), url)
        self.ln(7)
        self.set_text_color(0, 0, 0)


# ============================================================================
# MAIN BUILDER
# ============================================================================

def build_pdf(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, parsed_requests, is_car_mode=False, result=None):
    pdf = TravelPDF()
    
    # 1. Safe Date Handling
    start_date = None
    if result and result.get('start_date'):
        start_date = result['start_date']
    
    # Ensure start_date is a proper datetime object
    if start_date and isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            start_date = None

    # Get trip type
    trip_type = prefs.get('trip_type', 'Point-to-point') if prefs else 'Point-to-point'
    is_hub_trip = trip_type == 'Star/Hub'

    # ========================================================================
    # COVER PAGE
    # ========================================================================
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, 'ANDALUSIA', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 12, 'ROAD TRIP', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Route cities
    if ordered_cities:
        pdf.set_font('Helvetica', '', 12)
        pdf.set_text_color(52, 73, 94)
        route_text = ' - '.join([safe_text(c, 20) for c in ordered_cities[:8]])
        pdf.cell(0, 8, route_text, align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Duration and dates
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(52, 73, 94)
    pdf.cell(0, 8, f'{days} Days of Adventure', align='C', new_x="LMARGIN", new_y="NEXT")
    
    if start_date:
        try:
            end_date = start_date + timedelta(days=days-1)
            date_str = f"{start_date.strftime('%d %B')} - {end_date.strftime('%d %B %Y')}"
            pdf.set_font('Helvetica', '', 11)
            pdf.cell(0, 8, date_str, align='C', new_x="LMARGIN", new_y="NEXT")
        except:
            pass
    
    pdf.ln(10)
    
    # Full route Google Maps link
    if maps_link:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 8, 'VIEW COMPLETE ROUTE:', align='C', new_x="LMARGIN", new_y="NEXT")
        
        # Center the clickable link
        pdf.set_font('Helvetica', 'U', 10)
        pdf.set_text_color(41, 128, 185)
        link_text = 'Open Full Route in Google Maps'
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
        
        # Calculate date for this day
        current_date_obj = None
        current_date_str = ""
        if start_date:
            try:
                current_date_obj = start_date + timedelta(days=day_num - 1)
                current_date_str = f" - {current_date_obj.strftime('%a, %d %b')}"
            except:
                pass

        # Day header
        pdf.chapter_title(f"DAY {day_num}: {city.upper()}{current_date_str}", (243, 156, 18))
        
        # Day in city info
        day_in_city = day.get('day_in_city', 1)
        total_days_in_city = day.get('total_days_in_city', 1)
        if total_days_in_city > 1:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(127, 140, 141)
            pdf.cell(0, 5, f'Day {day_in_city} of {total_days_in_city} in {city}', new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(3)
        
        # ---------------------------------------------------------
        # FIX #1: Daily Google Maps Link - use the one from itinerary
        # ---------------------------------------------------------
        day_map_url = day.get('google_maps_url')
        if day_map_url:
            pdf.add_link_cell("Open Today's Route in Google Maps", day_map_url)
            pdf.ln(2)
        
        # ---------------------------------------------------------
        # FIX #3: YouTube Video Link - make it clickable
        # ---------------------------------------------------------
        if day_in_city == 1:
            video_added = False
            try:
                from youtube_helper import get_video_for_city
                videos = get_video_for_city(city, max_videos=1)
                if videos and len(videos) > 0:
                    video = videos[0]
                    video_title = safe_text(video.get('title', f'{city} Travel Guide'), 50)
                    video_url = video.get('watch_url', '')
                    if video_url:
                        pdf.add_link_cell(f"Watch: {video_title}", video_url)
                        video_added = True
            except Exception as e:
                pass
            
            # Fallback: YouTube search link if no video found
            if not video_added:
                query = quote_plus(f"{city} Spain travel guide 4K")
                fallback_url = f"https://www.youtube.com/results?search_query={query}"
                pdf.add_link_cell(f"Watch {city} Travel Videos on YouTube", fallback_url)
            
            pdf.ln(2)

        # ---------------------------------------------------------
        # ATTRACTIONS
        # ---------------------------------------------------------
        cities_data = day.get('cities', [])
        if not cities_data:
            cities_data = [{'city': city, 'attractions': day.get('attractions', [])}]
        
        for city_stop in cities_data:
            attractions = city_stop.get('attractions', [])
            if attractions:
                pdf.section_title("TODAY'S HIGHLIGHTS", (155, 89, 182))
                pdf.ln(1)
                
                for idx, attr in enumerate(attractions[:8], 1):
                    attr_name = safe_text(attr.get('name', 'Attraction'), 60)
                    
                    # Attraction name
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(44, 62, 80)
                    pdf.cell(0, 7, f'{idx}. {attr_name}', new_x="LMARGIN", new_y="NEXT")
                    
                    # Description
                    description = attr.get('description', '')
                    if description:
                        pdf.set_font('Helvetica', '', 9)
                        pdf.set_text_color(52, 73, 94)
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.multi_cell(0, 5, safe_text(description, 250))
                    
                    # Details line
                    details = []
                    rating = attr.get('rating')
                    if rating:
                        details.append(f'Rating: {rating}')
                    category = attr.get('category', '')
                    if category:
                        details.append(safe_text(category.title(), 20))
                    
                    if details:
                        pdf.set_font('Helvetica', 'I', 8)
                        pdf.set_text_color(127, 140, 141)
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.cell(0, 5, ' | '.join(details), new_x="LMARGIN", new_y="NEXT")
                    
                    # Google Maps link for attraction
                    lat = attr.get('lat')
                    lon = attr.get('lon') or attr.get('lng')
                    if lat and lon:
                        attr_map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.add_link_cell('View on Google Maps', attr_map_url)
                    
                    pdf.ln(2)

        # ---------------------------------------------------------
        # FIX #2: Hotels with Correct Dates
        # ---------------------------------------------------------
        hotels = day.get('hotels', [])
        if hotels and day_in_city == 1 and not is_hub_trip:
            pdf.ln(3)
            pdf.section_title(f'WHERE TO STAY', (46, 204, 113))
            pdf.ln(1)
            
            # Calculate nights
            nights = total_days_in_city
            
            # Calculate check-in/check-out dates
            checkin_str = ""
            checkout_str = ""
            if current_date_obj:
                try:
                    checkout_date = current_date_obj + timedelta(days=nights)
                    checkin_str = current_date_obj.strftime('%Y-%m-%d')
                    checkout_str = checkout_date.strftime('%Y-%m-%d')
                except:
                    pass
            
            for hotel in hotels[:3]:
                hotel_name = safe_text(hotel.get('name', 'Hotel'), 50)
                if 'Hotels in' in hotel_name:
                    continue
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(44, 62, 80)
                pdf.cell(0, 6, f'* {hotel_name}', new_x="LMARGIN", new_y="NEXT")
                
                # Address
                address = hotel.get('address', '')
                if address:
                    pdf.set_font('Helvetica', 'I', 8)
                    pdf.set_text_color(127, 140, 141)
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.cell(0, 5, safe_text(address, 60), new_x="LMARGIN", new_y="NEXT")
                
                # Booking link with dates
                hotel_search = quote_plus(f"{hotel.get('name', '')} {overnight}"[:60])
                if checkin_str and checkout_str:
                    booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}&checkin={checkin_str}&checkout={checkout_str}"
                else:
                    booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}"
                
                pdf.set_x(pdf.get_x() + 5)
                pdf.add_link_cell('Book on Booking.com', booking_url)
                pdf.ln(1)

        # ---------------------------------------------------------
        # RESTAURANTS
        # ---------------------------------------------------------
        lunch = day.get('lunch_restaurant')
        dinner = day.get('dinner_restaurant')
        
        if lunch or dinner:
            pdf.ln(3)
            pdf.section_title('WHERE TO EAT', (230, 126, 34))
            pdf.ln(1)
            
            for meal_type, restaurant in [('Lunch', lunch), ('Dinner', dinner)]:
                if restaurant:
                    rest_name = safe_text(restaurant.get('name', 'Restaurant'), 50)
                    
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.set_text_color(44, 62, 80)
                    pdf.cell(0, 6, f'{meal_type}: {rest_name}', new_x="LMARGIN", new_y="NEXT")
                    
                    # Google Maps link
                    lat = restaurant.get('lat')
                    lon = restaurant.get('lon') or restaurant.get('lng')
                    if lat and lon:
                        rest_map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.add_link_cell('View on Google Maps', rest_map_url)
                    
                    pdf.ln(1)

    # ========================================================================
    # TRAVEL TIPS PAGE
    # ========================================================================
    pdf.add_page()
    pdf.chapter_title('ESSENTIAL TRAVEL TIPS', (52, 152, 219))
    pdf.ln(3)
    
    tips = [
        ('Spanish Schedule', 'Lunch 2-4pm, Dinner 9pm+. Many restaurants closed 4-8pm.'),
        ('Book Ahead', 'Alhambra, Alcazar, Cathedral tours need advance booking!'),
        ('Cash is King', 'Small towns and tapas bars often prefer cash.'),
        ('Free Tapas', 'In Granada, many bars give FREE tapas with drinks!'),
        ('Monday Closures', 'Many museums closed Mondays.'),
        ('Summer Heat', 'June-August can reach 40C+. Plan indoor activities for midday.'),
    ]
    
    for title, desc in tips:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(41, 128, 185)
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(52, 73, 94)
        pdf.set_x(pdf.get_x() + 5)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(2)

    # ========================================================================
    # OUTPUT
    # ========================================================================
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer
