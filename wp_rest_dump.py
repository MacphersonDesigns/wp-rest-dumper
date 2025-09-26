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
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", "", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6])>", "\n", html, flags=re.I)
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

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

def setup_authentication(session: requests.Session):
    """Prompt user for authentication credentials and set up session."""
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

def main():
    ap = argparse.ArgumentParser(description="Dump WordPress text & media via REST API")
    ap.add_argument("base", help="Site base URL, e.g. https://example.com (no trailing slash required)")
    ap.add_argument("--out", default="wp_dump", help="Output directory (default: wp_dump)")
    ap.add_argument("--sleep", type=float, default=0.2, help="Delay between requests (seconds)")
    ap.add_argument("--all-types", action="store_true", help="Include public custom post types")
    ap.add_argument("--skip-media", action="store_true", help="Skip media download")
    ap.add_argument("--verbose", "-v", action="store_true", help="Show verbose output including skipped endpoints")
    ap.add_argument("--no-auth", action="store_true", help="Skip authentication prompt (for automated runs)")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    out = pathlib.Path(args.out)
    pages_dir = out / "pages"
    images_dir = out / "images"
    ensure_dir(out); ensure_dir(pages_dir); ensure_dir(images_dir)

    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    # Sanity check: is REST enabled?
    try:
        root = get_json(s, urljoin(base, "/wp-json/")).json()
    except Exception as e:
        print(f"[!] Could not reach REST API at {base}/wp-json/  :: {e}", file=sys.stderr)
        sys.exit(1)

    site_name = (root.get("name") or urlparse(base).netloc)
    print(f"==> Connected to: {site_name}")

    # Optional authentication setup
    authenticated = False if args.no_auth else setup_authentication(s)

    # Discover types
    types = discover_types(s, base, include_all=args.all_types, verbose=args.verbose, authenticated=authenticated)
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
            for item in paged(s, base, endpoint, sleep=args.sleep):
                count += 1
                slug = item.get("slug") or str(item.get("id"))
                title = (item.get("title", {}) or {}).get("rendered", "") or ""
                body_html = (item.get("content", {}) or {}).get("rendered", "") or ""
                text = (title.strip() + "\n\n" + html_to_text(body_html)).strip()
                # Avoid empty files
                if not text.strip():
                    continue
                # Disambiguate filename with type prefix to avoid slug collisions
                fname = f"{rest_base}-{slug}.txt"
                (pages_dir / fname).write_text(text, encoding="utf-8")
                index["items"].append({
                    "type": rest_base,
                    "id": item.get("id"),
                    "slug": slug,
                    "title": re.sub(r"\s+", " ", title).strip(),
                    "link": item.get("link"),
                    "file": str((pages_dir / fname).as_posix())
                })
        except HTTPError as e:
            if e.response.status_code in (401, 403):
                if args.verbose:
                    print(f"   … skipped {rest_base} (HTTP {e.response.status_code}: access denied)")
                else:
                    print(f"   … skipped {rest_base} (access denied)")
                continue
            elif e.response.status_code in (400, 404):
                if args.verbose:
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
    if not args.skip_media:
        print("-- Fetching media …")
        media_endpoint = "/wp-json/wp/v2/media"
        mcount = 0
        seen_names = set()
        try:
            for media in paged(s, base, media_endpoint, sleep=args.sleep):
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
                if args.verbose:
                    print(f"   … skipped media (HTTP {e.response.status_code}: access denied)")
                else:
                    print(f"   … skipped media (access denied)")
            elif e.response.status_code in (400, 404):
                if args.verbose:
                    print(f"   … skipped media (HTTP {e.response.status_code}: {e.response.reason})")
                else:
                    print(f"   … skipped media (endpoint error)")
            else:
                print(f"   … media fetch failed: {e}")
        except Exception as e:
            print(f"   … skipped media (error: {e})")

        print(f"   … downloaded {mcount} media file(s)")

    # Write index
    (out / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"==> Done. See: {out.resolve()}")

if __name__ == "__main__":
    main()
