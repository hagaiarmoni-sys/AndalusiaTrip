"""
Andalusia Event Photo Downloader
Downloads authentic event photos from Unsplash with proper search terms
"""

import requests
import os
import time
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# UNSPLASH API CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Get your free API key from: https://unsplash.com/developers
# Sign up (free) → Create new application → Copy Access Key
UNSPLASH_ACCESS_KEY = "dcrmf8WQM5FKedvzsTejemIa2VaMReN8ToHQSpl-Xwc"  # Replace with your key

# API endpoint
UNSPLASH_API = "https://api.unsplash.com/search/photos"

# Output directory (current directory, not nested)
OUTPUT_DIR = "."  # Save in current directory where script is run

# ═══════════════════════════════════════════════════════════
# EVENT PHOTO SPECIFICATIONS
# ═══════════════════════════════════════════════════════════

EVENT_PHOTOS = {
    # Event name: (filename, search_query, description)
    
    # ✅ KEEP - Already correct
    "Cruces de Mayo": {
        "filename": "cruces_de_mayo.jpg",
        "search": "Cruces de Mayo Cordoba Spain flower crosses",
        "keep_existing": True,  # Already good
    },
    "Noche en Blanco": {
        "filename": "noche_en_blanco.jpg", 
        "search": "Noche en Blanco Malaga Spain night cultural",
        "keep_existing": True,  # Already good
    },
    "Music": {
        "filename": "music.jpg",
        "search": "music studio instruments microphone",
        "keep_existing": True,  # Already good
    },
    
    # ❌ REPLACE - Wrong photos
    "Patios de Córdoba": {
        "filename": "patios_de_cordoba.jpg",
        "search": "Patios de Cordoba Spain flowers courtyard festival",
        "keep_existing": False,  # WRONG! (Shows Bali)
    },
    "Bienal de Flamenco": {
        "filename": "bienal_de_flamenco.jpg",
        "search": "flamenco dancer Spain",  # Simplified - more likely to find
        "keep_existing": False,
    },
    "Romería del Rocío": {
        "filename": "romeria_del_rocio.jpg",
        "search": "Romeria del Rocio pilgrimage Spain horses wagons",
        "keep_existing": False,  # WRONG! (Shows Barcelona)
    },
    "Flamenco": {
        "filename": "flamenco.jpg",
        "search": "flamenco dancer Spain traditional dress performance",
        "keep_existing": False,  # WRONG! (Shows travel gear)
    },
    "Festival de Jerez": {
        "filename": "festival_de_jerez.jpg",
        "search": "horse fair Spain",  # Simplified - more results
        "keep_existing": False,
    },
    "Feria de Abril": {
        "filename": "feria_de_abril.jpg",
        "search": "Feria de Abril Seville Spain casetas colorful",
        "keep_existing": False,  # WRONG! (Generic concert)
    },
    "Feria de Córdoba": {
        "filename": "feria_de_cordoba.jpg",
        "search": "Feria de Cordoba Spain fair casetas",
        "keep_existing": False,  # WRONG! (Hostel beds!)
    },
    "Feria de Málaga": {
        "filename": "feria_de_malaga.jpg",
        "search": "Feria de Malaga Spain fair festival casetas",
        "keep_existing": False,  # WRONG! (Generic concert)
    },
    "Semana Santa": {
        "filename": "semana_santa.jpg",
        "search": "Semana Santa Spain Holy Week procession nazarenos",
        "keep_existing": False,  # WRONG! (Barcelona)
    },
    "Religious": {
        "filename": "religious.jpg",
        "search": "Semana Santa Andalusia procession religious Spain",
        "keep_existing": False,  # WRONG! (Sunset)
    },
    "Cultural": {
        "filename": "cultural.jpg",
        "search": "Spanish cultural event Andalusia traditional culture",
        "keep_existing": False,  # WRONG! (Tech conference)
    },
    "Carnival": {
        "filename": "carnival.jpg",
        "search": "Carnaval de Cadiz Spain costumes masks colorful",
        "keep_existing": False,  # Generic bokeh
    },
    "Carnaval de Cádiz": {
        "filename": "carnaval_de_cadiz.jpg",
        "search": "Carnaval de Cadiz Spain street celebration costumes",
        "keep_existing": False,  # Generic bokeh
    },
    "Festival": {
        "filename": "festival.jpg",
        "search": "Spanish festival Andalusia celebration traditional",
        "keep_existing": False,  # Too generic
    },
}


