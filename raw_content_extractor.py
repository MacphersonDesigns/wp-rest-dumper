#!/usr/bin/env python3
"""
Raw Content Extractor for JB Lund Dealer Directory
Handles both tabular format and nectar_gmap coordinate data
"""

import re
import csv
import html
from urllib.parse import urlparse

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_map_businesses(content):
    """Extract businesses from nectar_gmap coordinate data"""
    businesses = []
    
    # Find the nectar_gmap section - look for the map_markers attribute specifically
    # The pattern includes HTML entities like &#8221; for quotes and spans multiple lines
    gmap_pattern = r'map_markers=&#8221;(.*?)&#8221;'
    gmap_match = re.search(gmap_pattern, content, re.DOTALL)
    
    if not gmap_match:
        print("No map_markers found with HTML entities")
        # Try alternative pattern without HTML entities
        alt_pattern = r'map_markers="(.*?)"'
        gmap_match = re.search(alt_pattern, content, re.DOTALL)
        if not gmap_match:
            print("No nectar_gmap section found")
            return businesses
        
    map_markers_content = gmap_match.group(1)
    print(f"Found map_markers content, length: {len(map_markers_content)}")
    
    # Extract coordinate data - format: latitude | longitude | business info
    # Each entry is on its own line: 46.383255 | -95.745433 | Advanced Docks and Lifts
    coordinate_pattern = r'([\d.-]+)\s*\|\s*([\d.-]+)\s*\|\s*([^\n\r]+)'
    
    coordinate_matches = re.findall(coordinate_pattern, map_markers_content, re.MULTILINE)
    print(f"Found {len(coordinate_matches)} coordinate entries")
    
    for lat, lon, business_info in coordinate_matches:
        try:
            # Clean the business info
            business_info = clean_text(business_info)
            
            # Skip empty entries
            if not business_info or len(business_info) < 10:
                continue
                
            # Parse business information
            # Split by <br> tags or newlines
            info_parts = re.split(r'<br\s*/?>\s*|\n', business_info)
            info_parts = [clean_text(part) for part in info_parts if clean_text(part)]
            
            if not info_parts:
                continue
                
            # First part is usually the business name
            name = info_parts[0]
            
            # Look for address, phone, etc.
            address = ""
            phone = ""
            
            for part in info_parts[1:]:
                # Check if it looks like a phone number
                if re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', part):
                    phone = part
                # Check if it looks like an address (has numbers and street-like words)
                elif re.search(r'\d+.*(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|blvd|boulevard|hwy|highway)', part, re.IGNORECASE):
                    if not address:  # Take the first address-like string
                        address = part
                # If it has city/state pattern, append to address
                elif re.search(r'[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}', part):
                    if address:
                        address += ", " + part
                    else:
                        address = part
            
            # Determine services based on business name/info
            services = []
            name_lower = name.lower()
            business_info_lower = business_info.lower()
            
            if any(word in name_lower or word in business_info_lower for word in ['dock', 'lift']):
                if 'dock' in name_lower or 'dock' in business_info_lower:
                    services.append('docks')
                if 'lift' in name_lower or 'lift' in business_info_lower:
                    services.append('lifts')
            
            if any(word in name_lower or word in business_info_lower for word in ['trailer', 'transport']):
                services.append('trailers')
                
            if not services:
                # Default service based on context
                services = ['docks & lifts']
            
            business = {
                'name': name,
                'address': address,
                'address_url': f"https://maps.google.com/?q={lat},{lon}",
                'phone': phone,
                'website_url': "",  # Map data typically doesn't include websites
                'services': ' & '.join(services),
                'extra_locations': [{'name': f"{lat},{lon}", 'coordinates': f"{lat},{lon}"}],
                'source': 'map_coordinates'
            }
            
            businesses.append(business)
            print(f"Extracted map business: {name}")
            
        except Exception as e:
            print(f"Error processing coordinate entry: {e}")
            continue
    
    return businesses

