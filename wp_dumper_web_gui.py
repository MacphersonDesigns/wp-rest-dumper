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
        'password': data.get('password') if data.get('useAuth') else None
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

        # Run scraping
        success, output_dir, message = dump_wordpress_content(**kwargs)

        # Update state
        app_state['scraping_active'] = False
        app_state['last_output_dir'] = output_dir if success else None
        app_state['success'] = success

        if success:
            # Add success message
            app_state['output_messages'].put(f"\n✅ {message}")

            # Automatically create ZIP file
            app_state['output_messages'].put(f"\n📦 Creating ZIP file...")
            try:
                zip_path = create_zip_file(output_dir)
                app_state['zip_file_path'] = zip_path
                app_state['current_status'] = 'Scraping completed! ZIP file ready for download.'
                app_state['output_messages'].put(f"\n✅ ZIP file created successfully!")
                app_state['output_messages'].put(f"\n💾 Click 'Download ZIP' to save the file")
            except Exception as zip_error:
                app_state['current_status'] = 'Scraping completed, but ZIP creation failed'
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

def main():
    """Launch the web GUI."""
    print("\n🌐 WordPress REST Dumper - Web Interface")
    print("=" * 50)
    print("Starting web server...")
    print("\n📱 Open your browser and go to:")
    print("   http://localhost:8080")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)

    # Use 0.0.0.0 for Docker compatibility, 127.0.0.1 for local development
    import os
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    debug = os.getenv('FLASK_ENV') != 'production'
    
    try:
        app.run(host=host, port=8080, debug=debug, threaded=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")

if __name__ == "__main__":
    main()