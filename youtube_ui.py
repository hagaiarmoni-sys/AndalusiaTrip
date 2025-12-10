"""
YouTube UI Helper for Streamlit
Displays embedded YouTube videos in the Andalusia Travel App
"""

import streamlit as st
import json
import os

# ============================================================================
# VIDEO URL CONVERSION
# ============================================================================

def convert_to_embed_url(youtube_url: str) -> str:
    """
    Converts a standard YouTube watch URL to an embed URL.
    
    Args:
        youtube_url: The URL from the JSON file 
                     (e.g., https://www.youtube.com/watch?v=XXXX or https://youtu.be/XXXX)
    
    Returns:
        The embed-compatible URL (e.g., https://www.youtube.com/embed/XXXX)
    """
    if not youtube_url:
        return ""
    
    # 1. Handle standard 'watch' link
    if 'watch?v=' in youtube_url:
        return youtube_url.replace('watch?v=', 'embed/')
    
    # 2. Handle short 'youtu.be' link
    elif 'youtu.be/' in youtube_url:
        # Extract the video ID after the last slash
        video_id = youtube_url.split('/')[-1].split('?')[0]
        return f"https://www.youtube.com/embed/{video_id}"
    
    # 3. If it's already an embed link, return as is
    elif 'embed/' in youtube_url:
        return youtube_url
    
    return youtube_url


def get_video_id(youtube_url: str) -> str:
    """Extract video ID from any YouTube URL format"""
    if not youtube_url:
        return ""
    
    if 'watch?v=' in youtube_url:
        return youtube_url.split('watch?v=')[1].split('&')[0]
    elif 'youtu.be/' in youtube_url:
        return youtube_url.split('/')[-1].split('?')[0]
    elif 'embed/' in youtube_url:
        return youtube_url.split('embed/')[1].split('?')[0]
    
    return ""