def extract_table_businesses(content):
    """Extract businesses from the tabular vc_row_inner format"""
    businesses = []
    
    # Find all vc_row_inner sections that contain business data
    row_pattern = r'\[vc_row_inner[^\]]*\](.*?)\[/vc_row_inner\]'
    row_matches = re.findall(row_pattern, content, re.DOTALL)
    
    print(f"Found {len(row_matches)} table rows")
    
    for row_content in row_matches:
        # Skip header rows and dividers
        if 'divider' in row_content or len(row_content.strip()) < 100:
            continue
            
        # Extract column content
        col_pattern = r'\[vc_column_text\](.*?)\[/vc_column_text\]'
        columns = re.findall(col_pattern, row_content, re.DOTALL)
        columns = [clean_text(col) for col in columns if clean_text(col)]
        
        # Skip empty or header rows
        if not columns or len(columns) < 3:
            continue
            
        # Check if this looks like a business row (has phone number pattern)
        has_phone = any(re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', col) for col in columns)
        if not has_phone:
            continue
            
        try:
            # Parse columns - typical format: Name, Address, Phone, Website, Services...
            name = columns[0] if len(columns) > 0 else ""
            address = columns[1] if len(columns) > 1 else ""
            phone = columns[2] if len(columns) > 2 else ""
            
            # Look for website indicator
            website_url = ""
            if len(columns) > 3 and "website" in columns[3].lower():
                website_url = ""  # Placeholder - actual URL would need to be extracted from links
            
            # Extract services from remaining columns
            services = []
            for col in columns[3:]:
                col_lower = col.lower()
                if 'dock' in col_lower and 'lift' in col_lower:
                    services.append('docks & lifts')
                elif 'dock' in col_lower:
                    services.append('docks')
                elif 'lift' in col_lower:
                    services.append('lifts')
                elif 'trailer' in col_lower:
                    services.append('trailers')
            
            if not services:
                services = ['docks & lifts']  # Default
            
            # Generate Google Maps URL for address
            address_url = ""
            if address:
                address_encoded = address.replace(' ', '+').replace(',', '%2C')
                address_url = f"https://maps.google.com/?q={address_encoded}"
            
            business = {
                'name': name,
                'address': address,
                'address_url': address_url,
                'phone': phone,
                'website_url': website_url,
                'services': ' & '.join(services),
                'extra_locations': "",
                'source': 'table_format'
            }
            
            businesses.append(business)
            print(f"Extracted table business: {name}")
            
        except Exception as e:
            print(f"Error processing table row: {e}")
            continue
    
    return businesses

def extract_all_businesses(raw_content_file):
    """Extract all businesses from raw content file"""
    try:
        with open(raw_content_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Processing file: {raw_content_file}")
        print(f"Content length: {len(content)} characters")
        
        # Extract from both sources
        map_businesses = extract_map_businesses(content)
        table_businesses = extract_table_businesses(content)
        
        print(f"\nExtracted {len(map_businesses)} businesses from map coordinates")
        print(f"Extracted {len(table_businesses)} businesses from table format")
        
        # Combine and deduplicate
        all_businesses = []
        seen_names = set()
        
        # Add all businesses, preferring table format for duplicates (more complete data)
        for business in table_businesses + map_businesses:
            name_normalized = business['name'].lower().strip()
            if name_normalized not in seen_names:
                all_businesses.append(business)
                seen_names.add(name_normalized)
        
        print(f"Total unique businesses: {len(all_businesses)}")
        return all_businesses
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return []

def save_to_csv(businesses, output_file):
    """Save businesses to CSV file"""
    if not businesses:
        print("No businesses to save")
        return
        
    fieldnames = ['name', 'address', 'address_url', 'phone', 'website_url', 'services', 'extra_locations', 'source']
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for business in businesses:
                writer.writerow(business)
        
        print(f"Saved {len(businesses)} businesses to {output_file}")
        
    except Exception as e:
        print(f"Error saving CSV: {e}")

if __name__ == "__main__":
    raw_file = "/Users/macphersondesigns/Sites/wp_dumpper/wp_dump/JB-Lund-Dock-amp-Lift/raw_pages/pages-dealers.txt"
    output_file = "/Users/macphersondesigns/Sites/wp_dumpper/complete_business_data.csv"
    
    businesses = extract_all_businesses(raw_file)
    
    if businesses:
        save_to_csv(businesses, output_file)
        
        # Show summary
        print("\n=== EXTRACTION SUMMARY ===")
        print(f"Total businesses extracted: {len(businesses)}")
        
        # Count by source
        map_count = sum(1 for b in businesses if b['source'] == 'map_coordinates')
        table_count = sum(1 for b in businesses if b['source'] == 'table_format')
        
        print(f"From map coordinates: {map_count}")
        print(f"From table format: {table_count}")
        
        # Show first few businesses
        print("\n=== SAMPLE BUSINESSES ===")
        for i, business in enumerate(businesses[:5]):
            print(f"{i+1}. {business['name']} - {business['address']} - {business['services']} ({business['source']})")
            
        if len(businesses) > 5:
            print(f"... and {len(businesses) - 5} more")
    else:
        print("No businesses extracted!")