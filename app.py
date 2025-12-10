"""
Andalusia Road Trip Planner - Main Application
Optimized for car-based travel with base cities and day trips
"""

import streamlit as st
import json
import os

# Page configuration
st.set_page_config(
    page_title="Wanderlust - Andalusia Road Trip Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


# ✅ OPTIMIZED: Cache data loading to prevent reloading on every interaction
@st.cache_data(ttl=3600)  # Cache for 1 hour (3600 seconds)
def load_cached_json(filename):
    """
    Load JSON with caching to improve performance
    
    Benefits:
    - Loads data only once per hour (or until cache is cleared)
    - Reduces memory usage
    - Speeds up app considerably
    - Critical for cloud deployment (free tiers have limited RAM)
    
    Args:
        filename: Name of the JSON file to load
        
    Returns:
        List of data from JSON file
    """
    # Try current directory first, then data/ subdirectory
    if os.path.exists(filename):
        filepath = filename
    elif os.path.exists(f"data/{filename}"):
        filepath = f"data/{filename}"
    else:
        # print(f"❌ File not found: {filename} (checked current dir and data/ subdir)")
        return []
    
    # Load the file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        file_size = os.path.getsize(filepath)
        # print(f"✅ Loaded {filepath} ({len(data):,} records, {file_size / 1024:.1f} KB)")
        
        return data
        
    except json.JSONDecodeError as e:
        # print(f"❌ JSON decode error in {filepath}: {str(e)}")
        return []
    except Exception as e:
        # print(f"❌ Error loading {filepath}: {str(e)}")
        return []


def show_my_trips():
    """Display saved trips"""
    trips_dir = "trips"
    
    if not os.path.exists(trips_dir):
        st.info("📭 No saved trips yet. Create your first road trip!")
        return
    
    trip_files = [f for f in os.listdir(trips_dir) if f.endswith('.json')]
    
    if not trip_files:
        st.info("📭 No saved trips yet. Create your first road trip!")
        return
    
    st.write(f"Found {len(trip_files)} saved trips:")
    
    for trip_file in sorted(trip_files, reverse=True):
        try:
            filepath = os.path.join(trips_dir, trip_file)
            with open(filepath, 'r', encoding='utf-8') as f:
                trip_data = json.load(f)
            
            with st.expander(f"🚗 {trip_data.get('start_end_text', 'Unknown')} - {trip_data.get('created_at', 'Unknown date')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Days", trip_data.get('days', '?'))
                with col2:
                    cities = trip_data.get('ordered_cities', [])
                    st.metric("Cities", len(cities))
                with col3:
                    st.metric("Budget", trip_data.get('preferences', {}).get('budget', '?'))
                
                st.write("**Route:**", " → ".join(trip_data.get('ordered_cities', [])))
                
                # Action buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(f"📂 Load Trip", key=f"load_{trip_file}"):
                        st.info("🔄 Loading saved trip... (Feature coming soon)")
                with btn_col2:
                    if st.button(f"🗑️ Delete", key=f"del_{trip_file}"):
                        os.remove(filepath)
                        st.success(f"Deleted {trip_file}")
                        st.rerun()
        
        except Exception as e:
            st.error(f"Error loading {trip_file}: {str(e)}")


def show_preferences():
    """Display and edit preferences"""
    
    prefs_file = "preferences.json"
    
    # Load existing preferences
    default_prefs = {
        "default_trip_type": "Point-to-point",
        "default_budget": "mid-range",
        "default_pace": "medium",
        "max_km_per_day": 300,
        "poi_categories": ["history", "architecture", "museums", "nature", "beaches", "neighborhoods", "viewpoints"],
        "hotel_platform": "Any",
        "max_price_per_night": 150,
        "min_poi_rating": 3.5,
        "max_same_category_per_day": 2
    }
    
    if os.path.exists(prefs_file):
        try:
            with open(prefs_file, 'r', encoding='utf-8') as f:
                saved_prefs = json.load(f)
                default_prefs.update(saved_prefs)
        except:
            pass
    
    st.markdown("### 🚗 Road Trip Preferences")
    
    with st.form("preferences_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Default Settings**")
            
            trip_type_options = ["Point-to-point", "Circular", "Star/Hub"]
            default_trip = default_prefs.get("default_trip_type", "Point-to-point")
            
            trip_type = st.selectbox(
                "Trip Type",
                trip_type_options,
                index=trip_type_options.index(default_trip) if default_trip in trip_type_options else 0,
                help="Point-to-point: A→B | Circular: Loop back to start | Star/Hub: Day trips from one base ⭐"
            )
            
            budget = st.selectbox(
                "Budget",
                ["budget", "mid-range", "luxury"],
                index=["budget", "mid-range", "luxury"].index(default_prefs["default_budget"])
            )
            
            pace = st.selectbox(
                "Travel Pace",
                ["easy", "medium", "fast"],
                index=["easy", "medium", "fast"].index(default_prefs["default_pace"])
            )
            
            max_km = st.number_input(
                "Max driving km per day",
                min_value=100,
                max_value=500,
                value=default_prefs["max_km_per_day"],
                step=50
            )
        
        with col2:
            st.markdown("**Accommodation**")
            
            platform = st.selectbox(
                "Preferred Platform",
                ["Any", "Booking", "Airbnb"],
                index=["Any", "Booking", "Airbnb"].index(default_prefs["hotel_platform"])
            )
            
            max_price = st.number_input(
                "Max price per night (€)",
                min_value=0,
                max_value=500,
                value=default_prefs["max_price_per_night"],
                step=10,
                help="0 = no limit"
            )
            
            st.markdown("**Attractions**")
            
            min_rating = st.slider(
                "Minimum POI rating",
                min_value=0.0,
                max_value=5.0,
                value=default_prefs.get("min_poi_rating", 3.5),
                step=0.5,
                help="⭐ Filter attractions by rating (5 stars = excellent)"
            )
            
            max_same = st.slider(
                "Max same category per day",
                min_value=1,
                max_value=4,
                value=default_prefs["max_same_category_per_day"]
            )
        
        st.markdown("**POI Categories**")
        categories = st.multiselect(
            "Preferred attraction types",
            ["art", "museums", "history", "architecture", "parks", "nature",
             "gardens", "beaches", "viewpoints", "markets", "religious", "castles",
             "palaces", "neighborhoods", "food & tapas", "wine & bodegas", "activities", "entertainment"],
            default=default_prefs["poi_categories"],
            help="These categories are mapped to database POIs automatically"
        )
        
        submitted = st.form_submit_button("💾 Save Preferences", use_container_width=True)
        
        if submitted:
            new_prefs = {
                "default_trip_type": trip_type,
                "default_budget": budget,
                "default_pace": pace,
                "max_km_per_day": max_km,
                "poi_categories": categories,
                "hotel_platform": platform,
                "max_price_per_night": max_price,
                "min_poi_rating": min_rating,
                "max_same_category_per_day": max_same
            }
            
            with open(prefs_file, 'w', encoding='utf-8') as f:
                json.dump(new_prefs, f, ensure_ascii=False, indent=2)
            
            st.success("✅ Preferences saved!")
            st.rerun()
    
    # Cache management section
    st.markdown("---")
    st.markdown("### 🗑️ Cache Management")
    st.write("Clear cached data to force reload from disk:")
    
    if st.button("🔄 Clear Data Cache"):
        st.cache_data.clear()
        st.success("✅ Cache cleared! Data will be reloaded on next interaction.")
        st.info("💡 Use this if you've updated your JSON data files")


def main():
    """Main application entry point"""
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🌍 Wanderlust")
        st.markdown("_Your Personal Trip Planner_")
        st.markdown("---")
        
        # Navigation
        st.markdown("**Navigation**")
        page = st.radio(
            "Go to:",
            ["Plan a Trip", "My Trips", "Preferences"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.caption("Traveller - plan your perfect journey")
    
    # ✅ OPTIMIZED: Load data using cache
    # This will only load once per hour instead of on every page interaction
    attractions_data = load_cached_json("andalusia_attractions_filtered.json")
    hotels_data = load_cached_json("andalusia_hotels_osm.json")
    restaurants_data = load_cached_json("restaurants_andalusia.json")
    
    # Validate critical data
    if not attractions_data:
        st.error("❌ CRITICAL: No attractions data loaded! Cannot generate trips.")
        st.info("💡 Make sure `andalusia_attractions_filtered.json` is in the current directory or in the `data/` folder")
        st.stop()
    
    # Route to appropriate page
    if page == "Plan a Trip":
        from trip_planner_page import show_trip_planner_full
        show_trip_planner_full(attractions_data, hotels_data, restaurants_data)
    
    elif page == "My Trips":
        st.title("📚 My Saved Trips")
        show_my_trips()
    
    elif page == "Preferences":
        st.title("⚙️ Preferences")
        show_preferences()


if __name__ == "__main__":
    main()
