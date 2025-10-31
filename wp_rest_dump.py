#!/usr/bin/env python3
"""
Quick WordPress REST dumper
- Dumps text from pages/posts/CPTs to ./wp_dump/pages/*.txt
- Downloads original media to ./wp_dump/images/*
- Writes ./wp_dump/index.json with basic metadata

Usage:
  python wp_rest_dump.py https://jblunddock.com [--out wp_dump] [--all-types] [--sleep 0.2]

Notes:
- Works with public REST API (site.com/wp-json/)
- By default grabs types: pages, posts. Use --all-types to include public CPTs.
- Interactive authentication prompt allows access to protected endpoints.
- Use --no-auth to skip authentication prompt for automated runs.
"""

import argparse, getpass, json, os, pathlib, re, sys, time
from urllib.parse import urljoin, urlparse
import requests
from requests.exceptions import HTTPError

UA = "WP-Dumper/1.0 (+https://jblunddock.com/)"

def html_to_text(html: str) -> str:
    """Original HTML to text converter - strips all HTML"""
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", "", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6])>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def html_to_text_enhanced(html_str: str) -> str:
    """Enhanced HTML to text converter that preserves links and important tags"""
    if not html_str:
        return ""

    # Decode HTML entities first
    import html
    html_str = html.unescape(html_str)

    # Remove scripts and styles completely
    html_str = re.sub(r"<(script|style)[\s\S]*?</\1>", "", html_str, flags=re.I)
    html_str = re.sub(r"<(noscript)[\s\S]*?</\1>", "", html_str, flags=re.I)

    # Convert links/buttons to "Button Text | Button URL" format
    html_str = re.sub(
        r'<a[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        lambda m: f"{re.sub(r'<[^>]+>', '', m.group(2)).strip()} | {m.group(1).strip()}",
        html_str,
        flags=re.I | re.DOTALL
    )

    # Preserve important heading tags with markers
    html_str = re.sub(r'<h1[^>]*>(.*?)</h1>', r'[H1] \1', html_str, flags=re.I | re.DOTALL)
    html_str = re.sub(r'<h2[^>]*>(.*?)</h2>', r'[H2] \1', html_str, flags=re.I | re.DOTALL)
    html_str = re.sub(r'<h3[^>]*>(.*?)</h3>', r'[H3] \1', html_str, flags=re.I | re.DOTALL)
    html_str = re.sub(r'<h4[^>]*>(.*?)</h4>', r'[H4] \1', html_str, flags=re.I | re.DOTALL)
    html_str = re.sub(r'<h5[^>]*>(.*?)</h5>', r'[H5] \1', html_str, flags=re.I | re.DOTALL)
    html_str = re.sub(r'<h6[^>]*>(.*?)</h6>', r'[H6] \1', html_str, flags=re.I | re.DOTALL)

    # Convert block elements to line breaks
    html_str = re.sub(r"<br\s*/?>", "\n", html_str, flags=re.I)
    html_str = re.sub(r"</(p|div|li|article|section|header|footer|nav|main)>", "\n", html_str, flags=re.I)

    # Remove remaining HTML tags
    text = re.sub(r"<[^>]+>", "", html_str)

    # Clean up whitespace
    text = re.sub(r"\r?\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\r?\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

def clean_theme_shortcodes(text: str) -> str:
    """Remove theme builder shortcodes while preserving content and structure"""
    if not text:
        return text

    # Remove WordPress theme builder shortcodes (Visual Composer, Elementor, Divi, etc.)
    # These are the common ones that create noise

    # Remove VC (Visual Composer) shortcodes with all their attributes
    text = re.sub(r'\[vc_\w+[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[/vc_\w+\]', '', text, flags=re.IGNORECASE)

    # Remove Elementor shortcodes
    text = re.sub(r'\[elementor-template[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[/elementor-template\]', '', text, flags=re.IGNORECASE)

    # Remove Divi builder shortcodes
    text = re.sub(r'\[et_pb_\w+[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[/et_pb_\w+\]', '', text, flags=re.IGNORECASE)

    # Remove other common page builder shortcodes
    text = re.sub(r'\[nectar_\w+[^\]]*\]', '', text, flags=re.IGNORECASE)  # Nectar/Salient theme
    text = re.sub(r'\[divider[^\]]*\]', '', text, flags=re.IGNORECASE)      # Common dividers
    text = re.sub(r'\[/divider\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[ultimate_\w+[^\]]*\]', '', text, flags=re.IGNORECASE) # Ultimate Addons
    text = re.sub(r'\[/ultimate_\w+\]', '', text, flags=re.IGNORECASE)

    # Remove WPBakery specific shortcodes that are pure layout
    text = re.sub(r'\[vc_raw_html\][^\[]*\[/vc_raw_html\]', '', text, flags=re.IGNORECASE)

    # Clean up any remaining generic shortcode patterns that look like serialized data
    # Pattern: [shortcode key="value" key2="value2" ...]
    text = re.sub(r'\[\w+(?:\s+\w+="[^"]*")*\s*\]', '', text)
    text = re.sub(r'\[/\w+\]', '', text)

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
        # Parse individual markers: lat | lng | business_name
        marker_pattern = r'([\d.-]+)\s*\|\s*([\d.-]+)\s*\|\s*([^\r\n]+?)(?=\s*[\d.-]+\s*\||\Z)'

        marker_matches = re.finditer(marker_pattern, markers_data, re.MULTILINE | re.DOTALL)

        for match in marker_matches:
            try:
                lat, lng, business_name = match.groups()

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

                    # Now try to find additional details for this business in the surrounding text
                    # Look for patterns around the business name
                    business_section_pattern = rf'({re.escape(business_name)}.*?)(?=\n\s*[A-Z].*?\n|$)'
                    business_match = re.search(business_section_pattern, text, re.IGNORECASE | re.DOTALL)

                    if business_match:
                        business_section = business_match.group(1)

                        # Extract phone numbers (including tel: links)
                        phone_patterns = [
                            r'(\d{3}-\d{3}-\d{4})',  # Already formatted
                            r'(\d{3})-(\d{3})-(\d{4})'  # Standard format
                        ]
                        for pattern in phone_patterns:
                            phone_match = re.search(pattern, business_section)
                            if phone_match:
                                if len(phone_match.groups()) == 1:
                                    business['phone'] = phone_match.group(1)
                                else:
                                    business['phone'] = f"{phone_match.group(1)}-{phone_match.group(2)}-{phone_match.group(3)}"
                                break

                        # Extract websites
                        website_match = re.search(r'Website \| (https?://[^\s]+)', business_section)
                        if website_match:
                            business['website'] = website_match.group(1)

                        # Extract emails
                        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', business_section)
                        if email_match:
                            business['email'] = email_match.group(1)

                        # Extract addresses (city, state zip)
                        address_patterns = [
                            r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)',  # City, ST ZIP
                            r'(\d+[^,\n]+),?\s*([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)'  # Street, City, ST ZIP
                        ]
                        for pattern in address_patterns:
                            address_match = re.search(pattern, business_section)
                            if address_match:
                                groups = address_match.groups()
                                if len(groups) == 3:  # City, State, ZIP
                                    business['address'] = {
                                        'city': groups[0].strip(),
                                        'state': groups[1],
                                        'zip_code': groups[2]
                                    }
                                elif len(groups) == 4:  # Street, City, State, ZIP
                                    business['address'] = {
                                        'street': groups[0].strip(),
                                        'city': groups[1].strip(),
                                        'state': groups[2],
                                        'zip_code': groups[3]
                                    }
                                break

                        # Extract business categories/services
                        if 'Docks & Lifts' in business_section:
                            business.setdefault('services', []).append('Docks & Lifts')
                        if 'Trailers' in business_section:
                            business.setdefault('services', []).append('Trailers')

                    businesses.append(business)

            except (ValueError, IndexError) as e:
                # Skip invalid coordinate data
                continue

    # Clean up the text - remove the gmap shortcode and messy coordinate data
    cleaned_text = text

    # Remove nectar_gmap shortcodes entirely
    cleaned_text = re.sub(r'\[nectar_gmap[^\]]*\]', '', cleaned_text)

    # Remove coordinate spam that's left over
    cleaned_text = re.sub(r'\d+\.\d+\s*\|\s*-?\d+\.\d+[^\n]*', '', cleaned_text)

    # Remove long Google Maps URLs
    cleaned_text = re.sub(r'https://[^\s]*google\.com/maps[^\s]*', '[Google Maps Link]', cleaned_text)
    cleaned_text = re.sub(r'https://maps\.app\.goo\.gl/[^\s]*', '[Google Maps Link]', cleaned_text)

    return cleaned_text, businesses

