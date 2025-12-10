"""
Date Picker System for Trip Planner
Replaces duration dropdown with calendar date selection
"""

import streamlit as st
from datetime import datetime, timedelta

def create_date_picker():
    """
    Creates a single date range picker UI
    Returns: (start_date, end_date, num_days)
    """
    
    # Single date range picker (no header - added in calling code)
    min_date = datetime.now().date()
    default_start = min_date + timedelta(days=30)  # Default: 1 month from now
    default_end = default_start + timedelta(days=6)  # Default: 7-day trip
    
    # Streamlit's date_input can accept a tuple for date range!
    date_range = st.date_input(
        "📅 Trip Dates (Start → End)",
        value=(default_start, default_end),
        min_value=min_date,
        help="Select your trip start and end dates",
        key="trip_date_range"
    )
    
    # Handle the date range
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        
        # Calculate number of days
        if end_date > start_date:
            num_days = (end_date - start_date).days + 1  # +1 to include both start and end day
        else:
            num_days = 1
            st.warning("⚠️ End date must be after start date!")
        
        # Show trip duration with ACTUAL selected dates
        st.info(f"✈️ **Trip Duration:** {num_days} days ({start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')})")
        
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        # User only selected start date
        start_date = date_range[0]
        end_date = start_date + timedelta(days=6)  # Default to 7 days
        num_days = 7
        st.warning("⚠️ Please select an end date by clicking on the calendar again!")
        
    else:
        # Fallback
        start_date = date_range if hasattr(date_range, 'year') else default_start
        end_date = start_date + timedelta(days=6)
        num_days = 7
    
    return start_date, end_date, num_days


def format_day_header(day_number, start_date):
    """
    Formats day header with date
    Example: "Day 1: 25 Aug 2024"
    """
    trip_date = start_date + timedelta(days=day_number - 1)
    date_str = trip_date.strftime('%d %b %Y')  # "25 Aug 2024"
    
    return f"Day {day_number}: {date_str}"


def format_day_header_with_weekday(day_number, start_date):
    """
    Formats day header with weekday and date
    Example: "Day 1 - Monday, 25 Aug 2024"
    """
    trip_date = start_date + timedelta(days=day_number - 1)
    weekday = trip_date.strftime('%A')  # "Monday"
    date_str = trip_date.strftime('%d %b %Y')  # "25 Aug 2024"
    
    return f"Day {day_number} - {weekday}, {date_str}"


# Example usage in your app:
"""
# In your main app file, REPLACE this:
days = st.selectbox("Duration (days)", [3, 4, 5, 6, 7, 8, 9, 10, 14])

# WITH this:
start_date, end_date, days = create_date_picker()

# Store dates in session state for use in document generation
st.session_state['start_date'] = start_date
st.session_state['end_date'] = end_date
"""

# For document generation:
"""
# In document_generator.py, when generating day headers:

# OLD:
day_header = f"Day {day_num}: {city}"

# NEW:
from datetime import timedelta
start_date = itinerary_params.get('start_date')  # Pass this to build_word_doc
trip_date = start_date + timedelta(days=day_num - 1)
date_str = trip_date.strftime('%d %b %Y')
day_header = f"Day {day_num} ({date_str}): {city}"
"""
