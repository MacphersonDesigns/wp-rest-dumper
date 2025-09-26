# Changelog

All notable changes to the WordPress REST Dumper project are documented in this file.

## [2.0.0] - 2025-09-26

### 🎉 Major Features Added

#### Web-Based GUI Interface

- **New**: Complete web-based interface at `wp_dumper_web_gui.py`
- **Browser Access**: Modern GUI accessible at `http://localhost:8080`
- **Real-time Progress**: Live terminal-style output with status updates
- **Form-based Configuration**: User-friendly inputs for all options
- **Authentication Panel**: Toggle-able username/password fields

#### Site-Specific Organization

- **Automatic Folder Creation**: Each website gets its own subdirectory
- **Smart Naming**: Site names cleaned and formatted (e.g., "My Blog!" → "My-Blog")
- **Organized Structure**: `wp_dump/Site-Name/pages/` and `wp_dump/Site-Name/images/`
- **No More Mixing**: Different websites no longer overwrite each other's content

#### Automatic ZIP Packaging

- **Auto-Generation**: ZIP files created automatically when scraping completes
- **Timestamped Names**: Format: `Site-Name_YYYYMMDD_HHMMSS.zip`
- **Instant Downloads**: "Download ZIP" button appears immediately when ready
- **Complete Archives**: Includes all pages, images, and metadata

#### Enhanced User Experience

- **Save Location Chooser**: Users can specify custom output directories
- **Progress Indicators**: Visual progress bars and status messages
- **Error Recovery**: Graceful handling of port conflicts and permission issues
- **Cross-platform**: Web interface works on all operating systems

### 🔧 Technical Improvements

#### Core Functionality

- **Refactored Architecture**: Separated CLI and core logic for reusability
- **Import Support**: `dump_wordpress_content()` function can be imported by other tools
- **Better Error Handling**: Improved authentication and endpoint error recovery
- **Output Capture**: Redirect stdout for GUI integration

#### Code Organization

- **Template System**: HTML moved to separate `templates/index.html` file
- **Modular Design**: Clean separation between web interface and scraping logic
- **Type Safety**: Better parameter validation and error messaging

### 🛠️ Bug Fixes

- **Port Conflicts**: Automatic fallback from port 5000 to 8080 for macOS compatibility
- **Template Rendering**: Fixed large HTML template loading issues
- **Authentication Flow**: Improved credential handling in web interface
- **File Path Resolution**: Better handling of output directory creation

### 📚 Documentation Updates

- **Comprehensive README**: Updated with web GUI instructions and new features
- **Usage Examples**: Added web interface and site organization examples
- **Installation Guide**: Updated dependencies to include Flask
- **Feature Documentation**: Detailed explanations of new capabilities

### 🧹 Cleanup

- **Removed Test Files**: Cleaned up development artifacts
  - Removed: `simple_gui_test.py`, `test_flask.py`, `wp_dumper_gui.py`
  - Removed: `test_output/` and mixed content directories
- **Organized Structure**: Clean project layout with only production files

## [1.0.0] - 2025-09-25

### Initial Release

#### Core Features

- **WordPress REST API Integration**: Extract content via standard WP REST API
- **Content Types**: Support for pages, posts, and custom post types
- **Media Downloads**: Download images, documents, and other media files
- **Authentication**: Interactive authentication for protected content
- **Text Extraction**: Convert HTML content to clean text format
- **Metadata Export**: JSON index with complete site structure
- **Error Resilience**: Graceful handling of missing endpoints and auth errors

#### CLI Interface

- **Command Line Tool**: Full-featured CLI with comprehensive options
- **Flexible Configuration**: Customizable output directories, request delays
- **Verbose Logging**: Detailed output for debugging and monitoring
- **Content Filtering**: Options to include/exclude media and custom post types
- **Automated Support**: No-auth flag for scripting and automation

#### Technical Foundation

- **Python 3.7+ Support**: Modern Python with requests library
- **Rate Limiting**: Configurable delays between requests
- **Content Discovery**: Automatic detection of available content types
- **Security**: HTTPS support and secure credential handling

---

## Version History

- **v2.0.0**: Major update with web GUI, site organization, and ZIP packaging
- **v1.0.0**: Initial CLI-only release with core scraping functionality

## Migration Guide

### From v1.0.0 to v2.0.0

#### New Output Structure

- **Before**: All content in `wp_dump/pages/` and `wp_dump/images/`
- **After**: Site-specific folders like `wp_dump/Site-Name/pages/` and `wp_dump/Site-Name/images/`

#### Dependencies

```bash
# Old installation
pip install requests

# New installation
pip install requests flask
```

#### Usage

```bash
# CLI usage unchanged
python wp_rest_dump.py https://example.com --all-types

# NEW: Web interface
python wp_dumper_web_gui.py
# Then visit: http://localhost:8080
```

#### Benefits

- ✅ **Backward Compatible**: All CLI functionality preserved
- ✅ **Organized Output**: No more mixed content between sites
- ✅ **User Friendly**: Web interface for non-technical users
- ✅ **Automatic Packaging**: ZIP files created automatically