def format_to_markdown(content: str, title: str = "", url: str = "") -> str:
    """Convert content to beautiful markdown format"""
    if not content:
        return ""

    markdown = []

    # Add title and metadata
    if title:
        markdown.append(f"# {title}")
        markdown.append("")

    if url:
        markdown.append(f"**Source:** [{url}]({url})")
        markdown.append("")
        markdown.append("---")
        markdown.append("")

    # Split content into sections and format
    lines = content.split('\n')
    current_section = []

    for line in lines:
        line = line.strip()

        # Skip empty lines in section building
        if not line:
            if current_section:
                markdown.extend(current_section)
                markdown.append("")
                current_section = []
            continue

        # Detect headers (lines that might be titles/headings)
        if (len(line) < 60 and
            not line.endswith('.') and
            not line.startswith('http') and
            not re.search(r'\d{3}-\d{3}-\d{4}', line) and
            line[0].isupper()):

            # Flush current section
            if current_section:
                markdown.extend(current_section)
                markdown.append("")
                current_section = []

            # Add as header
            markdown.append(f"## {line}")
            markdown.append("")
            continue

        # Format phone numbers
        if re.search(r'\d{3}-\d{3}-\d{4}', line):
            line = f"📞 **Phone:** {line}"

        # Format websites
        if line.startswith('Website |'):
            url_part = line.split('| ', 1)[1] if '| ' in line else line.replace('Website ', '')
            line = f"🌐 **Website:** [{url_part}]({url_part})"

        # Format emails
        if '@' in line and '.' in line:
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
            if email_match:
                email = email_match.group(1)
                line = f"✉️ **Email:** [{email}](mailto:{email})"

        # Format addresses (lines with city, state, zip)
        if re.search(r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)', line):
            line = f"📍 **Address:** {line}"

        current_section.append(line)

    # Add final section
    if current_section:
        markdown.extend(current_section)

    return '\n'.join(markdown)

