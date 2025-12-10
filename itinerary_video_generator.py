"""
Itinerary Video Generator - Animated Bird's Eye View Flyover
============================================================

Generates a ~1 minute animated video showing your travel route from above.

Features:
- Animated route drawing on satellite/terrain map
- Smooth camera pan following the route
- City labels and markers
- Multiple output formats (MP4, GIF, HTML)

Requirements:
    pip install folium selenium pillow opencv-python numpy --break-system-packages
    
    For video export, you also need:
    - Chrome/Chromium browser installed
    - chromedriver (or use webdriver-manager)
    
    pip install webdriver-manager --break-system-packages

Usage:
    from itinerary_video_generator import generate_route_video
    
    # From coordinates
    coords = [
        {"city": "Málaga", "lat": 36.7213, "lon": -4.4214},
        {"city": "Granada", "lat": 37.1773, "lon": -3.5986},
        {"city": "Córdoba", "lat": 37.8882, "lon": -4.7794},
        {"city": "Seville", "lat": 37.3891, "lon": -5.9845},
    ]
    generate_route_video(coords, output_file="my_trip.mp4")
    
    # From itinerary JSON
    generate_video_from_itinerary("trip_result.json", output_file="trip_video.mp4")

Author: Andalusia Travel App
"""

import json
import os
import time
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class VideoConfig:
    """Configuration for video generation"""
    duration_seconds: int = 60          # Total video duration
    fps: int = 30                        # Frames per second
    width: int = 1280                    # Video width
    height: int = 720                    # Video height
    map_style: str = "satellite"         # satellite, terrain, streets
    line_color: str = "#FF5722"          # Route line color (orange)
    line_weight: int = 4                 # Route line thickness
    marker_color: str = "#E91E63"        # City marker color (pink)
    show_labels: bool = True             # Show city names
    zoom_start: int = 7                  # Starting zoom level
    zoom_end: int = 10                   # Ending zoom level (closer)
    pause_at_cities: float = 2.0         # Seconds to pause at each city


# ============================================================================
# COORDINATE UTILITIES
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def interpolate_points(start: Tuple[float, float], end: Tuple[float, float], num_points: int) -> List[Tuple[float, float]]:
    """Generate interpolated points between two coordinates"""
    points = []
    for i in range(num_points):
        t = i / (num_points - 1) if num_points > 1 else 0
        lat = start[0] + t * (end[0] - start[0])
        lon = start[1] + t * (end[1] - start[1])
        points.append((lat, lon))
    return points


def get_route_bounds(coordinates: List[Dict]) -> Tuple[float, float, float, float]:
    """Get bounding box for route"""
    lats = [c["lat"] for c in coordinates]
    lons = [c["lon"] for c in coordinates]
    return min(lats), max(lats), min(lons), max(lons)


def get_route_center(coordinates: List[Dict]) -> Tuple[float, float]:
    """Get center point of route"""
    min_lat, max_lat, min_lon, max_lon = get_route_bounds(coordinates)
    return (min_lat + max_lat) / 2, (min_lon + max_lon) / 2


# ============================================================================
# METHOD 1: FOLIUM + SELENIUM (Recommended)
# ============================================================================

