import streamlit as st
import pandas as pd
import json
import os
import io
from datetime import datetime, timedelta
from urllib.parse import quote_plus

# ✅ CRITICAL: Use car-based generator
from itinerary_generator_car import generate_simple_trip
from document_generator import build_word_doc
from restaurant_service import get_restaurant_tips
from text_norm import canonicalize_city, norm_key  # ✅ NEW: Import text normalization
from date_picker_system import create_date_picker

# ✅ NEW: Import validation system (optional - comment out if not using)
try:
    from trip_validation_system import validate_all_parameters
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("⚠️ trip_validation_system not found - validation disabled")

# ✅ NEW: Import community itineraries service
try:
    from community_itineraries_service import (
        load_community_itineraries,
        filter_itineraries,
        get_recommended_days_per_city,
        get_recommended_duration,
        validate_trip_duration,
        format_itinerary_summary,
        get_itinerary_by_id,
        get_cities_from_itinerary,
        get_itineraries_stats
    )
    COMMUNITY_ITINERARIES_AVAILABLE = True
    # print("✅ community_itineraries_service imported successfully")
except ImportError as e:
    COMMUNITY_ITINERARIES_AVAILABLE = False
    print(f"⚠️ community_itineraries_service not found: {e}")




# Import events service
try:
    from events_service import get_events_for_trip
    EVENTS_AVAILABLE = True
except ImportError:
    EVENTS_AVAILABLE = False
    print("⚠️ events_service not found - events display disabled")

# ✅ NEW: Import YouTube UI helper
try:
    from youtube_ui import display_video_expander, get_videos_for_city
    YOUTUBE_UI_AVAILABLE = True
    # print("✅ youtube_ui imported successfully")
except ImportError as e:
    YOUTUBE_UI_AVAILABLE = False
    print(f"⚠️ youtube_ui not found - YouTube videos disabled in UI: {e}")

# ✅ Video generator will be imported lazily when needed
VIDEO_GENERATOR_AVAILABLE = None  # Will be set on first use

def get_video_generator():
    """Lazy import of video generator to speed up page load."""
    global VIDEO_GENERATOR_AVAILABLE
    if VIDEO_GENERATOR_AVAILABLE is None:
        try:
            from poi_video_generator import generate_poi_slideshow, SlideshowConfig
            VIDEO_GENERATOR_AVAILABLE = True
            return generate_poi_slideshow, SlideshowConfig
        except ImportError as e:
            VIDEO_GENERATOR_AVAILABLE = False
            print(f"⚠️ poi_video_generator not found: {e}")
            return None, None
    elif VIDEO_GENERATOR_AVAILABLE:
        from poi_video_generator import generate_poi_slideshow, SlideshowConfig
        return generate_poi_slideshow, SlideshowConfig
    else:
        return None, None

# Configuration
TRIPS_DIR = "trips"
os.makedirs(TRIPS_DIR, exist_ok=True)

def add_plan_again_button():
    """
    Add a 'Plan Again' button that clears the itinerary but preserves form values
    """
    st.write("")
    st.write("---")
    
    # Center the button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🔄 Plan Again", type="primary", use_container_width=True, key="plan_again_btn"):
            # Clear only the result-related session state, keep form values
            keys_to_clear = [
                'current_trip_result',
                'current_trip_prefs',
                'current_trip_days',
                'form_submitted',
                'selected_community_itinerary'
                # ✅ NOTE: Don't clear 'form_data' - preserve user's input
            ]
            
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Success message
            st.success("✅ Ready to plan a new trip!")
            
            # Rerun to refresh the page
            st.rerun()

POI_CATEGORIES = [
    "art", "museums", "history", "architecture", "parks", "nature",
    "gardens", "beaches", "viewpoints", "markets", "religious", "castles",
    "palaces", "neighborhoods", "food & tapas", "wine & bodegas",
    "music & flamenco"
]

def calculate_driving_time(distance_km):
    """Calculate driving time"""
    if distance_km < 30:
        return distance_km / 40 + 0.25
    elif distance_km < 100:
        return distance_km / 70 + 0.25
    else:
        return distance_km / 100 + 0.75

def load_prefs():
    default = {
        "default_trip_type": "Point-to-point",  # Can be Point-to-point, Circular, or Star/Hub
        "default_budget": "mid-range",
        "default_pace": "medium",
        "max_km_per_day": 200,
        "poi_categories": ["history", "architecture", "museums", "parks"],
        "hotel_platform": "Any",
        "max_price_per_night": 150,
        "min_poi_rating": 0.0,
        "max_same_category_per_day": 2
    }
    try:
        if os.path.exists("preferences.json"):
            with open("preferences.json", "r", encoding="utf-8") as f:
                saved = json.load(f) or {}
                default.update(saved)
    except Exception:
        pass
    return default

def build_hotel_links(hotel, city, checkin_date=None, checkout_date=None):
    """Build Booking.com link for a hotel.
    
    Args:
        hotel: Hotel dict with name, booking_url
        city: City name for search
        checkin_date: Check-in date (datetime or string)
        checkout_date: Check-out date (datetime or string)
    
    Returns:
        Tuple with Booking.com link (Airbnb placeholder for compatibility)
    """
    name = hotel.get("name", "")
    booking = hotel.get("booking_url")
    
    # Build search query
    q = quote_plus(f"{name} {city}") if name else quote_plus(city)
    
    # Build Booking.com URL with dates if available
    if not booking:
        if checkin_date and checkout_date:
            # Convert dates to strings if needed
            if hasattr(checkin_date, 'strftime'):
                checkin_str = checkin_date.strftime('%Y-%m-%d')
            else:
                checkin_str = str(checkin_date)
            
            if hasattr(checkout_date, 'strftime'):
                checkout_str = checkout_date.strftime('%Y-%m-%d')
            else:
                checkout_str = str(checkout_date)
            
            booking = f"https://www.booking.com/searchresults.html?ss={q}&checkin={checkin_str}&checkout={checkout_str}"
        else:
            booking = f"https://www.booking.com/searchresults.html?ss={q}"
    
    # Return only Booking.com link (Airbnb removed - no data)
    return f"[🔗 Book on Booking.com]({booking})", ""


# ============================================================================
# ✅ NEW: COMMUNITY ITINERARIES UI COMPONENTS
# ============================================================================