def download_photo(search_query, filename, event_name):
    """
    Download a photo from Unsplash based on search query
    
    Args:
        search_query: Search terms for Unsplash
        filename: Output filename
        event_name: Name of the event (for logging)
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n🔍 Searching for: {event_name}")
    print(f"   Query: {search_query}")
    
    try:
        # Search for photos
        params = {
            "query": search_query,
            "per_page": 5,  # Get top 5 results
            "orientation": "landscape",  # Prefer landscape
            "client_id": UNSPLASH_ACCESS_KEY
        }
        
        response = requests.get(UNSPLASH_API, params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            print(f"   ❌ No photos found for '{search_query}'")
            return False
        
        # Get the first (best) result
        photo = results[0]
        download_url = photo["urls"]["regular"]  # High quality, not full size
        photo_id = photo["id"]
        photographer = photo["user"]["name"]
        
        print(f"   ✅ Found photo by {photographer}")
        print(f"   📥 Downloading...")
        
        # Download the photo
        img_response = requests.get(download_url)
        img_response.raise_for_status()
        
        # Save to file
        output_path = os.path.join(OUTPUT_DIR, filename)
        with open(output_path, 'wb') as f:
            f.write(img_response.content)
        
        print(f"   💾 Saved to: {output_path}")
        
        # Trigger download tracking (Unsplash API requirement)
        download_endpoint = photo["links"]["download_location"]
        requests.get(download_endpoint, params={"client_id": UNSPLASH_ACCESS_KEY})
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error downloading: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")
        return False


def main():
    """Main function to download all event photos"""
    
    print("="*80)
    print("ANDALUSIA EVENT PHOTO DOWNLOADER")
    print("="*80)
    
    # Check API key
    if UNSPLASH_ACCESS_KEY == "YOUR_ACCESS_KEY_HERE":
        print("\n❌ ERROR: Please set your Unsplash API key!")
        print("\n📝 How to get a free API key:")
        print("   1. Go to: https://unsplash.com/developers")
        print("   2. Sign up (free)")
        print("   3. Create a new application")
        print("   4. Copy your Access Key")
        print("   5. Paste it in this script as UNSPLASH_ACCESS_KEY")
        return
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n📁 Output directory: {OUTPUT_DIR}")
    
    # Statistics
    downloaded = 0
    kept = 0
    failed = 0
    
    # Process each event photo
    for event_name, config in EVENT_PHOTOS.items():
        filename = config["filename"]
        search_query = config["search"]
        keep_existing = config.get("keep_existing", False)
        
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        # Check if we should keep existing
        if keep_existing and os.path.exists(output_path):
            print(f"\n✅ KEEPING: {event_name}")
            print(f"   File: {filename} (already correct)")
            kept += 1
            continue
        
        # Download new photo
        success = download_photo(search_query, filename, event_name)
        
        if success:
            downloaded += 1
        else:
            failed += 1
        
        # Rate limiting - be nice to Unsplash API
        time.sleep(1)  # 1 second between requests
    
    # Summary
    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE!")
    print("="*80)
    print(f"\n📊 Statistics:")
    print(f"   ✅ Downloaded: {downloaded} new photos")
    print(f"   ✅ Kept existing: {kept} photos")
    if failed > 0:
        print(f"   ❌ Failed: {failed} photos")
    print(f"\n📁 All photos saved to: {os.path.abspath(OUTPUT_DIR)}")
    
    if failed > 0:
        print("\n💡 Tip: For failed downloads, try:")
        print("   - Different search terms")
        print("   - Manual download from Unsplash.com")
        print("   - Running the script again")


if __name__ == "__main__":
    main()
