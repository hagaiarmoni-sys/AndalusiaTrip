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
# CUSTOM PDF CLASS WITH STYLING
# ============================================================================

class TravelPDF(FPDF):
    """Custom PDF class with travel document styling"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        """Page header"""
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
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        
    def section_title(self, title, color=(52, 73, 94)):
        """Add a styled section title"""
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*color)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        
    def body_text(self, text):
        """Add body text"""
        self.set_font('Helvetica', '', 10)
        self.set_text_color(52, 73, 94)
        self.multi_cell(0, 6, text)
        self.ln(2)
        
    def add_link_text(self, text, url, color=(41, 128, 185)):
        """Add clickable hyperlink"""
        self.set_font('Helvetica', 'U', 10)
        self.set_text_color(*color)
        self.cell(0, 6, text, link=url, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)  # Reset color
        
    def add_bullet(self, text, indent=10):
        """Add a bullet point"""
        self.set_font('Helvetica', '', 10)
        self.set_text_color(52, 73, 94)
        self.set_x(self.get_x() + indent)
        self.cell(5, 6, chr(149))  # Bullet character
        self.multi_cell(0, 6, text)


# ============================================================================
# MAIN PDF BUILDER
# ============================================================================

def build_pdf(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, parsed_requests, is_car_mode=False, result=None):
    """
    Build a travel PDF document with working hyperlinks
    
    Args:
        itinerary: List of day dictionaries
        hop_kms: List of distances between cities
        maps_link: Google Maps route URL
        ordered_cities: List of cities in order
        days: Number of trip days
        prefs: User preferences dict
        parsed_requests: Parsed special requests
        is_car_mode: Whether this is a car trip
        result: Full result dict (for hub trips)
    
    Returns:
        BytesIO buffer containing the PDF
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
        route_text = ' -> '.join(ordered_cities)
        pdf.multi_cell(0, 8, route_text, align='C')
    
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
    
    pdf.ln(20)
    
    # Google Maps link
    if maps_link:
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 8, 'VIEW COMPLETE ROUTE:', align='C', new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font('Helvetica', 'U', 10)
        pdf.set_text_color(41, 128, 185)
        # Center the link
        link_text = 'Open in Google Maps'
        link_width = pdf.get_string_width(link_text)
        pdf.set_x((210 - link_width) / 2)
        pdf.cell(link_width, 8, link_text, link=maps_link, new_x="LMARGIN", new_y="NEXT")
    
    # ========================================================================
    # TRIP OVERVIEW
    # ========================================================================
    
    pdf.add_page()
    pdf.chapter_title('TRIP OVERVIEW', (52, 152, 219))
    pdf.ln(5)
    
    # Trip type
    pdf.section_title(f'Trip Type: {trip_type}')
    pdf.ln(3)
    
    # Route summary
    if hop_kms and len(hop_kms) > 0:
        total_km = sum(hop_kms)
        pdf.body_text(f'Total driving distance: {total_km:.0f} km')
        
        # City by city distances
        if len(ordered_cities) > 1:
            pdf.section_title('Driving Distances:')
            for i, km in enumerate(hop_kms):
                if i < len(ordered_cities) - 1:
                    pdf.add_bullet(f'{ordered_cities[i]} to {ordered_cities[i+1]}: {km:.0f} km')
    
    pdf.ln(5)
    
    # ========================================================================
    # HUB TRIP HOTELS (if applicable)
    # ========================================================================
    
    if is_hub_trip and result:
        base_city = result.get('base_city', '')
        base_hotels = result.get('base_hotels', [])
        
        if base_city and base_hotels:
            pdf.section_title(f'Your Base: {base_city}', (46, 204, 113))
            pdf.ln(3)
            
            for hotel in base_hotels[:3]:
                hotel_name = hotel.get('name', 'Hotel')
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(44, 62, 80)
                pdf.cell(0, 6, f'* {hotel_name}', new_x="LMARGIN", new_y="NEXT")
                
                # Booking link
                from urllib.parse import quote_plus
                hotel_search = quote_plus(f"{hotel_name} {base_city}")
                booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}"
                
                pdf.set_x(pdf.get_x() + 10)
                pdf.set_font('Helvetica', 'U', 9)
                pdf.set_text_color(41, 128, 185)
                pdf.cell(0, 5, 'Book on Booking.com', link=booking_url, new_x="LMARGIN", new_y="NEXT")
            
            pdf.ln(5)
    
    # ========================================================================
    # DAILY ITINERARY
    # ========================================================================
    
    for day in itinerary:
        pdf.add_page()
        
        day_num = day.get('day', 0)
        city = day.get('city', 'Unknown')
        overnight = day.get('overnight_city', city)
        
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
        
        pdf.ln(3)
        
        # Google Maps link for the day
        day_map_url = day.get('google_maps_url')
        if day_map_url:
            pdf.set_font('Helvetica', 'U', 9)
            pdf.set_text_color(41, 128, 185)
            pdf.cell(0, 5, "Today's Route on Google Maps", link=day_map_url, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        
        # ====================================================================
        # ATTRACTIONS
        # ====================================================================
        
        cities_data = day.get('cities', [])
        if not cities_data:
            # Fallback for simpler structure
            cities_data = [{'city': city, 'attractions': day.get('attractions', [])}]
        
        for city_stop in cities_data:
            attractions = city_stop.get('attractions', [])
            
            if attractions:
                pdf.section_title("TODAY'S HIGHLIGHTS", (155, 89, 182))
                pdf.ln(2)
                
                for idx, attr in enumerate(attractions, 1):
                    attr_name = attr.get('name', 'Attraction')
                    
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
                        pdf.multi_cell(0, 5, description[:300] + ('...' if len(description) > 300 else ''))
                    
                    # Details line
                    details = []
                    rating = attr.get('rating')
                    if rating:
                        details.append(f'Rating: {rating}')
                    
                    duration = attr.get('recommended_duration') or attr.get('duration')
                    if duration:
                        details.append(f'Duration: {duration}')
                    
                    category = attr.get('category', '')
                    if category:
                        details.append(category.title())
                    
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
                        pdf.set_font('Helvetica', 'U', 8)
                        pdf.set_text_color(41, 128, 185)
                        pdf.cell(0, 5, 'View on Google Maps', link=attr_map_url, new_x="LMARGIN", new_y="NEXT")
                    
                    pdf.ln(3)
        
        # ====================================================================
        # HOTELS
        # ====================================================================
        
        hotels = day.get('hotels', [])
        if hotels and day_in_city == 1 and not is_hub_trip:
            pdf.ln(3)
            pdf.section_title(f'WHERE TO STAY IN {overnight.upper()}', (46, 204, 113))
            pdf.ln(2)
            
            # Calculate nights
            nights = total_days_in_city
            
            for hotel in hotels[:3]:
                hotel_name = hotel.get('name', 'Hotel')
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
                    pdf.cell(0, 5, address, new_x="LMARGIN", new_y="NEXT")
                
                # Booking link with dates
                from urllib.parse import quote_plus
                hotel_search = quote_plus(f"{hotel_name} {overnight}")
                
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
                pdf.set_font('Helvetica', 'U', 9)
                pdf.set_text_color(41, 128, 185)
                pdf.cell(0, 5, 'Book on Booking.com', link=booking_url, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
        
        # ====================================================================
        # RESTAURANTS
        # ====================================================================
        
        lunch = day.get('lunch_restaurant')
        dinner = day.get('dinner_restaurant')
        
        if lunch or dinner:
            pdf.ln(3)
            pdf.section_title('WHERE TO EAT', (230, 126, 34))
            pdf.ln(2)
            
            for meal_type, restaurant in [('Lunch', lunch), ('Dinner', dinner)]:
                if restaurant:
                    rest_name = restaurant.get('name', 'Restaurant')
                    
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.set_text_color(44, 62, 80)
                    pdf.cell(0, 6, f'{meal_type}: {rest_name}', new_x="LMARGIN", new_y="NEXT")
                    
                    # Address
                    address = restaurant.get('address', '')
                    if address:
                        pdf.set_font('Helvetica', 'I', 8)
                        pdf.set_text_color(127, 140, 141)
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.cell(0, 5, address, new_x="LMARGIN", new_y="NEXT")
                    
                    # Google Maps link
                    lat = restaurant.get('lat')
                    lon = restaurant.get('lon') or restaurant.get('lng')
                    if lat and lon:
                        rest_map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.set_font('Helvetica', 'U', 8)
                        pdf.set_text_color(41, 128, 185)
                        pdf.cell(0, 5, 'View on Google Maps', link=rest_map_url, new_x="LMARGIN", new_y="NEXT")
                    
                    pdf.ln(2)
    
    # ========================================================================
    # TRAVEL TIPS PAGE
    # ========================================================================
    
    pdf.add_page()
    pdf.chapter_title('ESSENTIAL TRAVEL TIPS', (52, 152, 219))
    pdf.ln(5)
    
    tips = [
        ('Spanish Schedule', 'Lunch 2-4pm, Dinner 9pm+. Many restaurants closed 4-8pm.'),
        ('Book Ahead', 'Alhambra, Alcazar, Cathedral tours need 2-3 weeks advance booking!'),
        ('Cash is King', 'Small towns, markets, and tapas bars often prefer cash.'),
        ('Free Tapas', 'In Granada, many bars give FREE tapas with drinks!'),
        ('Monday Closures', 'Many museums closed Mondays - plan accordingly.'),
        ('Summer Heat', 'June-August can reach 40C+. Plan indoor activities for midday.'),
        ('Siesta Time', 'Small shops close 2-5pm (tourist areas stay open).'),
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
    
    # Return as BytesIO buffer
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    
    return pdf_buffer


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test the PDF generator
    test_itinerary = [
        {
            'day': 1,
            'city': 'Malaga',
            'overnight_city': 'Malaga',
            'day_in_city': 1,
            'total_days_in_city': 2,
            'cities': [{
                'city': 'Malaga',
                'attractions': [
                    {'name': 'Alcazaba', 'description': 'Moorish fortress', 'rating': 4.6, 'lat': 36.7213, 'lon': -4.4167},
                    {'name': 'Picasso Museum', 'description': 'Art museum', 'rating': 4.5, 'lat': 36.7215, 'lon': -4.4180},
                ]
            }],
            'hotels': [{'name': 'Hotel Molina Lario', 'address': 'Calle Molina Lario 22'}],
        }
    ]
    
    pdf_buffer = build_pdf(
        itinerary=test_itinerary,
        hop_kms=[150, 200],
        maps_link='https://maps.google.com',
        ordered_cities=['Malaga', 'Granada', 'Seville'],
        days=7,
        prefs={'trip_type': 'Point-to-point'},
        parsed_requests={},
        result={'start_date': datetime.now()}
    )
    
    with open('test_trip.pdf', 'wb') as f:
        f.write(pdf_buffer.read())
    
    print("Test PDF generated: test_trip.pdf")
