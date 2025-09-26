# WordPress REST API Dumper

A Python tool for extracting content from WordPress sites via the REST API. Dumps pages, posts, custom post types, and media files to local storage with structured metadata.

## Features

- 🚀 **Fast Content Extraction**: Efficiently fetches all public content via REST API
- 📄 **Text Content**: Converts HTML to clean text for pages, posts, and custom post types
- 🖼️ **Media Downloads**: Downloads original images and files with metadata
- 🔐 **Authentication Support**: Interactive authentication for protected endpoints
- 📊 **Structured Output**: Generates JSON index with all metadata
- 🛡️ **Error Resilient**: Gracefully handles authentication errors and missing endpoints
- 🎯 **Smart Discovery**: Automatically discovers available content types
- 📝 **Verbose Logging**: Detailed output for debugging and monitoring

## Installation

```bash
# Clone or download the script
git clone <repository-url>
cd wp_dumpper

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install requests
```

## Quick Start

```bash
# Basic usage - pages and posts only
python wp_rest_dump.py https://example.com

# Include all content types
python wp_rest_dump.py https://example.com --all-types

# With authentication for protected content
python wp_rest_dump.py https://example.com --all-types --verbose
# Answer 'y' when prompted for authentication
```

## Command Line Options

### Required Arguments

| Argument | Description                                 |
| -------- | ------------------------------------------- |
| `base`   | Site base URL (e.g., `https://example.com`) |

### Optional Arguments

| Flag              | Description                                 | Default            |
| ----------------- | ------------------------------------------- | ------------------ |
| `--out OUT`       | Output directory                            | `wp_dump`          |
| `--sleep SLEEP`   | Delay between requests (seconds)            | `0.2`              |
| `--all-types`     | Include public custom post types            | Only pages/posts   |
| `--skip-media`    | Skip media file downloads                   | Downloads media    |
| `--verbose`, `-v` | Show detailed output and skipped endpoints  | Minimal output     |
| `--no-auth`       | Skip authentication prompt (for automation) | Interactive prompt |
| `--help`, `-h`    | Show help message and exit                  | -                  |

## Authentication

The script supports WordPress HTTP Basic Authentication to access protected endpoints.

### Interactive Authentication (Default)

```bash
python wp_rest_dump.py https://example.com --all-types
```

The script will prompt:

```
==> Do you want to authenticate? This will allow access to protected endpoints (y/N):
```

- **Press 'y'**: Enter WordPress username and password
- **Press 'n'** or **Enter**: Continue without authentication

### Automated Runs (No Prompts)

For scripts, cron jobs, or CI/CD pipelines:

```bash
python wp_rest_dump.py https://example.com --no-auth --all-types
```

### Authentication Requirements

- **WordPress Application Passwords** (WordPress 5.6+)
- **HTTP Basic Auth plugin** (for older WordPress versions)
- **HTTPS recommended** for secure credential transmission

## Output Structure

The script creates the following directory structure:

```
wp_dump/
├── index.json          # Complete metadata for all content
├── pages/              # Text content files
│   ├── pages-homepage.txt
│   ├── pages-about.txt
│   ├── posts-hello-world.txt
│   └── custom-type-item.txt
└── images/             # Downloaded media files
    ├── image1.jpg
    ├── document.pdf
    └── video.mp4
```

### index.json Structure

```json
{
	"site": "https://example.com",
	"generated_at": 1632150000,
	"items": [
		{
			"type": "pages",
			"id": 123,
			"slug": "about",
			"title": "About Us",
			"link": "https://example.com/about/",
			"file": "wp_dump/pages/pages-about.txt"
		}
	],
	"media": [
		{
			"id": 456,
			"file": "wp_dump/images/hero-image.jpg",
			"source_url": "https://example.com/wp-content/uploads/hero-image.jpg",
			"post": 123,
			"alt_text": "Hero image description",
			"title": "Hero Image"
		}
	]
}
```

## Usage Examples

### Basic Content Extraction

```bash
# Pages and posts only
python wp_rest_dump.py https://myblog.com

# All public content types
python wp_rest_dump.py https://myblog.com --all-types

# Custom output directory
python wp_rest_dump.py https://myblog.com --out my_backup
```

### Advanced Options

```bash
# Verbose output with slower requests
python wp_rest_dump.py https://myblog.com --all-types --verbose --sleep 1.0

# Skip media downloads (text only)
python wp_rest_dump.py https://myblog.com --all-types --skip-media

# Automated backup script
python wp_rest_dump.py https://myblog.com --all-types --no-auth --verbose
```

### With Authentication

```bash
# Interactive authentication
python wp_rest_dump.py https://private-site.com --all-types --verbose

# Example session:
# ==> Do you want to authenticate? (y/N): y
# Username: admin
# Password: [hidden]
# ✓ Authentication configured
```

## Content Types

### Default Types (Always Included)

- **pages**: WordPress pages
- **posts**: Blog posts

### Additional Types (with `--all-types`)

- **media**: Images, documents, videos
- **Custom Post Types**: Products, events, portfolios, etc.
- **menu-items**: Navigation menu items
- **And more**: Any publicly accessible custom content types

### Filtered Types

The script automatically filters out problematic endpoints:

**Without Authentication:**

- `blocks`, `templates`, `template-parts`
- `font-families`, `global-styles`
- `navigation`, `patterns`

**With Authentication:**

- Attempts all discovered endpoints
- Gracefully handles access denied errors

## Error Handling

The script is designed to be robust and handle various error conditions:

| Error Type               | Behavior                               |
| ------------------------ | -------------------------------------- |
| **401/403 Unauthorized** | Skip endpoint, continue with others    |
| **400 Bad Request**      | Skip endpoint (often pagination limit) |
| **404 Not Found**        | Skip endpoint                          |
| **Network Errors**       | Skip item, continue processing         |
| **Malformed Endpoints**  | Automatically filtered out             |

## Troubleshooting

### Common Issues

**"Could not reach REST API"**

- Check if the site URL is correct
- Verify the WordPress REST API is enabled
- Test manually: visit `https://yoursite.com/wp-json/`

**"Access denied" for many endpoints**

- Use authentication for protected content
- Check WordPress user permissions
- Verify application passwords are enabled

**"Malformed endpoint pattern"**

- This is normal - the script filters these automatically
- Use `--verbose` to see which endpoints are skipped

### Performance Tuning

```bash
# Faster requests (use carefully)
python wp_rest_dump.py https://example.com --sleep 0.1

# Slower requests (for rate-limited sites)
python wp_rest_dump.py https://example.com --sleep 1.0

# Skip media for faster text-only backup
python wp_rest_dump.py https://example.com --all-types --skip-media
```

## Security Notes

- **HTTPS Recommended**: Always use HTTPS sites for authentication
- **Application Passwords**: Preferred over regular passwords
- **Credentials**: Never store credentials in scripts
- **Rate Limiting**: Respect server resources with appropriate `--sleep` values

## Requirements

- **Python 3.7+**
- **requests library**: `pip install requests`
- **WordPress site**: With REST API enabled (default since WP 4.7)
- **Network access**: To the target WordPress site

## License

This tool is provided as-is for educational and backup purposes. Respect website terms of service and robots.txt when scraping content.
