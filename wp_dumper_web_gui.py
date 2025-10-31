#!/usr/bin/env python3
"""
WordPress REST Dumper Web GUI
A web-based interface for the WordPress REST API content dumper.
Uses Flask for a simple, cross-platform GUI that runs in your browser.
"""

try:
    from flask import Flask, render_template, request, jsonify, send_file
except ImportError:
    print("Flask is required for the web GUI. Install it with:")
    print("pip install flask")
    exit(1)

import threading
import sys
import pathlib
import io
import contextlib
import zipfile
import pathlib
import os
import tempfile
import shutil
from datetime import datetime
import json
import queue

# Import our core scraping functionality
from wp_rest_dump import dump_wordpress_content

app = Flask(__name__)

# Global state for the web app
app_state = {
    'scraping_active': False,
    'last_output_dir': None,
    'output_messages': queue.Queue(),
    'current_status': 'Ready',
    'zip_file_path': None
}

class OutputCapture:
    """Captures output for the web interface."""
    def __init__(self, message_queue):
        self.queue = message_queue
        self.original_stdout = sys.stdout

    def write(self, text):
        if text.strip():
            self.queue.put(text)
        self.original_stdout.write(text)

    def flush(self):
        self.original_stdout.flush()

# HTML template is now in templates/index.html

@app.route('/')
def index():
    """Serve the main web interface."""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<html><body><h1>Template Error</h1><p>{str(e)}</p></body></html>"

@app.route('/scrape', methods=['POST'])
def scrape():
    """Start the scraping process."""
    if app_state['scraping_active']:
        return jsonify({'error': 'Scraping already in progress'}), 400

    data = request.get_json()

    # Clear previous messages
    while not app_state['output_messages'].empty():
        app_state['output_messages'].get()

    # Prepare parameters
    kwargs = {
        'base_url': data.get('url'),
        'output_dir': data.get('outputDir', 'wp_dump'),
        'sleep_time': float(data.get('sleepTime', 0.2)),
        'all_types': data.get('allTypes', False),
        'skip_media': data.get('skipMedia', False),
        'verbose': data.get('verbose', False),
        'use_auth': data.get('useAuth', False),
        'username': data.get('username') if data.get('useAuth') else None,
        'password': data.get('password') if data.get('useAuth') else None,
        # Analytics options
        'run_analytics': data.get('runAnalytics', False),
        'run_seo_analysis': data.get('runSeoAnalysis', False),
        'create_master': data.get('createMaster', False)
    }

    # Start scraping in background thread
    app_state['scraping_active'] = True
    app_state['current_status'] = 'Scraping in progress...'

    thread = threading.Thread(target=scrape_worker, kwargs=kwargs)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})

def create_zip_file(output_dir):
    """Create a ZIP file from the scraped content and return the path."""
    if not output_dir or not os.path.exists(output_dir):
        raise Exception('No scraped content found')

    # Create ZIP file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    site_folder_name = os.path.basename(output_dir)
    zip_filename = f"{site_folder_name}_{timestamp}.zip"

    # Store ZIP in same parent directory as the scraped content
    parent_dir = os.path.dirname(output_dir)
    zip_path = os.path.join(parent_dir, zip_filename)

    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        output_path = pathlib.Path(output_dir)
        for file_path in output_path.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(output_path.parent)
                zipf.write(file_path, arcname)

    return zip_path