def format_directory_content(text: str) -> str:
    """Format directory-style content with smart shortcode removal and JSON extraction"""
    if not text:
        return text

    # First, clean theme shortcodes
    text = clean_theme_shortcodes(text)

    # Extract structured business data
    text, businesses = extract_business_data(text)

    # Phone number regex
    phone_pattern = r"(?:\+?1[\s\-.]?)?(?:\(\d{3}\)|\d{3})[\s\-.]?\d{3}[\s\-.]?\d{4}"

    def normalize_phone(match):
        """Normalize phone number to XXX-XXX-XXXX format"""
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        return match.group(0)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Add line breaks before key elements that might be jammed together
    text = re.sub(r"(?<!\n)(Website\s*\|)", r"\n\1", text)
    text = re.sub(rf"(?<!\n)(?=({phone_pattern}))", r"\n", text)

    # Add line break after ZIP codes (5 digits or 5+4 format)
    text = re.sub(r"(\b\d{5}(?:-\d{4})?)(?!\n)", r"\1\n", text)

    # Normalize phone numbers
    text = re.sub(phone_pattern, normalize_phone, text)

    # Clean up excessive blank lines while preserving intentional spacing
    lines = [line.rstrip() for line in text.split("\n")]
    cleaned_lines = []
    blank_count = 0

    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 1:  # Allow max 1 consecutive blank line
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    # Add structured business data as JSON at the end if we found any
    result_text = "\n".join(cleaned_lines).strip()

    if businesses:
        import json
        result_text += "\n\n" + "="*50 + "\n"
        result_text += "🏢 STRUCTURED BUSINESS DATA (JSON):\n"
        result_text += "="*50 + "\n"
        result_text += json.dumps(businesses, indent=2, ensure_ascii=False)

    return result_text

