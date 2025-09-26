# WordPress REST API Dumper

A powerful Python tool for extracting content from WordPress sites via the REST API. Features both command-line and web-based interfaces, with automatic site organization and ZIP packaging.

## Features

- 🚀 **Fast Content Extraction**: Efficiently fetches all public content via REST API
- 🌐 **Web GUI**: Modern browser-based interface for easy use
- 📁 **Site Organization**: Automatically creates separate folders for each website
- 📦 **Automatic ZIP Packaging**: Creates downloadable ZIP files on completion
- 📄 **Text Content**: Converts HTML to clean text for pages, posts, and custom post types
- 🖼️ **Media Downloads**: Downloads original images and files with metadata
- 🔐 **Authentication Support**: Interactive authentication for protected endpoints
- 📊 **Structured Output**: Generates JSON index with all metadata
- 🛡️ **Error Resilient**: Gracefully handles authentication errors and missing endpoints
- 🎯 **Smart Discovery**: Automatically discovers available content types
- 📝 **Verbose Logging**: Detailed output for debugging and monitoring
- ⚡ **Real-time Progress**: Live updates in both CLI and web interface

## Installation

### 🐳 Docker (Recommended - Zero Setup)

```bash
# Clone the repository
git clone https://github.com/MacphersonDesigns/wp-rest-dumper.git
cd wp-rest-dumper

# Start the service (builds and runs automatically)
docker-compose up -d

# Or use the interactive manager
./docker-manager.sh
```

**Access at: http://localhost:8080** - No terminal needed, runs as persistent service!

### 🐍 Manual Python Setup

```bash
# Clone the repository
git clone https://github.com/MacphersonDesigns/wp-rest-dumper.git
cd wp-rest-dumper

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage Modes

### 🌐 Web Interface (Recommended)

Launch the web-based GUI for an intuitive, point-and-click experience:

```bash
python wp_dumper_web_gui.py
```

Then open your browser to: **http://localhost:8080**

**Web Interface Features:**

- 📱 **User-friendly form**: Enter URL, configure options, set save location
- 📊 **Real-time progress**: Live updates and terminal-style output
- 📦 **Instant ZIP downloads**: Automatically created when scraping completes
- 🔐 **Authentication panel**: Toggle-able username/password fields
- ⚙️ **All CLI options**: Include all content types, skip media, verbose output
- 💾 **Custom save locations**: Choose where to save your scraped content

### 💻 Command Line Interface

For automation, scripting, or advanced users:

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

The tool creates site-specific directories to keep different websites organized:

```
wp_dump/
├── Site-Name-1/                    # Each site gets its own folder
│   ├── index.json                  # Complete metadata for this site
│   ├── pages/                      # Text content files
│   │   ├── pages-homepage.txt
│   │   ├── pages-about.txt
│   │   ├── posts-hello-world.txt
│   │   └── custom-type-item.txt
│   └── images/                     # Downloaded media files
│       ├── image1.jpg
│       ├── document.pdf
│       └── video.mp4
├── Site-Name-2/                    # Another site's content
│   ├── index.json
│   ├── pages/
│   └── images/
└── Site-Name-1_20250926_141105.zip # Automatic ZIP files
```

**Site Folder Names**: Generated from the WordPress site name, with special characters removed and spaces converted to hyphens (e.g., "My Blog!" becomes "My-Blog").

**ZIP Files**: Automatically created with timestamp for easy backup and sharing.

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