def scrape_worker(**kwargs):
    """Worker function that runs the scraping."""
    old_stdout = sys.stdout  # Save original stdout first
    try:
        # Capture output
        output_capture = OutputCapture(app_state['output_messages'])
        sys.stdout = output_capture

        # Extract analytics parameters before passing to dump function
        analytics_params = {
            'run_analytics': kwargs.pop('run_analytics', False),
            'run_seo_analysis': kwargs.pop('run_seo_analysis', False),
            'create_master': kwargs.pop('create_master', False)
        }

        # Run scraping (without analytics params)
        success, output_dir, message = dump_wordpress_content(**kwargs)

        # Update state
        app_state['scraping_active'] = False
        app_state['last_output_dir'] = output_dir if success else None
        app_state['success'] = success

        if success:
            # Add success message
            app_state['output_messages'].put(f"\n✅ {message}")
            app_state['output_messages'].put(f"\n📁 Raw text files saved to: {os.path.join(output_dir, 'raw_pages/')}")
            app_state['output_messages'].put(f"\n✨ Pretty text files saved to: {os.path.join(output_dir, 'pretty_pages/')}")
            app_state['output_messages'].put(f"\n🖼️ Media files saved to: {os.path.join(output_dir, 'images/')}")

            # Run analytics if requested
            site_path = pathlib.Path(output_dir)
            analytics_files = []

            if analytics_params.get('run_analytics', False):
                app_state['output_messages'].put(f"\n📊 Running content analytics...")
                try:
                    from content_analytics import analyze_site_content, generate_insights, create_dashboard_html
                    analytics = analyze_site_content(site_path)
                    insights = generate_insights(analytics)
                    analytics_file = site_path / 'content_analytics_dashboard.html'
                    create_dashboard_html(analytics, analytics_file)
                    analytics_files.append('content_analytics_dashboard.html')
                    app_state['output_messages'].put(f"\n✅ Content analytics dashboard generated!")
                except Exception as e:
                    app_state['output_messages'].put(f"\n❌ Analytics failed: {e}")

            if analytics_params.get('run_seo_analysis', False):
                app_state['output_messages'].put(f"\n🎯 Running SEO analysis...")
                try:
                    from seo_analyzer import analyze_site_seo, create_seo_report_html
                    seo_analysis = analyze_site_seo(site_path)
                    seo_file = site_path / 'seo_analysis_report.html'
                    create_seo_report_html(seo_analysis, seo_file)
                    analytics_files.append('seo_analysis_report.html')
                    app_state['output_messages'].put(f"\n✅ SEO analysis report generated!")
                except Exception as e:
                    app_state['output_messages'].put(f"\n❌ SEO analysis failed: {e}")

            if analytics_params.get('create_master', False):
                app_state['output_messages'].put(f"\n🌟 Creating master dashboard...")
                try:
                    from complete_analyzer import create_master_dashboard
                    analyses = {
                        'content_analytics': 'content_analytics_dashboard.html' in analytics_files,
                        'seo_analysis': 'seo_analysis_report.html' in analytics_files
                    }
                    create_master_dashboard(site_path, analyses)
                    app_state['output_messages'].put(f"\n✅ Master dashboard generated!")
                except Exception as e:
                    app_state['output_messages'].put(f"\n❌ Master dashboard failed: {e}")

            # Automatically create ZIP file
            app_state['output_messages'].put(f"\n📦 Creating ZIP file...")
            try:
                zip_path = create_zip_file(output_dir)
                app_state['zip_file_path'] = zip_path
                app_state['current_status'] = 'Complete analysis finished! ZIP file ready for download.'
                app_state['output_messages'].put(f"\n✅ ZIP file created successfully!")
                app_state['output_messages'].put(f"\n💾 Click 'Download ZIP' to save the file")
                if analytics_files:
                    app_state['output_messages'].put(f"\n📊 Analysis reports included in ZIP:")
                    for file in analytics_files:
                        app_state['output_messages'].put(f"\n   • {file}")
            except Exception as zip_error:
                app_state['current_status'] = 'Analysis completed, but ZIP creation failed'
                app_state['output_messages'].put(f"\n⚠️ ZIP creation failed: {zip_error}")
        else:
            app_state['current_status'] = 'Scraping failed'
            app_state['output_messages'].put(f"\n❌ {message}")

    except Exception as e:
        app_state['scraping_active'] = False
        app_state['current_status'] = 'Error occurred'
        app_state['success'] = False
        app_state['output_messages'].put(f"\n❌ Error: {e}")
    finally:
        # Always restore stdout
        sys.stdout = old_stdout

@app.route('/status')
def status():
    """Get current status and new messages."""
    messages = []
    while not app_state['output_messages'].empty():
        try:
            messages.append(app_state['output_messages'].get_nowait())
        except:
            break

    return jsonify({
        'scraping_active': app_state['scraping_active'],
        'status': app_state['current_status'],
        'messages': messages,
        'success': app_state.get('success', False),
        'output_dir': app_state.get('last_output_dir')
    })

