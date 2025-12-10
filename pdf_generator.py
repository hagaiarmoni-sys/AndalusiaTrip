"""
PDF Generator for Andalusia Trip Planner
Converts Word document content to PDF format using reportlab
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, ListFlowable, ListItem, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


def create_styles():
    """Create custom styles for the PDF"""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='TripTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=colors.HexColor('#E74C3C'),
        spaceAfter=20,
        alignment=TA_CENTER
    ))
    
    # Subtitle
    styles.add(ParagraphStyle(
        name='TripSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#7F8C8D'),
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    # Day header
    styles.add(ParagraphStyle(
        name='DayHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2980B9'),
        spaceBefore=20,
        spaceAfter=10,
        borderWidth=1,
        borderColor=colors.HexColor('#3498DB'),
        borderPadding=5
    ))
    
    # City header
    styles.add(ParagraphStyle(
        name='CityHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#27AE60'),
        spaceBefore=15,
        spaceAfter=8
    ))
    
    # POI name
    styles.add(ParagraphStyle(
        name='POIName',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#2C3E50'),
        fontName='Helvetica-Bold',
        spaceBefore=8,
        spaceAfter=4
    ))
    
    # POI description
    styles.add(ParagraphStyle(
        name='POIDesc',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=6,
        alignment=TA_JUSTIFY
    ))
    
    # Tip style
    styles.add(ParagraphStyle(
        name='Tip',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#8E44AD'),
        leftIndent=20,
        spaceBefore=4,
        spaceAfter=4
    ))
    
    # Hotel style
    styles.add(ParagraphStyle(
        name='Hotel',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#E67E22'),
        spaceBefore=10,
        spaceAfter=5
    ))
    
    # Restaurant style
    styles.add(ParagraphStyle(
        name='Restaurant',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#16A085'),
        spaceBefore=5,
        spaceAfter=5
    ))
    
    return styles


def build_pdf(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, parsed_requests, is_car_mode=False, result=None):
    """
    Build a PDF travel document
    
    Args:
        itinerary: List of day dictionaries
        hop_kms: Distance data between cities
        maps_link: Google Maps link
        ordered_cities: List of cities in order
        days: Number of days
        prefs: User preferences
        parsed_requests: Parsed special requests
        is_car_mode: Whether this is a car trip
        result: Full result dictionary
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = create_styles()
    story = []
    
    # === COVER PAGE ===
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("🌍 ANDALUSIA", styles['TripTitle']))
    story.append(Paragraph("Road Trip Itinerary", styles['TripTitle']))
    story.append(Spacer(1, 0.5*inch))
    
    # Trip summary
    route_str = " → ".join(ordered_cities) if ordered_cities else "Custom Route"
    story.append(Paragraph(f"📍 {route_str}", styles['TripSubtitle']))
    story.append(Paragraph(f"📅 {days} Days", styles['TripSubtitle']))
    
    # Get dates if available
    if result and result.get('start_date'):
        start_date = result['start_date']
        if hasattr(start_date, 'strftime'):
            story.append(Paragraph(f"🗓️ {start_date.strftime('%B %d, %Y')}", styles['TripSubtitle']))
    
    story.append(Spacer(1, 1*inch))
    story.append(Paragraph("Your personalized travel guide", styles['TripSubtitle']))
    story.append(PageBreak())
    
    # === ITINERARY PAGES ===
    for day_data in itinerary:
        day_num = day_data.get('day', '?')
        city = day_data.get('city', 'Unknown')
        date_str = ""
        
        if day_data.get('date'):
            date_obj = day_data['date']
            if hasattr(date_obj, 'strftime'):
                date_str = f" - {date_obj.strftime('%A, %B %d')}"
        
        # Day header
        story.append(Paragraph(f"📅 Day {day_num}{date_str}", styles['DayHeader']))
        story.append(Paragraph(f"📍 {city}", styles['CityHeader']))
        
        # Horizontal line
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#BDC3C7')))
        story.append(Spacer(1, 0.2*inch))
        
        # POIs/Attractions
        cities_data = day_data.get('cities', [])
        for city_info in cities_data:
            attractions = city_info.get('attractions', [])
            
            if attractions:
                story.append(Paragraph("🎯 <b>Today's Highlights</b>", styles['CityHeader']))
                
                for idx, poi in enumerate(attractions, 1):
                    poi_name = poi.get('name', 'Unknown')
                    poi_desc = poi.get('description', '')
                    poi_rating = poi.get('rating', '')
                    poi_category = poi.get('category', '')
                    
                    # POI name with number
                    name_text = f"{idx}. {poi_name}"
                    if poi_rating:
                        name_text += f" ⭐ {poi_rating}"
                    story.append(Paragraph(name_text, styles['POIName']))
                    
                    # Description
                    if poi_desc:
                        # Truncate long descriptions
                        if len(poi_desc) > 300:
                            poi_desc = poi_desc[:300] + "..."
                        story.append(Paragraph(poi_desc, styles['POIDesc']))
                    
                    # Category
                    if poi_category:
                        story.append(Paragraph(f"🏷️ {poi_category}", styles['Tip']))
        
        # Hotels
        hotels = day_data.get('hotels', [])
        overnight_city = day_data.get('overnight_city', city)
        
        if hotels:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(f"🏨 <b>Stay in {overnight_city}</b>", styles['Hotel']))
            
            for hotel in hotels[:2]:  # Show top 2 hotels
                hotel_name = hotel.get('name', 'Hotel')
                hotel_rating = hotel.get('rating', '')
                rating_str = f" ⭐ {hotel_rating}" if hotel_rating else ""
                story.append(Paragraph(f"• {hotel_name}{rating_str}", styles['POIDesc']))
        
        # Restaurants
        lunch = day_data.get('lunch_restaurant')
        dinner = day_data.get('dinner_restaurant')
        
        if lunch or dinner:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("🍽️ <b>Where to Eat</b>", styles['Restaurant']))
            
            if lunch and isinstance(lunch, dict):
                lunch_name = lunch.get('name', 'Local restaurant')
                story.append(Paragraph(f"☀️ Lunch: {lunch_name}", styles['POIDesc']))
            
            if dinner and isinstance(dinner, dict):
                dinner_name = dinner.get('name', 'Local restaurant')
                story.append(Paragraph(f"🌙 Dinner: {dinner_name}", styles['POIDesc']))
        
        # Route stops (hidden gems between cities)
        route_stops = day_data.get('route_stops', [])
        if route_stops:
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph("🛣️ <b>Stops Along the Way</b>", styles['CityHeader']))
            
            for stop in route_stops:
                stop_name = stop.get('name', 'Stop')
                stop_highlight = stop.get('highlight', '')
                story.append(Paragraph(f"• {stop_name}: {stop_highlight}", styles['POIDesc']))
        
        story.append(PageBreak())
    
    # === PRACTICAL INFO PAGE ===
    story.append(Paragraph("📋 Practical Information", styles['TripTitle']))
    story.append(Spacer(1, 0.3*inch))
    
    # Google Maps link
    if maps_link:
        story.append(Paragraph("🗺️ <b>Full Route Map</b>", styles['CityHeader']))
        story.append(Paragraph(f"<link href='{maps_link}'>Click here to open in Google Maps</link>", styles['POIDesc']))
        story.append(Spacer(1, 0.2*inch))
    
    # Distances
    if hop_kms and ordered_cities and len(ordered_cities) > 1:
        story.append(Paragraph("📏 <b>Driving Distances</b>", styles['CityHeader']))
        for i, km in enumerate(hop_kms):
            if i < len(ordered_cities) - 1 and km is not None:
                from_city = ordered_cities[i]
                to_city = ordered_cities[i + 1]
                story.append(Paragraph(f"• {from_city} → {to_city}: {km} km", styles['POIDesc']))
        story.append(Spacer(1, 0.2*inch))
    
    # Tips
    story.append(Paragraph("💡 <b>Travel Tips</b>", styles['CityHeader']))
    tips = [
        "Siesta time (2-5pm): Many shops close, perfect for a long lunch",
        "Dinner starts late: Restaurants fill up after 9pm",
        "Book Alhambra tickets 2-3 months in advance",
        "Carry water: Summer temperatures can exceed 40°C inland",
        "Free tapas: In Granada, you often get a free tapa with drinks"
    ]
    for tip in tips:
        story.append(Paragraph(f"• {tip}", styles['Tip']))
    
    # Footer
    story.append(Spacer(1, 1*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#BDC3C7')))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d')} | Wanderlust Andalusia Trip Planner",
        styles['TripSubtitle']
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


# Alias for compatibility
def build_pdf_doc(*args, **kwargs):
    """Alias for build_pdf"""
    return build_pdf(*args, **kwargs)
