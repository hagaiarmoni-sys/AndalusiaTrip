"""
Download Cruces de Mayo Photo
Get a distinct photo showing flower crosses (not patios)
"""

import requests
import os

# ═══════════════════════════════════════════════════════════
# UNSPLASH API CONFIGURATION
# ═══════════════════════════════════════════════════════════

UNSPLASH_ACCESS_KEY = "dcrmf8WQM5FKedvzsTejemIa2VaMReN8ToHQSpl-Xwc"
UNSPLASH_API = "https://api.unsplash.com/search/photos"

# ═══════════════════════════════════════════════════════════
# SEARCH CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Try multiple search terms to get the best match
SEARCH_TERMS = [
    "flower cross Spain May festival",           # Most specific
    "May festival flower decorations Spain",     # Alternative
    "religious flower cross festival",           # Generic fallback
    "spring flower festival crosses street",     # Very generic
]

OUTPUT_FILE = "cruces_de_mayo.jpg"

# ═══════════════════════════════════════════════════════════
# DOWNLOAD FUNCTION
# ═══════════════════════════════════════════════════════════

def download_cruces_photo():
    """Try each search term until we find a good photo"""
    
    print("="*70)
    print("DOWNLOADING CRUCES DE MAYO PHOTO")
    print("="*70)
    print("\nGoal: Get a photo showing FLOWER CROSSES (not patios)")
    print("      This will be different from Patios de Córdoba photo\n")
    
    for attempt, search_query in enumerate(SEARCH_TERMS, 1):
        print(f"\n🔍 Attempt {attempt}: Searching Unsplash...")
        print(f"   Query: '{search_query}'")
        
        try:
            # Search Unsplash
            params = {
                "query": search_query,
                "per_page": 5,
                "orientation": "landscape",
                "client_id": UNSPLASH_ACCESS_KEY
            }
            
            response = requests.get(UNSPLASH_API, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                print(f"   ❌ No results found")
                continue
            
            # Show what we found
            print(f"   ✅ Found {len(results)} photos")
            
            # Get the best result
            photo = results[0]
            photographer = photo["user"]["name"]
            description = photo.get("description") or photo.get("alt_description") or "No description"
            
            print(f"   📸 Best match:")
            print(f"      Photographer: {photographer}")
            print(f"      Description: {description}")
            
            # Download the photo
            download_url = photo["urls"]["regular"]
            
            print(f"   📥 Downloading...")
            img_response = requests.get(download_url)
            img_response.raise_for_status()
            
            # Save
            with open(OUTPUT_FILE, 'wb') as f:
                f.write(img_response.content)
            
            file_size = len(img_response.content) / 1024  # KB
            print(f"   💾 Saved: {OUTPUT_FILE} ({file_size:.0f} KB)")
            
            # Track download (Unsplash requirement)
            download_endpoint = photo["links"]["download_location"]
            requests.get(download_endpoint, params={"client_id": UNSPLASH_ACCESS_KEY})
            
            print("\n" + "="*70)
            print("✅ SUCCESS!")
            print("="*70)
            print(f"\n📁 Photo saved as: {os.path.abspath(OUTPUT_FILE)}")
            print(f"\n💡 Next steps:")
            print(f"   1. Open {OUTPUT_FILE} and verify it shows FLOWER CROSSES")
            print(f"   2. If good, copy to: event_photos/{OUTPUT_FILE}")
            print(f"   3. If not good, delete and run script again (tries different search)")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            continue
    
    # All attempts failed
    print("\n" + "="*70)
    print("❌ FAILED - No suitable photos found")
    print("="*70)
    print("\n💡 Alternative options:")
    print("   1. Go to https://unsplash.com manually")
    print("   2. Search: 'flower cross Spain May festival'")
    print("   3. Download a good photo")
    print("   4. Save as: cruces_de_mayo.jpg")
    print("   5. Copy to event_photos folder")
    
    return False


if __name__ == "__main__":
    download_cruces_photo()