@app.route('/browse')
def browse_directories():
    """Browse directories for output location selection."""
    path = request.args.get('path', '')

    # Map container paths to host paths for Docker, or use local paths
    if not path:
        # Check if we're running in Docker or locally
        import os
        if os.path.exists('/app/host_home'):
            # Docker environment
            return jsonify({
                'current_path': '',
                'directories': [
                    {'name': 'Home Directory', 'path': '/app/host_home', 'type': 'directory'},
                    {'name': 'External Drives', 'path': '/app/volumes', 'type': 'directory'},
                    {'name': 'Local Project', 'path': '/app/wp_dump', 'type': 'directory'}
                ],
                'can_select': False
            })
        else:
            # Local environment - use actual system paths
            home_dir = os.path.expanduser('~')
            current_dir = os.getcwd()
            return jsonify({
                'current_path': '',
                'directories': [
                    {'name': 'Home Directory', 'path': home_dir, 'type': 'directory'},
                    {'name': 'Desktop', 'path': os.path.join(home_dir, 'Desktop'), 'type': 'directory'},
                    {'name': 'Downloads', 'path': os.path.join(home_dir, 'Downloads'), 'type': 'directory'},
                    {'name': 'Documents', 'path': os.path.join(home_dir, 'Documents'), 'type': 'directory'},
                    {'name': 'Current Project', 'path': current_dir, 'type': 'directory'}
                ],
                'can_select': False
            })

    try:
        # Import os here since we need it in the function
        import os
        
        # Security check - adapt for local or Docker environment
        if os.path.exists('/app/host_home'):
            # Docker environment - only allow browsing mounted directories
            allowed_prefixes = ['/app/host_home', '/app/volumes', '/app/wp_dump', '/app']
            if not any(path.startswith(prefix) for prefix in allowed_prefixes):
                return jsonify({'error': 'Access denied'}), 403
        else:
            # Local environment - allow browsing user directories
            home_dir = os.path.expanduser('~')
            allowed_prefixes = [home_dir, '/tmp', os.getcwd()]
            # Allow browsing within reasonable system directories
            if path and not any(path.startswith(prefix) for prefix in allowed_prefixes):
                # Be more permissive for local development, but still secure
                if not (path.startswith('/Users/') or path.startswith('/home/') or 
                       path.startswith(os.getcwd()) or path.startswith(home_dir)):
                    return jsonify({'error': 'Access denied'}), 403

        if not os.path.exists(path):
            return jsonify({'error': 'Directory not found'}), 404

        items = []

        # Add parent directory link (except at root)
        is_docker = os.path.exists('/app/host_home')
        root_path = '/app' if is_docker else '/'
        
        if path != root_path and '/' in path.rstrip('/'):
            parent = os.path.dirname(path.rstrip('/'))
            # Don't allow going above allowed directories
            if is_docker:
                if parent.startswith(('/app/host_home', '/app/volumes', '/app/wp_dump', '/app')):
                    items.append({'name': '..', 'path': parent, 'type': 'parent'})
            else:
                # For local development, allow reasonable parent navigation
                home_dir = os.path.expanduser('~')
                if (parent.startswith(home_dir) or 
                    parent.startswith(os.getcwd()) or
                    parent.startswith('/Users/') or 
                    parent.startswith('/home/')):
                    items.append({'name': '..', 'path': parent, 'type': 'parent'})

        # List directories
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    items.append({
                        'name': item,
                        'path': item_path,
                        'type': 'directory'
                    })
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403

        return jsonify({
            'current_path': path,
            'directories': items,
            'can_select': True  # Allow selecting any browseable directory
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-zip', methods=['POST'])
def download_zip():
    """Download the pre-created ZIP file of the scraped content."""
    zip_path = app_state.get('zip_file_path')

    # If no pre-created ZIP, fall back to creating one
    if not zip_path or not os.path.exists(zip_path):
        output_dir = app_state.get('last_output_dir')
        if not output_dir or not os.path.exists(output_dir):
            return jsonify({'error': 'No scraped content found'}), 404

        try:
            zip_path = create_zip_file(output_dir)
            app_state['zip_file_path'] = zip_path
        except Exception as e:
            return jsonify({'error': f'Failed to create ZIP: {e}'}), 500

    try:
        zip_filename = os.path.basename(zip_path)
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    except Exception as e:
        return jsonify({'error': f'Failed to send ZIP: {e}'}), 500

@app.route('/analytics-only', methods=['POST'])
def run_analytics_only():
    """Run just the analytics report on existing data."""
    output_dir = app_state.get('last_output_dir')
    if not output_dir or not os.path.exists(output_dir):
        return jsonify({'error': 'No output directory available - run a scrape first'}), 400

    try:
        # Run content analytics using the existing functions
        import sys
        import pathlib
        sys.path.append('.')
        from content_analytics import analyze_site_content, generate_insights, create_dashboard_html

        site_path = pathlib.Path(output_dir)
        analytics = analyze_site_content(site_path)
        insights = generate_insights(analytics)

        # Generate HTML report
        analytics_file = site_path / 'content_analytics_dashboard.html'
        create_dashboard_html(analytics, analytics_file)

        return jsonify({'success': True, 'file': 'content_analytics_dashboard.html'})

    except Exception as e:
        return jsonify({'error': f'Analytics failed: {str(e)}'}), 500@app.route('/seo-only', methods=['POST'])
def run_seo_only():
    """Run just the SEO analysis on existing data."""
    output_dir = app_state.get('last_output_dir')
    if not output_dir or not os.path.exists(output_dir):
        return jsonify({'error': 'No output directory available - run a scrape first'}), 400

    try:
        # Run SEO analysis using existing functions
        import sys
        import pathlib
        sys.path.append('.')
        from seo_analyzer import analyze_site_seo, create_seo_report_html

        site_path = pathlib.Path(output_dir)
        seo_analysis = analyze_site_seo(site_path)

        # Generate HTML report
        seo_file = site_path / 'seo_analysis_report.html'
        create_seo_report_html(seo_analysis, seo_file)

        return jsonify({'success': True, 'file': 'seo_analysis_report.html'})

    except Exception as e:
        return jsonify({'error': f'SEO analysis failed: {str(e)}'}), 500

@app.route('/dashboard')
def view_dashboard():
    """Serve the master dashboard if it exists."""
    output_dir = app_state.get('last_output_dir')
    if not output_dir:
        return "No dashboard available - run a scrape first!", 404

    dashboard_file = os.path.join(output_dir, 'master_dashboard.html')

    if os.path.exists(dashboard_file):
        return send_file(dashboard_file)
    else:
        return "Dashboard not found - run a complete analysis first!", 404

@app.route('/extract-single-page', methods=['POST'])
def extract_single_page():
    """Extract data from a single WordPress page to CSV."""
    try:
        data = request.get_json()
        
        # Import our single page extractor
        from single_page_extractor import extract_single_page_data, export_detailed_to_csv, export_to_csv
        
        # Extract the page data
        page_url = data.get('singlePageUrl')
        username = data.get('singleUsername') if data.get('singleUseAuth') else None
        password = data.get('singlePassword') if data.get('singleUseAuth') else None
        verbose = data.get('singleVerbose', False)
        detailed = data.get('singleDetailed', True)
        output_dir = data.get('singleOutputDir', 'single_page_extracts')
        
        if verbose:
            print(f"🔍 Extracting data from: {page_url}")
        
        # Extract the data
        extracted_data = extract_single_page_data(
            page_url, 
            username=username, 
            password=password,
            verbose=verbose
        )
        
        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        page_slug = extracted_data['basic_info'].get('slug', 'page')
        output_folder = os.path.join(output_dir, f"{page_slug}_{timestamp}")
        
        # Export to CSV
        if detailed:
            files_created = export_detailed_to_csv(extracted_data, output_folder)
        else:
            output_file = os.path.join(output_folder, 'page_extract.csv')
            os.makedirs(output_folder, exist_ok=True)
            export_to_csv(extracted_data, output_file)
            files_created = [output_file]
        
        # Prepare summary data
        basic = extracted_data['basic_info']
        content = extracted_data['content_analysis']
        business_count = len(extracted_data.get('business_data', []))
        
        summary = {
            'title': basic.get('title', 'Untitled'),
            'type': basic.get('type', 'unknown'),
            'word_count': content.get('word_count', 0),
            'heading_count': content.get('heading_count', 0),
            'link_count': content.get('link_count', 0),
            'image_count': content.get('image_count', 0),
            'business_count': business_count
        }
        
        return jsonify({
            'success': True,
            'files': [os.path.basename(f) for f in files_created],
            'output_directory': output_folder,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def main():
    """Launch the web GUI."""
    print("\n🌐 WordPress REST Dumper - Web Interface")
    print("=" * 50)
    print("Starting web server...")
    print("\n📱 Open your browser and go to:")
    print("   http://localhost:5001")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)

    # Use 0.0.0.0 for Docker compatibility, 127.0.0.1 for local development
    import os
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    debug = os.getenv('FLASK_ENV') != 'production'

    try:
        app.run(host=host, port=5001, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    main()