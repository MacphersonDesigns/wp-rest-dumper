#!/usr/bin/env python3
"""
Single Page WordPress Extractor
Extracts specific data from a single WordPress page and outputs to CSV format.

This module can analyze any WordPress page URL and extract:
- Basic page metadata (title, URL, date, etc.)
- Content analysis (word count, headings, links)
- SEO data (meta tags, structured data)
- Business data (contact info, addresses, phone numbers)
- Media information (images, videos)
- Form information
"""

import csv
import json
import os
import re
import requests
from urllib.parse import urljoin, urlparse
from datetime import datetime
import pathlib
from bs4 import BeautifulSoup
from wp_rest_dump import (
    html_to_text_enhanced,
    extract_business_data,
    clean_theme_shortcodes,
    UA
)

def extract_single_page_data(page_url, username=None, password=None, verbose=False):
    """
    Extract comprehensive data from a single WordPress page.

    Args:
        page_url (str): Full URL to the WordPress page
        username (str): Optional WordPress username for authentication
        password (str): Optional WordPress password for authentication
        verbose (bool): Show detailed output

    Returns:
        dict: Extracted page data
    """

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    # Set up authentication if provided
    if username and password:
        session.auth = (username, password)
        if verbose:
            print(f"✓ Using authentication for {username}")

    try:
        # Parse the URL to get base site and determine if this is a REST API call
        parsed_url = urlparse(page_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Check if this is already a REST API URL
        if '/wp-json/' in page_url:
            api_url = page_url
        else:
            # Try to find the page via REST API
            # First, get the page slug from URL
            path_parts = [p for p in parsed_url.path.strip('/').split('/') if p]

            if not path_parts:
                # This might be the homepage
                api_url = urljoin(base_url, '/wp-json/wp/v2/pages?slug=home')
            else:
                page_slug = path_parts[-1]  # Last part is usually the slug
                api_url = urljoin(base_url, f'/wp-json/wp/v2/pages?slug={page_slug}')

        if verbose:
            print(f"🔍 Fetching page data from: {api_url}")

        # Get page data from REST API
        response = session.get(api_url)
        response.raise_for_status()
        pages_data = response.json()

        # Handle different response formats
        if isinstance(pages_data, list):
            if not pages_data:
                # Try posts endpoint if no pages found
                # Get path parts again in case they weren't defined earlier
                path_parts = [p for p in parsed_url.path.strip('/').split('/') if p]
                post_slug = path_parts[-1] if path_parts else 'home'
                api_url = urljoin(base_url, f'/wp-json/wp/v2/posts?slug={post_slug}')
                if verbose:
                    print(f"🔍 Trying posts endpoint: {api_url}")
                response = session.get(api_url)
                response.raise_for_status()
                pages_data = response.json()
                if not pages_data:
                    raise Exception("Page not found in WordPress REST API")
            page_data = pages_data[0]
        else:
            page_data = pages_data

        if verbose:
            print(f"✓ Found page: {page_data.get('title', {}).get('rendered', 'Untitled')}")

        # Extract basic page information
        page_info = {
            'id': page_data.get('id'),
            'title': page_data.get('title', {}).get('rendered', '').strip(),
            'url': page_data.get('link', page_url),
            'slug': page_data.get('slug', ''),
            'status': page_data.get('status', ''),
            'type': page_data.get('type', ''),
            'date_published': page_data.get('date', ''),
            'date_modified': page_data.get('modified', ''),
            'author_id': page_data.get('author', ''),
        }

        # Get the HTML content
        html_content = page_data.get('content', {}).get('rendered', '')
        excerpt = page_data.get('excerpt', {}).get('rendered', '')

        # Clean and process the content
        clean_content = clean_theme_shortcodes(html_content)
        text_content = html_to_text_enhanced(clean_content)

        # Extract business data - try both the original method and enhanced dealer directory parsing
        formatted_content, business_data = extract_business_data(text_content)

        # If no business data found with the original method, try enhanced dealer directory parsing
        if not business_data:
            business_data = extract_dealer_directory_data(html_content, text_content)

        # For JB Lund dealers page, use comprehensive raw content extraction if available
        if not business_data and 'jblund' in page_url.lower() and 'dealer' in page_url.lower():
            raw_file = "/Users/macphersondesigns/Sites/wp_dumpper/wp_dump/JB-Lund-Dock-amp-Lift/raw_pages/pages-dealers.txt"
            if os.path.exists(raw_file):
                if verbose:
                    print("Using comprehensive raw content extraction for JB Lund dealers")
                try:
                    import sys
                    sys.path.append('/Users/macphersondesigns/Sites/wp_dumpper')
                    from raw_content_extractor import extract_all_businesses
                    business_data = extract_all_businesses(raw_file)
                except ImportError as e:
                    if verbose:
                        print(f"Could not import raw_content_extractor: {e}")
                    business_data = []

        # If still no business data and we have shortcode content, try to parse that
        if not business_data and '[vc_' in html_content:
            business_data = extract_dealer_directory_from_shortcodes(html_content)

        # Analyze content
        content_analysis = analyze_content(html_content, text_content)

        # Extract SEO data
        seo_data = extract_seo_data(page_data, html_content)

        # Extract media information
        media_data = extract_media_data(html_content, base_url)

        # Extract form information
        form_data = extract_form_data(html_content)

        # Extract contact information
        contact_data = extract_contact_data(text_content)

        # Combine all data
        extracted_data = {
            'basic_info': page_info,
            'content_analysis': content_analysis,
            'seo_data': seo_data,
            'business_data': business_data,
            'media_data': media_data,
            'form_data': form_data,
            'contact_data': contact_data,
            'raw_content': {
                'html': html_content[:1000] + '...' if len(html_content) > 1000 else html_content,
                'text': formatted_content[:1000] + '...' if len(formatted_content) > 1000 else formatted_content,
                'excerpt': excerpt
            }
        }

        return extracted_data

    except requests.RequestException as e:
        # For JB Lund dealers page, try raw content extraction even if REST API fails
        if 'jblund' in page_url.lower() and 'dealer' in page_url.lower():
            if verbose:
                print("🔄 REST API failed, trying raw content extraction for JB Lund dealers...")
            raw_file = "/Users/macphersondesigns/Sites/wp_dumpper/wp_dump/JB-Lund-Dock-amp-Lift/raw_pages/pages-dealers.txt"
            if os.path.exists(raw_file):
                try:
                    import sys
                    sys.path.append('/Users/macphersondesigns/Sites/wp_dumpper')
                    from raw_content_extractor import extract_all_businesses
                    business_data = extract_all_businesses(raw_file)
                    # Return structure compatible with web GUI expectations
                    return {
                        'page_url': page_url,
                        'business_data': business_data,
                        'basic_info': {
                            'title': 'JB Lund Dealers Directory',
                            'slug': 'dealers',
                            'type': 'page',
                            'url': page_url,
                            'date': datetime.now().isoformat(),
                            'status': 'publish',
                            'content_length': len(str(business_data))
                        },
                        'content_analysis': {
                            'word_count': len(str(business_data).split()),
                            'heading_count': 1,
                            'link_count': len([b for b in business_data if b.get('Website_URL')]),
                            'image_count': 0,
                            'has_forms': False,
                            'has_videos': False
                        },
                        'seo_data': {
                            'meta_title': 'JB Lund Dealers Directory',
                            'meta_description': f'Directory of {len(business_data)} JB Lund dealers',
                            'meta_keywords': [],
                            'canonical_url': page_url
                        },
                        'media_data': {
                            'images': [],
                            'videos': []
                        },
                        'form_data': {
                            'forms': []
                        },
                        'extracted_from': 'raw_content',
                        'total_businesses': len(business_data)
                    }
                except Exception as raw_error:
                    if verbose:
                        print(f"Raw content extraction also failed: {raw_error}")
        raise Exception(f"Failed to fetch page data: {e}")
    except Exception as e:
        # For JB Lund dealers page, try raw content extraction even if REST API fails
        if 'jblund' in page_url.lower() and 'dealer' in page_url.lower():
            if verbose:
                print("🔄 REST API failed, trying raw content extraction for JB Lund dealers...")
            raw_file = "/Users/macphersondesigns/Sites/wp_dumpper/wp_dump/JB-Lund-Dock-amp-Lift/raw_pages/pages-dealers.txt"
            if os.path.exists(raw_file):
                try:
                    import sys
                    sys.path.append('/Users/macphersondesigns/Sites/wp_dumpper')
                    from raw_content_extractor import extract_all_businesses
                    business_data = extract_all_businesses(raw_file)
                    # Return structure compatible with web GUI expectations
                    return {
                        'page_url': page_url,
                        'business_data': business_data,
                        'basic_info': {
                            'title': 'JB Lund Dealers Directory',
                            'slug': 'dealers',
                            'type': 'page',
                            'url': page_url,
                            'date': datetime.now().isoformat(),
                            'status': 'publish',
                            'content_length': len(str(business_data))
                        },
                        'content_analysis': {
                            'word_count': len(str(business_data).split()),
                            'heading_count': 1,
                            'link_count': len([b for b in business_data if b.get('Website_URL')]),
                            'image_count': 0,
                            'has_forms': False,
                            'has_videos': False
                        },
                        'seo_data': {
                            'meta_title': 'JB Lund Dealers Directory',
                            'meta_description': f'Directory of {len(business_data)} JB Lund dealers',
                            'meta_keywords': [],
                            'canonical_url': page_url
                        },
                        'media_data': {
                            'images': [],
                            'videos': []
                        },
                        'form_data': {
                            'forms': []
                        },
                        'contact_data': {
                            'email': None,
                            'phone': None,
                            'social_media': []
                        },
                        'extracted_from': 'raw_content',
                        'total_businesses': len(business_data)
                    }
                except Exception as raw_error:
                    if verbose:
                        print(f"Raw content extraction also failed: {raw_error}")
        raise Exception(f"Error extracting page data: {e}")

def extract_dealer_directory_data(html_content, text_content):
    """Extract structured business data from dealer directory pages."""
    soup = BeautifulSoup(html_content, 'html.parser')
    business_data = []

    # Try different patterns common in dealer directories
    business_blocks = []

    # Pattern 1: Look for divs containing business listings
    potential_blocks = soup.find_all(['div', 'article', 'section'], class_=lambda x: x and any(
        keyword in x.lower() for keyword in ['dealer', 'business', 'listing', 'directory', 'card', 'item']
    ))

    if potential_blocks:
        business_blocks.extend(potential_blocks)

    # Pattern 2: Look for repeated structure patterns (headings followed by content)
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    for heading in headings:
        # Check if heading looks like a business name
        heading_text = heading.get_text().strip()
        if len(heading_text.split()) >= 2 and len(heading_text) > 5:  # Multi-word, reasonable length
            # Look for contact info in the next few siblings
            contact_section = []
            current = heading.next_sibling
            for _ in range(10):  # Look at next 10 siblings
                if current is None:
                    break
                if hasattr(current, 'get_text'):
                    text = current.get_text().strip()
                    if text:
                        contact_section.append(text)
                        # Stop if we hit another heading
                        if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break
                current = current.next_sibling

            if contact_section:
                business_blocks.append({
                    'name': heading_text,
                    'content': ' '.join(contact_section)
                })

    # Pattern 3: Parse text content for business-like patterns
    lines = text_content.split('\n')
    current_business = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this line looks like a business name (all caps, multi-word)
        if (line.isupper() and len(line.split()) >= 2 and
            not re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line) and  # Not a phone
            not re.search(r'\b\d+\s+\w+\s+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|ct|court)', line.lower())):  # Not an address

            if current_business:
                business_data.append(current_business)

            current_business = {
                'name': line,
                'address': '',
                'phone': '',
                'services': [],
                'other_info': []
            }

        elif current_business:
            # Try to categorize this line
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
            if phone_match:
                current_business['phone'] = phone_match.group().strip()

            # Check if it's an address
            elif re.search(r'\b\d+\s+\w+\s+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|ct|court)', line.lower()):
                current_business['address'] = line

            # Check if it contains state/zip pattern
            elif re.search(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?\b', line):
                if current_business['address']:
                    current_business['address'] += ', ' + line
                else:
                    current_business['address'] = line

            # Check for service-related keywords
            elif any(keyword in line.lower() for keyword in ['service', 'repair', 'parts', 'sales', 'marine', 'boat', 'engine', 'motor']):
                current_business['services'].append(line)

            else:
                current_business['other_info'].append(line)

    # Don't forget the last business
    if current_business:
        business_data.append(current_business)

    # Process business blocks from HTML structure
    for block in business_blocks:
        if isinstance(block, dict):
            # Already processed
            continue

        block_text = block.get_text().strip()
        if not block_text:
            continue

        # Try to extract business info from this block
        lines = [line.strip() for line in block_text.split('\n') if line.strip()]
        if len(lines) < 2:
            continue

        business_name = lines[0]
        business_info = {
            'name': business_name,
            'address': '',
            'phone': '',
            'services': [],
            'other_info': []
        }

        for line in lines[1:]:
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
            if phone_match:
                business_info['phone'] = phone_match.group().strip()
            elif re.search(r'\b\d+\s+\w+\s+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|ct|court)', line.lower()):
                business_info['address'] = line
            elif re.search(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?\b', line):
                if business_info['address']:
                    business_info['address'] += ', ' + line
                else:
                    business_info['address'] = line
            elif any(keyword in line.lower() for keyword in ['service', 'repair', 'parts', 'sales', 'marine', 'boat', 'engine', 'motor']):
                business_info['services'].append(line)
            else:
                business_info['other_info'].append(line)

        business_data.append(business_info)

    return business_data

def extract_dealer_directory_from_shortcodes(html_content):
    """Extract business data from WordPress shortcode content like Visual Composer."""
    business_data = []

    # Find all vc_column_text sections in order
    column_texts = re.findall(r'\[vc_column_text[^\]]*\](.*?)\[/vc_column_text\]', html_content, re.DOTALL)

    # Also extract all links to match with businesses later
    all_links = []
    link_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([^<]*)</a>'
    for section in column_texts:
        links_in_section = re.findall(link_pattern, section)
        all_links.extend(links_in_section)

    # Clean all sections
    cleaned_sections = []
    for section in column_texts:
        clean_content = re.sub(r'<[^>]+>', '', section)
        clean_content = clean_content.replace('&amp;', '&').replace('&#8217;', "'").replace('&#8243;', '"')
        clean_content = clean_content.strip()

        if clean_content:
            lines = [line.strip() for line in clean_content.split('\n') if line.strip()]
            if lines:
                cleaned_sections.append(lines)

    # Skip header sections (find where dealers actually start)
    start_index = 0
    for i, section_lines in enumerate(cleaned_sections):
        first_line = section_lines[0].lower()
        if 'advanced docks and lifts' in first_line:  # First known dealer
            start_index = i
            break

    # Process sections sequentially starting from the first dealer
    i = start_index
    current_business = None

    while i < len(cleaned_sections):
        section_lines = cleaned_sections[i]
        first_line = section_lines[0]

        # Skip clearly non-business sections
        if any(skip in first_line.lower() for skip in [
            'website', 'email', 'contact', 'phone', 'address', 'http'
        ]):
            # Check if this is a "Website" label - extract the website URL from next section
            if first_line.lower() == 'website' and current_business:
                # Look for website URL in the next section
                if i + 1 < len(cleaned_sections):
                    next_section_lines = cleaned_sections[i + 1]
                    raw_next_section = column_texts[i + 1] if i + 1 < len(column_texts) else ''

                    # Try multiple patterns for website URL extraction
                    website_patterns = [
                        r'href="([^"]*)"',
                        r"href='([^']*)'",
                        r'href=([^\s>]+)',
                    ]

                    for pattern in website_patterns:
                        website_match = re.search(pattern, raw_next_section, re.IGNORECASE)
                        if website_match:
                            url = website_match.group(1)
                            # Make sure it's an actual website URL (not maps or empty)
                            if url.startswith('http') and 'google.com/maps' not in url:
                                current_business['website_url'] = url
                                break

                # Skip both the "Website" section and the link section
                i += 2
                continue
            i += 1
            continue

        # Check if this looks like a phone number
        if re.search(r'^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$', first_line):
            if current_business:
                current_business['phone'] = first_line
            i += 1
            continue

        # Check if this looks like an address
        if (re.search(r'^\d+\s+\w+\s+(st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|ct|court)', first_line.lower()) or
            re.search(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?\b', first_line) or
            (len(section_lines) > 1 and re.search(r'\b[A-Z]{2}\s+\d{5}(-\d{4})?\b', section_lines[1]))):

            if current_business:
                # Combine all lines in this section as address
                current_business['address'] = ', '.join(section_lines)

                # Look for Google Maps URL for this address in the raw section
                raw_section = column_texts[i] if i < len(column_texts) else ''
                maps_matches = re.findall(r'<a[^>]*href=["\']([^"\']*google\.com/maps[^"\']*)["\'][^>]*>', raw_section)
                if maps_matches:
                    current_business['address_url'] = maps_matches[0]
            i += 1
            continue

        # Check if this looks like coordinate data (skip it for business name processing)
        if re.search(r'\d+\.\d+\s*\|\s*-?\d+\.\d+', first_line):
            i += 1
            continue

        # If we get here, this should be a business name
        # First, save the previous business if it exists
        if current_business:
            business_data.append(current_business)

        # Start a new business
        business_name = first_line

        # Handle multi-line business names (like "Advanced Auto" + "& Marine")
        if len(section_lines) > 1:
            second_line = section_lines[1]
            # If second line looks like part of the name (short, starts with &, etc.)
            if (len(second_line) < 20 and
                (second_line.startswith('&') or
                 second_line.lower() in ['marine', 'auto', 'sales', 'service', 'inc', 'llc', 'corp'])):
                business_name += ' ' + second_line

        # Categorize services based on business name
        services = []
        name_lower = business_name.lower()
        if 'dock' in name_lower and 'lift' in name_lower:
            services.append('docks & lifts')
        elif 'dock' in name_lower:
            services.append('docks')
        elif 'lift' in name_lower:
            services.append('lifts')
        if 'trailer' in name_lower:
            services.append('trailers')
        if 'marine' in name_lower:
            services.append('marine')
        if 'auto' in name_lower:
            services.append('auto')

        current_business = {
            'name': business_name,
            'address': '',
            'address_url': '',
            'phone': '',
            'website_url': '',
            'services': ', '.join(services) if services else ''
        }

        i += 1

    # Don't forget the last business
    if current_business:
        business_data.append(current_business)

    # Now look for extra locations in the coordinate data
    coordinate_section = None
    for section in column_texts:
        if '|' in section and re.search(r'\d+\.\d+\s*\|\s*-?\d+\.\d+', section):
            coordinate_section = section
            break

    if coordinate_section:
        # Extract businesses with coordinates that might have extra locations
        coord_lines = coordinate_section.split('<br />')
        for line in coord_lines:
            if '|' in line:
                # Pattern: lat | lng | Business Name
                parts = line.split('|')
                if len(parts) >= 3:
                    business_name = parts[2].strip()
                    # Clean up HTML entities
                    business_name = business_name.replace('&amp;', '&').replace('&#8217;', "'").replace('&#8243;', '"')

                    # Check if this is a business we haven't seen or an extra location
                    existing_business = None
                    for biz in business_data:
                        if business_name.lower() in biz['name'].lower() or biz['name'].lower() in business_name.lower():
                            existing_business = biz
                            break

                    if not existing_business:
                        # This might be an extra location or new business
                        lat = parts[0].strip()
                        lng = parts[1].strip()

                        # Check if this looks like an extra location for an existing business
                        for biz in business_data:
                            base_name = biz['name'].replace('&', '').replace(',', '').replace('LLC', '').replace('Inc', '').strip()
                            if any(word in business_name.lower() for word in base_name.lower().split() if len(word) > 3):
                                # This looks like an extra location
                                if 'extra_locations' not in biz:
                                    biz['extra_locations'] = []
                                biz['extra_locations'].append({
                                    'name': business_name,
                                    'coordinates': f"{lat}, {lng}"
                                })
                                break
                        else:
                            # This is a completely new business from coordinates
                            services = []
                            name_lower = business_name.lower()
                            if 'dock' in name_lower and 'lift' in name_lower:
                                services.append('docks & lifts')
                            elif 'dock' in name_lower:
                                services.append('docks')
                            elif 'lift' in name_lower:
                                services.append('lifts')
                            if 'trailer' in name_lower:
                                services.append('trailers')
                            if 'marine' in name_lower:
                                services.append('marine')
                            if 'auto' in name_lower:
                                services.append('auto')

                            business_data.append({
                                'name': business_name,
                                'address': f"Coordinates: {lat}, {lng}",
                                'address_url': '',
                                'phone': '',
                                'website_url': '',
                                'services': ', '.join(services) if services else ''
                            })

    return business_data

def analyze_content(html_content, text_content):
    """Analyze the content and return metrics."""

    # Word count
    words = len(text_content.split())

    # Character count
    chars = len(text_content)

    # Extract headings
    headings = []
    heading_patterns = [
        (r'<h1[^>]*>(.*?)</h1>', 'H1'),
        (r'<h2[^>]*>(.*?)</h2>', 'H2'),
        (r'<h3[^>]*>(.*?)</h3>', 'H3'),
        (r'<h4[^>]*>(.*?)</h4>', 'H4'),
        (r'<h5[^>]*>(.*?)</h5>', 'H5'),
        (r'<h6[^>]*>(.*?)</h6>', 'H6'),
    ]

    for pattern, level in heading_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            clean_heading = re.sub(r'<[^>]+>', '', match).strip()
            if clean_heading:
                headings.append({'level': level, 'text': clean_heading})

    # Extract links
    links = []
    link_pattern = r'<a[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>'
    link_matches = re.findall(link_pattern, html_content, re.IGNORECASE | re.DOTALL)

    for href, link_text in link_matches:
        clean_text = re.sub(r'<[^>]+>', '', link_text).strip()
        if clean_text and href:
            link_type = 'internal' if not href.startswith(('http://', 'https://')) else 'external'
            links.append({
                'url': href,
                'text': clean_text,
                'type': link_type
            })

    # Count paragraphs
    paragraphs = len(re.findall(r'<p[^>]*>.*?</p>', html_content, re.IGNORECASE | re.DOTALL))

    # Count images in content
    images = len(re.findall(r'<img[^>]*>', html_content, re.IGNORECASE))

    return {
        'word_count': words,
        'character_count': chars,
        'paragraph_count': paragraphs,
        'heading_count': len(headings),
        'headings': headings,
        'link_count': len(links),
        'links': links,
        'image_count': images
    }

def extract_seo_data(page_data, html_content):
    """Extract SEO-related data from the page."""

    seo_data = {
        'meta_title': '',
        'meta_description': '',
        'meta_keywords': '',
        'og_title': '',
        'og_description': '',
        'og_image': '',
        'twitter_card': '',
        'schema_markup': [],
        'canonical_url': '',
        'robots': ''
    }

    # Try to get SEO data from Yoast or RankMath if available
    yoast_meta = page_data.get('yoast_head', '')
    rankmath_meta = page_data.get('rankmath_head', '')

    meta_content = yoast_meta or rankmath_meta or html_content

    # Extract meta tags
    meta_patterns = {
        'meta_title': r'<title[^>]*>(.*?)</title>',
        'meta_description': r'<meta[^>]*name\s*=\s*["\']description["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
        'meta_keywords': r'<meta[^>]*name\s*=\s*["\']keywords["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
        'og_title': r'<meta[^>]*property\s*=\s*["\']og:title["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
        'og_description': r'<meta[^>]*property\s*=\s*["\']og:description["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
        'og_image': r'<meta[^>]*property\s*=\s*["\']og:image["\'][^>]*content\s*=\s*["\']([^"\']*)["\']',
        'canonical_url': r'<link[^>]*rel\s*=\s*["\']canonical["\'][^>]*href\s*=\s*["\']([^"\']*)["\']',
        'robots': r'<meta[^>]*name\s*=\s*["\']robots["\'][^>]*content\s*=\s*["\']([^"\']*)["\']'
    }

    for key, pattern in meta_patterns.items():
        match = re.search(pattern, meta_content, re.IGNORECASE | re.DOTALL)
        if match:
            seo_data[key] = match.group(1).strip()

    # Extract Twitter card data
    twitter_match = re.search(r'<meta[^>]*name\s*=\s*["\']twitter:card["\'][^>]*content\s*=\s*["\']([^"\']*)["\']', meta_content, re.IGNORECASE)
    if twitter_match:
        seo_data['twitter_card'] = twitter_match.group(1).strip()

    # Extract structured data (JSON-LD)
    json_ld_pattern = r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    json_ld_matches = re.findall(json_ld_pattern, html_content, re.IGNORECASE | re.DOTALL)

    for json_ld in json_ld_matches:
        try:
            parsed_json = json.loads(json_ld.strip())
            seo_data['schema_markup'].append(parsed_json)
        except json.JSONDecodeError:
            continue

    return seo_data

def extract_media_data(html_content, base_url=""):
    """Extract media information from the page."""

    media_data = {
        'images': [],
        'videos': [],
        'audio': []
    }

    # Extract images
    img_pattern = r'<img[^>]*src\s*=\s*["\']([^"\']+)["\'][^>]*(?:alt\s*=\s*["\']([^"\']*)["\'])?[^>]*>'
    img_matches = re.findall(img_pattern, html_content, re.IGNORECASE)

    for src, alt in img_matches:
        # Make relative URLs absolute
        if src.startswith('/') and base_url:
            src = urljoin(base_url, src)

        media_data['images'].append({
            'src': src,
            'alt': alt,
            'type': 'image'
        })

    # Extract videos
    video_patterns = [
        r'<video[^>]*src\s*=\s*["\']([^"\']+)["\'][^>]*>',
        r'<iframe[^>]*src\s*=\s*["\']([^"\']*(?:youtube|vimeo|wistia)[^"\']*)["\'][^>]*>',
        r'<embed[^>]*src\s*=\s*["\']([^"\']*video[^"\']*)["\'][^>]*>'
    ]

    for pattern in video_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for src in matches:
            if src.startswith('/') and base_url:
                src = urljoin(base_url, src)
            media_data['videos'].append({
                'src': src,
                'type': 'video'
            })

    # Extract audio
    audio_pattern = r'<audio[^>]*src\s*=\s*["\']([^"\']+)["\'][^>]*>'
    audio_matches = re.findall(audio_pattern, html_content, re.IGNORECASE)

    for src in audio_matches:
        if src.startswith('/') and base_url:
            src = urljoin(base_url, src)
        media_data['audio'].append({
            'src': src,
            'type': 'audio'
        })

    return media_data

def extract_form_data(html_content):
    """Extract form information from the page."""

    forms = []

    # Find all forms
    form_pattern = r'<form[^>]*>(.*?)</form>'
    form_matches = re.findall(form_pattern, html_content, re.IGNORECASE | re.DOTALL)

    for form_content in form_matches:
        form_info = {
            'action': '',
            'method': 'GET',
            'fields': []
        }

        # Extract form attributes
        action_match = re.search(r'action\s*=\s*["\']([^"\']*)["\']', form_content, re.IGNORECASE)
        if action_match:
            form_info['action'] = action_match.group(1)

        method_match = re.search(r'method\s*=\s*["\']([^"\']*)["\']', form_content, re.IGNORECASE)
        if method_match:
            form_info['method'] = method_match.group(1).upper()

        # Extract form fields
        field_patterns = [
            r'<input[^>]*name\s*=\s*["\']([^"\']*)["\'][^>]*(?:type\s*=\s*["\']([^"\']*)["\'])?[^>]*>',
            r'<textarea[^>]*name\s*=\s*["\']([^"\']*)["\'][^>]*>',
            r'<select[^>]*name\s*=\s*["\']([^"\']*)["\'][^>]*>'
        ]

        for pattern in field_patterns:
            matches = re.findall(pattern, form_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    field_name = match[0]
                    field_type = match[1] if len(match) > 1 else 'text'
                else:
                    field_name = match
                    field_type = 'text'

                form_info['fields'].append({
                    'name': field_name,
                    'type': field_type
                })

        forms.append(form_info)

    return {'forms': forms, 'form_count': len(forms)}

def extract_contact_data(text_content):
    """Extract contact information from the page content."""

    contact_data = {
        'phone_numbers': [],
        'email_addresses': [],
        'addresses': [],
        'social_links': []
    }

    # Extract phone numbers
    phone_patterns = [
        r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',  # US format
        r'(\(\d{3}\)\s?\d{3}[-.\s]?\d{4})',  # (123) 456-7890
        r'(\+\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4})'  # International
    ]

    for pattern in phone_patterns:
        matches = re.findall(pattern, text_content)
        contact_data['phone_numbers'].extend(matches)

    # Extract email addresses
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    email_matches = re.findall(email_pattern, text_content)
    contact_data['email_addresses'] = list(set(email_matches))  # Remove duplicates

    # Extract addresses (basic pattern for US addresses)
    address_patterns = [
        r'(\d+[^,\n]+,?\s*[A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)',
        r'([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)'
    ]

    for pattern in address_patterns:
        matches = re.findall(pattern, text_content)
        contact_data['addresses'].extend(matches)

    # Extract social media links (would need HTML content for this)
    # This is a simplified version
    social_keywords = ['facebook', 'twitter', 'instagram', 'linkedin', 'youtube']
    for keyword in social_keywords:
        if keyword in text_content.lower():
            contact_data['social_links'].append(keyword)

    return contact_data

def export_to_csv(extracted_data, output_file):
    """Export the extracted data to a CSV file."""

    # Flatten the data for CSV export
    flattened_data = []

    # Basic info
    basic = extracted_data['basic_info']
    content = extracted_data['content_analysis']
    seo = extracted_data['seo_data']
    contact = extracted_data['contact_data']
    media = extracted_data['media_data']
    forms = extracted_data['form_data']

    # Create main row with basic page data
    main_row = {
        'page_id': basic.get('id', ''),
        'title': basic.get('title', ''),
        'url': basic.get('url', ''),
        'slug': basic.get('slug', ''),
        'status': basic.get('status', ''),
        'type': basic.get('type', ''),
        'date_published': basic.get('date_published', ''),
        'date_modified': basic.get('date_modified', ''),
        'author_id': basic.get('author_id', ''),

        # Content metrics
        'word_count': content.get('word_count', 0),
        'character_count': content.get('character_count', 0),
        'paragraph_count': content.get('paragraph_count', 0),
        'heading_count': content.get('heading_count', 0),
        'link_count': content.get('link_count', 0),
        'image_count': content.get('image_count', 0),

        # SEO data
        'meta_title': seo.get('meta_title', ''),
        'meta_description': seo.get('meta_description', ''),
        'meta_keywords': seo.get('meta_keywords', ''),
        'og_title': seo.get('og_title', ''),
        'og_description': seo.get('og_description', ''),
        'og_image': seo.get('og_image', ''),
        'canonical_url': seo.get('canonical_url', ''),
        'robots': seo.get('robots', ''),
        'schema_markup_count': len(seo.get('schema_markup', [])),

        # Contact data
        'phone_numbers': '; '.join(contact.get('phone_numbers', [])),
        'email_addresses': '; '.join(contact.get('email_addresses', [])),
        'addresses': '; '.join(contact.get('addresses', [])),
        'social_links': '; '.join(contact.get('social_links', [])),

        # Media counts
        'total_images': len(media.get('images', [])),
        'total_videos': len(media.get('videos', [])),
        'total_audio': len(media.get('audio', [])),

        # Form data
        'form_count': forms.get('form_count', 0),

        # Business data count
        'business_listings': len(extracted_data.get('business_data', [])),

        # Timestamps
        'extracted_at': datetime.now().isoformat()
    }

    flattened_data.append(main_row)

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        if flattened_data:
            fieldnames = flattened_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_data)

    return output_file

def export_detailed_to_csv(extracted_data, output_directory):
    """Export detailed data to multiple CSV files."""

    output_dir = pathlib.Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    files_created = []

    # Main page data
    main_file = output_dir / 'page_summary.csv'
    export_to_csv(extracted_data, main_file)
    files_created.append(str(main_file))

    # Headings
    headings = extracted_data['content_analysis'].get('headings', [])
    if headings:
        headings_file = output_dir / 'headings.csv'
        with open(headings_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['level', 'text'])
            writer.writeheader()
            writer.writerows(headings)
        files_created.append(str(headings_file))

    # Links
    links = extracted_data['content_analysis'].get('links', [])
    if links:
        links_file = output_dir / 'links.csv'
        with open(links_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['url', 'text', 'type'])
            writer.writeheader()
            writer.writerows(links)
        files_created.append(str(links_file))

    # Images
    images = extracted_data['media_data'].get('images', [])
    if images:
        images_file = output_dir / 'images.csv'
        with open(images_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['src', 'alt', 'type'])
            writer.writeheader()
            writer.writerows(images)
        files_created.append(str(images_file))

    # Business data
    business_data = extracted_data.get('business_data', [])
    if business_data:
        business_file = output_dir / 'business_data.csv'

        # Flatten business data for CSV - use the new optimized format
        flattened_business = []
        for business in business_data:
            if isinstance(business, dict):
                # Use the new field structure that matches user requirements
                flat_business = {
                    'name': business.get('name', ''),
                    'address': business.get('address', ''),
                    'address_url': business.get('address_url', ''),
                    'phone': business.get('phone', ''),
                    'website_url': business.get('website_url', business.get('website', '')),
                    'services': business.get('services', ''),
                    'extra_locations': '; '.join([f"{loc['name']} ({loc['coordinates']})" for loc in business.get('extra_locations', [])])
                }

                # Handle legacy formats if needed
                if not flat_business['services'] and business.get('services') and isinstance(business['services'], list):
                    flat_business['services'] = '; '.join(business['services'])

                flattened_business.append(flat_business)

        with open(business_file, 'w', newline='', encoding='utf-8') as csvfile:
            if flattened_business:
                fieldnames = flattened_business[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened_business)
        files_created.append(str(business_file))

    return files_created

def main():
    """CLI interface for single page extraction."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract data from a single WordPress page to CSV')
    parser.add_argument('url', help='WordPress page URL to extract data from')
    parser.add_argument('-o', '--output', default='page_extract.csv', help='Output CSV file (default: page_extract.csv)')
    parser.add_argument('-d', '--detailed', action='store_true', help='Create detailed CSV files for each data type')
    parser.add_argument('-u', '--username', help='WordPress username for authentication')
    parser.add_argument('-p', '--password', help='WordPress password for authentication')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')

    args = parser.parse_args()

    try:
        print(f"🔍 Extracting data from: {args.url}")

        # Extract data
        extracted_data = extract_single_page_data(
            args.url,
            username=args.username,
            password=args.password,
            verbose=args.verbose
        )

        if args.detailed:
            # Create directory for detailed output
            output_dir = pathlib.Path(args.output).stem + '_detailed'
            files_created = export_detailed_to_csv(extracted_data, output_dir)
            print(f"✅ Detailed data exported to {len(files_created)} files:")
            for file in files_created:
                print(f"   📄 {file}")
        else:
            # Single CSV file
            export_to_csv(extracted_data, args.output)
            print(f"✅ Data exported to: {args.output}")

        # Show summary
        basic = extracted_data['basic_info']
        content = extracted_data['content_analysis']

        print(f"\n📊 Summary:")
        print(f"   Title: {basic.get('title', 'Untitled')}")
        print(f"   Type: {basic.get('type', 'unknown')}")
        print(f"   Words: {content.get('word_count', 0)}")
        print(f"   Headings: {content.get('heading_count', 0)}")
        print(f"   Links: {content.get('link_count', 0)}")
        print(f"   Images: {content.get('image_count', 0)}")

        business_count = len(extracted_data.get('business_data', []))
        if business_count > 0:
            print(f"   Business listings: {business_count}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())