def display_community_itineraries_section(days: int, trip_type: str, budget: str):
    """
    Display recommended community itineraries based on user selections
    
    Args:
        days: Number of trip days selected
        trip_type: Selected trip type
        budget: Selected budget level
    """
    if not COMMUNITY_ITINERARIES_AVAILABLE:
        return
    
    st.markdown("---")
    st.markdown("### 📚 Recommended Itineraries")
    st.caption("Pre-planned routes from travel experts and community. Click to use as your starting point!")
    
    # Filter itineraries based on user selections
    matching = filter_itineraries(
        duration_range=(max(3, days - 2), days + 3),  # Allow some flexibility
        trip_type=trip_type,
        budget_level=budget,
        max_results=6
    )
    
    if not matching:
        st.info("No matching itineraries found. Try adjusting your trip duration or type.")
        return
    
    # Display in a grid (2 columns)
    cols = st.columns(2)
    
    for idx, itin in enumerate(matching):
        summary = format_itinerary_summary(itin)
        
        with cols[idx % 2]:
            with st.container(border=True):
                # Header with name and duration
                st.markdown(f"**{summary['name']}**")
                
                # Key info row
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"📅 {summary['duration']} days")
                with col2:
                    st.caption(f"🗺️ {summary['type']}")
                
                # Cities
                st.caption(f"📍 {summary['cities_str']}")
                
                # Tags
                if summary['tags']:
                    tags_str = " · ".join([f"`{t}`" for t in summary['tags'][:3]])
                    st.markdown(tags_str, unsafe_allow_html=True)
                
                # Badges (profile fit)
                if summary['badges']:
                    st.caption(" ".join(summary['badges'][:2]))
                
                # Cost
                if summary['cost_str']:
                    st.caption(f"💰 {summary['cost_str']}")
                
                # Action buttons
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if st.button("📋 Use This", key=f"use_itin_{summary['id']}", use_container_width=True):
                        # Store selected itinerary in session state
                        st.session_state.selected_community_itinerary = itin
                        st.success(f"✅ Selected: {summary['name']}")
                        st.rerun()
                
                with btn_col2:
                    if st.button("👁️ Details", key=f"view_itin_{summary['id']}", use_container_width=True):
                        st.session_state[f"show_details_{summary['id']}"] = True
                
                # Show details if expanded
                if st.session_state.get(f"show_details_{summary['id']}", False):
                    with st.expander("📖 Full Itinerary Details", expanded=True):
                        display_itinerary_details(itin)
                        if st.button("Close", key=f"close_{summary['id']}"):
                            st.session_state[f"show_details_{summary['id']}"] = False
                            st.rerun()


def display_itinerary_details(itin: dict):
    """Display detailed view of a community itinerary"""
    
    # Header info
    st.markdown(f"**Source:** {itin.get('source', 'Community')}")
    
    # Highlights
    highlights = itin.get("highlights", [])
    if highlights:
        st.markdown("**✨ Highlights:**")
        for h in highlights[:5]:
            st.markdown(f"• {h}")
    
    # User tips
    tips = itin.get("user_tips", [])
    if tips:
        st.markdown("**💡 Tips:**")
        for t in tips[:3]:
            st.info(t)
    
    # Daily plan summary
    daily_plan = itin.get("daily_plan", [])
    if daily_plan:
        st.markdown("**📅 Day-by-Day:**")
        for day in daily_plan:
            day_num = day.get("day_number", day.get("day", "?"))
            city = day.get("city_or_region", day.get("city", ""))
            activities = day.get("activities", [])
            
            activity_str = ", ".join(activities[:3]) if activities else "Explore"
            if len(activities) > 3:
                activity_str += f" (+{len(activities)-3} more)"
            
            st.caption(f"**Day {day_num}:** {city} - {activity_str}")
    
    # Cost breakdown
    costs = itin.get("estimated_total_cost_per_person", {})
    if costs:
        st.markdown("**💰 Estimated Cost (per person):**")
        cost_cols = st.columns(3)
        with cost_cols[0]:
            st.metric("Budget", f"€{costs.get('budget', '?')}")
        with cost_cols[1]:
            st.metric("Mid-Range", f"€{costs.get('mid_range', '?')}")
        with cost_cols[2]:
            st.metric("Luxury", f"€{costs.get('luxury', '?')}")


def display_recommended_days_helper(cities: list):
    """
    Show recommended days for selected cities
    
    Args:
        cities: List of city names
    """
    if not COMMUNITY_ITINERARIES_AVAILABLE or not cities:
        return
    
    rec = get_recommended_duration(cities)
    
    if rec and rec.get("breakdown"):
        with st.expander("📊 Recommended Trip Duration", expanded=False):
            st.markdown(f"**For {', '.join(cities)}:**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Minimum", f"{rec['minimum']} days")
            with col2:
                st.metric("Recommended", f"{rec['recommended']} days")
            with col3:
                st.metric("Comfortable", f"{rec['comfortable']} days")
            
            # Breakdown by city
            if rec.get("breakdown"):
                st.markdown("**Per city:**")
                for city, info in rec["breakdown"].items():
                    days_str = info.get("days", "?")
                    notes = info.get("notes", "")
                    st.caption(f"• **{city}:** {days_str} days" + (f" - {notes}" if notes else ""))


def apply_community_itinerary_to_form():
    """
    Apply selected community itinerary to form fields
    Returns dict with pre-filled form values or None
    """
    if 'selected_community_itinerary' not in st.session_state:
        return None
    
    itin = st.session_state.selected_community_itinerary
    
    # Extract key fields
    cities = get_cities_from_itinerary(itin)
    duration = itin.get("duration_days", 7)
    
    # Determine trip type
    itin_type = itin.get("type", "").lower()
    if "hub" in itin_type or "star" in itin_type:
        trip_type = "Star/Hub"
    elif "circular" in itin_type or "loop" in itin_type:
        trip_type = "Circular"
    else:
        trip_type = "Point-to-point"
    
    # Build start/end text
    if len(cities) >= 2:
        start_end = f"{cities[0]} to {cities[-1]}"
    elif cities:
        start_end = cities[0]
    else:
        start_end = ""
    
    # Get budget
    budget = itin.get("budget_level", "mid-range").lower()
    if budget not in ["budget", "mid-range", "luxury"]:
        budget = "mid-range"
    
    return {
        "start_end_text": start_end,
        "trip_days": duration,
        "trip_type": trip_type,
        "budget": budget,
        "cities": cities,
        "itinerary_name": itin.get("name", "")
    }



