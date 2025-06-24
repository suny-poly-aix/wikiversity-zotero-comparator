#!/usr/bin/env python3
"""
Wikiversity-Zotero Citation Comparator

This script compares citations from Wikiversity pages with your Zotero library
and identifies which Wikiversity citations are missing from Zotero.

Requirements:
- pyzotero: pip install pyzotero
- requests: pip install requests
- beautifulsoup4: pip install beautifulsoup4
- python-dotenv: pip install python-dotenv (optional, for environment variables)

Setup:
1. Get your Zotero API key from https://www.zotero.org/settings/keys
2. Find your Zotero User ID from the same page
3. Set these as environment variables or modify the script directly
"""

import re
import requests
from bs4 import BeautifulSoup
from pyzotero import zotero
import json
from urllib.parse import urljoin, urlparse
from difflib import SequenceMatcher
import os
from typing import List, Dict, Set, Tuple

class WikiversityZoteroComparator:
    def __init__(self, zotero_user_id: str, zotero_api_key: str, library_type: str = 'user'):
        """
        Initialize the comparator with Zotero credentials.
        
        Args:
            zotero_user_id: Your Zotero user ID
            zotero_api_key: Your Zotero API key
            library_type: 'user' or 'group' (default: 'user')
        """
        self.zot = zotero.Zotero(zotero_user_id, library_type, zotero_api_key)
        self.zotero_items = []
        self.wikiversity_citations = []
        
    def load_zotero_library(self) -> List[Dict]:
        """Load all items from Zotero library."""
        print("Loading Zotero library...")
        try:
            # Get all items from library
            items = self.zot.everything(self.zot.items())
            self.zotero_items = items
            print(f"Loaded {len(items)} items from Zotero library")
            return items
        except Exception as e:
            print(f"Error loading Zotero library: {e}")
            return []
    
    def extract_wikiversity_citations(self, wikiversity_urls: List[str]) -> List[Dict]:
        """
        Extract citations from Wikiversity pages.
        
        Args:
            wikiversity_urls: List of Wikiversity page URLs to analyze
            
        Returns:
            List of citation dictionaries
        """
        all_citations = []
        
        for url in wikiversity_urls:
            print(f"Processing Wikiversity page: {url}")
            citations = self._parse_wikiversity_page(url)
            all_citations.extend(citations)
        
        self.wikiversity_citations = all_citations
        print(f"Found {len(all_citations)} citations across all Wikiversity pages")
        return all_citations
    
    def _parse_wikiversity_page(self, url: str) -> List[Dict]:
        """Parse a single Wikiversity page for citations."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            citations = []
            
            # Look for reference sections
            ref_sections = soup.find_all(['div', 'section'], class_=re.compile(r'references|bibliography'))
            
            # Also look for <references> tags and reference lists
            ref_tags = soup.find_all('references')
            ref_lists = soup.find_all('ol', class_='references')
            
            all_ref_elements = ref_sections + ref_tags + ref_lists
            
            for ref_element in all_ref_elements:
                # Extract citation text from various formats
                ref_items = ref_element.find_all(['li', 'cite', 'ref'])
                
                for item in ref_items:
                    citation_text = item.get_text(strip=True)
                    if citation_text and len(citation_text) > 20:  # Filter out very short entries
                        citation_info = self._parse_citation_text(citation_text, url)
                        if citation_info:
                            citations.append(citation_info)
            
            # Also look for inline citations in {{cite}} format
            cite_templates = self._extract_cite_templates(str(soup))
            citations.extend(cite_templates)
            
            return citations
            
        except Exception as e:
            print(f"Error parsing {url}: {e}")
            return []
    
    def _extract_cite_templates(self, page_content: str) -> List[Dict]:
        """Extract citations from MediaWiki cite templates."""
        citations = []
        
        # Pattern to match {{cite web}}, {{cite journal}}, etc.
        cite_pattern = r'\{\{cite[^}]+\}\}'
        matches = re.findall(cite_pattern, page_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            citation_info = self._parse_cite_template(match)
            if citation_info:
                citations.append(citation_info)
        
        return citations
    
    def _parse_cite_template(self, template: str) -> Dict:
        """Parse a MediaWiki cite template."""
        # Extract key-value pairs from the template
        template = template.strip('{}')
        parts = template.split('|')
        
        if not parts:
            return None
        
        cite_type = parts[0].strip().replace('cite ', '')
        citation = {
            'type': cite_type,
            'title': '',
            'author': '',
            'url': '',
            'date': '',
            'journal': '',
            'raw_text': template
        }
        
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key in ['title']:
                    citation['title'] = value
                elif key in ['author', 'last', 'first']:
                    if citation['author']:
                        citation['author'] += f" {value}"
                    else:
                        citation['author'] = value
                elif key in ['url']:
                    citation['url'] = value
                elif key in ['date', 'year']:
                    citation['date'] = value
                elif key in ['journal', 'website']:
                    citation['journal'] = value
        
        return citation if citation['title'] else None
    
    def _parse_citation_text(self, text: str, source_url: str) -> Dict:
        """Parse plain text citation into structured format."""
        # Basic citation parsing - this can be enhanced based on your needs
        citation = {
            'title': '',
            'author': '',
            'url': '',
            'date': '',
            'journal': '',
            'raw_text': text,
            'source_url': source_url
        }
        
        # Try to extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        if urls:
            citation['url'] = urls[0]
        
        # Try to extract years
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        if years:
            citation['date'] = years[0]
        
        # Use the first part as potential title (very basic)
        if '.' in text:
            potential_title = text.split('.')[0].strip()
            if len(potential_title) > 10:
                citation['title'] = potential_title
        
        return citation
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""
        # Remove punctuation, convert to lowercase, remove extra spaces
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, str1, str2).ratio()
    
    def find_matching_zotero_items(self, wikiversity_citation: Dict, threshold: float = 0.8) -> List[Dict]:
        """Find Zotero items that might match a Wikiversity citation."""
        matches = []
        wiki_title = self.normalize_title(wikiversity_citation.get('title', ''))
        
        if not wiki_title:
            return matches
        
        for item in self.zotero_items:
            item_data = item.get('data', {})
            zot_title = self.normalize_title(item_data.get('title', ''))
            
            if not zot_title:
                continue
            
            # Compare titles
            title_similarity = self.similarity_score(wiki_title, zot_title)
            
            # Also check URL if available
            url_match = False
            wiki_url = wikiversity_citation.get('url', '')
            zot_url = item_data.get('url', '')
            
            if wiki_url and zot_url:
                url_match = wiki_url == zot_url or self.similarity_score(wiki_url, zot_url) > 0.9
            
            # Consider it a match if title similarity is high or URLs match
            if title_similarity >= threshold or url_match:
                matches.append({
                    'zotero_item': item,
                    'title_similarity': title_similarity,
                    'url_match': url_match
                })
        
        return sorted(matches, key=lambda x: x['title_similarity'], reverse=True)
    
    def compare_citations(self, similarity_threshold: float = 0.8) -> Dict:
        """
        Compare Wikiversity citations with Zotero library.
        
        Returns:
            Dictionary with comparison results
        """
        if not self.zotero_items:
            print("No Zotero items loaded. Call load_zotero_library() first.")
            return {}
        
        if not self.wikiversity_citations:
            print("No Wikiversity citations loaded. Call extract_wikiversity_citations() first.")
            return {}
        
        results = {
            'missing_from_zotero': [],
            'found_in_zotero': [],
            'potential_matches': [],
            'summary': {}
        }
        
        print("Comparing citations...")
        
        for wiki_citation in self.wikiversity_citations:
            matches = self.find_matching_zotero_items(wiki_citation, similarity_threshold)
            
            if not matches:
                results['missing_from_zotero'].append(wiki_citation)
            elif matches[0]['title_similarity'] >= similarity_threshold or matches[0]['url_match']:
                results['found_in_zotero'].append({
                    'wikiversity_citation': wiki_citation,
                    'zotero_match': matches[0]
                })
            else:
                results['potential_matches'].append({
                    'wikiversity_citation': wiki_citation,
                    'possible_matches': matches[:3]  # Top 3 potential matches
                })
        
        # Generate summary
        results['summary'] = {
            'total_wikiversity_citations': len(self.wikiversity_citations),
            'found_in_zotero': len(results['found_in_zotero']),
            'missing_from_zotero': len(results['missing_from_zotero']),
            'potential_matches': len(results['potential_matches'])
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Print comparison results in a readable format."""
        print("\n" + "="*60)
        print("WIKIVERSITY-ZOTERO CITATION COMPARISON RESULTS")
        print("="*60)
        
        summary = results['summary']
        print(f"\nSUMMARY:")
        print(f"Total Wikiversity citations: {summary['total_wikiversity_citations']}")
        print(f"Found in Zotero: {summary['found_in_zotero']}")
        print(f"Missing from Zotero: {summary['missing_from_zotero']}")
        print(f"Potential matches: {summary['potential_matches']}")
        
        print(f"\n" + "-"*40)
        print("CITATIONS MISSING FROM ZOTERO:")
        print("-"*40)
        
        for i, citation in enumerate(results['missing_from_zotero'], 1):
            print(f"\n{i}. {citation.get('title', 'No title')}")
            if citation.get('author'):
                print(f"   Author: {citation['author']}")
            if citation.get('url'):
                print(f"   URL: {citation['url']}")
            if citation.get('date'):
                print(f"   Date: {citation['date']}")
            print(f"   Raw text: {citation['raw_text'][:100]}...")
        
        if results['potential_matches']:
            print(f"\n" + "-"*40)
            print("POTENTIAL MATCHES (Manual review needed):")
            print("-"*40)
            
            for i, match_info in enumerate(results['potential_matches'], 1):
                wiki_cit = match_info['wikiversity_citation']
                print(f"\n{i}. Wikiversity: {wiki_cit.get('title', 'No title')}")
                print("   Potential Zotero matches:")
                
                for j, match in enumerate(match_info['possible_matches'], 1):
                    zot_item = match['zotero_item']['data']
                    similarity = match['title_similarity']
                    print(f"     {j}. {zot_item.get('title', 'No title')} (similarity: {similarity:.2f})")
    
    def export_missing_citations(self, results: Dict, filename: str = 'missing_citations.json'):
        """Export missing citations to a JSON file."""
        missing_citations = results['missing_from_zotero']
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(missing_citations, f, indent=2, ensure_ascii=False)
        
        print(f"\nMissing citations exported to {filename}")


