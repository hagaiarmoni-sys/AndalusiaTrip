# ADD THIS TO YOUR STREAMLIT APP (e.g., in sidebar or as an expander)

import streamlit as st
from compound_attractions_handler import COMPOUND_LOAD_STATUS, COMPOUND_CONFIG

# Option 1: Show in sidebar (always visible)
with st.sidebar:
    if COMPOUND_LOAD_STATUS:
        if "✅" in COMPOUND_LOAD_STATUS:
            st.success(COMPOUND_LOAD_STATUS)
            st.caption(f"Covering {len([k for k in COMPOUND_CONFIG.keys() if k not in ['clustering_rules', 'neighborhoods']])} cities")
        else:
            st.warning(COMPOUND_LOAD_STATUS)

# Option 2: Show in expander (collapsed by default)
with st.expander("🔧 System Status"):
    st.write("**Compound Attractions Handler**")
    if COMPOUND_LOAD_STATUS:
        if "✅" in COMPOUND_LOAD_STATUS:
            st.success(COMPOUND_LOAD_STATUS)
            cities = [k for k in COMPOUND_CONFIG.keys() if k not in ['clustering_rules', 'neighborhoods']]
            st.info(f"Active for: {', '.join(cities)}")
        else:
            st.error(COMPOUND_LOAD_STATUS)
    else:
        st.warning("Compound attractions handler not loaded")

# Option 3: Show only if there's an error (minimal UI clutter)
if COMPOUND_LOAD_STATUS and "⚠️" in COMPOUND_LOAD_STATUS:
    st.warning(COMPOUND_LOAD_STATUS)