def generate_animated_html(
    coordinates: List[Dict],
    output_file: str = "route_animation.html",
    config: VideoConfig = None
) -> str:
    """
    Generate an animated HTML file showing the route with auto-play animation.
    This can be viewed in any browser and recorded with screen capture.
    
    Args:
        coordinates: List of dicts with 'city', 'lat', 'lon' keys
        output_file: Output HTML file path
        config: VideoConfig instance
    
    Returns:
        Path to generated HTML file
    """
    if config is None:
        config = VideoConfig()
    
    center_lat, center_lon = get_route_center(coordinates)
    
    # Calculate total route distance for timing
    total_distance = 0
    for i in range(len(coordinates) - 1):
        total_distance += haversine_distance(
            coordinates[i]["lat"], coordinates[i]["lon"],
            coordinates[i+1]["lat"], coordinates[i+1]["lon"]
        )
    
    # Build coordinate arrays for JavaScript
    route_coords = [[c["lat"], c["lon"]] for c in coordinates]
    city_names = [c.get("city", f"Stop {i+1}") for i, c in enumerate(coordinates)]
    
    # Generate smooth path with many interpolated points
    smooth_path = []
    for i in range(len(coordinates) - 1):
        start = (coordinates[i]["lat"], coordinates[i]["lon"])
        end = (coordinates[i+1]["lat"], coordinates[i+1]["lon"])
        segment_dist = haversine_distance(start[0], start[1], end[0], end[1])
        # More points for longer segments
        num_points = max(10, int(segment_dist / 5))
        segment_points = interpolate_points(start, end, num_points)
        smooth_path.extend(segment_points[:-1])  # Avoid duplicates
    smooth_path.append((coordinates[-1]["lat"], coordinates[-1]["lon"]))
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>🗺️ Your Andalusia Road Trip</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        
        #map {{
            width: 100%;
            height: 100vh;
        }}
        
        .title-overlay {{
            position: absolute;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            backdrop-filter: blur(5px);
        }}
        
        .info-overlay {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            min-width: 200px;
        }}
        
        .info-overlay h3 {{
            color: #E91E63;
            margin-bottom: 10px;
            font-size: 18px;
        }}
        
        .info-overlay .stat {{
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
            font-size: 14px;
        }}
        
        .info-overlay .stat-label {{
            color: #666;
        }}
        
        .info-overlay .stat-value {{
            font-weight: bold;
            color: #333;
        }}
        
        .current-city {{
            position: absolute;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 15px;
            font-size: 28px;
            font-weight: bold;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: all 0.5s ease;
        }}
        
        .progress-bar {{
            position: absolute;
            bottom: 0;
            left: 0;
            width: 0%;
            height: 5px;
            background: linear-gradient(90deg, #FF5722, #E91E63);
            z-index: 1000;
            transition: width 0.1s linear;
        }}
        
        .city-marker {{
            background: #E91E63;
            border: 3px solid white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        
        .city-label {{
            background: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            white-space: nowrap;
        }}
        
        @keyframes pulse {{
            0% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.2); opacity: 0.8; }}
            100% {{ transform: scale(1); opacity: 1; }}
        }}
        
        .current-marker {{
            animation: pulse 1s infinite;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="title-overlay">
        ✈️ Your Andalusia Adventure
    </div>
    
    <div class="info-overlay">
        <h3>📊 Trip Stats</h3>
        <div class="stat">
            <span class="stat-label">Total Distance:</span>
            <span class="stat-value">{total_distance:.0f} km</span>
        </div>
        <div class="stat">
            <span class="stat-label">Cities:</span>
            <span class="stat-value">{len(coordinates)}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Progress:</span>
            <span class="stat-value" id="progress-text">0%</span>
        </div>
    </div>
    
    <div class="current-city" id="current-city">
        📍 {coordinates[0].get("city", "Start")}
    </div>
    
    <div class="progress-bar" id="progress-bar"></div>
    
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <script>
        // Route data
        const routeCoords = {json.dumps(route_coords)};
        const cityNames = {json.dumps(city_names)};
        const smoothPath = {json.dumps(smooth_path)};
        
        // Animation settings
        const ANIMATION_DURATION = {config.duration_seconds * 1000}; // ms
        const FPS = {config.fps};
        
        // Initialize map
        const map = L.map('map', {{
            zoomControl: false,
            attributionControl: false
        }}).setView([{center_lat}, {center_lon}], {config.zoom_start});
        
        // Satellite tiles (Esri)
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
        }}).addTo(map);
        
        // Labels overlay
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
        }}).addTo(map);
        
        // Add city markers
        const markers = [];
        routeCoords.forEach((coord, idx) => {{
            const marker = L.circleMarker(coord, {{
                radius: 10,
                fillColor: '{config.marker_color}',
                color: 'white',
                weight: 3,
                opacity: 1,
                fillOpacity: 0.9
            }}).addTo(map);
            
            // Add label
            const label = L.tooltip({{
                permanent: true,
                direction: 'top',
                offset: [0, -15],
                className: 'city-label'
            }}).setContent(cityNames[idx]);
            
            marker.bindTooltip(label);
            markers.push(marker);
        }});
        
        // Animated route line
        const routeLine = L.polyline([], {{
            color: '{config.line_color}',
            weight: {config.line_weight},
            opacity: 0.9,
            lineCap: 'round',
            lineJoin: 'round'
        }}).addTo(map);
        
        // Current position marker
        const currentMarker = L.circleMarker(smoothPath[0], {{
            radius: 12,
            fillColor: '#FF5722',
            color: 'white',
            weight: 4,
            opacity: 1,
            fillOpacity: 1,
            className: 'current-marker'
        }}).addTo(map);
        
        // Animation state
        let currentIndex = 0;
        let animationStartTime = null;
        let drawnPath = [];
        
        // Find which city we're near
        function getCurrentCity(lat, lon) {{
            let minDist = Infinity;
            let nearestCity = cityNames[0];
            
            routeCoords.forEach((coord, idx) => {{
                const dist = Math.sqrt(
                    Math.pow(coord[0] - lat, 2) + 
                    Math.pow(coord[1] - lon, 2)
                );
                if (dist < minDist) {{
                    minDist = dist;
                    nearestCity = cityNames[idx];
                }}
            }});
            
            return nearestCity;
        }}
        
        // Animation loop
        function animate(timestamp) {{
            if (!animationStartTime) {{
                animationStartTime = timestamp;
            }}
            
            const elapsed = timestamp - animationStartTime;
            const progress = Math.min(elapsed / ANIMATION_DURATION, 1);
            
            // Calculate current position in path
            const pathIndex = Math.floor(progress * (smoothPath.length - 1));
            
            // Update drawn path
            if (pathIndex > currentIndex) {{
                for (let i = currentIndex; i <= pathIndex && i < smoothPath.length; i++) {{
                    drawnPath.push(smoothPath[i]);
                }}
                routeLine.setLatLngs(drawnPath);
                currentIndex = pathIndex;
            }}
            
            // Update current marker position
            if (pathIndex < smoothPath.length) {{
                const currentPos = smoothPath[pathIndex];
                currentMarker.setLatLng(currentPos);
                
                // Pan map to follow (smooth)
                map.panTo(currentPos, {{
                    animate: true,
                    duration: 0.5
                }});
                
                // Update current city display
                const city = getCurrentCity(currentPos[0], currentPos[1]);
                document.getElementById('current-city').innerHTML = '📍 ' + city;
            }}
            
            // Update progress
            document.getElementById('progress-bar').style.width = (progress * 100) + '%';
            document.getElementById('progress-text').textContent = Math.round(progress * 100) + '%';
            
            // Gradually zoom in
            const targetZoom = {config.zoom_start} + ({config.zoom_end} - {config.zoom_start}) * progress;
            if (Math.abs(map.getZoom() - targetZoom) > 0.5) {{
                map.setZoom(targetZoom);
            }}
            
            // Continue animation
            if (progress < 1) {{
                requestAnimationFrame(animate);
            }} else {{
                // Animation complete
                document.getElementById('current-city').innerHTML = '🏁 Journey Complete!';
                
                // Fit to full route
                setTimeout(() => {{
                    map.fitBounds(routeLine.getBounds(), {{ padding: [50, 50] }});
                }}, 1000);
            }}
        }}
        
        // Start animation after a brief delay
        setTimeout(() => {{
            // Fit bounds first
            const bounds = L.latLngBounds(routeCoords);
            map.fitBounds(bounds, {{ padding: [100, 100] }});
            
            // Then start animation
            setTimeout(() => {{
                requestAnimationFrame(animate);
            }}, 2000);
        }}, 1000);
    </script>
