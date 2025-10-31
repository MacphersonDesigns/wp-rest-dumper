#!/usr/bin/env python3
"""
WordPress SEO Analysis Tool
Analyzes scraped WordPress content for SEO opportunities and issues
"""

import json
import pathlib
import re
from collections import Counter, defaultdict
from datetime import datetime
import argparse
from urllib.parse import urljoin, urlparse
from html import unescape


def unescape_html(text):
    """Helper function to unescape HTML entities"""
    return unescape(text)


class SEOAnalyzer:
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }

    def analyze_content(self, html_content: str, url: str = "") -> dict:
        """Analyze HTML content for SEO factors"""
        analysis = {
            'url': url,
            'title': self.extract_title(html_content),
            'meta_description': self.extract_meta_description(html_content),
            'headings': self.extract_headings(html_content),
            'word_count': self.get_word_count(html_content),
            'keyword_density': self.analyze_keyword_density(html_content),
            'internal_links': self.extract_internal_links(html_content, url),
            'external_links': self.extract_external_links(html_content, url),
            'images': self.analyze_images(html_content),
            'readability': self.calculate_readability(html_content),
            'seo_score': 0,
            'issues': [],
            'recommendations': []
        }

        # Calculate SEO score and generate recommendations
        analysis = self.calculate_seo_score(analysis)
        return analysis

    def extract_title(self, html: str) -> dict:
        """Extract and analyze page title"""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = unescape_html(title_match.group(1).strip())
            return {
                'text': title,
                'length': len(title),
                'word_count': len(title.split()),
                'has_brand': any(brand in title.lower() for brand in ['jb lund', 'dock', 'lift']),
                'optimal_length': 30 <= len(title) <= 60
            }
        return {'text': '', 'length': 0, 'word_count': 0, 'has_brand': False, 'optimal_length': False}

    def extract_meta_description(self, html: str) -> dict:
        """Extract and analyze meta description"""
        desc_pattern = r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\'][^>]*>'
        desc_match = re.search(desc_pattern, html, re.IGNORECASE)
        if desc_match:
            desc = unescape(desc_match.group(1).strip())
            return {
                'text': desc,
                'length': len(desc),
                'word_count': len(desc.split()),
                'optimal_length': 120 <= len(desc) <= 160
            }
        return {'text': '', 'length': 0, 'word_count': 0, 'optimal_length': False}

    def extract_headings(self, html: str) -> dict:
        """Extract and analyze heading structure"""
        headings = {'h1': [], 'h2': [], 'h3': [], 'h4': [], 'h5': [], 'h6': []}

        for level in range(1, 7):
            pattern = rf'<h{level}[^>]*>(.*?)</h{level}>'
            matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                text = unescape(re.sub(r'<[^>]+>', '', match.group(1)).strip())
                headings[f'h{level}'].append({
                    'text': text,
                    'length': len(text),
                    'word_count': len(text.split())
                })

        return {
            'structure': headings,
            'h1_count': len(headings['h1']),
            'total_headings': sum(len(h) for h in headings.values()),
            'has_proper_hierarchy': self.check_heading_hierarchy(headings)
        }

    def check_heading_hierarchy(self, headings: dict) -> bool:
        """Check if headings follow proper hierarchy"""
        # Should have exactly one H1, then H2s, then H3s etc.
        h1_count = len(headings['h1'])
        if h1_count != 1:
            return False

        # Check that we don't skip levels (e.g., H1 -> H3 without H2)
        used_levels = [i for i in range(1, 7) if headings[f'h{i}']]
        if used_levels != list(range(min(used_levels), max(used_levels) + 1)):
            return False

        return True

    def get_word_count(self, html: str) -> int:
        """Get word count from text content"""
        text = re.sub(r'<[^>]+>', '', html)
        text = unescape(text)
        words = re.findall(r'\b\w+\b', text.lower())
        return len(words)

    def analyze_keyword_density(self, html: str) -> dict:
        """Analyze keyword density and key phrases"""
        text = re.sub(r'<[^>]+>', '', html)
        text = unescape(text).lower()
        words = re.findall(r'\b\w+\b', text)

        # Filter out stop words
        meaningful_words = [w for w in words if w not in self.stop_words and len(w) > 2]

        # Single word analysis
        word_freq = Counter(meaningful_words)
        total_words = len(meaningful_words)

        # Two-word phrases
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)
                  if words[i] not in self.stop_words and words[i+1] not in self.stop_words]
        bigram_freq = Counter(bigrams)

        # Three-word phrases
        trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)
                   if all(w not in self.stop_words for w in words[i:i+3])]
        trigram_freq = Counter(trigrams)

        return {
            'total_words': total_words,
            'top_keywords': [(word, count, round(count/total_words*100, 2))
                           for word, count in word_freq.most_common(20)],
            'top_bigrams': [(phrase, count) for phrase, count in bigram_freq.most_common(10)],
            'top_trigrams': [(phrase, count) for phrase, count in trigram_freq.most_common(5)]
        }

    def extract_internal_links(self, html: str, base_url: str) -> list:
        """Extract internal links"""
        if not base_url:
            return []

        domain = urlparse(base_url).netloc
        link_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>'
        links = []

        for match in re.finditer(link_pattern, html, re.IGNORECASE | re.DOTALL):
            href, anchor_text = match.groups()

            # Skip if it's an external link
            if href.startswith('http') and domain not in href:
                continue

            # Clean up anchor text
            anchor_clean = unescape(re.sub(r'<[^>]+>', '', anchor_text).strip())

            links.append({
                'url': href,
                'anchor_text': anchor_clean,
                'anchor_length': len(anchor_clean)
            })

        return links

    def extract_external_links(self, html: str, base_url: str) -> list:
        """Extract external links"""
        if not base_url:
            return []

        domain = urlparse(base_url).netloc
        link_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>'
        links = []

        for match in re.finditer(link_pattern, html, re.IGNORECASE | re.DOTALL):
            href, anchor_text = match.groups()

            # Only include external links
            if not href.startswith('http') or domain in href:
                continue

            anchor_clean = unescape(re.sub(r'<[^>]+>', '', anchor_text).strip())

            links.append({
                'url': href,
                'anchor_text': anchor_clean,
                'domain': urlparse(href).netloc
            })

        return links

    def analyze_images(self, html: str) -> dict:
        """Analyze image SEO"""
        img_pattern = r'<img[^>]*>'
        images = []

        for match in re.finditer(img_pattern, html, re.IGNORECASE):
            img_tag = match.group(0)

            # Extract attributes
            src = re.search(r'src=["\']([^"\']*)["\']', img_tag)
            alt = re.search(r'alt=["\']([^"\']*)["\']', img_tag)
            title = re.search(r'title=["\']([^"\']*)["\']', img_tag)

            images.append({
                'src': src.group(1) if src else '',
                'alt': alt.group(1) if alt else '',
                'title': title.group(1) if title else '',
                'has_alt': bool(alt),
                'alt_length': len(alt.group(1)) if alt else 0
            })

        return {
            'total_images': len(images),
            'images_with_alt': sum(1 for img in images if img['has_alt']),
            'images_without_alt': sum(1 for img in images if not img['has_alt']),
            'images': images[:10]  # Limit to first 10 for analysis
        }

    def calculate_readability(self, html: str) -> dict:
        """Calculate readability metrics"""
        text = re.sub(r'<[^>]+>', '', html)
        text = unescape(text)

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = re.findall(r'\b\w+\b', text)

        if not sentences or not words:
            return {'flesch_score': 0, 'grade_level': 'Unknown'}

        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = sum(self.count_syllables(word) for word in words) / len(words)

        # Flesch Reading Ease
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        flesch_score = max(0, min(100, flesch_score))

        # Grade level interpretation
        if flesch_score >= 90:
            grade_level = "5th grade"
        elif flesch_score >= 80:
            grade_level = "6th grade"
        elif flesch_score >= 70:
            grade_level = "7th grade"
        elif flesch_score >= 60:
            grade_level = "8th-9th grade"
        elif flesch_score >= 50:
            grade_level = "10th-12th grade"
        elif flesch_score >= 30:
            grade_level = "College level"
        else:
            grade_level = "Graduate level"

        return {
            'flesch_score': round(flesch_score, 1),
            'grade_level': grade_level,
            'avg_sentence_length': round(avg_sentence_length, 1),
            'avg_syllables_per_word': round(avg_syllables_per_word, 1)
        }

    def count_syllables(self, word: str) -> int:
        """Count syllables in a word"""
        word = word.lower()
        vowels = 'aeiouy'
        syllable_count = 0
        prev_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                syllable_count += 1
            prev_vowel = is_vowel

        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1

        return max(1, syllable_count)

    def calculate_seo_score(self, analysis: dict) -> dict:
        """Calculate overall SEO score and generate recommendations"""
        score = 0
        issues = []
        recommendations = []

        # Title analysis (20 points)
        title = analysis['title']
        if title['text']:
            if title['optimal_length']:
                score += 15
            else:
                issues.append(f"Title length is {title['length']} characters (optimal: 30-60)")
                recommendations.append("Optimize title length to 30-60 characters")

            if title['word_count'] >= 3:
                score += 5
            else:
                issues.append("Title is too short (less than 3 words)")
        else:
            issues.append("Missing page title")
            recommendations.append("Add a descriptive page title")

        # Meta description (15 points)
        meta = analysis['meta_description']
        if meta['text']:
            if meta['optimal_length']:
                score += 15
            else:
                issues.append(f"Meta description length is {meta['length']} characters (optimal: 120-160)")
                recommendations.append("Optimize meta description length to 120-160 characters")
        else:
            issues.append("Missing meta description")
            recommendations.append("Add a compelling meta description")

        # Headings (20 points)
        headings = analysis['headings']
        if headings['h1_count'] == 1:
            score += 10
        elif headings['h1_count'] == 0:
            issues.append("Missing H1 tag")
            recommendations.append("Add exactly one H1 tag per page")
        else:
            issues.append(f"Multiple H1 tags found ({headings['h1_count']})")
            recommendations.append("Use only one H1 tag per page")

        if headings['has_proper_hierarchy']:
            score += 10
        else:
            issues.append("Poor heading hierarchy")
            recommendations.append("Structure headings properly (H1 → H2 → H3, etc.)")

        # Content length (15 points)
        word_count = analysis['word_count']
        if word_count >= 300:
            score += 15
        elif word_count >= 150:
            score += 10
            recommendations.append("Consider adding more content (current: {word_count} words)")
        else:
            issues.append(f"Content too short ({word_count} words)")
            recommendations.append("Add more content (aim for 300+ words)")

        # Images (10 points)
        images = analysis['images']
        if images['total_images'] > 0:
            alt_ratio = images['images_with_alt'] / images['total_images']
            score += int(alt_ratio * 10)

            if images['images_without_alt'] > 0:
                issues.append(f"{images['images_without_alt']} images missing alt text")
                recommendations.append("Add descriptive alt text to all images")

        # Readability (10 points)
        readability = analysis['readability']
        if readability['flesch_score'] >= 60:
            score += 10
        elif readability['flesch_score'] >= 30:
            score += 5
            recommendations.append("Consider simplifying content for better readability")
        else:
            issues.append("Content is difficult to read")
            recommendations.append("Simplify sentences and use common words")

        # Links (10 points)
        internal_links = len(analysis['internal_links'])
        external_links = len(analysis['external_links'])

        if internal_links >= 3:
            score += 5
        else:
            recommendations.append("Add more internal links to improve site structure")

        if external_links > 0 and external_links <= 5:
            score += 5
        elif external_links > 5:
            recommendations.append("Consider reducing external links")

        analysis['seo_score'] = min(100, score)
        analysis['issues'] = issues
        analysis['recommendations'] = recommendations

        return analysis