def main():
    """Main function to run the comparison."""
    
    # Configuration - Replace with your actual credentials
    ZOTERO_USER_ID = os.getenv('ZOTERO_USER_ID', 'YOUR_USER_ID_HERE')
    ZOTERO_API_KEY = os.getenv('ZOTERO_API_KEY', 'YOUR_API_KEY_HERE')
    
    # Wikiversity URLs to analyze - Replace with your actual URLs
    WIKIVERSITY_URLS = [
        'https://en.wikiversity.org/wiki/YOUR_PAGE_HERE',
        # Add more URLs as needed
    ]
    
    if ZOTERO_USER_ID == 'YOUR_USER_ID_HERE' or ZOTERO_API_KEY == 'YOUR_API_KEY_HERE':
        print("Please set your Zotero credentials in the script or as environment variables:")
        print("ZOTERO_USER_ID and ZOTERO_API_KEY")
        return
    
    if not WIKIVERSITY_URLS or WIKIVERSITY_URLS[0] == 'https://en.wikiversity.org/wiki/YOUR_PAGE_HERE':
        print("Please add your Wikiversity URLs to the WIKIVERSITY_URLS list")
        return
    
    # Initialize comparator
    comparator = WikiversityZoteroComparator(ZOTERO_USER_ID, ZOTERO_API_KEY)
    
    # Load Zotero library
    comparator.load_zotero_library()
    
    # Extract Wikiversity citations
    comparator.extract_wikiversity_citations(WIKIVERSITY_URLS)
    
    # Compare citations
    results = comparator.compare_citations()
    
    # Print results
    comparator.print_results(results)
    
    # Export missing citations
    comparator.export_missing_citations(results)


if __name__ == "__main__":
    main()