def get_json(session: requests.Session, url: str, params=None, timeout=25):
    r = session.get(url, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r

def paged(session: requests.Session, base: str, endpoint: str, per_page=100, sleep=0.2):
    """Yield items across WP REST pagination."""
    url = urljoin(base, endpoint)
    page = 1
    while True:
        try:
            r = get_json(session, url, params={"per_page": per_page, "page": page})
            items = r.json()
            if not items:
                break
            for it in items:
                yield it
            page += 1
            time.sleep(sleep)
        except HTTPError as e:
            if e.response.status_code == 400 and page > 1:
                # Sometimes WP returns 400 when requesting beyond available pages
                break
            else:
                # Re-raise for the caller to handle
                raise

def discover_types(session: requests.Session, base: str, include_all=False, verbose=False, authenticated=False):
    # Always include core pages/posts
    types = {"pages": "pages", "posts": "posts"}
    if not include_all:
        return types

    # Known problematic endpoints that often require authentication or are malformed
    # If authenticated, we'll be more liberal about what we try
    if authenticated:
        blocked_endpoints = set()  # Try everything if authenticated
        if verbose:
            print("   → Authentication enabled - will attempt all endpoints")
    else:
        blocked_endpoints = {
            "font-families", "font-faces", "global-styles", "template-parts",
            "templates", "navigation", "blocks", "patterns"
        }

    # Add public CPTs
    r = get_json(session, urljoin(base, "/wp-json/wp/v2/types"))
    data = r.json()
    for k, v in data.items():
        if k in ("page", "post"):  # already included via pages/posts
            continue
        rest_base = v.get("rest_base")
        viewable = v.get("viewable", True)
        if rest_base and viewable:
            # Skip endpoints with regex patterns or special characters
            if any(char in rest_base for char in ['(?', ')', '[', ']', '+']):
                if verbose:
                    print(f"   → Skipping {rest_base} (malformed endpoint pattern)")
                continue
            if rest_base in blocked_endpoints:
                if verbose:
                    print(f"   → Skipping {rest_base} (known to require authentication)")
            else:
                types[rest_base] = rest_base
    return types

def ensure_dir(path: pathlib.Path):
    path.mkdir(parents=True, exist_ok=True)

def save_triple_text_files(html_content: str, title: str, filename: str, base_dir: pathlib.Path, url: str = "") -> tuple[str, str, str]:
    """Save raw, pretty, and markdown versions of text files"""
    # Create directory structure
    raw_dir = base_dir / "raw_pages"
    pretty_dir = base_dir / "pretty_pages"
    markdown_dir = base_dir / "markdown_pages"
    ensure_dir(raw_dir)
    ensure_dir(pretty_dir)
    ensure_dir(markdown_dir)

    # Generate all three versions
    raw_text = html_to_text(html_content)
    pretty_text = html_to_text_enhanced(html_content)
    formatted_text = format_directory_content(pretty_text)

    # Create markdown version with beautiful formatting
    markdown_text = format_to_markdown(formatted_text, title.strip(), url)

    # Add title to raw and pretty versions (markdown already has it)
    if title.strip():
        raw_text = (title.strip() + "\n\n" + raw_text).strip()
        formatted_text = (title.strip() + "\n\n" + formatted_text).strip()

    # Save files
    raw_path = raw_dir / filename
    pretty_path = pretty_dir / filename
    markdown_path = markdown_dir / filename.replace('.txt', '.md')

    raw_path.write_text(raw_text, encoding="utf-8")
    pretty_path.write_text(formatted_text, encoding="utf-8")
    markdown_path.write_text(markdown_text, encoding="utf-8")

    return str(raw_path), str(pretty_path), str(markdown_path)

def setup_authentication(session: requests.Session, interactive=True, username=None, password=None):
    """Set up authentication credentials for session."""
    if not interactive and username and password:
        # Direct authentication for GUI
        session.auth = (username, password)
        return True
    elif interactive:
        # Interactive CLI authentication
        try:
            response = input("\n==> Do you want to authenticate? This will allow access to protected endpoints (y/N): ").strip().lower()
            if response in ('y', 'yes'):
                print("\nWordPress Authentication:")
                print("Enter your WordPress username and password.")
                print("(This uses HTTP Basic Auth - only use on HTTPS sites)")

                username = input("Username: ").strip()
                if not username:
                    print("No username provided, continuing without authentication.")
                    return False

                password = getpass.getpass("Password: ")
                if not password:
                    print("No password provided, continuing without authentication.")
                    return False

                # Set up HTTP Basic Auth
                session.auth = (username, password)
                print("✓ Authentication configured")
                return True
            else:
                print("Continuing without authentication.")
                return False
        except (KeyboardInterrupt, EOFError):
            print("\nContinuing without authentication.")
            return False
    return False

def dump_wordpress_content(base_url, output_dir="wp_dump", sleep_time=0.2, all_types=False,
                         skip_media=False, verbose=False, use_auth=False, username=None, password=None,
                         interactive_auth=False):
    """
    Core function to dump WordPress content. Can be called from CLI or GUI.

    Args:
        base_url (str): Site base URL
        output_dir (str): Output directory path
        sleep_time (float): Delay between requests
        all_types (bool): Include all content types
        skip_media (bool): Skip media downloads
        verbose (bool): Show verbose output
        use_auth (bool): Use authentication
        username (str): WordPress username (if use_auth=True)
        password (str): WordPress password (if use_auth=True)

    Returns:
        tuple: (success: bool, output_dir: str, message: str)
    """
    try:
        base = base_url.rstrip("/")

        s = requests.Session()
        s.headers.update({"User-Agent": UA})

        # Sanity check: is REST enabled?
        try:
            root = get_json(s, urljoin(base, "/wp-json/")).json()
        except Exception as e:
            return False, output_dir, f"Could not reach REST API at {base}/wp-json/ :: {e}"

        # Get site name and create site-specific directory
        site_name = (root.get("name") or urlparse(base).netloc)
        # Clean site name for use as directory name
        clean_site_name = re.sub(r'[^\w\s-]', '', site_name).strip()
        clean_site_name = re.sub(r'[-\s]+', '-', clean_site_name)

        # Create site-specific output directory
        base_out = pathlib.Path(output_dir)
        site_out = base_out / clean_site_name
        images_dir = site_out / "images"
        ensure_dir(base_out); ensure_dir(site_out); ensure_dir(images_dir)

        print(f"==> Connected to: {site_name}")
        print(f"==> Saving to: {site_out}")

        # Authentication setup
        authenticated = False
        if interactive_auth:
            authenticated = setup_authentication(s, interactive=True)
        elif use_auth and username and password:
            authenticated = setup_authentication(s, interactive=False, username=username, password=password)
            if verbose and authenticated:
                print("✓ Authentication configured")

        # Discover types
        types = discover_types(s, base, include_all=all_types, verbose=verbose, authenticated=authenticated)
        print(f"==> Will fetch content types: {', '.join(sorted(types.keys()))}")

        index = {
            "site": base,
            "generated_at": int(time.time()),
            "items": [],
            "media": []
        }

        # Dump text content
        for rest_base in sorted(types.keys()):
            endpoint = f"/wp-json/wp/v2/{rest_base}"
            print(f"-- Fetching {rest_base} ...")
            count = 0
            try:
                for item in paged(s, base, endpoint, sleep=sleep_time):
                    count += 1
                    slug = item.get("slug") or str(item.get("id"))
                    title = (item.get("title", {}) or {}).get("rendered", "") or ""
                    body_html = (item.get("content", {}) or {}).get("rendered", "") or ""

                    # Skip empty content
                    if not body_html.strip() and not title.strip():
                        continue

                    # Disambiguate filename with type prefix to avoid slug collisions
                    fname = f"{rest_base}-{slug}.txt"

                    # Save raw, pretty, and markdown versions
                    raw_path, pretty_path, markdown_path = save_triple_text_files(body_html, title, fname, site_out, url=item.get('link', ''))

                    index["items"].append({
                        "type": rest_base,
                        "id": item.get("id"),
                        "slug": slug,
                        "title": re.sub(r"\s+", " ", title).strip(),
                        "link": item.get("link"),
                        "raw_file": raw_path,
                        "pretty_file": pretty_path
                    })
            except HTTPError as e:
                if e.response.status_code in (401, 403):
                    if verbose:
                        print(f"   … skipped {rest_base} (HTTP {e.response.status_code}: access denied)")
                    else:
                        print(f"   … skipped {rest_base} (access denied)")
                    continue
                elif e.response.status_code in (400, 404):
                    if verbose:
                        print(f"   … skipped {rest_base} (HTTP {e.response.status_code}: {e.response.reason})")
                    else:
                        print(f"   … skipped {rest_base} (endpoint error)")
                    continue
                else:
                    # Re-raise other HTTP errors
                    raise
            except Exception as e:
                print(f"   … skipped {rest_base} (error: {e})")
                continue
            print(f"   … saved {count} item(s) from {rest_base}")

        # Download media originals
        if not skip_media:
            print("-- Fetching media …")
            media_endpoint = "/wp-json/wp/v2/media"
            mcount = 0
            seen_names = set()
            try:
                for media in paged(s, base, media_endpoint, sleep=sleep_time):
                    src = media.get("source_url")
                    if not src:
                        continue
                    # Prefer original filename; ensure uniqueness
                    name = os.path.basename(urlparse(src).path) or f"{media.get('id')}.bin"
                    if name in seen_names:
                        stem, ext = os.path.splitext(name)
                        name = f"{stem}-{media.get('id')}{ext}"
                    dest = images_dir / name
                    if not dest.exists():
                        try:
                            with s.get(src, stream=True, timeout=40) as r:
                                r.raise_for_status()
                                with open(dest, "wb") as f:
                                    for chunk in r.iter_content(1 << 15):
                                        if chunk:
                                            f.write(chunk)
                            mcount += 1
                        except Exception as e:
                            print(f"   !! Failed {src} :: {e}")
                    seen_names.add(name)
                    index["media"].append({
                        "id": media.get("id"),
                        "file": str(dest.as_posix()),
                        "source_url": src,
                        "post": media.get("post"),
                        "alt_text": media.get("alt_text", ""),
                        "title": (media.get("title", {}) or {}).get("rendered", ""),
                    })
            except HTTPError as e:
                if e.response.status_code in (401, 403):
                    if verbose:
                        print(f"   … skipped media (HTTP {e.response.status_code}: access denied)")
                    else:
                        print(f"   … skipped media (access denied)")
                elif e.response.status_code in (400, 404):
                    if verbose:
                        print(f"   … skipped media (HTTP {e.response.status_code}: {e.response.reason})")
                    else:
                        print(f"   … skipped media (endpoint error)")
                else:
                    print(f"   … media fetch failed: {e}")
            except Exception as e:
                print(f"   … skipped media (error: {e})")

            print(f"   … downloaded {mcount} media file(s)")

        # Write index
        (site_out / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
        print(f"==> Done. See: {site_out.resolve()}")
        print(f"    Raw text files: {site_out}/raw_pages/")
        print(f"    Pretty text files: {site_out}/pretty_pages/")
        print(f"    📝 Markdown files: {site_out}/markdown_pages/")
        print(f"    Media files: {site_out}/images/")

        return True, str(site_out.resolve()), "Content dumped successfully with dual output format"

    except Exception as e:
        return False, output_dir, f"Error during content dump: {e}"

def main():
    """CLI entry point that handles argument parsing and calls the core function."""
    ap = argparse.ArgumentParser(description="Dump WordPress text & media via REST API")
    ap.add_argument("base", help="Site base URL, e.g. https://example.com (no trailing slash required)")
    ap.add_argument("--out", default="wp_dump", help="Output directory (default: wp_dump)")
    ap.add_argument("--sleep", type=float, default=0.2, help="Delay between requests (seconds)")
    ap.add_argument("--all-types", action="store_true", help="Include public custom post types")
    ap.add_argument("--skip-media", action="store_true", help="Skip media download")
    ap.add_argument("--verbose", "-v", action="store_true", help="Show verbose output including skipped endpoints")
    ap.add_argument("--no-auth", action="store_true", help="Skip authentication prompt (for automated runs)")
    args = ap.parse_args()

    # Handle authentication for CLI
    use_auth = not args.no_auth
    username = None
    password = None

    # Call the core function
    success, output_dir, message = dump_wordpress_content(
        base_url=args.base,
        output_dir=args.out,
        sleep_time=args.sleep,
        all_types=args.all_types,
        skip_media=args.skip_media,
        verbose=args.verbose,
        interactive_auth=use_auth
    )

    if not success:
        print(f"[!] {message}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