def analyze_site_seo(site_dir: pathlib.Path) -> dict:
    """Analyze SEO for all pages in a site"""
    analyzer = SEOAnalyzer()

    site_analysis = {
        'site_info': {
            'name': site_dir.name,
            'analyzed_at': datetime.now().isoformat(),
            'total_pages': 0
        },
        'pages': [],
        'summary': {
            'avg_seo_score': 0,
            'common_issues': Counter(),
            'top_recommendations': Counter()
        }
    }

    # Look for content files referenced in index.json
    index_file = site_dir / 'index.json'
    if index_file.exists():
        try:
            index_data = json.loads(index_file.read_text(encoding='utf-8'))

            for item in index_data.get('items', []):
                if item.get('type') == 'pages':
                    # Read content from the raw file
                    raw_file_path = item.get('raw_file', '')
                    if raw_file_path:
                        # Convert relative path to absolute path within the site directory
                        # Remove the leading site directory part from the path
                        relative_path = raw_file_path.replace(f"wp_dump/{site_dir.name}/", "")
                        content_file = site_dir / relative_path

                        if content_file.exists():
                            try:
                                text_content = content_file.read_text(encoding='utf-8')
                                # For SEO analysis, we'll treat the text content as if it were HTML
                                # The analyzer will extract what it can from the plain text
                                page_analysis = analyzer.analyze_content(
                                    text_content,
                                    item.get('link', '')
                                )
                                page_analysis['title_from_wp'] = item.get('title', '')
                                site_analysis['pages'].append(page_analysis)
                                site_analysis['site_info']['total_pages'] += 1

                                # Collect common issues and recommendations
                                for issue in page_analysis['issues']:
                                    site_analysis['summary']['common_issues'][issue] += 1
                                for rec in page_analysis['recommendations']:
                                    site_analysis['summary']['top_recommendations'][rec] += 1
                            except Exception as e:
                                print(f"Error reading content file {content_file}: {e}")

        except Exception as e:
            print(f"Error reading index.json: {e}")

    # Calculate summary statistics
    if site_analysis['pages']:
        total_score = sum(page['seo_score'] for page in site_analysis['pages'])
        site_analysis['summary']['avg_seo_score'] = round(total_score / len(site_analysis['pages']), 1)

    return site_analysis


