#!/usr/bin/env python3
"""Debug script to test business data extraction"""

import re
import json

def clean_theme_shortcodes(text: str) -> str:
    """Remove various theme builder shortcodes while preserving useful content"""
    if not text:
        return text

    # Visual Composer shortcodes
    text = re.sub(r'\[vc_[^\]]*\]', '', text)
    text = re.sub(r'\[\/vc_[^\]]*\]', '', text)

    # Elementor shortcodes
    text = re.sub(r'\[elementor-template[^\]]*\]', '', text)

    # Divi Builder shortcodes
    text = re.sub(r'\[et_pb_[^\]]*\]', '', text)
    text = re.sub(r'\[\/et_pb_[^\]]*\]', '', text)

    # Nectar theme shortcodes (but keep some content)
    text = re.sub(r'\[nectar_btn[^\]]*\]', '', text)

    # Remove other common theme shortcodes
    text = re.sub(r'\[[a-z_]+_shortcode[^\]]*\]', '', text)
    text = re.sub(r'\[\/[a-z_]+_shortcode[^\]]*\]', '', text)

    return text

def extract_business_data(text: str) -> tuple[str, list]:
    """Extract structured business data and convert to JSON objects"""
    if not text:
        return text, []

    businesses = []

    # First, extract nectar_gmap map_markers data - this contains the core business list
    gmap_pattern = r'map_markers="([^"]+)"'
    gmap_match = re.search(gmap_pattern, text)

    if gmap_match:
        markers_data = gmap_match.group(1)
        print(f"Found map_markers data: {markers_data[:200]}...")

        # Parse individual markers: lat | lng | business_name
        marker_pattern = r'([\d.-]+)\s*\|\s*([\d.-]+)\s*\|\s*([^\r\n]+?)(?=\s*[\d.-]+\s*\||\Z)'

        marker_matches = re.finditer(marker_pattern, markers_data, re.MULTILINE | re.DOTALL)

        for match in marker_matches:
            try:
                lat, lng, business_name = match.groups()
                print(f"Found business: {business_name[:50]}...")

                # Clean up business name - remove HTML entities and extra whitespace
                business_name = business_name.strip()
                business_name = re.sub(r'&#\d+;', '', business_name)  # Remove HTML entities like &#8217;
                business_name = re.sub(r'&\w+;', '', business_name)   # Remove HTML entities like &amp;
                business_name = re.sub(r'\s+', ' ', business_name)    # Normalize whitespace

                if business_name and lat and lng:
                    business = {
                        'name': business_name,
                        'coordinates': {
                            'latitude': float(lat),
                            'longitude': float(lng)
                        }
                    }
                    businesses.append(business)

            except (ValueError, IndexError) as e:
                print(f"Error parsing business data: {e}")
                continue
    else:
        print("No nectar_gmap shortcode found")

    # Clean up the text - remove the gmap shortcode and messy coordinate data
    cleaned_text = text

    # Remove nectar_gmap shortcodes entirely
    cleaned_text = re.sub(r'\[nectar_gmap[^\]]*\]', '', cleaned_text)

    return cleaned_text, businesses

if __name__ == "__main__":
    # Read the raw dealers file
    try:
        with open('/app/test_json/JB-Lund-Dock-amp-Lift/raw_pages/pages-dealers.txt', 'r') as f:
            raw_content = f.read()

        print("Raw content length:", len(raw_content))
        print("Searching for nectar_gmap...")

        # Test extraction
        cleaned_text, businesses = extract_business_data(raw_content)

        print(f"Found {len(businesses)} businesses:")
        for i, business in enumerate(businesses):
            print(f"  {i+1}. {business['name']} at {business['coordinates']}")

        if businesses:
            print("\nJSON output:")
            print(json.dumps(businesses, indent=2))

    except Exception as e:
        print(f"Error: {e}")
