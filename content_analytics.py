#!/usr/bin/env python3
"""
WordPress Content Analytics Dashboard
Analyzes scraped content and provides insights, statistics, and visualizations
"""

import json
import pathlib
import re
from collections import Counter, defaultdict
from datetime import datetime
import argparse


def analyze_text_content(text: str) -> dict:
    """Analyze text content and extract statistics"""
    if not text:
        return {}

    # Basic stats
    word_count = len(text.split())
    char_count = len(text)
    line_count = len(text.splitlines())

    # Extract all words (for word frequency analysis)
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    word_freq = Counter(words)

    # Extract phone numbers
    phone_pattern = r'(\d{3}[-.]?\d{3}[-.]?\d{4})'
    phones = re.findall(phone_pattern, text)

    # Extract email addresses
    email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    emails = re.findall(email_pattern, text)

    # Extract URLs
    url_pattern = r'(https?://[^\s]+)'
    urls = re.findall(url_pattern, text)

    # Extract addresses (basic city, state zip pattern)
    address_pattern = r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)'
    addresses = re.findall(address_pattern, text)

    # Content analysis
    sentences = re.split(r'[.!?]+', text)
    avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(len(sentences), 1)

    return {
        'word_count': word_count,
        'character_count': char_count,
        'line_count': line_count,
        'sentence_count': len(sentences),
        'avg_sentence_length': round(avg_sentence_length, 2),
        'top_words': word_freq.most_common(20),
        'phone_numbers': list(set(phones)),
        'email_addresses': list(set(emails)),
        'urls': list(set(urls)),
        'addresses': addresses,
        'readability_score': calculate_readability_score(text)
    }


def calculate_readability_score(text: str) -> float:
    """Simple readability score based on word and sentence length"""
    if not text:
        return 0

    words = text.split()
    sentences = re.split(r'[.!?]+', text)

    if not words or not sentences:
        return 0

    avg_words_per_sentence = len(words) / len(sentences)
    avg_syllables_per_word = sum(count_syllables(word) for word in words) / len(words)

    # Simplified Flesch Reading Ease formula
    score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    return max(0, min(100, score))


def count_syllables(word: str) -> int:
    """Count syllables in a word (approximation)"""
    word = word.lower()
    vowels = 'aeiouy'
    syllable_count = 0
    prev_char_was_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_char_was_vowel:
            syllable_count += 1
        prev_char_was_vowel = is_vowel

    # Handle silent 'e'
    if word.endswith('e') and syllable_count > 1:
        syllable_count -= 1

    return max(1, syllable_count)


def analyze_site_content(site_dir: pathlib.Path) -> dict:
    """Analyze all content from a scraped WordPress site"""
    analytics = {
        'site_info': {
            'name': site_dir.name,
            'analyzed_at': datetime.now().isoformat(),
            'total_files': 0
        },
        'content_types': defaultdict(int),
        'combined_stats': {},
        'files': [],
        'insights': []
    }

    # Analyze content from the pretty_pages directory (to avoid triple-counting)
    # Pretty pages have the best content quality with shortcodes cleaned
    content_type = 'pretty_pages'
    content_dir = site_dir / content_type

    if content_dir.exists():
        for file_path in content_dir.glob('*.txt'):
            try:
                content = file_path.read_text(encoding='utf-8')
                file_stats = analyze_text_content(content)

                # Determine content category from filename
                category = file_path.stem.split('-')[0] if '-' in file_path.stem else 'unknown'
                analytics['content_types'][category] += 1
                analytics['site_info']['total_files'] += 1

                analytics['files'].append({
                    'filename': file_path.name,
                    'category': category,
                    'content_type': content_type,
                    'stats': file_stats
                })

            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")

    # If pretty_pages doesn't exist, fall back to raw_pages
    elif (site_dir / 'raw_pages').exists():
        content_dir = site_dir / 'raw_pages'
        content_type = 'raw_pages'

        for file_path in content_dir.glob('*.txt'):
            try:
                content = file_path.read_text(encoding='utf-8')
                file_stats = analyze_text_content(content)

                # Determine content category from filename
                category = file_path.stem.split('-')[0] if '-' in file_path.stem else 'unknown'
                analytics['content_types'][category] += 1
                analytics['site_info']['total_files'] += 1

                analytics['files'].append({
                    'filename': file_path.name,
                    'category': category,
                    'content_type': content_type,
                    'stats': file_stats
                })

            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")

    # Calculate combined statistics
    all_stats = [f['stats'] for f in analytics['files'] if f.get('stats')]

    if all_stats:
        analytics['combined_stats'] = {
            'total_words': sum(s.get('word_count', 0) for s in all_stats),
            'total_characters': sum(s.get('character_count', 0) for s in all_stats),
            'avg_readability': round(sum(s.get('readability_score', 0) for s in all_stats) / len(all_stats), 2),
            'all_phones': list(set(phone for s in all_stats for phone in s.get('phone_numbers', []))),
            'all_emails': list(set(email for s in all_stats for email in s.get('email_addresses', []))),
            'all_urls': list(set(url for s in all_stats for url in s.get('urls', [])))
        }

        # Generate insights
        analytics['insights'] = generate_insights(analytics)

    return analytics