# ============================================================================
# VIDEO DATABASE LOADING
# ============================================================================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_youtube_database():
    """Load YouTube videos database with caching"""
    # Try multiple possible locations
    possible_paths = [
        "youtube_videos_db.json",
        "data/youtube_videos_db.json",
        os.path.join(os.path.dirname(__file__), "data", "youtube_videos_db.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('destinations', {})
            except Exception as e:
                pass  # Silently continue to next path
    
    return {}


def normalize_city_name(city_name: str) -> str:
    """Normalize city name for matching (lowercase, no accents)"""
    if not city_name:
        return ""
    
    import unicodedata
    nfd = unicodedata.normalize('NFD', city_name)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return without_accents.lower().strip()


def get_videos_for_city(city_name: str, max_videos: int = 2) -> list:
    """
    Get YouTube videos for a city
    
    Args:
        city_name: City name (with or without accents)
        max_videos: Maximum number of videos to return
    
    Returns:
        List of video dictionaries
    """
    db = load_youtube_database()
    
    if not db:
        return []
    
    city_norm = normalize_city_name(city_name)
    
    # Try exact match first
    for db_city, videos in db.items():
        if normalize_city_name(db_city) == city_norm:
            return videos[:max_videos]
    
    # Try partial match
    for db_city, videos in db.items():
        if city_norm in normalize_city_name(db_city) or normalize_city_name(db_city) in city_norm:
            return videos[:max_videos]
    
    return []


# ============================================================================
# STREAMLIT DISPLAY COMPONENTS
# ============================================================================

def display_city_video_simple(city_name: str):
    """
    Display a single YouTube video for a city using st.video()
    Simple version - just the video player
    """
    videos = get_videos_for_city(city_name, max_videos=1)
    
    if videos:
        video = videos[0]
        watch_url = video.get('watch_url', '')
        title = video.get('title', 'Video')
        channel = video.get('channel', '')
        
        if watch_url:
            st.video(watch_url)
            st.caption(f"📺 {title} • {channel}")
            return True
    
    return False


def display_city_video_card(city_name: str, show_title: bool = True):
    """
    Display YouTube video in a nice card format with thumbnail preview
    
    Args:
        city_name: City to show video for
        show_title: Whether to show "🎬 Watch a preview" header
    """
    videos = get_videos_for_city(city_name, max_videos=1)
    
    if not videos:
        return False
    
    video = videos[0]
    watch_url = video.get('watch_url', '')
    title = video.get('title', 'Video')
    channel = video.get('channel', '')
    thumbnail_url = video.get('thumbnail_url', '')
    
    if not watch_url:
        return False
    
    if show_title:
        st.markdown("#### 🎬 Watch a preview")
    
    # Option 1: Use st.video (native Streamlit - recommended)
    st.video(watch_url)
    
    # Show video info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"**{title}**")
        st.caption(f"📺 {channel}")
    with col2:
        st.link_button("▶️ YouTube", watch_url, use_container_width=True)
    
    return True


def display_city_video_embed(city_name: str, width: int = 560, height: int = 315):
    """
    Display YouTube video using iframe embed (more customizable)
    
    Args:
        city_name: City to show video for
        width: Video width in pixels
        height: Video height in pixels
    """
    videos = get_videos_for_city(city_name, max_videos=1)
    
    if not videos:
        return False
    
    video = videos[0]
    watch_url = video.get('watch_url', '')
    title = video.get('title', 'Video')
    channel = video.get('channel', '')
    
    if not watch_url:
        return False
    
    embed_url = convert_to_embed_url(watch_url)
    
    st.markdown("#### 🎬 Watch a preview")
    
    # Iframe embed
    st.markdown(f'''
        <iframe 
            width="{width}" 
            height="{height}" 
            src="{embed_url}" 
            frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen>
        </iframe>
    ''', unsafe_allow_html=True)
    
    st.caption(f"**{title}** • 📺 {channel}")
    
    return True


def display_multiple_videos(city_name: str, max_videos: int = 2):
    """
    Display multiple videos in a row for a city
    
    Args:
        city_name: City to show videos for
        max_videos: Maximum number of videos to show
    """
    videos = get_videos_for_city(city_name, max_videos=max_videos)
    
    if not videos:
        return False
    
    st.markdown("#### 🎬 Video Previews")
    
    # Create columns based on number of videos
    cols = st.columns(len(videos))
    
    for idx, (col, video) in enumerate(zip(cols, videos)):
        with col:
            watch_url = video.get('watch_url', '')
            title = video.get('title', 'Video')
            channel = video.get('channel', '')
            
            if watch_url:
                st.video(watch_url)
                
                # Truncate long titles
                display_title = title[:40] + "..." if len(title) > 40 else title
                st.caption(f"**{display_title}**")
                st.caption(f"📺 {channel}")
    
    return True


def display_video_expander(city_name: str, expanded: bool = False):
    """
    Display YouTube video inside an expander (collapsible)
    Good for keeping the UI clean
    
    Args:
        city_name: City to show video for
        expanded: Whether expander is open by default
    """
    videos = get_videos_for_city(city_name, max_videos=1)
    
    if not videos:
        return False
    
    video = videos[0]
    watch_url = video.get('watch_url', '')
    title = video.get('title', 'Video')
    channel = video.get('channel', '')
    
    if not watch_url:
        return False
    
    with st.expander(f"🎬 Watch: {title[:50]}...", expanded=expanded):
        st.video(watch_url)
        st.caption(f"📺 Channel: {channel}")
        st.link_button("▶️ Open in YouTube", watch_url)
    
    return True


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test the module
    st.title("🎬 YouTube Video Test")
    
    test_cities = ["Seville", "Granada", "Córdoba", "Málaga", "Ronda"]
    
    for city in test_cities:
        st.markdown(f"### {city}")
        
        videos = get_videos_for_city(city)
        if videos:
            st.success(f"Found {len(videos)} video(s)")
            display_city_video_card(city)
        else:
            st.warning(f"No videos found for {city}")
        
        st.markdown("---")
