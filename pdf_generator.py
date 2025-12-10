"""
PDF Generator for Andalusia Travel App
Uses fpdf2 for reliable hyperlink support across all platforms

This replaces LibreOffice conversion which doesn't preserve hyperlinks on Streamlit Cloud.
"""

from fpdf import FPDF
from datetime import datetime, timedelta
import os
import io

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_text(text, max_length=200):
    """Truncate text to prevent overflow and remove problematic characters"""
    if not text:
        return ""
    # Convert to string and clean
    text = str(text)
    # Remove or replace problematic characters
    text = text.encode('latin-1', errors='replace').decode('latin-1')
    # Truncate if too long
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

def safe_url(url):
    """Ensure URL is valid"""
    if not url:
        return ""
    url = str(url)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


# ============================================================================
# CUSTOM PDF CLASS WITH STYLING
# ============================================================================

class TravelPDF(FPDF):
    """Custom PDF class with travel document styling"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)  # left, top, right margins
        
    def header(self):
        """Page header"""
        if self.page_no() > 1:  # Skip header on cover page
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, 'Andalusia Road Trip Planner', align='C')
            self.ln(5)
        
    def footer(self):
        """Page footer with page number"""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def chapter_title(self, title, color=(41, 128, 185)):
        """Add a styled chapter title"""
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*color)
        self.multi_cell(0, 10, safe_text(title, 100))
        self.ln(2)
        
    def section_title(self, title, color=(52, 73, 94)):
        """Add a styled section title"""
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*color)
        self.multi_cell(0, 8, safe_text(title, 80))
        self.ln(1)
        
    def body_text(self, text):
        """Add body text"""
        if not text:
            return
        self.set_font('Helvetica', '', 10)
        self.set_text_color(52, 73, 94)
        self.multi_cell(0, 6, safe_text(text, 500))
        self.ln(2)
        
    def add_link_cell(self, text, url, color=(41, 128, 185)):
        """Add clickable hyperlink that handles long text"""
        if not url:
            return
        self.set_font('Helvetica', 'U', 9)
        self.set_text_color(*color)
        display_text = safe_text(text, 60)
        self.cell(0, 6, display_text, link=safe_url(url), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)


# ============================================================================
# MAIN PDF BUILDER
# ============================================================================

def build_pdf(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, parsed_requests, is_car_mode=False, result=None):
    """
    Build a travel PDF document with working hyperlinks
    """
    
    pdf = TravelPDF()
    
    # Get start date
    start_date = None
    try:
        if result and result.get('start_date'):
            start_date = result['start_date']
    except:
        pass
    
    # Get trip type
    trip_type = prefs.get('trip_type', 'Point-to-point') if prefs else 'Point-to-point'
    is_hub_trip = trip_type == 'Star/Hub'
    
    # ========================================================================
    # COVER PAGE
    # ========================================================================
    
    pdf.add_page()
    pdf.ln(30)
    
    # Title
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 15, 'ANDALUSIA', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 12, 'ROAD TRIP', align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Trip details
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(52, 73, 94)
    
    # Cities
    if ordered_cities:
        route_text = ' - '.join([safe_text(c, 20) for c in ordered_cities[:6]])
        if len(ordered_cities) > 6:
            route_text += '...'
        pdf.cell(0, 8, route_text, align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Duration
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f'{days} Days of Adventure', align='C', new_x="LMARGIN", new_y="NEXT")
    
    # Dates
    if start_date:
        try:
            if hasattr(start_date, 'strftime'):
                end_date = start_date + timedelta(days=days-1)
                date_str = f"{start_date.strftime('%d %B')} - {end_date.strftime('%d %B %Y')}"
                pdf.set_font('Helvetica', '', 11)
                pdf.cell(0, 8, date_str, align='C', new_x="LMARGIN", new_y="NEXT")
        except:
            pass
    
    pdf.ln(15)
    
    # Google Maps link
    if maps_link:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 8, 'VIEW COMPLETE ROUTE:', align='C', new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', 'U', 10)
        pdf.set_text_color(41, 128, 185)
        link_text = 'Open in Google Maps'
        link_width = pdf.get_string_width(link_text) + 10
        pdf.set_x((210 - link_width) / 2)
        pdf.cell(link_width, 8, link_text, link=safe_url(maps_link), align='C', new_x="LMARGIN", new_y="NEXT")
    
    # ========================================================================
    # TRIP OVERVIEW
    # ========================================================================
    
    pdf.add_page()
    pdf.chapter_title('TRIP OVERVIEW', (52, 152, 219))
    pdf.ln(3)
    
    # Trip type
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(52, 73, 94)
    pdf.cell(0, 7, f'Trip Type: {trip_type}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    # Route summary
    if hop_kms and len(hop_kms) > 0:
        total_km = sum(hop_kms)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Total driving distance: {total_km:.0f} km', new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        
        # City by city distances
        if len(ordered_cities) > 1 and len(hop_kms) > 0:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(0, 6, 'Driving Distances:', new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 9)
            for i, km in enumerate(hop_kms):
                if i < len(ordered_cities) - 1:
                    city_from = safe_text(ordered_cities[i], 25)
                    city_to = safe_text(ordered_cities[i+1], 25)
                    pdf.cell(0, 5, f'  * {city_from} to {city_to}: {km:.0f} km', new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # ========================================================================
    # HUB TRIP HOTELS
    # ========================================================================
    
    if is_hub_trip and result:
        base_city = result.get('base_city', '')
        base_hotels = result.get('base_hotels', [])
        
        if base_city and base_hotels:
            pdf.section_title(f'Your Base: {safe_text(base_city, 30)}', (46, 204, 113))
            pdf.ln(2)
            
            for hotel in base_hotels[:3]:
                hotel_name = safe_text(hotel.get('name', 'Hotel'), 50)
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(44, 62, 80)
                pdf.cell(0, 6, f'* {hotel_name}', new_x="LMARGIN", new_y="NEXT")
                
                # Booking link
                from urllib.parse import quote_plus
                hotel_search = quote_plus(f"{hotel.get('name', '')} {base_city}"[:50])
                booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}"
                
                pdf.set_x(pdf.get_x() + 8)
                pdf.add_link_cell('Book on Booking.com', booking_url)
            
            pdf.ln(3)
    
    # ========================================================================
    # DAILY ITINERARY
    # ========================================================================
    
    for day in itinerary:
        pdf.add_page()
        
        day_num = day.get('day', 0)
        city = safe_text(day.get('city', 'Unknown'), 30)
        overnight = safe_text(day.get('overnight_city', city), 30)
        
        # Day header
        day_title = f'DAY {day_num}: {city.upper()}'
        if start_date and hasattr(start_date, 'strftime'):
            try:
                day_date = start_date + timedelta(days=day_num - 1)
                day_title = f'DAY {day_num}: {day_date.strftime("%a, %d %b")} - {city.upper()}'
            except:
                pass
        
        pdf.chapter_title(day_title, (243, 156, 18))
        
        # Day in city info
        day_in_city = day.get('day_in_city', 1)
        total_days_in_city = day.get('total_days_in_city', 1)
        if total_days_in_city > 1:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(127, 140, 141)
            pdf.cell(0, 5, f'Day {day_in_city} of {total_days_in_city} in {city}', new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(2)
        
        # Google Maps link for the day
        day_map_url = day.get('google_maps_url')
        if day_map_url:
            pdf.add_link_cell("Today's Route on Google Maps", day_map_url)
            pdf.ln(2)
        
        # ====================================================================
        # ATTRACTIONS
        # ====================================================================
        
        cities_data = day.get('cities', [])
        if not cities_data:
            cities_data = [{'city': city, 'attractions': day.get('attractions', [])}]
        
        for city_stop in cities_data:
            attractions = city_stop.get('attractions', [])
            
            if attractions:
                pdf.section_title("TODAY'S HIGHLIGHTS", (155, 89, 182))
                pdf.ln(1)
                
                for idx, attr in enumerate(attractions[:8], 1):  # Limit to 8 attractions
                    attr_name = safe_text(attr.get('name', 'Attraction'), 60)
                    
                    # Attraction name
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(44, 62, 80)
                    pdf.cell(0, 7, f'{idx}. {attr_name}', new_x="LMARGIN", new_y="NEXT")
                    
                    # Description (shortened)
                    description = attr.get('description', '')
                    if description:
                        pdf.set_font('Helvetica', '', 9)
                        pdf.set_text_color(52, 73, 94)
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.multi_cell(0, 5, safe_text(description, 200))
                    
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
                    
                    # Google Maps link
                    lat = attr.get('lat')
                    lon = attr.get('lon') or attr.get('lng')
                    if lat and lon:
                        attr_map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.add_link_cell('View on Google Maps', attr_map_url)
                    
                    pdf.ln(2)
        
        # ====================================================================
        # HOTELS
        # ====================================================================
        
        hotels = day.get('hotels', [])
        if hotels and day_in_city == 1 and not is_hub_trip:
            pdf.ln(2)
            pdf.section_title(f'WHERE TO STAY', (46, 204, 113))
            pdf.ln(1)
            
            nights = total_days_in_city
            
            for hotel in hotels[:3]:
                hotel_name = safe_text(hotel.get('name', 'Hotel'), 50)
                if 'Hotels in' in hotel_name:
                    continue
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(44, 62, 80)
                pdf.cell(0, 6, f'* {hotel_name}', new_x="LMARGIN", new_y="NEXT")
                
                # Booking link with dates
                from urllib.parse import quote_plus
                hotel_search = quote_plus(f"{hotel.get('name', '')} {overnight}"[:50])
                
                if start_date and hasattr(start_date, 'strftime'):
                    try:
                        checkin = start_date + timedelta(days=day_num - 1)
                        checkout = checkin + timedelta(days=nights)
                        checkin_str = checkin.strftime('%Y-%m-%d')
                        checkout_str = checkout.strftime('%Y-%m-%d')
                        booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}&checkin={checkin_str}&checkout={checkout_str}"
                    except:
                        booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}"
                else:
                    booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}"
                
                pdf.set_x(pdf.get_x() + 5)
                pdf.add_link_cell('Book on Booking.com', booking_url)
                pdf.ln(1)
        
        # ====================================================================
        # RESTAURANTS
        # ====================================================================
        
        lunch = day.get('lunch_restaurant')
        dinner = day.get('dinner_restaurant')
        
        if lunch or dinner:
            pdf.ln(2)
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