def show_trip_planner_full(attractions, hotels, restaurants=None):
    """Main trip planner UI with city name normalization"""
    
    if restaurants is None:
        restaurants = []
    
    # ✅ NEW: Build set of known cities from attractions data
    known_cities = {(item.get("city") or "").strip() for item in attractions}
    known_cities.discard("")  # Remove empty strings
    
    st.title("✈️ Plan a New Trip")
    
    # ✅ NEW: Disclaimer/Agreement
    if 'disclaimer_accepted' not in st.session_state:
        st.session_state.disclaimer_accepted = False
    
    if not st.session_state.disclaimer_accepted:
        st.markdown("""
        <div style="background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 10px; padding: 25px; margin-bottom: 20px;">
            <h2 style="color: #856404; margin-top: 0;">⚠️ Please Read Before Using</h2>
            <p style="font-size: 18px; color: #856404; line-height: 1.6;">
                This trip planner is an <strong>AI-powered tool</strong> designed to help you plan your Andalusia adventure. 
                While we strive for accuracy, please note:
            </p>
            <ul style="font-size: 17px; color: #856404; line-height: 1.8;">
                <li><strong>Verify all information</strong> - Opening hours, prices, and availability may change</li>
                <li><strong>Double-check bookings</strong> - Always confirm hotel and attraction reservations directly</li>
                <li><strong>Use your judgment</strong> - The app may occasionally suggest incorrect or outdated information</li>
                <li><strong>Not a substitute for official sources</strong> - Check official tourism websites for the latest info</li>
            </ul>
            <p style="font-size: 16px; color: #856404; margin-bottom: 0; font-style: italic;">
                By using this app, you acknowledge that it's a planning aid and not a guaranteed travel guide.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("✅ I Understand - Let's Plan!", type="primary", use_container_width=True):
            st.session_state.disclaimer_accepted = True
            st.rerun()
        
        st.stop()  # Don't show the rest of the app until accepted
    
    # ✅ NEW: Show if community itinerary was selected
    if 'selected_community_itinerary' in st.session_state:
        itin = st.session_state.selected_community_itinerary
        st.success(f"📚 Using template: **{itin.get('name', 'Community Itinerary')}** ({itin.get('duration_days', '?')} days)")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("✖️ Clear Template", key="clear_template_btn"):
                del st.session_state.selected_community_itinerary
                st.rerun()

    
    prefs_state = load_prefs()
    
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'start_end_text': "",
            'special_requests': "",
            'trip_days': 7,
            'trip_type': prefs_state["default_trip_type"],
            'max_km': int(prefs_state["max_km_per_day"]),
            'budget': prefs_state["default_budget"],
            'pace': prefs_state["default_pace"],
            'platform_pref': prefs_state["hotel_platform"],
            'max_price_per_night': int(prefs_state.get("max_price_per_night", 150)),
            'cats': [c for c in prefs_state["poi_categories"] if c in POI_CATEGORIES],
            'max_same_category': int(prefs_state.get("max_same_category_per_day", 2))
        }
    
    # 📅 DATE PICKER - OUTSIDE FORM so it updates immediately!
    st.write("### 📅 Select Your Travel Dates")
    start_date, end_date, days = create_date_picker()
    
    
    # ✅ Save to session state IMMEDIATELY
    st.session_state.current_trip_start_date = start_date
    st.session_state.current_trip_end_date = end_date
    st.session_state.form_data['trip_days'] = days
    st.session_state.form_data['start_date'] = start_date
    st.session_state.form_data['end_date'] = end_date
    
    
    with st.form("trip_form"):
        start_end_text = st.text_input("Start & End Location", 
                                      value=st.session_state.form_data['start_end_text'],
                                      placeholder="e.g., Malaga to Seville",
                                      help="You can use city names with or without accents (Malaga = Málaga)")
        
        colA, colB, colC = st.columns(3)
        with colA:
            trip_type_options = ["Point-to-point", "Circular", "Star/Hub"]
            current_trip_type = st.session_state.form_data.get('trip_type', 'Point-to-point')
            if current_trip_type not in trip_type_options:
                current_trip_type = 'Point-to-point'
            trip_type = st.selectbox(
                "Trip Type",
                trip_type_options, 
                index=trip_type_options.index(current_trip_type),
                help="Point-to-point: A→B | Circular: Loop | Star/Hub: Day trips ⭐"
            )
        with colB:
            st.markdown("**Budget**")
        with colC:
            max_km = st.number_input(
                "Max driving km/day",
                min_value=50,
                max_value=500, 
                value=st.session_state.form_data['max_km'],
                step=10
            )

        special = st.text_area(
            "Special Requests", 
            value=st.session_state.form_data['special_requests'],
        )
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            budget_options = ["budget", "mid-range", "luxury"]
            budget = st.selectbox("Budget", budget_options, 
                                index=budget_options.index(st.session_state.form_data['budget']))
        with col2:
            pace_options = ["easy", "medium", "fast"]
            pace = st.selectbox("Travel pace", pace_options, 
                              index=pace_options.index(st.session_state.form_data['pace']))
        with col3:
            platform_options = ["Booking.com"]  # Airbnb removed - no data yet
            platform_pref = st.selectbox("Hotel platform", platform_options, 
                                       index=0)  # Always Booking.com for now
        with col4:
            max_price_per_night = st.number_input("Max hotel (€/night)", min_value=0, step=10, 
                                                value=st.session_state.form_data['max_price_per_night'], 
                                                help="0 = no cap")
        
        cats = st.multiselect("POI categories", POI_CATEGORIES, 
                            default=st.session_state.form_data['cats'])
        
        max_same_category = st.slider("🎨 Max same category per day (Diversity)", 
                                     min_value=1, max_value=4, 
                                     value=st.session_state.form_data['max_same_category'])
        
        submitted = st.form_submit_button("✨ Generate Trip")
        
        if submitted:
            # ✅ VALIDATION (if available)
            if VALIDATION_AVAILABLE:
                from itinerary_core import parse_start_end
                start_city, end_city = parse_start_end(start_end_text, trip_type)
                
                # Extract avoid cities from special requests
                cities_to_avoid = []
                if special:
                    special_lower = special.lower()
                    avoid_keywords = ['avoid', 'skip', 'no', "don't visit", 'exclude', 'not interested']
                    for keyword in avoid_keywords:
                        if keyword in special_lower:
                            for city in known_cities:
                                if city.lower() in special_lower:
                                    cities_to_avoid.append(city)
                
                # Prepare validation parameters
                validation_params = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'start_city': start_city or "",
                    'end_city': end_city or "",
                    'trip_type': trip_type,
                    'cities_to_include': [],
                    'cities_to_avoid': cities_to_avoid,
                    'special_requests': special,
                    'pace': pace
                }
                
                # Run validation
                errors, warnings, is_valid = validate_all_parameters(validation_params)
                
                # ✅ FIX: Filter out irrelevant warnings
                # Don't show "use Circular/Hub" warning if already using Circular or Hub
                if trip_type in ["Circular", "Star/Hub"]:
                    warnings = [w for w in warnings if "Circular" not in w and "Hub" not in w]
                
                # Display validation results
                if errors:
                    st.error("### 🚫 Cannot Generate Trip - Please Fix These Issues:")
                    for error in errors:
                        st.error(error)
                    st.session_state.form_submitted = False
                    st.stop()  # Stop execution, don't generate trip
                
                if warnings:
                    st.warning("### ⚠️ Suggestions:")
                    for warning in warnings:
                        st.warning(warning)
            
            # If validation passed, continue with trip generation
            # ✅ NEW: Normalize city names in the start_end_text
            normalized_text = normalize_start_end_text(start_end_text, known_cities)
            
            st.session_state.form_data = {
                'start_end_text': normalized_text,  # ✅ Use normalized version
                'special_requests': special,
                'trip_days': days,
                'trip_type': trip_type,
                'max_km': max_km,
                'budget': budget,
                'pace': pace,
                'platform_pref': platform_pref,
                'max_price_per_night': int(max_price_per_night),
                'cats': cats,
                'max_same_category': max_same_category
            }
            
            # ✅ NEW: Show normalization feedback
            if normalized_text != start_end_text:
                st.success(f"✓ Matched: '{start_end_text}' → '{normalized_text}'")
            
            st.session_state.form_submitted = True
    

    if st.session_state.form_submitted and st.session_state.form_data['start_end_text']:
        form_vals = st.session_state.form_data
        
        prefs = {
            "trip_type": form_vals['trip_type'],  # ✅ CRITICAL FIX: Add trip_type!
            "budget": form_vals['budget'],
            "pace": form_vals['pace'],
            "notes": form_vals['special_requests'],
            "max_km_per_day": form_vals['max_km'],
            "poi_categories": form_vals['cats'],
            "hotel_platform": form_vals['platform_pref'],
            "max_price_per_night": form_vals['max_price_per_night'],
            "min_poi_rating": float(prefs_state.get("min_poi_rating", 0.0)),
            "max_same_category_per_day": form_vals['max_same_category'],
        }
        
        with st.spinner("Generating your itinerary..."):
            # ✅ Call generate_simple_trip from itinerary_generator module
            result = generate_simple_trip(
                form_vals['start_end_text'], 
                form_vals['trip_days'], 
                prefs, 
                form_vals['trip_type'], 
                attractions, 
                hotels,
                restaurants,  # ✅ Added restaurants
                start_date    # ✅ NEW: Pass start_date for seasonal filtering
            )
        
        if not result or not result.get("itinerary"):
            st.error("Could not generate itinerary.")
            st.session_state.form_submitted = False
            return
        
        st.session_state.current_trip_result = result
        st.session_state.current_trip_prefs = prefs
        st.session_state.current_trip_days = form_vals['trip_days']
        # ✅ FIX: Don't overwrite start_date - it's already set by date picker (line 147)!
        # st.session_state.current_trip_start_date = st.session_state.form_data.get('start_date')  # ❌ This was overwriting with None!
        
        # ✅ NEW: Add dates to each day in itinerary RIGHT AWAY
        # This ensures dates are available for display AND document generation
        start_date = st.session_state.get('current_trip_start_date')
        
        if start_date and result.get('itinerary'):
            for idx, day in enumerate(result['itinerary']):
                try:
                    day_date = start_date + timedelta(days=idx)
                    day['date'] = day_date.strftime('%Y-%m-%d')  # String for JSON
                    day['date_obj'] = day_date  # Datetime for document
                except Exception as e:
                    print(f"⚠️ Error adding date to day {idx}: {e}")
                    pass
            
            # ✅ CRITICAL: Update session state with the modified result!
            st.session_state.current_trip_result = result
        else:
            print(f"⚠️ WARNING: Cannot add dates - start_date={start_date}, has_itinerary={bool(result.get('itinerary'))}")
    
    if 'current_trip_result' in st.session_state:
        # ✅ CRITICAL FIX: Ensure dates are in itinerary before display
        # (In case page reloaded without going through form submission)
        result = st.session_state.current_trip_result
        start_date = st.session_state.get('current_trip_start_date')
        
        if start_date and result.get('itinerary'):
            # Check if dates are missing from first day
            first_day = result['itinerary'][0] if result['itinerary'] else {}
            if 'date' not in first_day or 'date_obj' not in first_day:
                print("⚠️ Dates missing from itinerary! Adding them now...")
                for idx, day in enumerate(result['itinerary']):
                    try:
                        day_date = start_date + timedelta(days=idx)
                        day['date'] = day_date.strftime('%Y-%m-%d')
                        day['date_obj'] = day_date
                        # print(f"✅ (Re-)Added date {day['date']} to day {idx+1}")
                    except Exception as e:
                        print(f"⚠️ Error adding date: {e}")
        
        display_itinerary(
            st.session_state.current_trip_result, 
            st.session_state.current_trip_prefs, 
            st.session_state.current_trip_days, 
            attractions, 
            hotels,
            restaurants
        )

# ✅ NEW: Helper function to normalize start/end text
def normalize_start_end_text(text, known_cities):
    """
    Normalize city names in 'Start to End' text
    Examples:
        'Malaga to Seville' → 'Málaga to Seville'
        'malaga' → 'Málaga'
        'cordoba to cadiz' → 'Córdoba to Cádiz'
    """
    if not text:
        return text
    
    # Handle both " to " and "-" separators (case-insensitive)
    import re
    match = re.search(r'\s+to\s+', text, re.IGNORECASE)
    
    if match:
        # Split using the matched separator
        parts = re.split(r'\s+to\s+', text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            start_normalized = canonicalize_city(parts[0].strip(), known_cities)
            end_normalized = canonicalize_city(parts[1].strip(), known_cities)
            
            if start_normalized and end_normalized:
                return f"{start_normalized} to {end_normalized}"
            elif start_normalized:
                return f"{start_normalized} to {parts[1].strip()}"
            elif end_normalized:
                return f"{parts[0].strip()} to {end_normalized}"
    
    # Single city (circular trip)
    normalized = canonicalize_city(text.strip(), known_cities)
    if normalized:
        return normalized
    
    # Return original if no match
    return text

def display_itinerary(result, prefs, days, attractions, hotels, restaurants):
    """Display generated itinerary"""
    itinerary = result.get("itinerary", [])
    hop_kms = result.get("hop_kms", [])  # FIXED: was "hop_km_list"
    maps_link = result.get("maps_link", "")
    ordered_cities = result.get("ordered_cities", [])
    is_car_mode = result.get("is_car_mode", True)

    # Trip start date (if selected)
    start_date = None
    try:
        start_date = st.session_state.get('current_trip_start_date')
    except Exception as e:
        print(f"❌ DISPLAY: Error getting start_date: {e}")
        start_date = None
    
    # ✅ Detect Star/Hub trip
    is_star_hub = result.get('trip_type') == 'Star/Hub'
    base_hotels = result.get('base_hotels', [])
    base_city = result.get('base_city', '')
    
    st.success(f"✅ Generated {days}-day {'road trip' if is_car_mode else 'itinerary'}!")
    
    if not itinerary:
        st.warning("No itinerary data to display")
        return
    
    # Show route overview
    if ordered_cities:
        st.markdown("### 📍 Route")
        if is_star_hub:
            st.info(f"⭐ **Base: {base_city}** (day trips from here)")
        else:
            route_str = " → ".join(ordered_cities)
            st.info(f"**{route_str}**")
            
            # ✅ FIX: Use link_button for clickable Google Maps link
            if maps_link:
                st.link_button("🗺️ OPEN ROUTE IN GOOGLE MAPS", maps_link)
    
    # ✅ For Star/Hub trips, show base hotels at the top
    if is_star_hub and base_hotels:
        st.markdown("---")
        st.markdown("### 🏨 Accommodation (Your Base for All Nights)")
        st.info(f"⭐ Stay in **{base_city}** for the entire trip. Return here each evening after day trips.")
        
        # Get full trip date range
        start_date_obj = st.session_state.get('current_trip_start_date')
        end_date_obj = st.session_state.get('current_trip_end_date')
        
        for hotel in base_hotels:
            # ✅ NEW: Create booking link with FULL trip dates
            from urllib.parse import quote_plus
            hotel_search = quote_plus(f"{hotel.get('name', base_city)} {base_city}")
            
            # Build booking URL with dates
            # Note: checkout date should be the day AFTER the last night
            if start_date_obj and end_date_obj:
                # Convert date to string format
                checkin_str = start_date_obj.strftime('%Y-%m-%d') if hasattr(start_date_obj, 'strftime') else str(start_date_obj)
                # Checkout is day AFTER end_date (end_date is last day of trip, checkout is next morning)
                checkout_date = end_date_obj + timedelta(days=1)
                checkout_str = checkout_date.strftime('%Y-%m-%d') if hasattr(checkout_date, 'strftime') else str(checkout_date)
                booking_url = f"https://www.booking.com/searchresults.html?ss={hotel_search}&checkin={checkin_str}&checkout={checkout_str}"
                booking_link = f"[🔗 Book on Booking.com]({booking_url})"
            else:
                # Fallback without dates
                booking_url = f"https://www.booking.com/search.html?ss={hotel_search}"
                booking_link = f"[🔗 Book on Booking.com]({booking_url})"
            
            h_col1, h_col2 = st.columns([3, 1])
            with h_col1:
                st.markdown(f"**{hotel.get('name', 'Unknown')}**")
                if hotel.get("address"):
                    st.caption(f"📍 {hotel['address']}")
                # Show date range
                if start_date_obj and end_date_obj:
                    checkout_display = end_date_obj + timedelta(days=1)
                    date_range = f"{start_date_obj.strftime('%d %b')} - {checkout_display.strftime('%d %b %Y')}"
                    num_nights = (end_date_obj - start_date_obj).days + 1  # +1 because end_date is inclusive
                    st.caption(f"📅 {date_range} ({num_nights} nights)")
            with h_col2:
                st.markdown(booking_link)
        st.markdown("---")
    
    # Show special requests acknowledgment
    parsed_req = result.get("parsed_requests", {})
    if parsed_req:
        st.markdown("### ✓ Special Requests Applied")
        col1, col2, col3 = st.columns(3)
        if parsed_req.get("must_see_cities"):
            with col1:
                st.success(f"Must see: {', '.join(parsed_req['must_see_cities'])}")
        if parsed_req.get("avoid_cities"):
            with col2:
                st.warning(f"Avoiding: {', '.join(parsed_req['avoid_cities'])}")
        if parsed_req.get("stay_requests"):
            with col3:
                stays = [f"{s['city']} ({s['days']}d)" for s in parsed_req['stay_requests']]
                st.info(f"Extended stays: {', '.join(stays)}")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # ✅ FIX: Use total_km from result (pre-calculated) instead of summing itinerary
        # For Star/Hub trips: itinerary has driving_km per day
        # For Point-to-Point trips: result has total_km from hop_kms
        if is_star_hub:
            total_km = sum(d.get("driving_km", 0) for d in itinerary)
        else:
            total_km = result.get("total_km", 0)
            # Fallback: if total_km not in result, sum hop_kms
            if total_km == 0 and hop_kms:
                total_km = sum(km for km in hop_kms if km is not None)
        
        st.metric("🚗 Total Driving", f"{total_km:.0f} km")
    
    with col2:
        # Calculate drive time from total_km
        if is_star_hub:
            total_hours = sum(d.get("driving_hours", 0) for d in itinerary)
        else:
            # Calculate driving time: assume average 80 km/h
            total_hours = total_km / 80 if total_km > 0 else 0
        st.metric("⏱️ Drive Time", f"{total_hours:.1f}h")
    
    with col3:
        total_pois = sum(len(cs.get("attractions", [])) for d in itinerary for cs in d.get("cities", []))
        st.metric("📍 Total POIs", total_pois)
    
    with col4:
        avg_pois = total_pois / len(itinerary) if itinerary else 0
        st.metric("📊 Avg POIs/day", f"{avg_pois:.1f}")
    
    # Day-by-day itinerary
    st.markdown("---")
    st.markdown("### 📅 Daily Itinerary")
    
    # ✅ Calculate total trip days for booking link calculation
    total_trip_days = len(itinerary)

    for day_data in itinerary:
        day_num = day_data.get("day", 0)
        day_type = day_data.get("type", "base_city")
        overnight = day_data.get("overnight_city", day_data.get("city", "Unknown"))

        # Build day label with optional calendar date
        if start_date and day_num:
            trip_date = start_date + timedelta(days=day_num - 1)
            date_str = trip_date.strftime("%a, %d-%b-%Y")  # e.g. Tue, 25-Aug-2026
            day_prefix = f"Day {day_num}: {date_str}"
        else:
            day_prefix = f"Day {day_num}"

        # ✅ NEW: Add day X of Y in city info
        day_in_city = day_data.get("day_in_city", 1)
        total_days_in_city = day_data.get("total_days_in_city", 1)
        city_day_suffix = ""
        if total_days_in_city > 1:
            city_day_suffix = f" (Day {day_in_city}/{total_days_in_city})"

        # Day header
        if day_type == "driving_day":
            st.markdown(f"## {day_prefix} 🚗 Driving Day → {overnight}")
        elif day_type == "day_trip":
            base = day_data.get("base", "?")
            st.markdown(f"## {day_prefix} 🏖️ Day Trip from {base}")
        else:
            # ✅ FIX: For circular trips last day, show visited city + return note
            city = day_data.get("city", "Unknown")
            if city != overnight:
                # This is circular trip last day - visiting city but returning to overnight
                st.markdown(f"## {day_prefix} 📍 {city}{city_day_suffix} (returning to {overnight})")
            else:
                st.markdown(f"## {day_prefix} 📍 {overnight}{city_day_suffix}")
        
        # Driving info
        driving_km = day_data.get("driving_km", 0)
        driving_hours = day_data.get("driving_hours", 0)
        if driving_km > 0:
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"🚗 **Driving:** {driving_km} km (~{driving_hours:.1f}h)")
            with col2:
                if day_type == "day_trip":
                    st.info("🏨 **Overnight:** Same base city")
                else:
                    st.info(f"🏨 **Overnight:** {overnight}")
        
        # Cities visited
        cities_list = day_data.get("cities", [])
        for city_stop in cities_list:
            city_name = city_stop.get("city", "Unknown")
            
            # POIs
            pois = city_stop.get("attractions", [])
            if pois:
                st.markdown(f"### 📍 {city_name} ({len(pois)} attractions)")
                
                # 🎬 YouTube Video Preview for this city - ONLY ON FIRST DAY
                day_in_city = day_data.get("day_in_city", 1)
                if YOUTUBE_UI_AVAILABLE and day_in_city == 1:
                    # print(f"🎬 Trying to display video for: {city_name}")
                    from youtube_ui import get_videos_for_city
                    videos = get_videos_for_city(city_name, max_videos=1)
                    if videos:
                        video = videos[0]
                        watch_url = video.get('watch_url', '')
                        title = video.get('title', 'Video')
                        if watch_url:
                            st.markdown(f"**🎬 {title[:60]}**")
                            st.video(watch_url)
                            # print(f"🎬 Video DISPLAYED for {city_name}: {watch_url}")
                    else:
                        pass  # No video found for this city
                
                for idx, poi in enumerate(pois, 1):
                    with st.expander(f"**{idx}. {poi.get('name', 'Unknown')}**", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            desc = poi.get("description", "No description")
                            st.write(desc)
                            
                            if poi.get("insider_tip"):
                                st.info(f"💡 **Tip:** {poi['insider_tip']}")
                        
                        with col2:
                            if poi.get("rating"):
                                st.metric("⭐ Rating", f"{poi['rating']}/10")
                            if poi.get("duration"):
                                st.metric("⏱️ Duration", poi["duration"])
                            if poi.get("price"):
                                st.metric("💶 Price", poi["price"])
                            
                            category = poi.get("category", "")
                            if category:
                                st.caption(f"🏷️ {category}")
        
        # Restaurants
        lunch = day_data.get("lunch_restaurant")
        dinner = day_data.get("dinner_restaurant")
        
        if lunch or dinner:
            st.markdown("### 🍽️ Dining")
            rest_col1, rest_col2 = st.columns(2)
            
            with rest_col1:
                if lunch:
                    st.markdown(f"**🥗 Lunch:** {lunch.get('name', 'N/A')}")
                    if lunch.get("cuisine"):
                        st.caption(f"Cuisine: {lunch['cuisine']}")
                    if lunch.get("address"):
                        st.caption(f"📍 {lunch['address']}")
            
            with rest_col2:
                if dinner:
                    st.markdown(f"**🍷 Dinner:** {dinner.get('name', 'N/A')}")
                    if dinner.get("cuisine"):
                        st.caption(f"Cuisine: {dinner['cuisine']}")
                    if dinner.get("address"):
                        st.caption(f"📍 {dinner['address']}")
        
        # Hotels (skip for Star/Hub since shown at top)
        if not is_star_hub:
            hotels_list = day_data.get("hotels", [])
            day_in_city = day_data.get("day_in_city", 1)
            total_days_in_city = day_data.get("total_days_in_city", 1)
            
            # ✅ Only show hotels on FIRST day in city (like hub trips)
            if hotels_list and day_in_city == 1:
                # Nights = days in city (same for ALL cities including last)
                nights = total_days_in_city
                
                nights_text = f" ({nights} night{'s' if nights > 1 else ''})" if nights >= 1 else ""
                st.markdown(f"### 🏨 Accommodation{nights_text}")
                
                # ✅ Calculate check-in and check-out dates
                checkin_date = None
                checkout_date = None
                if start_date and day_num:
                    checkin_date = start_date + timedelta(days=day_num - 1)
                    checkout_date = checkin_date + timedelta(days=nights)
                
                for hotel in hotels_list:
                    booking_link, _ = build_hotel_links(hotel, overnight, checkin_date, checkout_date)
                    
                    h_col1, h_col2 = st.columns([3, 1])
                    with h_col1:
                        st.markdown(f"**{hotel.get('name', 'Unknown')}**")
                        if hotel.get("address"):
                            st.caption(f"📍 {hotel['address']}")
                    with h_col2:
                        st.markdown(booking_link)
            elif day_in_city > 1:
                # Not first day - just show reminder
                st.info(f"🏨 **Continuing at your hotel in {overnight}** (Day {day_in_city} of {total_days_in_city})")
        else:
            # For Star/Hub day trips, show return message
            if day_data.get('is_day_trip'):
                st.markdown("### 🏨 Accommodation")
                st.info(f"🔙 Return to {base_city} for the night")
        
        # ✅ NEW: Show route stops on travel days (last day in city)
        route_stops = day_data.get("route_stops", [])
        if route_stops:
            st.markdown("### 🛣️ Stops Along the Way")
            st.caption("Recommended stops when driving to your next destination")
            for stop in route_stops:
                stop_name = stop.get('name', 'Unknown')
                stop_type = stop.get('type', 'stop')
                highlight = stop.get('highlight', '')
                detour = stop.get('detour_km', 0)
                time_min = stop.get('time_min', 30)
                
                st.markdown(f"**{stop_name}** ({stop_type.replace('_', ' ').title()})")
                if highlight:
                    st.caption(f"✨ {highlight}")
                st.caption(f"⏱️ ~{time_min} min visit • 🚗 +{detour}km detour")
        
        st.markdown("---")
    
    # Maps link
    if maps_link:
        st.markdown("### 🗺️ Route Map")
        st.markdown(f"[Open in Google Maps]({maps_link})")
    
    # AI insights removed
    

    # ✅ Display Events (fetch from events_service)
    if EVENTS_AVAILABLE and ordered_cities:
        try:
            # Get date range - handle both date objects and strings
            if start_date:
                # Convert date object to string if needed
                if hasattr(start_date, 'strftime'):
                    trip_start = start_date.strftime('%Y-%m-%d')
                    trip_end = (start_date + timedelta(days=days)).strftime('%Y-%m-%d')
                else:
                    trip_start = start_date
                    trip_end = start_date  # Fallback
            else:
                # Default dates if none provided
                trip_start = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                trip_end = (datetime.now() + timedelta(days=30+days)).strftime('%Y-%m-%d')
            
            # ✅ Check ALL major Andalusia cities for events (not just user's cities)
            all_events = []
            
            # Major cities to always check for events
            major_cities = ['Seville', 'Granada', 'Córdoba', 'Málaga', 'Cádiz', 'Jerez', 'Ronda']
            
            # Combine user's cities with major cities (no duplicates)
            cities_to_check = list(set([c.title() for c in ordered_cities] + major_cities))
            
            for city in cities_to_check:
                city_events = get_events_for_trip(city, trip_start, trip_end)
                all_events.extend(city_events)
            
            
            # Remove duplicates based on name and date
            seen = set()
            unique_events = []
            for event in all_events:
                key = (event.get('name'), event.get('date'))
                if key not in seen:
                    seen.add(key)
                    unique_events.append(event)
            
            # Sort by tier (tier_1 first) then by date
            tier_order = {'tier_1': 0, 'tier_2': 1, 'tier_3': 2}
            unique_events.sort(key=lambda x: (tier_order.get(x.get('tier', 'tier_3'), 3), x.get('date', '')))
            
            if unique_events:
                st.markdown("---")
                st.markdown("### 🎉 Events During Your Trip")
                st.write(f"Found **{len(unique_events)}** special events happening during your visit!")
                
                for event in unique_events:
                    with st.expander(f"🎊 {event.get('name', 'Event')} - {event.get('date', 'TBD')}", expanded=True):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Show if event city is in user's route
                            event_city = event.get('city', event.get('location', 'N/A'))
                            in_route = any(event_city.lower() in c.lower() or c.lower() in event_city.lower() for c in ordered_cities)
                            city_note = " ✓ *In your route*" if in_route else " *(detour possible)*"
                            st.markdown(f"**📍 Location:** {event_city}{city_note}")
                            st.markdown(f"**📅 Date:** {event.get('date', 'N/A')}")
                            if event.get('description'):
                                st.write(event['description'])
                            if event.get('tip'):
                                st.info(f"💡 **Tip:** {event['tip']}")
                        
                        with col2:
                            st.markdown(f"**🏷️ Type:** {event.get('type', 'Festival')}")
                            if event.get('tier'):
                                tier_names = {'tier_1': '⭐⭐⭐', 'tier_2': '⭐⭐', 'tier_3': '⭐'}
                                tier_emoji = tier_names.get(event['tier'], '⭐')
                                st.markdown(f"**Importance:** {tier_emoji}")
                            if event.get('source'):
                                st.caption(f"ℹ️ Source: {event['source']}")
        except Exception as e:
            st.error(f"❌ ERROR loading events: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    # ✅ NEW: Show SIMILAR community itineraries based on user's actual trip
    if COMMUNITY_ITINERARIES_AVAILABLE:
        st.markdown("---")
        st.markdown("### 📚 Similar Itineraries from the Community")
        st.caption("Explore how other travelers planned similar trips - get tips and day-by-day inspiration!")
        
        # Get user's actual choices from their generated trip
        user_cities = ordered_cities if ordered_cities else []
        user_days = days if days else 7
        user_trip_type = prefs.get('trip_type', 'Point-to-point') if prefs else 'Point-to-point'
        user_budget = prefs.get('budget', 'mid-range') if prefs else 'mid-range'
        
        # Debug: show what we're filtering by
        # print(f"🔍 Filtering community itineraries for: {user_cities}, {user_days} days, {user_trip_type}")
        
        if not user_cities:
            st.info("Generate an itinerary first to see similar community trips.")
        else:
            # ✅ UPDATED: Filter strictly to ±1 day of user's trip length
            all_itineraries = filter_itineraries(
                duration_range=(max(3, user_days - 1), user_days + 1),  # ±1 day only
                max_results=10
            )
            
            # Strict filter: MUST share at least 2 cities with user's trip
            # Handle city name variations (Seville/Sevilla, Cordoba/Córdoba)
            city_aliases = {
                'seville': ['seville', 'sevilla'],
                'cordoba': ['cordoba', 'córdoba'],
                'malaga': ['malaga', 'málaga'],
                'cadiz': ['cadiz', 'cádiz'],
                'jerez': ['jerez', 'jerez de la frontera'],
                'granada': ['granada'],
                'ronda': ['ronda'],
                'marbella': ['marbella'],
                'nerja': ['nerja'],
                'tarifa': ['tarifa'],
            }
            
            def normalize_city(city_name):
                """Normalize city name for matching"""
                city_lower = city_name.lower().strip()
                for key, aliases in city_aliases.items():
                    if any(alias in city_lower or city_lower in alias for alias in aliases):
                        return key
                return city_lower
            
            user_cities_normalized = set(normalize_city(c) for c in user_cities)
            
            similar_itineraries = []
            for itin in all_itineraries:
                itin_cities = get_cities_from_itinerary(itin)
                itin_cities_normalized = set(normalize_city(c) for c in itin_cities)
                
                # Count matching cities
                matching = user_cities_normalized & itin_cities_normalized
                
                if len(matching) >= 2:
                    similar_itineraries.append({
                        'itinerary': itin,
                        'matching_cities': len(matching),
                        'matched': matching
                    })
            
            # Sort by number of matching cities (most matches first)
            similar_itineraries.sort(key=lambda x: x['matching_cities'], reverse=True)
            
            # ✅ UPDATED: Show only 1 best match
            similar_itineraries = [x['itinerary'] for x in similar_itineraries[:1]]
            
            if similar_itineraries:
                # Store for Word doc export
                st.session_state['similar_community_itineraries'] = similar_itineraries
                
                # ✅ UPDATED: Single itinerary display (no columns)
                itin = similar_itineraries[0]
                summary = format_itinerary_summary(itin)
                with st.container(border=True):
                    st.markdown(f"**{summary['name']}**")
                    st.caption(f"📅 {summary['duration']} days · 🗺️ {summary['type']}")
                    st.caption(f"📍 {summary['cities_str']}")
                    
                    # Show day-by-day summary
                    daily_plan = itin.get('daily_plan', [])
                    if daily_plan:
                        st.markdown("**📅 Day-by-Day:**")
                        for day in daily_plan[:7]:  # Show up to 7 days
                            day_num = day.get('day_number', day.get('day', '?'))
                            city = day.get('city_or_region', day.get('city', ''))
                            activities = day.get('activities', [])
                            
                            # Format activities - extract 'label' from activity dicts
                            if activities:
                                act_list = []
                                for act in activities[:3]:
                                    if isinstance(act, dict):
                                        # Use 'label' field which contains the activity name
                                        label = act.get('label', '')
                                        if label:
                                            act_list.append(label)
                                    elif isinstance(act, str):
                                        act_list.append(act)
                                
                                if act_list:
                                    act_str = ", ".join(act_list)
                                    if len(activities) > 3:
                                        act_str += f" +{len(activities)-3} more"
                                else:
                                    act_str = "Explore"
                            else:
                                act_str = "Explore"
                            
                            st.caption(f"Day {day_num}: **{city}** - {act_str}")
                        
                        if len(daily_plan) > 7:
                            st.caption(f"... +{len(daily_plan) - 7} more days")
                    
                    # User tips (most valuable part)
                    tips = itin.get('user_tips', [])[:2]
                    if tips:
                        st.markdown("**💡 Tips:**")
                        for tip in tips:
                            st.info(f"{tip}")
            else:
                st.info(f"No community itineraries found matching your cities: {', '.join(user_cities[:4])}")
    
    # ✅ NEW: Plan Again button (before export options)
    add_plan_again_button()
    
    # Export options
    st.markdown("---")
    st.markdown("### 💾 Export Options")
    
    # Show a prominent loading message
    loading_placeholder = st.empty()
    loading_placeholder.markdown("""
    <div style="text-align: center; padding: 20px; background-color: #f0f8ff; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: #1e90ff;">⏳ Generating your travel documents...</h2>
        <p style="font-size: 18px; color: #666;">This may take a moment. Please wait.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate files
    with st.spinner(""):
        col1, col2 = st.columns(2)
        
        # Excel export
        with col1:
            try:
                excel_file = build_excel(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, is_car_mode)
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_file,
                    file_name=f"andalusia_trip_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ Error generating Excel: {str(e)}")
        
        # PDF export (Pure Python - fpdf2, no LibreOffice needed)
        with col2:
            try:
                from pdf_generator import build_pdf
                
                pdf_buffer = build_pdf(
                    itinerary=itinerary,
                    hop_kms=hop_kms,
                    maps_link=maps_link,
                    ordered_cities=ordered_cities,
                    days=total_trip_days,
                    prefs=prefs,
                    parsed_requests=result.get("parsed_requests", {}),
                    is_car_mode=True,
                    result=result
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"andalusia_trip_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
                import traceback
                print(traceback.format_exc())
    
    # Clear the loading message after files are ready
    loading_placeholder.empty()
    
    # 🎬 VIDEO SLIDESHOW SECTION (lazy loaded)
    st.markdown("---")
    st.markdown("### 🎬 Trip Video")
    st.caption("Generate a slideshow video from your itinerary's POI photos")
    
    vid_col1, vid_col2 = st.columns([1, 2])
    
    with vid_col1:
        generate_btn = st.button("🎬 Generate Video", use_container_width=True, key="gen_slideshow_btn")
    
    with vid_col2:
        # Show download button if video was generated
        if st.session_state.get('slideshow_ready') and st.session_state.get('slideshow_video'):
            st.download_button(
                label="📥 Download Trip Video (MP4)",
                data=st.session_state['slideshow_video'],
                file_name=f"andalusia_trip_{datetime.now().strftime('%Y%m%d')}.mp4",
                mime="video/mp4",
                use_container_width=True,
                key="download_slideshow_btn"
            )
            st.caption("🖼️ ~1.5 seconds per POI with city/attraction labels")
    
    # Handle video generation AFTER the UI is rendered
    if generate_btn:
        progress_placeholder = st.empty()
        progress_placeholder.info("⏳ Loading video generator...")
        
        try:
            # Lazy import
            generate_poi_slideshow, SlideshowConfig = get_video_generator()
            
            if generate_poi_slideshow is None:
                progress_placeholder.error("❌ Video generator not available. Make sure poi_video_generator.py exists.")
            else:
                progress_placeholder.info("🎬 Creating your trip video... This may take a minute.")
                
                output_file = f"trip_slideshow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                
                config = SlideshowConfig(
                    duration_per_slide=1.5,
                    fps=24,
                    width=1280,
                    height=720
                )
                
                # Use data/photos directory
                photos_dir = os.path.join(os.path.dirname(__file__), 'data', 'photos')
                
                video_path = generate_poi_slideshow(result, output_file, config, photos_dir)
                
                if video_path and os.path.exists(video_path):
                    # Store in session state
                    with open(video_path, 'rb') as f:
                        st.session_state['slideshow_video'] = f.read()
                    st.session_state['slideshow_ready'] = True
                    
                    # Cleanup temp file
                    try:
                        os.remove(video_path)
                    except:
                        pass
                    
                    progress_placeholder.success("✅ Video ready!")
                    st.rerun()
                else:
                    progress_placeholder.error("❌ Failed to generate video. Check that photos exist in data/photos/")
                
        except Exception as e:
            progress_placeholder.error(f"❌ Error: {str(e)}")
            import traceback
            print(traceback.format_exc())


def build_excel(itinerary, hop_kms, maps_link, ordered_cities, days, prefs, is_car_mode=False):
    """Build Excel export with car-specific columns"""
    import pandas as pd
    import io
    
    rows = []
    for i, d in enumerate(itinerary):
        day_type = d.get("type", "base_city")
        overnight = d.get("overnight_city", d.get("city", "?"))
        city_visited = d.get("city", "?")
        base = d.get("base", city_visited)
        
        cities_list = d.get("cities", [])
        all_pois = []
        for city_stop in cities_list:
            all_pois.extend(city_stop.get("attractions", []))
        
        poi_names = ", ".join(a.get("name") or "Unknown" for a in all_pois if a.get("name"))
        hotel_names = ", ".join(h.get("name") or "?" for h in d.get("hotels", []) if h.get("name"))
        
        lunch_restaurant = d.get("lunch_restaurant")
        lunch_name = lunch_restaurant.get("name", "") if lunch_restaurant else ""

        dinner_restaurant = d.get("dinner_restaurant")
        dinner_name = dinner_restaurant.get("name", "") if dinner_restaurant else ""
        
        driving_km = d.get("driving_km", 0)
        driving_hours = d.get("driving_hours", 0)
        
        row_data = {
            "Day": d["day"],
            "City": city_visited,
            "POIs": poi_names,
            "Hotels": hotel_names,
            "Lunch": lunch_name,
            "Dinner": dinner_name
        }
        
        if is_car_mode:
            row_data["Type"] = day_type.replace("_", " ").title()
            row_data["Base"] = base
            row_data["Driving (km)"] = driving_km
            row_data["Drive Time (h)"] = driving_hours
        
        rows.append(row_data)
    
    df = pd.DataFrame(rows)
    
    # Reorder columns for car mode
    if is_car_mode:
        col_order = ["Day", "Type", "Base", "City", "Driving (km)", "Drive Time (h)", "POIs", "Hotels", "Lunch", "Dinner"]
        df = df[[c for c in col_order if c in df.columns]]
    
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Itinerary")
        
        # Summary sheet
        summary_data = {
            "Trip Type": ["Road Trip (Car)" if is_car_mode else "Walking/Transit"],
            "Start": [ordered_cities[0] if ordered_cities else "?"],
            "End": [ordered_cities[-1] if len(ordered_cities) > 1 else ordered_cities[0]],
            "Days": [days],
            "Base Cities": [len(ordered_cities) if is_car_mode else "N/A"],
            "Total Driving (km)": [sum(d.get('driving_km', 0) for d in itinerary)] if is_car_mode else ["N/A"],
            "Budget": [prefs.get("budget", "?")],
            "Pace": [prefs.get("pace", "?")]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
    
    bio.seek(0)
    return bio

def save_trip(result, prefs, ordered_cities, days):
    """Save trip to file"""
    from datetime import datetime
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{TRIPS_DIR}/roadtrip_{ts}.json"
    
    parsed_requests = result.get("parsed_requests", {})
    
    payload = {
        "created_at": ts,
        "trip_type": "car_road_trip",
        "start_end_text": " to ".join(ordered_cities[:2]) if len(ordered_cities) >= 2 else ordered_cities[0],
        "days": days,
        "preferences": prefs,
        "ordered_cities": ordered_cities,
        "base_cities": result.get("base_cities", ordered_cities),
        "special_requests": prefs.get("notes", ""),
        "parsed_requests": parsed_requests,
        "result": result
    }
    
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    st.success(f"✅ Saved road trip: {fname}")
