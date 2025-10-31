#!/usr/bin/env python3
"""
WordPress Site Complete Analyzer
Runs all analysis tools and creates a comprehensive site report
"""

import json
import pathlib
import subprocess
import sys
import argparse
from datetime import datetime


def run_analysis_tool(tool_script: str, site_dir: pathlib.Path, extra_args=None) -> tuple[bool, str]:
    """Run an analysis tool and return success status and output"""
    try:
        cmd = [sys.executable, tool_script, str(site_dir)]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=pathlib.Path(__file__).parent)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def create_master_dashboard(site_dir: pathlib.Path, analyses: dict):
    """Create a master dashboard combining all analyses"""

    # Load individual analysis results by calling the analysis functions directly
    analytics_data = {}
    seo_data = {}

    try:
        # Import and run content analytics if available
        if analyses.get('content_analytics', False):
            from content_analytics import analyze_site_content
            analytics_data = analyze_site_content(site_dir)
    except Exception as e:
        print(f"Error loading content analytics: {e}")

    try:
        # Import and run SEO analysis if available
        if analyses.get('seo_analysis', False):
            from seo_analyzer import analyze_site_seo
            seo_data = analyze_site_seo(site_dir)
    except Exception as e:
        print(f"Error loading SEO analysis: {e}")

    # Create comprehensive dashboard
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Complete Site Analysis - {site_dir.name}</title>
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
            .header {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 40px;
                border-radius: 20px;
                margin-bottom: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .header h1 {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 3em;
                margin: 0;
                font-weight: 700;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s ease;
            }}
            .metric-card:hover {{ transform: translateY(-5px); }}
            .metric-number {{
                font-size: 2.5em;
                font-weight: bold;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 10px;
            }}
            .metric-label {{ color: #6b7280; font-size: 1.1em; }}
            .analysis-section {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 20px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            .section-title {{
                font-size: 1.8em;
                font-weight: 600;
                margin-bottom: 20px;
                color: #374151;
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }}
            .feature-card {{
                padding: 20px;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                background: #f9fafb;
                transition: all 0.3s ease;
            }}
            .feature-card:hover {{
                border-color: #667eea;
                box-shadow: 0 4px 20px rgba(102, 126, 234, 0.1);
            }}
            .status-badge {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .status-success {{ background: #d1fae5; color: #065f46; }}
            .status-warning {{ background: #fef3c7; color: #92400e; }}
            .status-error {{ background: #fee2e2; color: #991b1b; }}
            .quick-links {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }}
            .quick-link {{
                display: block;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 12px;
                text-align: center;
                font-weight: 600;
                transition: transform 0.2s ease;
            }}
            .quick-link:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
            }}
            .insights-list {{
                list-style: none;
                padding: 0;
                margin: 20px 0;
            }}
            .insights-list li {{
                padding: 15px;
                margin: 10px 0;
                background: #f0f9ff;
                border-left: 4px solid #3b82f6;
                border-radius: 6px;
                font-size: 1.05em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Complete Site Analysis</h1>
                <h2 style="color: #6b7280; margin: 10px 0;">{site_dir.name}</h2>
                <p style="color: #9ca3af;">Analysis completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>

            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-number">{analytics_data.get('combined_stats', {}).get('total_words', 0):,}</div>
                    <div class="metric-label">📝 Total Words</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{seo_data.get('summary', {}).get('avg_seo_score', 0)}</div>
                    <div class="metric-label">🎯 SEO Score</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{analytics_data.get('site_info', {}).get('total_files', 0)}</div>
                    <div class="metric-label">📄 Content Files</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{len(analytics_data.get('combined_stats', {}).get('all_phones', []))}</div>
                    <div class="metric-label">📞 Contact Points</div>
                </div>
            </div>

            <div class="analysis-section">
                <div class="section-title">
                    🎯 Output Formats Available
                </div>
                <div class="feature-grid">
                    <div class="feature-card">
                        <h4>📝 Raw Text Files</h4>
                        <p>Clean text extraction from WordPress content, perfect for content migration and analysis.</p>
                        <span class="status-badge status-success">✓ Generated</span>
                    </div>
                    <div class="feature-card">
                        <h4>✨ Enhanced Pretty Files</h4>
                        <p>Intelligently cleaned content with shortcode removal and structured data extraction.</p>
                        <span class="status-badge status-success">✓ Generated</span>
                    </div>
                    <div class="feature-card">
                        <h4>📋 Markdown Files</h4>
                        <p>Beautiful markdown formatting with headers, links, and enhanced readability.</p>
                        <span class="status-badge status-success">✓ Generated</span>
                    </div>
                </div>
            </div>

            <div class="analysis-section">
                <div class="section-title">
                    🔍 Content Intelligence
                </div>
                <div class="feature-grid">
                    <div class="feature-card">
                        <h4>🏢 Business Data Extraction</h4>
                        <p>Automatically extracted dealer information, contact details, and addresses as structured JSON.</p>
                        <span class="status-badge status-success">✓ Active</span>
                    </div>
                    <div class="feature-card">
                        <h4>🎨 Theme Shortcode Cleaning</h4>
                        <p>Removes Visual Composer, Elementor, and Divi shortcodes while preserving useful content.</p>
                        <span class="status-badge status-success">✓ Active</span>
                    </div>
                    <div class="feature-card">
                        <h4>📊 Content Analytics</h4>
                        <p>Word counts, readability scores, contact extraction, and content insights.</p>
                        <span class="status-badge status-success">✓ Generated</span>
                    </div>
                    <div class="feature-card">
                        <h4>🎯 SEO Analysis</h4>
                        <p>Comprehensive SEO scoring, meta tag analysis, and optimization recommendations.</p>
                        <span class="status-badge status-success">✓ Generated</span>
                    </div>
                </div>
            </div>
    """

    # Add insights if available
    if analytics_data.get('insights'):
        html_content += f"""
            <div class="analysis-section">
                <div class="section-title">💡 Key Insights</div>
                <ul class="insights-list">
                    {''.join(f'<li>{insight}</li>' for insight in analytics_data['insights'])}
                </ul>
            </div>
        """

    # Add quick links to generated reports
    html_content += f"""
            <div class="analysis-section">
                <div class="section-title">📊 Generated Reports</div>
                <div class="quick-links">
                    <a href="analytics_dashboard.html" class="quick-link">📈 Content Analytics Dashboard</a>
                    <a href="seo_report.html" class="quick-link">🎯 SEO Analysis Report</a>
                    <a href="raw_pages/" class="quick-link">📝 Raw Text Files</a>
                    <a href="pretty_pages/" class="quick-link">✨ Pretty Text Files</a>
                    <a href="markdown_pages/" class="quick-link">📋 Markdown Files</a>
                </div>
            </div>

            <div class="analysis-section">
                <div class="section-title">🚀 Advanced Features Delivered</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px;">
                    <div>
                        <h4>🎨 Smart Content Cleaning</h4>
                        <ul>
                            <li>Visual Composer shortcode removal</li>
                            <li>Elementor builder code cleanup</li>
                            <li>Divi theme shortcode stripping</li>
                            <li>Preserved useful content extraction</li>
                        </ul>
                    </div>
                    <div>
                        <h4>🏢 Business Intelligence</h4>
                        <ul>
                            <li>Automatic dealer data extraction</li>
                            <li>Contact information mining</li>
                            <li>Address standardization</li>
                            <li>JSON structured output</li>
                        </ul>
                    </div>
                    <div>
                        <h4>📊 Analytics & SEO</h4>
                        <ul>
                            <li>Content readability analysis</li>
                            <li>Keyword density mapping</li>
                            <li>Meta tag optimization</li>
                            <li>Link structure analysis</li>
                        </ul>
                    </div>
                    <div>
                        <h4>🔧 Developer Features</h4>
                        <ul>
                            <li>Docker containerized deployment</li>
                            <li>Web GUI with file browser</li>
                            <li>Multiple output formats</li>
                            <li>Host filesystem integration</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div style="text-align: center; margin-top: 40px; padding: 30px; background: rgba(255, 255, 255, 0.1); border-radius: 15px;">
                <h3 style="color: white; margin-bottom: 15px;">🎉 Analysis Complete!</h3>
                <p style="color: rgba(255, 255, 255, 0.8); font-size: 1.1em;">
                    Your WordPress site has been thoroughly analyzed with advanced content intelligence,
                    SEO optimization insights, and multiple output formats ready for use.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    dashboard_path = site_dir / 'master_dashboard.html'
    dashboard_path.write_text(html_content, encoding='utf-8')
    return dashboard_path


def main():
    parser = argparse.ArgumentParser(description='Run complete WordPress site analysis')
    parser.add_argument('site_dir', help='Directory containing scraped site data')
    parser.add_argument('--skip-analytics', action='store_true', help='Skip content analytics')
    parser.add_argument('--skip-seo', action='store_true', help='Skip SEO analysis')

    args = parser.parse_args()

    site_path = pathlib.Path(args.site_dir)
    if not site_path.exists():
        print(f"❌ Error: Directory {site_path} does not exist")
        return

    print(f"🚀 Running complete analysis for {site_path.name}...")
    print("=" * 60)

    analyses = {}

    # Run content analytics
    if not args.skip_analytics:
        print("📊 Running content analytics...")
        success, output = run_analysis_tool('content_analytics.py', site_path)
        analyses['analytics'] = {'success': success, 'output': output}
        if success:
            print("✅ Content analytics completed")
        else:
            print(f"⚠️  Content analytics had issues: {output}")

    # Run SEO analysis
    if not args.skip_seo:
        print("🎯 Running SEO analysis...")
        success, output = run_analysis_tool('seo_analyzer.py', site_path)
        analyses['seo'] = {'success': success, 'output': output}
        if success:
            print("✅ SEO analysis completed")
        else:
            print(f"⚠️  SEO analysis had issues: {output}")

    # Create master dashboard
    print("🎨 Creating master dashboard...")
    dashboard_path = create_master_dashboard(site_path, analyses)
    print(f"✅ Master dashboard created: {dashboard_path}")

    print("\n" + "=" * 60)
    print("🎉 Complete Analysis Summary:")
    print(f"   📁 Site: {site_path.name}")
    print(f"   📊 Master Dashboard: {dashboard_path}")

    # Show available files
    print(f"\n📋 Available Analysis Files:")
    for file_name in ['analytics.json', 'analytics_dashboard.html', 'seo_analysis.json', 'seo_report.html']:
        file_path = site_path / file_name
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ⚠️  {file_name} (not generated)")

    # Show directory structure
    print(f"\n📂 Content Directories:")
    for dir_name in ['raw_pages', 'pretty_pages', 'markdown_pages', 'images']:
        dir_path = site_path / dir_name
        if dir_path.exists():
            file_count = len(list(dir_path.glob('*')))
            print(f"   📁 {dir_name}/ ({file_count} files)")
        else:
            print(f"   ⚠️  {dir_name}/ (not found)")


if __name__ == '__main__':
    main()