def create_seo_report_html(analysis: dict, output_path: pathlib.Path):
    """Create HTML SEO report"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SEO Analysis Report - {analysis['site_info']['name']}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f8fafc; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .score-circle {{ width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; color: white; margin: 20px auto; }}
            .score-excellent {{ background: #10b981; }}
            .score-good {{ background: #f59e0b; }}
            .score-poor {{ background: #ef4444; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .summary-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .page-analysis {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .issues {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 10px 0; }}
            .recommendations {{ background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 10px 0; }}
            .metric {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #e5e7eb; }}
            .metric:last-child {{ border-bottom: none; }}
            .good {{ color: #10b981; }}
            .warning {{ color: #f59e0b; }}
            .error {{ color: #ef4444; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 SEO Analysis Report</h1>
                <h2>{analysis['site_info']['name']}</h2>
                <p>Report generated: {analysis['site_info']['analyzed_at'][:19]}</p>

                <div class="score-circle {'score-excellent' if analysis['summary']['avg_seo_score'] >= 80 else 'score-good' if analysis['summary']['avg_seo_score'] >= 60 else 'score-poor'}">
                    {analysis['summary']['avg_seo_score']}/100
                </div>
                <p style="text-align: center; font-size: 18px;">Average SEO Score</p>
            </div>

            <div class="summary-grid">
                <div class="summary-card">
                    <h3>📊 Site Overview</h3>
                    <div class="metric">
                        <span>Total Pages Analyzed:</span>
                        <span>{analysis['site_info']['total_pages']}</span>
                    </div>
                    <div class="metric">
                        <span>Average SEO Score:</span>
                        <span class="{'good' if analysis['summary']['avg_seo_score'] >= 80 else 'warning' if analysis['summary']['avg_seo_score'] >= 60 else 'error'}">{analysis['summary']['avg_seo_score']}/100</span>
                    </div>
                </div>

                <div class="summary-card">
                    <h3>⚠️ Common Issues</h3>
                    {''.join(f'<div class="metric"><span>{issue}</span><span class="error">{count} pages</span></div>' for issue, count in analysis['summary']['common_issues'].most_common(5))}
                </div>
            </div>

            <div class="summary-card">
                <h3>💡 Top Recommendations</h3>
                {''.join(f'<div class="recommendations">{rec} (affects {count} pages)</div>' for rec, count in analysis['summary']['top_recommendations'].most_common(5))}
            </div>
    """

    # Add individual page analyses
    for i, page in enumerate(analysis['pages'][:10]):  # Limit to first 10 pages
        score_class = 'score-excellent' if page['seo_score'] >= 80 else 'score-good' if page['seo_score'] >= 60 else 'score-poor'

        html_content += f"""
        <div class="page-analysis">
            <h3>📄 {page.get('title_from_wp', 'Untitled Page')}
                <span style="float: right; color: {'#10b981' if page['seo_score'] >= 80 else '#f59e0b' if page['seo_score'] >= 60 else '#ef4444'};">{page['seo_score']}/100</span>
            </h3>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>📝 Content Metrics</h4>
                    <div class="metric">
                        <span>Title Length:</span>
                        <span class="{'good' if page['title']['optimal_length'] else 'warning'}">{page['title']['length']} chars</span>
                    </div>
                    <div class="metric">
                        <span>Meta Description:</span>
                        <span class="{'good' if page['meta_description']['optimal_length'] else 'warning'}">{page['meta_description']['length']} chars</span>
                    </div>
                    <div class="metric">
                        <span>Word Count:</span>
                        <span class="{'good' if page['word_count'] >= 300 else 'warning' if page['word_count'] >= 150 else 'error'}">{page['word_count']} words</span>
                    </div>
                    <div class="metric">
                        <span>Readability Score:</span>
                        <span class="{'good' if page['readability']['flesch_score'] >= 60 else 'warning'}">{page['readability']['flesch_score']}</span>
                    </div>
                </div>

                <div>
                    <h4>🔗 Links & Structure</h4>
                    <div class="metric">
                        <span>H1 Tags:</span>
                        <span class="{'good' if page['headings']['h1_count'] == 1 else 'error'}">{page['headings']['h1_count']}</span>
                    </div>
                    <div class="metric">
                        <span>Total Headings:</span>
                        <span>{page['headings']['total_headings']}</span>
                    </div>
                    <div class="metric">
                        <span>Internal Links:</span>
                        <span>{len(page['internal_links'])}</span>
                    </div>
                    <div class="metric">
                        <span>Images with Alt:</span>
                        <span class="{'good' if page['images']['images_without_alt'] == 0 else 'warning'}">{page['images']['images_with_alt']}/{page['images']['total_images']}</span>
                    </div>
                </div>
            </div>

            {f'<div class="issues"><h4>⚠️ Issues Found</h4>{"<br>".join(page["issues"])}</div>' if page['issues'] else ''}
            {f'<div class="recommendations"><h4>💡 Recommendations</h4>{"<br>".join(page["recommendations"])}</div>' if page['recommendations'] else ''}
        </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    output_path.write_text(html_content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Analyze WordPress site SEO')
    parser.add_argument('site_dir', help='Directory containing scraped site data')
    parser.add_argument('--format', choices=['json', 'html', 'both'], default='both',
                       help='Output format for SEO analysis')

    args = parser.parse_args()

    site_path = pathlib.Path(args.site_dir)
    if not site_path.exists():
        print(f"Error: Directory {site_path} does not exist")
        return

    print(f"🔍 Analyzing SEO for {site_path}...")
    analysis = analyze_site_seo(site_path)

    if args.format in ['json', 'both']:
        json_path = site_path / 'seo_analysis.json'
        json_path.write_text(json.dumps(analysis, indent=2, default=str), encoding='utf-8')
        print(f"📊 SEO analysis saved to: {json_path}")

    if args.format in ['html', 'both']:
        html_path = site_path / 'seo_report.html'
        create_seo_report_html(analysis, html_path)
        print(f"📈 SEO report saved to: {html_path}")

    # Print summary
    print(f"\n📈 SEO Summary for {analysis['site_info']['name']}:")
    print(f"   Average SEO Score: {analysis['summary']['avg_seo_score']}/100")
    print(f"   Pages Analyzed: {analysis['site_info']['total_pages']}")

    if analysis['summary']['common_issues']:
        print("\n⚠️  Top Issues:")
        for issue, count in list(analysis['summary']['common_issues'].most_common(3)):
            print(f"   • {issue} ({count} pages)")


if __name__ == '__main__':
    main()