def generate_insights(analytics: dict) -> list:
    """Generate interesting insights from the analytics data"""
    insights = []
    stats = analytics['combined_stats']

    # Content volume insights
    total_words = stats.get('total_words', 0)
    if total_words > 10000:
        insights.append(f"📚 Large content site with {total_words:,} total words")
    elif total_words > 5000:
        insights.append(f"📄 Medium-sized content site with {total_words:,} words")
    else:
        insights.append(f"📝 Compact site with {total_words:,} words")

    # Readability insights
    readability = stats.get('avg_readability', 0)
    if readability >= 80:
        insights.append(f"✅ Very readable content (score: {readability})")
    elif readability >= 60:
        insights.append(f"📖 Moderately readable content (score: {readability})")
    else:
        insights.append(f"🤔 Complex content that may need simplification (score: {readability})")

    # Contact information insights
    phones = len(stats.get('all_phones', []))
    emails = len(stats.get('all_emails', []))

    if phones > 5:
        insights.append(f"📞 Business-focused site with {phones} phone numbers")
    if emails > 3:
        insights.append(f"✉️ Multiple contact points with {emails} email addresses")

    # URL insights
    urls = len(stats.get('all_urls', []))
    if urls > 20:
        insights.append(f"🔗 Link-rich content with {urls} external URLs")

    # Content type insights
    content_types = analytics['content_types']
    if 'pages' in content_types and content_types['pages'] > 10:
        insights.append(f"🏢 Large website with {content_types['pages']} pages")

    return insights


def create_dashboard_html(analytics: dict, output_path: pathlib.Path):
    """Create an HTML dashboard for the analytics"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Content Analytics - {analytics['site_info']['name']}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .stat-number {{ font-size: 2em; font-weight: bold; color: #2563eb; }}
            .insights {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .insight {{ padding: 10px; margin: 5px 0; background: #f0f9ff; border-left: 4px solid #2563eb; }}
            .contact-info {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px; }}
            .contact-list {{ max-height: 200px; overflow-y: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Content Analytics Dashboard</h1>
                <h2>{analytics['site_info']['name']}</h2>
                <p>Analysis completed: {analytics['site_info']['analyzed_at'][:19]}</p>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{analytics['combined_stats'].get('total_words', 0):,}</div>
                    <div>Total Words</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{analytics['site_info']['total_files']}</div>
                    <div>Content Files</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{analytics['combined_stats'].get('avg_readability', 0)}</div>
                    <div>Readability Score</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(analytics['combined_stats'].get('all_phones', []))}</div>
                    <div>Phone Numbers</div>
                </div>
            </div>

            <div class="insights">
                <h3>🔍 Key Insights</h3>
                {''.join(f'<div class="insight">{insight}</div>' for insight in analytics['insights'])}
            </div>

            <div class="contact-info">
                <h3>📞 Contact Information Found</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4>Phone Numbers:</h4>
                        <div class="contact-list">
                            {'<br>'.join(analytics['combined_stats'].get('all_phones', ['None found']))}
                        </div>
                    </div>
                    <div>
                        <h4>Email Addresses:</h4>
                        <div class="contact-list">
                            {'<br>'.join(analytics['combined_stats'].get('all_emails', ['None found']))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    output_path.write_text(html_content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Analyze WordPress dump content')
    parser.add_argument('site_dir', help='Directory containing scraped site data')
    parser.add_argument('--format', choices=['json', 'html', 'both'], default='both',
                       help='Output format for analytics')

    args = parser.parse_args()

    site_path = pathlib.Path(args.site_dir)
    if not site_path.exists():
        print(f"Error: Directory {site_path} does not exist")
        return

    print(f"🔍 Analyzing content in {site_path}...")
    analytics = analyze_site_content(site_path)

    # Output results
    if args.format in ['json', 'both']:
        json_path = site_path / 'analytics.json'
        json_path.write_text(json.dumps(analytics, indent=2, default=str), encoding='utf-8')
        print(f"📊 Analytics saved to: {json_path}")

    if args.format in ['html', 'both']:
        html_path = site_path / 'analytics_dashboard.html'
        create_dashboard_html(analytics, html_path)
        print(f"🌐 Dashboard saved to: {html_path}")

    # Print summary
    stats = analytics['combined_stats']
    print(f"\n📈 Summary for {analytics['site_info']['name']}:")
    print(f"   Total files: {analytics['site_info']['total_files']}")
    print(f"   Total words: {stats.get('total_words', 0):,}")
    print(f"   Readability: {stats.get('avg_readability', 0)}/100")
    print(f"   Contact info: {len(stats.get('all_phones', []))} phones, {len(stats.get('all_emails', []))} emails")


if __name__ == '__main__':
    main()