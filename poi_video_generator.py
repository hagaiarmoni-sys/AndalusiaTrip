"""
POI Slideshow Video Generator with Mini-Map
============================================

Creates a ~1 minute video slideshow from your itinerary POI photos.
Each POI shows for 3-4 seconds with:
- Title overlay (City • POI Name) in bottom-left
- Mini-map with route progress in bottom-right

Requirements:
    pip install pillow opencv-python numpy

Usage:
    from poi_video_generator import generate_poi_slideshow
    
    # From itinerary result
    generate_poi_slideshow(result, output_file="my_trip.mp4")

Author: Andalusia Travel App
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass 
class SlideshowConfig:
    """Configuration for slideshow video"""
    duration_per_slide: float = 1.5      # Seconds per POI (reduced from 3.5)
    fps: int = 24                         # Frames per second
    width: int = 1280                     # Video width
    height: int = 720                     # Video height
    transition_frames: int = 8            # Frames for fade transition (reduced)
    
    # Text overlay settings
    font_size: int = 32
    title_font_size: int = 48
    text_color: Tuple[int, int, int] = (255, 255, 255)  # White
    shadow_color: Tuple[int, int, int] = (0, 0, 0)      # Black shadow
    overlay_opacity: float = 0.6          # Background overlay opacity
    
    # Mini-map settings
    show_mini_map: bool = False           # DISABLED - map was not accurate
    mini_map_size: int = 200              # Size of mini-map (square)
    mini_map_margin: int = 20             # Margin from edge
    mini_map_opacity: float = 0.85        # Mini-map background opacity
    route_color: Tuple[int, int, int] = (255, 87, 34)    # Orange route line
    completed_color: Tuple[int, int, int] = (76, 175, 80) # Green completed
    marker_color: Tuple[int, int, int] = (233, 30, 99)   # Pink marker
    
    # Paths
    photos_dir: str = "data/photos"
    maps_dir: str = "data/maps"
    mini_map_file: str = "andalusia_mini_map.png"


# ============================================================================
# PATH CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PHOTOS_DIR = os.path.join(DATA_DIR, 'photos')
MAPS_DIR = os.path.join(DATA_DIR, 'maps')


# ============================================================================
# CITY COORDINATES (for mini-map)
# ============================================================================

CITY_COORDS = {
    "málaga": (36.7213, -4.4214),
    "malaga": (36.7213, -4.4214),
    "granada": (37.1773, -3.5986),
    "seville": (37.3891, -5.9845),
    "sevilla": (37.3891, -5.9845),
    "córdoba": (37.8882, -4.7794),
    "cordoba": (37.8882, -4.7794),
    "cádiz": (36.5271, -6.2886),
    "cadiz": (36.5271, -6.2886),
    "ronda": (36.7462, -5.1619),
    "marbella": (36.5099, -4.8862),
    "nerja": (36.7580, -3.8765),
    "jerez": (36.6866, -6.1361),
    "jerez de la frontera": (36.6866, -6.1361),
    "antequera": (37.0194, -4.5603),
    "almería": (36.8340, -2.4637),
    "almeria": (36.8340, -2.4637),
    "tarifa": (36.0143, -5.6044),
    "gibraltar": (36.1408, -5.3536),
    "frigiliana": (36.7891, -3.8956),
    "mijas": (36.5959, -4.6370),
    "arcos de la frontera": (36.7508, -5.8069),
    "zahara de la sierra": (36.8403, -5.3907),
    "grazalema": (36.7616, -5.3685),
    "setenil de las bodegas": (36.8621, -5.1818),
    "olvera": (36.9354, -5.2688),
    "úbeda": (38.0133, -3.3706),
    "ubeda": (38.0133, -3.3706),
    "baeza": (37.9939, -3.4714),
    "carmona": (37.4714, -5.6419),
    "osuna": (37.2375, -5.1028),
    "écija": (37.5417, -5.0828),
    "priego de córdoba": (37.4386, -4.1961),
    "lucena": (37.4089, -4.4853),
    "cazorla": (37.9133, -3.0006),
    "mojácar": (37.1389, -1.8506),
    "cabo de gata": (36.7261, -2.1903),
    "el rocío": (37.1333, -6.4833),
    "aracena": (37.8933, -6.5633),
    "huelva": (37.2614, -6.9447),
}

# Andalusia map bounds - CALIBRATED to match andalusia_mini_map.png
# Map image is 2000x890 pixels (aspect ratio 2.247:1)
# Visible landmarks used for calibration:
# - Left edge: Olimão/Faro (Portugal) area
# - Right edge: Cartagena/Murcia area  
# - Top: Badajoz/Mérida area
# - Bottom: Gibraltar/Strait area
ANDALUSIA_BOUNDS = {
    "min_lat": 35.85,   # Bottom edge (Gibraltar strait)
    "max_lat": 39.05,   # Top edge (above Badajoz)
    "min_lon": -8.7,    # Left edge (Portugal coast)
    "max_lon": -0.6     # Right edge (past Cartagena)
}


# ============================================================================
# PHOTO LOADING
# ============================================================================

def find_photo_path(poi: Dict, photos_dir: str = None) -> Optional[str]:
    """Find the photo file for a POI."""
    if photos_dir is None:
        photos_dir = PHOTOS_DIR
    
    # Option 1: Use local_photo_path directly
    local_path = poi.get('local_photo_path', '')
    if local_path:
        local_path = local_path.replace('\\', os.sep).replace('/', os.sep)
        
        if os.path.exists(local_path):
            return local_path
        
        filename = os.path.basename(local_path)
        full_path = os.path.join(photos_dir, filename)
        if os.path.exists(full_path):
            return full_path
    
    # Option 2: Use place_id to construct filename
    place_id = poi.get('place_id', '')
    if place_id:
        for ext in ['.jpg', '.png', '.jpeg']:
            photo_path = os.path.join(photos_dir, f"{place_id}{ext}")
            if os.path.exists(photo_path):
                return photo_path
    
    return None


def load_and_resize_image(image_path: str, target_width: int, target_height: int):
    """Load an image and resize it to fit the target dimensions (center crop)."""
    try:
        from PIL import Image
        
        img = Image.open(image_path)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        img_aspect = img.width / img.height
        target_aspect = target_width / target_height
        
        if img_aspect > target_aspect:
            new_height = target_height
            new_width = int(target_height * img_aspect)
        else:
            new_width = target_width
            new_height = int(target_width / img_aspect)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        
        img = img.crop((left, top, right, bottom))
        
        return img
        
    except Exception as e:
        print(f"⚠️ Error loading image {image_path}: {e}")
        return None


def create_placeholder_image(width: int, height: int, text: str = "No Photo"):
    """Create a placeholder image when no photo is available."""
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (width, height), color=(40, 44, 52))
    draw = ImageDraw.Draw(img)
    
    for y in range(height):
        r = int(40 + (y / height) * 30)
        g = int(44 + (y / height) * 20)
        b = int(52 + (y / height) * 40)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
        except:
            font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), text, fill=(150, 150, 150), font=font)
    
    return img


# ============================================================================
# MINI-MAP RENDERING
# ============================================================================

def load_mini_map_base(config: SlideshowConfig) -> Optional['Image']:
    """
    Load the full Andalusia mini-map image (uncropped).
    
    Args:
        config: SlideshowConfig
    
    Returns:
        Full mini-map image (will be cropped per-frame)
    """
    from PIL import Image
    
    # Try to find the map file
    map_paths = [
        os.path.join(config.maps_dir, config.mini_map_file),
        os.path.join(MAPS_DIR, config.mini_map_file),
        os.path.join(DATA_DIR, 'maps', config.mini_map_file),
        os.path.join(BASE_DIR, 'data', 'maps', config.mini_map_file),
    ]
    
    for map_path in map_paths:
        if os.path.exists(map_path):
            try:
                img = Image.open(map_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                return img
            except Exception as e:
                print(f"⚠️ Error loading mini-map from {map_path}: {e}")
    
    print(f"⚠️ Mini-map not found. Tried: {map_paths}")
    return None


def crop_map_to_bounds(base_map: 'Image', window_bounds: dict, config: SlideshowConfig) -> Optional['Image']:
    """
    Crop the base map to show only the window bounds area.
    
    Args:
        base_map: Full Andalusia map image
        window_bounds: Bounding box to show
        config: SlideshowConfig
    
    Returns:
        Cropped and resized mini-map
    """
    from PIL import Image
    
    if base_map is None:
        return None
    
    try:
        img = base_map.copy()
        orig_width, orig_height = img.size
        
        # Calculate pixel coordinates for crop based on full Andalusia bounds
        full_bounds = ANDALUSIA_BOUNDS
        
        # Normalize window bounds to 0-1 range relative to full map
        left_norm = (window_bounds["min_lon"] - full_bounds["min_lon"]) / (full_bounds["max_lon"] - full_bounds["min_lon"])
        right_norm = (window_bounds["max_lon"] - full_bounds["min_lon"]) / (full_bounds["max_lon"] - full_bounds["min_lon"])
        top_norm = (full_bounds["max_lat"] - window_bounds["max_lat"]) / (full_bounds["max_lat"] - full_bounds["min_lat"])
        bottom_norm = (full_bounds["max_lat"] - window_bounds["min_lat"]) / (full_bounds["max_lat"] - full_bounds["min_lat"])
        
        # Convert to pixels
        left = int(left_norm * orig_width)
        right = int(right_norm * orig_width)
        top = int(top_norm * orig_height)
        bottom = int(bottom_norm * orig_height)
        
        # Clamp to image bounds
        left = max(0, min(orig_width - 1, left))
        right = max(left + 1, min(orig_width, right))
        top = max(0, min(orig_height - 1, top))
        bottom = max(top + 1, min(orig_height, bottom))
        
        # Crop
        img = img.crop((left, top, right, bottom))
        
        # Resize to mini-map size
        img = img.resize((config.mini_map_size, config.mini_map_size), Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        print(f"⚠️ Error cropping mini-map: {e}")
        return None


def load_mini_map(config: SlideshowConfig, route_bounds: dict = None) -> Optional['Image']:
    """
    Load the Andalusia mini-map image and crop to route bounds.
    (Legacy function - kept for compatibility)
    
    Args:
        config: SlideshowConfig
        route_bounds: Bounding box for the route (if None, uses full Andalusia)
    
    Returns:
        Cropped and resized mini-map image
    """
    from PIL import Image
    
    # Try to find the map file
    map_paths = [
        os.path.join(config.maps_dir, config.mini_map_file),
        os.path.join(MAPS_DIR, config.mini_map_file),
        os.path.join(DATA_DIR, 'maps', config.mini_map_file),
        os.path.join(BASE_DIR, 'data', 'maps', config.mini_map_file),
    ]
    
    for map_path in map_paths:
        if os.path.exists(map_path):
            try:
                img = Image.open(map_path)
                orig_width, orig_height = img.size
                
                # If we have route bounds, crop the map to that area
                if route_bounds:
                    # Calculate pixel coordinates for crop based on full Andalusia bounds
                    full_bounds = ANDALUSIA_BOUNDS
                    
                    # Normalize route bounds to 0-1 range relative to full map
                    left_norm = (route_bounds["min_lon"] - full_bounds["min_lon"]) / (full_bounds["max_lon"] - full_bounds["min_lon"])
                    right_norm = (route_bounds["max_lon"] - full_bounds["min_lon"]) / (full_bounds["max_lon"] - full_bounds["min_lon"])
                    top_norm = (full_bounds["max_lat"] - route_bounds["max_lat"]) / (full_bounds["max_lat"] - full_bounds["min_lat"])
                    bottom_norm = (full_bounds["max_lat"] - route_bounds["min_lat"]) / (full_bounds["max_lat"] - full_bounds["min_lat"])
                    
                    # Convert to pixels
                    left = int(left_norm * orig_width)
                    right = int(right_norm * orig_width)
                    top = int(top_norm * orig_height)
                    bottom = int(bottom_norm * orig_height)
                    
                    # Clamp to image bounds
                    left = max(0, min(orig_width - 1, left))
                    right = max(0, min(orig_width, right))
                    top = max(0, min(orig_height - 1, top))
                    bottom = max(0, min(orig_height, bottom))
                    
                    # Ensure we have a valid crop area
                    if right > left and bottom > top:
                        img = img.crop((left, top, right, bottom))
                
                # Resize to mini-map size
                img = img.resize((config.mini_map_size, config.mini_map_size), Image.Resampling.LANCZOS)
                
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                return img
                
            except Exception as e:
                print(f"⚠️ Error loading mini-map from {map_path}: {e}")
    
    print(f"⚠️ Mini-map not found. Tried: {map_paths}")
    return None


def lat_lon_to_pixel(lat: float, lon: float, map_size: int, bounds: dict = None) -> Tuple[int, int]:
    """Convert lat/lon to pixel coordinates on the mini-map."""
    if bounds is None:
        bounds = ANDALUSIA_BOUNDS
    
    # Normalize to 0-1 range
    x_norm = (lon - bounds["min_lon"]) / (bounds["max_lon"] - bounds["min_lon"])
    y_norm = (bounds["max_lat"] - lat) / (bounds["max_lat"] - bounds["min_lat"])  # Flip Y
    
    # Convert to pixels
    x = int(x_norm * map_size)
    y = int(y_norm * map_size)
    
    # Clamp to valid range
    x = max(0, min(map_size - 1, x))
    y = max(0, min(map_size - 1, y))
    
    return x, y


def calculate_route_bounds(coords: List[Tuple[float, float]], padding: float = 0.08) -> dict:
    """
    Calculate bounding box for the route with padding.
    
    Args:
        coords: List of (lat, lon) tuples
        padding: Percentage of padding to add around the route (0.08 = 8%)
    
    Returns:
        Dictionary with min_lat, max_lat, min_lon, max_lon
    """
    valid_coords = [c for c in coords if c is not None]
    
    if not valid_coords:
        return ANDALUSIA_BOUNDS
    
    lats = [c[0] for c in valid_coords]
    lons = [c[1] for c in valid_coords]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Calculate ranges
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    
    # Ensure minimum range (avoid too much zoom on very short routes)
    min_range = 0.2  # Small for tighter zoom
    if lat_range < min_range:
        center_lat = (min_lat + max_lat) / 2
        min_lat = center_lat - min_range / 2
        max_lat = center_lat + min_range / 2
        lat_range = min_range
    
    if lon_range < min_range:
        center_lon = (min_lon + max_lon) / 2
        min_lon = center_lon - min_range / 2
        max_lon = center_lon + min_range / 2
        lon_range = min_range
    
    # Make it square (use the larger range for both)
    max_range = max(lat_range, lon_range)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    # Add padding
    padded_range = max_range * (1 + padding * 2)
    
    return {
        "min_lat": center_lat - padded_range / 2,
        "max_lat": center_lat + padded_range / 2,
        "min_lon": center_lon - padded_range / 2,
        "max_lon": center_lon + padded_range / 2
    }


def calculate_window_bounds(all_coords: List[Tuple[float, float]], current_index: int, window_size: int = 12, padding: float = 0.2) -> dict:
    """
    Calculate bounding box for a sliding window of POIs around the current position.
    Shows current POI plus several before/after for context.
    
    Args:
        all_coords: List of all (lat, lon) tuples
        current_index: Current POI index
        window_size: Number of POIs to include in the window (default 12)
        padding: Percentage of padding around the window
    
    Returns:
        Dictionary with min_lat, max_lat, min_lon, max_lon
    """
    valid_coords = [c for c in all_coords if c is not None]
    
    if not valid_coords:
        return ANDALUSIA_BOUNDS
    
    # If we have few POIs, just show all of them
    if len(valid_coords) <= window_size:
        window_coords = valid_coords
    else:
        # Get indices for window around current position
        half_window = window_size // 2
        start_idx = max(0, current_index - half_window)
        end_idx = min(len(all_coords), current_index + half_window + 1)
        
        # Collect valid coords in this range
        window_coords = []
        for i in range(start_idx, end_idx):
            if i < len(all_coords) and all_coords[i] is not None:
                window_coords.append(all_coords[i])
        
        # If still too few, add more
        if len(window_coords) < 3:
            window_coords = valid_coords[:window_size]
    
    lats = [c[0] for c in window_coords]
    lons = [c[1] for c in window_coords]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    
    # Calculate ranges
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon
    
    # Ensure minimum range for readable map - MUCH LARGER for good context
    min_range = 1.0  # ~100km minimum view
    if lat_range < min_range:
        center_lat = (min_lat + max_lat) / 2
        min_lat = center_lat - min_range / 2
        max_lat = center_lat + min_range / 2
        lat_range = min_range
    
    if lon_range < min_range:
        center_lon = (min_lon + max_lon) / 2
        min_lon = center_lon - min_range / 2
        max_lon = center_lon + min_range / 2
        lon_range = min_range
    
    # Make it square
    max_range = max(lat_range, lon_range)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    # Add padding
    padded_range = max_range * (1 + padding * 2)
    
    return {
        "min_lat": center_lat - padded_range / 2,
        "max_lat": center_lat + padded_range / 2,
        "min_lon": center_lon - padded_range / 2,
        "max_lon": center_lon + padded_range / 2
    }


def get_poi_coordinates(poi: Dict) -> Optional[Tuple[float, float]]:
    """Get coordinates for a POI (from POI data or city lookup)."""
    # Try to get from POI coordinates
    coords = poi.get('coordinates', {})
    lat = coords.get('lat') or coords.get('latitude')
    lon = coords.get('lon') or coords.get('lng') or coords.get('longitude')
    
    if lat and lon:
        return (float(lat), float(lon))
    
    # Try top-level lat/lon
    lat = poi.get('lat')
    lon = poi.get('lon') or poi.get('lng')
    
    if lat and lon:
        return (float(lat), float(lon))
    
    # Fallback to city coordinates
    city = poi.get('city', '').lower()
    if city in CITY_COORDS:
        return CITY_COORDS[city]
    
    return None


def create_mini_map_overlay(
    base_map: 'Image',
    all_coords: List[Tuple[float, float]],
    current_index: int,
    config: SlideshowConfig,
    route_bounds: dict = None
) -> 'Image':
    """
    Create a mini-map overlay showing route progress.
    The route line grows progressively - only showing the path up to current POI.
    
    Args:
        base_map: Base mini-map image (already cropped to route area)
        all_coords: List of (lat, lon) tuples for all POIs
        current_index: Current POI index (0-based)
        config: SlideshowConfig
        route_bounds: Bounding box used for the map (for coordinate conversion)
    
    Returns:
        Mini-map image with route overlay
    """
    from PIL import Image, ImageDraw
    
    if base_map is None:
        return None
    
    # Create a copy to draw on
    map_img = base_map.copy()
    draw = ImageDraw.Draw(map_img, 'RGBA')
    
    map_size = config.mini_map_size
    
    # Use route bounds for coordinate conversion (map is cropped to this area)
    bounds = route_bounds if route_bounds else ANDALUSIA_BOUNDS
    
    # Convert all coordinates to pixels
    pixels = []
    for coord in all_coords:
        if coord:
            px = lat_lon_to_pixel(coord[0], coord[1], map_size, bounds)
            pixels.append(px)
        else:
            pixels.append(None)
    
    # Filter out None values but keep track of indices
    valid_pixels = [(i, px) for i, px in enumerate(pixels) if px is not None]
    
    if len(valid_pixels) < 1:
        return map_img
    
    # Only draw the route UP TO the current POI (progressive line)
    # Get pixels for POIs up to and including current
    completed_pixels = [px for i, px in valid_pixels if i <= current_index]
    
    # Draw the completed route line (grows with each POI)
    if len(completed_pixels) >= 2:
        for i in range(len(completed_pixels) - 1):
            draw.line(
                [completed_pixels[i], completed_pixels[i + 1]], 
                fill=config.route_color + (255,),  # Orange route
                width=3
            )
    
    # Draw markers only for visited POIs
    for i, px in valid_pixels:
        if i < current_index:
            # Completed - green dot
            draw.ellipse([px[0]-5, px[1]-5, px[0]+5, px[1]+5], 
                        fill=config.completed_color + (255,),
                        outline=(255, 255, 255, 200), width=1)
        elif i == current_index:
            # Current - large pink/red marker
            draw.ellipse([px[0]-8, px[1]-8, px[0]+8, px[1]+8], 
                        fill=config.marker_color + (255,),
                        outline=(255, 255, 255, 255), width=2)
        # Future POIs are NOT shown - only show visited ones
    
    return map_img


# ============================================================================
# TEXT OVERLAY
# ============================================================================

def add_text_overlay(img, city: str, poi_name: str, config: SlideshowConfig = None):
    """Add text overlay to image with city and POI name in bottom-left."""
    from PIL import Image, ImageDraw, ImageFont
    
    if config is None:
        config = SlideshowConfig()
    
    img = img.copy()
    draw = ImageDraw.Draw(img, 'RGBA')
    
    width, height = img.size
    
    # Load fonts
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", config.title_font_size)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", config.font_size)
    except:
        try:
            title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", config.title_font_size)
            subtitle_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", config.font_size)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
    
    # Truncate long names
    if len(poi_name) > 40:
        poi_name = poi_name[:37] + "..."
    
    title_text = poi_name
    subtitle_text = f"📍 {city}"
    
    # Calculate text dimensions
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_height = subtitle_bbox[3] - subtitle_bbox[1]
    
    # Padding
    padding = 20
    box_padding = 15
    
    # Calculate box dimensions (bottom left)
    box_width = max(title_width, subtitle_width) + box_padding * 2
    box_height = title_height + subtitle_height + box_padding * 3
    
    box_x = padding
    box_y = height - box_height - padding
    
    # Draw semi-transparent background box
    overlay_color = (0, 0, 0, int(255 * config.overlay_opacity))
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_width, box_y + box_height)],
        radius=10,
        fill=overlay_color
    )
    
    # Draw title
    title_x = box_x + box_padding
    title_y = box_y + box_padding
    
    draw.text((title_x + 2, title_y + 2), title_text, font=title_font, fill=(0, 0, 0, 180))
    draw.text((title_x, title_y), title_text, font=title_font, fill=config.text_color)
    
    # Draw subtitle
    subtitle_x = box_x + box_padding
    subtitle_y = title_y + title_height + box_padding
    
    draw.text((subtitle_x + 1, subtitle_y + 1), subtitle_text, font=subtitle_font, fill=(0, 0, 0, 150))
    draw.text((subtitle_x, subtitle_y), subtitle_text, font=subtitle_font, fill=(200, 200, 200))
    
    return img


def add_mini_map_to_image(img, mini_map: 'Image', config: SlideshowConfig):
    """Add mini-map overlay to bottom-right of image."""
    from PIL import Image, ImageDraw
    
    if mini_map is None:
        return img
    
    img = img.copy()
    width, height = img.size
    
    # Position in bottom-right
    map_x = width - config.mini_map_size - config.mini_map_margin
    map_y = height - config.mini_map_size - config.mini_map_margin
    
    # Create rounded rectangle mask for mini-map
    mask = Image.new('L', (config.mini_map_size, config.mini_map_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (config.mini_map_size - 1, config.mini_map_size - 1)],
        radius=10,
        fill=255
    )
    
    # Add semi-transparent background
    bg = Image.new('RGBA', (config.mini_map_size, config.mini_map_size), (0, 0, 0, int(255 * config.mini_map_opacity)))
    
    # Convert main image to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Paste background
    img.paste(bg, (map_x, map_y), mask)
    
    # Paste mini-map
    if mini_map.mode == 'RGBA':
        img.paste(mini_map, (map_x, map_y), mini_map)
    else:
        img.paste(mini_map, (map_x, map_y), mask)
    
    # Draw border
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [(map_x, map_y), (map_x + config.mini_map_size, map_y + config.mini_map_size)],
        radius=10,
        outline=(255, 255, 255, 200),
        width=2
    )
    
    return img.convert('RGB')


# ============================================================================
# VIDEO GENERATION
# ============================================================================

def generate_poi_slideshow_from_pois(
    pois: List[Dict],
    output_file: str = "trip_slideshow.mp4",
    config: SlideshowConfig = None,
    photos_dir: str = None
) -> Optional[str]:
    """Generate a slideshow video from a list of POIs with sliding window mini-map."""
    if config is None:
        config = SlideshowConfig()
    
    if photos_dir is None:
        photos_dir = PHOTOS_DIR
    
    try:
        from PIL import Image
        import cv2
        import numpy as np
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Install with: pip install pillow opencv-python numpy")
        return None
    
    if not pois:
        print("❌ No POIs provided")
        return None
    
    print(f"🎬 Generating slideshow video for {len(pois)} POIs...")
    print(f"   Duration per slide: {config.duration_per_slide}s")
    print(f"   Resolution: {config.width}x{config.height}")
    print(f"   Mini-map: {'Enabled (sliding window)' if config.show_mini_map else 'Disabled'}")
    
    # Get coordinates for all POIs FIRST (needed for map bounds)
    all_coords = [get_poi_coordinates(poi) for poi in pois]
    coords_found = sum(1 for c in all_coords if c is not None)
    print(f"   📍 Coordinates found: {coords_found}/{len(pois)}")
    
    # Load FULL mini-map (we'll crop per-frame for sliding window)
    base_mini_map = None
    if config.show_mini_map:
        base_mini_map = load_mini_map_base(config)
        if base_mini_map:
            print(f"   ✅ Mini-map loaded ({base_mini_map.size[0]}x{base_mini_map.size[1]}px)")
        else:
            print(f"   ⚠️ Mini-map not found, continuing without it")
    
    # Calculate frames per slide
    frames_per_slide = int(config.duration_per_slide * config.fps)
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, config.fps, (config.width, config.height))
    
    if not out.isOpened():
        print("❌ Failed to create video writer")
        return None
    
    total_frames = 0
    pois_with_photos = 0
    
    # Window size for sliding mini-map (show ~12 POIs at a time for good context)
    WINDOW_SIZE = 12
    
    for idx, poi in enumerate(pois):
        poi_name = poi.get('name', 'Unknown')
        city = poi.get('city', 'Andalusia')
        
        print(f"   [{idx + 1}/{len(pois)}] {city} - {poi_name}")
        
        # Find and load photo
        photo_path = find_photo_path(poi, photos_dir)
        
        if photo_path:
            img = load_and_resize_image(photo_path, config.width, config.height)
            if img:
                pois_with_photos += 1
            else:
                img = create_placeholder_image(config.width, config.height, poi_name[:30])
        else:
            print(f"      ⚠️ No photo found")
            img = create_placeholder_image(config.width, config.height, poi_name[:30])
        
        # Add text overlay (bottom-left)
        img_with_text = add_text_overlay(img, city, poi_name, config)
        
        # Add mini-map overlay (bottom-right) with SLIDING WINDOW bounds
        if config.show_mini_map and base_mini_map:
            # Calculate window bounds for current position (shows 2-3 nearby cities)
            window_bounds = calculate_window_bounds(all_coords, idx, window_size=WINDOW_SIZE)
            
            # Crop map to window bounds
            cropped_map = crop_map_to_bounds(base_mini_map, window_bounds, config)
            
            if cropped_map:
                # Draw route on cropped map
                mini_map_with_route = create_mini_map_overlay(cropped_map, all_coords, idx, config, window_bounds)
                img_with_text = add_mini_map_to_image(img_with_text, mini_map_with_route, config)
        
        # Convert PIL to OpenCV format
        frame = cv2.cvtColor(np.array(img_with_text), cv2.COLOR_RGB2BGR)
        
        # Write frames for this slide
        for _ in range(frames_per_slide):
            out.write(frame)
            total_frames += 1
        
        # Add fade transition
        if idx < len(pois) - 1 and config.transition_frames > 0:
            next_poi = pois[idx + 1]
            next_photo_path = find_photo_path(next_poi, photos_dir)
            
            if next_photo_path:
                next_img = load_and_resize_image(next_photo_path, config.width, config.height)
                if not next_img:
                    next_img = create_placeholder_image(config.width, config.height)
            else:
                next_img = create_placeholder_image(config.width, config.height)
            
            next_img_with_text = add_text_overlay(
                next_img, 
                next_poi.get('city', 'Andalusia'),
                next_poi.get('name', 'Unknown'),
                config
            )
            
            if config.show_mini_map and base_mini_map:
                # Window bounds for next POI
                next_window_bounds = calculate_window_bounds(all_coords, idx + 1, window_size=WINDOW_SIZE)
                next_cropped_map = crop_map_to_bounds(base_mini_map, next_window_bounds, config)
                
                if next_cropped_map:
                    next_mini_map = create_mini_map_overlay(next_cropped_map, all_coords, idx + 1, config, next_window_bounds)
                    next_img_with_text = add_mini_map_to_image(next_img_with_text, next_mini_map, config)
            
            next_frame = cv2.cvtColor(np.array(next_img_with_text), cv2.COLOR_RGB2BGR)
            
            for t in range(config.transition_frames):
                alpha = t / config.transition_frames
                blended = cv2.addWeighted(frame, 1 - alpha, next_frame, alpha, 0)
                out.write(blended)
                total_frames += 1
    
    out.release()
    
    duration = total_frames / config.fps
    print(f"\n✅ Video saved: {output_file}")
    print(f"   📊 Duration: {duration:.1f} seconds")
    print(f"   🖼️ POIs with photos: {pois_with_photos}/{len(pois)}")
    print(f"   🎞️ Total frames: {total_frames}")
    
    return output_file


def generate_poi_slideshow(
    result: Dict,
    output_file: str = "trip_slideshow.mp4",
    config: SlideshowConfig = None,
    photos_dir: str = None
) -> Optional[str]:
    """Generate a slideshow video from an itinerary result."""
    pois = []
    itinerary = result.get('itinerary', [])
    
    for day in itinerary:
        cities_list = day.get('cities', [])
        for city_stop in cities_list:
            city_name = city_stop.get('city', '')
            attractions = city_stop.get('attractions', [])
            
            for attr in attractions:
                poi = {
                    'name': attr.get('name', 'Unknown'),
                    'city': city_name or attr.get('city', 'Andalusia'),
                    'place_id': attr.get('place_id', ''),
                    'local_photo_path': attr.get('local_photo_path', ''),
                    'photo_references': attr.get('photo_references', []),
                    'coordinates': attr.get('coordinates', {}),
                    'lat': attr.get('lat'),
                    'lon': attr.get('lon'),
                }
                pois.append(poi)
    
    if not pois:
        print("❌ No POIs found in itinerary")
        return None
    
    print(f"📍 Found {len(pois)} POIs in itinerary")
    
    return generate_poi_slideshow_from_pois(pois, output_file, config, photos_dir)


# ============================================================================
# STREAMLIT INTEGRATION
# ============================================================================

def add_slideshow_button_to_streamlit(result: Dict, st_module, photos_dir: str = None):
    """Add slideshow generation button to Streamlit app."""
    st = st_module
    
    if st.button("🎬 Generate Trip Slideshow", use_container_width=True, key="gen_slideshow_btn"):
        with st.spinner("Creating your trip video... This may take a minute."):
            try:
                output_file = f"trip_slideshow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                
                config = SlideshowConfig(
                    duration_per_slide=3.5,
                    fps=24,
                    width=1280,
                    height=720,
                    show_mini_map=True
                )
                
                video_path = generate_poi_slideshow(result, output_file, config, photos_dir)
                
                if video_path and os.path.exists(video_path):
                    with open(video_path, 'rb') as f:
                        video_data = f.read()
                    
                    st.download_button(
                        label="📥 Download Trip Video (MP4)",
                        data=video_data,
                        file_name="andalusia_trip_slideshow.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                    
                    st.success("✅ Video generated successfully!")
                    
                    try:
                        os.remove(video_path)
                    except:
                        pass
                else:
                    st.error("❌ Failed to generate video. Check that photos exist.")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("🎬 POI SLIDESHOW VIDEO GENERATOR (with Mini-Map)")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else "trip_slideshow.mp4"
        photos = sys.argv[3] if len(sys.argv) > 3 else "data/photos"
        
        print(f"📂 Loading itinerary from: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            config = SlideshowConfig(show_mini_map=True)
            generate_poi_slideshow(result, output, config, photos_dir=photos)
            
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("Usage:")
        print("  python poi_video_generator.py <itinerary.json> [output.mp4] [photos_dir]")
        print()
        print("Example:")
        print("  python poi_video_generator.py trip.json my_video.mp4 data/photos")
        print()
        print("Features:")
        print("  - POI photos with 3.5s per slide")
        print("  - City/POI name overlay (bottom-left)")
        print("  - Mini-map with route progress (bottom-right)")
        print("=" * 60)