</body>
</html>'''
    
    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Generated animated HTML: {output_file}")
    print(f"   📺 Open in browser and use screen recording to capture video")
    print(f"   🎬 Animation duration: {config.duration_seconds} seconds")
    
    return output_file


# ============================================================================
# METHOD 2: SELENIUM + SCREEN CAPTURE (Automated MP4)
# ============================================================================

def generate_video_mp4(
    coordinates: List[Dict],
    output_file: str = "route_video.mp4",
    config: VideoConfig = None
) -> Optional[str]:
    """
    Generate MP4 video by capturing the HTML animation with Selenium.
    
    Requires:
        pip install selenium webdriver-manager opencv-python pillow --break-system-packages
        Chrome browser installed
    
    Args:
        coordinates: List of dicts with 'city', 'lat', 'lon' keys
        output_file: Output MP4 file path
        config: VideoConfig instance
    
    Returns:
        Path to generated video file, or None if failed
    """
    if config is None:
        config = VideoConfig()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from PIL import Image
        import cv2
        import numpy as np
        import io as bytes_io
    except ImportError as e:
        print(f"❌ Missing dependencies for video export: {e}")
        print("   Install with: pip install selenium webdriver-manager opencv-python pillow --break-system-packages")
        return None
    
    # First generate the HTML
    html_file = output_file.replace('.mp4', '_temp.html')
    generate_animated_html(coordinates, html_file, config)
    
    # Setup headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--window-size={config.width},{config.height}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        print("🎬 Starting video capture...")
        
        # Initialize browser
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Load HTML file
        html_path = os.path.abspath(html_file)
        driver.get(f"file://{html_path}")
        
        # Wait for map to load
        time.sleep(5)
        
        # Capture frames
        frames = []
        total_frames = config.duration_seconds * config.fps
        frame_interval = 1.0 / config.fps
        
        print(f"   Capturing {total_frames} frames at {config.fps} FPS...")
        
        for i in range(total_frames + 60):  # Extra frames for intro/outro
            # Take screenshot
            screenshot = driver.get_screenshot_as_png()
            
            # Convert to numpy array
            img = Image.open(bytes_io.BytesIO(screenshot))
            img = img.resize((config.width, config.height))
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frames.append(frame)
            
            # Progress update
            if i % 30 == 0:
                print(f"   Frame {i}/{total_frames}...")
            
            time.sleep(frame_interval)
        
        driver.quit()
        
        # Write video
        print(f"   Writing video to {output_file}...")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_file, fourcc, config.fps, (config.width, config.height))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        
        # Cleanup temp HTML
        if os.path.exists(html_file):
            os.remove(html_file)
        
        print(f"✅ Video saved: {output_file}")
        print(f"   📊 Duration: {len(frames) / config.fps:.1f} seconds")
        print(f"   📐 Resolution: {config.width}x{config.height}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error generating video: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# METHOD 3: ANIMATED GIF (Lightweight)
# ============================================================================

def generate_animated_gif(
    coordinates: List[Dict],
    output_file: str = "route_animation.gif",
    config: VideoConfig = None,
    num_frames: int = 60
) -> Optional[str]:
    """
    Generate a lightweight animated GIF of the route.
    
    Requires:
        pip install folium selenium pillow webdriver-manager --break-system-packages
    
    Args:
        coordinates: List of dicts with 'city', 'lat', 'lon' keys
        output_file: Output GIF file path
        config: VideoConfig instance
        num_frames: Number of frames in GIF
    
    Returns:
        Path to generated GIF file, or None if failed
    """
    if config is None:
        config = VideoConfig()
    
    try:
        import folium
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from PIL import Image
        import io as bytes_io
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        return None
    
    center_lat, center_lon = get_route_center(coordinates)
    
    # Setup headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--window-size={config.width},{config.height}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    frames = []
    temp_html = "temp_map_frame.html"
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"🎬 Generating {num_frames} frames for GIF...")
        
        # Generate frames showing progressive route drawing
        route_coords = [(c["lat"], c["lon"]) for c in coordinates]
        
        for frame_idx in range(num_frames):
            progress = frame_idx / (num_frames - 1)
            
            # Calculate how much of the route to show
            total_points = len(route_coords)
            show_points = max(1, int(progress * total_points) + 1)
            current_route = route_coords[:show_points]
            
            # Calculate current position for marker
            if show_points < total_points:
                # Interpolate between points
                segment_progress = (progress * total_points) - int(progress * total_points)
                if show_points < len(route_coords):
                    current_lat = current_route[-1][0] + segment_progress * (route_coords[show_points][0] - current_route[-1][0])
                    current_lon = current_route[-1][1] + segment_progress * (route_coords[show_points][1] - current_route[-1][1])
                else:
                    current_lat, current_lon = current_route[-1]
            else:
                current_lat, current_lon = current_route[-1]
            
            # Create map for this frame
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=config.zoom_start,
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri'
            )
            
            # Add route line
            if len(current_route) > 1:
                folium.PolyLine(
                    current_route,
                    color=config.line_color,
                    weight=config.line_weight,
                    opacity=0.9
                ).add_to(m)
            
            # Add city markers
            for i, coord in enumerate(coordinates):
                # Only show markers for visited cities
                if i < show_points:
                    folium.CircleMarker(
                        location=[coord["lat"], coord["lon"]],
                        radius=8,
                        color='white',
                        fill=True,
                        fill_color=config.marker_color,
                        fill_opacity=1,
                        popup=coord.get("city", "")
                    ).add_to(m)
            
            # Add current position marker
            folium.CircleMarker(
                location=[current_lat, current_lon],
                radius=12,
                color='white',
                fill=True,
                fill_color='#FF5722',
                fill_opacity=1
            ).add_to(m)
            
            # Fit bounds
            m.fit_bounds([[c["lat"], c["lon"]] for c in coordinates])
            
            # Save and capture
            m.save(temp_html)
            driver.get(f"file://{os.path.abspath(temp_html)}")
            time.sleep(0.3)
            
            screenshot = driver.get_screenshot_as_png()
            img = Image.open(bytes_io.BytesIO(screenshot))
            img = img.resize((config.width // 2, config.height // 2))  # Smaller for GIF
            frames.append(img)
            
            if frame_idx % 10 == 0:
                print(f"   Frame {frame_idx + 1}/{num_frames}")
        
        driver.quit()
        
        # Save GIF
        print(f"   Saving GIF to {output_file}...")
        frames[0].save(
            output_file,
            save_all=True,
            append_images=frames[1:],
            duration=int(config.duration_seconds * 1000 / num_frames),
            loop=0
        )
        
        # Cleanup
        if os.path.exists(temp_html):
            os.remove(temp_html)
        
        print(f"✅ GIF saved: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ Error generating GIF: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# ITINERARY INTEGRATION
# ============================================================================

def extract_coordinates_from_itinerary(itinerary_data: Dict) -> List[Dict]:
    """
    Extract coordinates from itinerary JSON data.
    
    Args:
        itinerary_data: Full itinerary result dict
    
    Returns:
        List of coordinate dicts with city, lat, lon
    """
    coordinates = []
    seen_cities = set()
    
    # Get ordered cities
    ordered_cities = itinerary_data.get("ordered_cities", [])
    itinerary = itinerary_data.get("itinerary", [])
    
    # City coordinate database (Andalusia)
    CITY_COORDS = {
        "málaga": {"lat": 36.7213, "lon": -4.4214},
        "malaga": {"lat": 36.7213, "lon": -4.4214},
        "granada": {"lat": 37.1773, "lon": -3.5986},
        "seville": {"lat": 37.3891, "lon": -5.9845},
        "sevilla": {"lat": 37.3891, "lon": -5.9845},
        "córdoba": {"lat": 37.8882, "lon": -4.7794},
        "cordoba": {"lat": 37.8882, "lon": -4.7794},
        "cádiz": {"lat": 36.5271, "lon": -6.2886},
        "cadiz": {"lat": 36.5271, "lon": -6.2886},
        "ronda": {"lat": 36.7462, "lon": -5.1619},
        "marbella": {"lat": 36.5099, "lon": -4.8862},
        "nerja": {"lat": 36.7580, "lon": -3.8765},
        "jerez": {"lat": 36.6866, "lon": -6.1361},
        "jerez de la frontera": {"lat": 36.6866, "lon": -6.1361},
        "antequera": {"lat": 37.0194, "lon": -4.5603},
        "almería": {"lat": 36.8340, "lon": -2.4637},
        "almeria": {"lat": 36.8340, "lon": -2.4637},
        "tarifa": {"lat": 36.0143, "lon": -5.6044},
        "gibraltar": {"lat": 36.1408, "lon": -5.3536},
        "frigiliana": {"lat": 36.7891, "lon": -3.8956},
        "mijas": {"lat": 36.5959, "lon": -4.6370},
        "arcos de la frontera": {"lat": 36.7508, "lon": -5.8069},
        "zahara de la sierra": {"lat": 36.8403, "lon": -5.3907},
        "grazalema": {"lat": 36.7616, "lon": -5.3685},
        "setenil de las bodegas": {"lat": 36.8621, "lon": -5.1818},
        "olvera": {"lat": 36.9354, "lon": -5.2688},
        "úbeda": {"lat": 38.0133, "lon": -3.3706},
        "baeza": {"lat": 37.9939, "lon": -3.4714},
    }
    
    # Try to get coordinates from itinerary first
    for day in itinerary:
        cities_list = day.get("cities", [])
        for city_stop in cities_list:
            city_name = city_stop.get("city", "")
            if not city_name or city_name.lower() in seen_cities:
                continue
            
            # Try to get from attractions
            attractions = city_stop.get("attractions", [])
            for attr in attractions:
                coords = attr.get("coordinates", {})
                lat = coords.get("latitude") or coords.get("lat")
                lon = coords.get("longitude") or coords.get("lon") or coords.get("lng")
                
                if lat and lon:
                    coordinates.append({
                        "city": city_name,
                        "lat": float(lat),
                        "lon": float(lon)
                    })
                    seen_cities.add(city_name.lower())
                    break
            
            # Fallback to database
            if city_name.lower() not in seen_cities:
                city_lower = city_name.lower()
                if city_lower in CITY_COORDS:
                    coordinates.append({
                        "city": city_name,
                        "lat": CITY_COORDS[city_lower]["lat"],
                        "lon": CITY_COORDS[city_lower]["lon"]
                    })
                    seen_cities.add(city_lower)
    
    # Fallback: use ordered_cities with database
    if not coordinates and ordered_cities:
        for city in ordered_cities:
            city_lower = city.lower()
            if city_lower in CITY_COORDS and city_lower not in seen_cities:
                coordinates.append({
                    "city": city,
                    "lat": CITY_COORDS[city_lower]["lat"],
                    "lon": CITY_COORDS[city_lower]["lon"]
                })
                seen_cities.add(city_lower)
    
    return coordinates


def generate_video_from_itinerary(
    itinerary_json_path: str,
    output_file: str = "trip_video.mp4",
    method: str = "html",
    config: VideoConfig = None
) -> Optional[str]:
    """
    Generate video from an itinerary JSON file.
    
    Args:
        itinerary_json_path: Path to itinerary JSON file
        output_file: Output file path
        method: "html" (browser), "mp4" (automated), or "gif"
        config: VideoConfig instance
    
    Returns:
        Path to generated file, or None if failed
    """
    # Load itinerary
    try:
        with open(itinerary_json_path, 'r', encoding='utf-8') as f:
            itinerary_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading itinerary: {e}")
        return None
    
    # Extract coordinates
    coordinates = extract_coordinates_from_itinerary(itinerary_data)
    
    if not coordinates:
        print("❌ No coordinates found in itinerary")
        return None
    
    print(f"📍 Found {len(coordinates)} cities: {', '.join(c['city'] for c in coordinates)}")
    
    # Generate based on method
    if method == "html":
        return generate_animated_html(coordinates, output_file.replace('.mp4', '.html'), config)
    elif method == "mp4":
        return generate_video_mp4(coordinates, output_file, config)
    elif method == "gif":
        return generate_animated_gif(coordinates, output_file.replace('.mp4', '.gif'), config)
    else:
        print(f"❌ Unknown method: {method}")
        return None


def generate_route_video(
    coordinates: List[Dict],
    output_file: str = "route_video.mp4",
    method: str = "html",
    config: VideoConfig = None
) -> Optional[str]:
    """
    Main function to generate route video from coordinates.
    
    Args:
        coordinates: List of dicts with 'city', 'lat', 'lon' keys
        output_file: Output file path
        method: "html" (browser), "mp4" (automated), or "gif"
        config: VideoConfig instance
    
    Returns:
        Path to generated file
    """
    if config is None:
        config = VideoConfig()
    
    print(f"🗺️ Generating route video for {len(coordinates)} cities...")
    print(f"   Route: {' → '.join(c['city'] for c in coordinates)}")
    
    if method == "html":
        return generate_animated_html(coordinates, output_file.replace('.mp4', '.html'), config)
    elif method == "mp4":
        return generate_video_mp4(coordinates, output_file, config)
    elif method == "gif":
        return generate_animated_gif(coordinates, output_file.replace('.mp4', '.gif'), config)
    else:
        print(f"❌ Unknown method: {method}. Use 'html', 'mp4', or 'gif'")
        return None


# ============================================================================
# STREAMLIT INTEGRATION
# ============================================================================

def add_video_generation_to_streamlit(result: Dict, st_module):
    """
    Add video generation button to Streamlit app.
    
    Usage in trip_planner_page.py:
        from itinerary_video_generator import add_video_generation_to_streamlit
        add_video_generation_to_streamlit(result, st)
    
    Args:
        result: Itinerary result dict
        st_module: Streamlit module (import streamlit as st)
    """
    st = st_module
    
    st.markdown("### 🎬 Generate Route Video")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗺️ Generate Animated Map (HTML)", use_container_width=True):
            coordinates = extract_coordinates_from_itinerary(result)
            
            if coordinates:
                output_file = "route_animation.html"
                generate_animated_html(coordinates, output_file)
                
                # Read and offer download
                with open(output_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                st.download_button(
                    label="📥 Download HTML Animation",
                    data=html_content,
                    file_name="andalusia_route_animation.html",
                    mime="text/html",
                    use_container_width=True
                )
                
                st.success("✅ Open the HTML file in your browser to view the animation!")
                st.info("💡 Tip: Use screen recording software to capture as video")
            else:
                st.error("❌ Could not extract coordinates from itinerary")
    
    with col2:
        if st.button("🎞️ Generate GIF", use_container_width=True):
            with st.spinner("Generating GIF... (this may take a minute)"):
                coordinates = extract_coordinates_from_itinerary(result)
                
                if coordinates:
                    output_file = generate_animated_gif(
                        coordinates, 
                        "route_animation.gif",
                        num_frames=30
                    )
                    
                    if output_file and os.path.exists(output_file):
                        with open(output_file, 'rb') as f:
                            gif_data = f.read()
                        
                        st.download_button(
                            label="📥 Download GIF",
                            data=gif_data,
                            file_name="andalusia_route.gif",
                            mime="image/gif",
                            use_container_width=True
                        )
                        
                        st.success("✅ GIF generated!")
                    else:
                        st.error("❌ Failed to generate GIF. Check console for errors.")
                else:
                    st.error("❌ Could not extract coordinates from itinerary")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("🎬 ITINERARY VIDEO GENERATOR")
    print("=" * 60)
    print()
    
    # Example usage with sample data
    sample_coordinates = [
        {"city": "Málaga", "lat": 36.7213, "lon": -4.4214},
        {"city": "Nerja", "lat": 36.7580, "lon": -3.8765},
        {"city": "Granada", "lat": 37.1773, "lon": -3.5986},
        {"city": "Córdoba", "lat": 37.8882, "lon": -4.7794},
        {"city": "Seville", "lat": 37.3891, "lon": -5.9845},
        {"city": "Cádiz", "lat": 36.5271, "lon": -6.2886},
        {"city": "Ronda", "lat": 36.7462, "lon": -5.1619},
        {"city": "Marbella", "lat": 36.5099, "lon": -4.8862},
        {"city": "Málaga", "lat": 36.7213, "lon": -4.4214},  # Back to start
    ]
    
    if len(sys.argv) > 1:
        # Load from JSON file
        json_path = sys.argv[1]
        method = sys.argv[2] if len(sys.argv) > 2 else "html"
        output = sys.argv[3] if len(sys.argv) > 3 else f"route_video.{method}"
        
        print(f"📂 Loading itinerary from: {json_path}")
        result = generate_video_from_itinerary(json_path, output, method)
    else:
        # Use sample data
        print("📍 Using sample Andalusia route...")
        print(f"   {' → '.join(c['city'] for c in sample_coordinates)}")
        print()
        
        # Generate HTML (recommended)
        config = VideoConfig(duration_seconds=60)
        result = generate_animated_html(sample_coordinates, "sample_route.html", config)
        
        print()
        print("=" * 60)
        print("Usage:")
        print("  python itinerary_video_generator.py <itinerary.json> [method] [output]")
        print()
        print("Methods:")
        print("  html  - Animated HTML (open in browser, screen record)")
        print("  gif   - Animated GIF (lightweight, shareable)")
        print("  mp4   - Video file (requires Chrome + Selenium)")
        print()
        print("Examples:")
        print("  python itinerary_video_generator.py trip.json html route.html")
        print("  python itinerary_video_generator.py trip.json gif route.gif")
        print("=" * 60)
