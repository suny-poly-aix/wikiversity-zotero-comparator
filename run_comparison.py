#!/usr/bin/env python3
"""
Enhanced Wikiversity-Zotero Citation Comparator with GitHub integration
"""

import os
import yaml
import json
import csv
from datetime import datetime
from citation_comparator import WikiversityZoteroComparator

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def save_markdown_report(results, filename='report.md'):
    """Save results as a markdown report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Wikiversity-Zotero Citation Comparison Report\n\n")
        f.write(f"**Generated on:** {timestamp}\n\n")
        
        summary = results['summary']
        f.write(f"## Summary\n\n")
        f.write(f"- **Total Wikiversity citations:** {summary['total_wikiversity_citations']}\n")
        f.write(f"- **Found in Zotero:** {summary['found_in_zotero']}\n")
        f.write(f"- **Missing from Zotero:** {summary['missing_from_zotero']}\n")
        f.write(f"- **Potential matches:** {summary['potential_matches']}\n\n")
        
        if results['missing_from_zotero']:
            f.write(f"## Citations Missing from Zotero\n\n")
            for i, citation in enumerate(results['missing_from_zotero'], 1):
                f.write(f"### {i}. {citation.get('title', 'No title')}\n\n")
                if citation.get('author'):
                    f.write(f"**Author:** {citation['author']}\n\n")
                if citation.get('url'):
                    f.write(f"**URL:** {citation['url']}\n\n")
                if citation.get('date'):
                    f.write(f"**Date:** {citation['date']}\n\n")
                if citation.get('source_url'):
                    f.write(f"**Source Page:** {citation['source_url']}\n\n")
                f.write(f"**Raw Citation:**\n```\n{citation['raw_text']}\n```\n\n")
                f.write("---\n\n")

def save_csv_report(results, filename='missing_citations.csv'):
    """Save missing citations as CSV"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['title', 'author', 'url', 'date', 'journal', 'source_url', 'raw_text']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for citation in results['missing_from_zotero']:
            # Clean the data for CSV
            row = {k: str(v) if v else '' for k, v in citation.items() if k in fieldnames}
            writer.writerow(row)

def main():
    """Main function"""
    # Load configuration
    config = load_config()
    
    # Get credentials from environment variables
    zotero_user_id = os.getenv('ZOTERO_USER_ID')
    zotero_api_key = os.getenv('ZOTERO_API_KEY')
    
    if not zotero_user_id or not zotero_api_key:
        print("❌ Error: Missing Zotero credentials")
        print("Please set ZOTERO_USER_ID and ZOTERO_API_KEY environment variables")
        return 1
    
    print("🚀 Starting Wikiversity-Zotero comparison...")
    
    # Initialize comparator
    comparator = WikiversityZoteroComparator(zotero_user_id, zotero_api_key)
    
    # Load Zotero library
    print("📚 Loading Zotero library...")
    comparator.load_zotero_library()
    
    # Extract Wikiversity citations
    print("🌐 Extracting Wikiversity citations...")
    wikiversity_urls = config.get('wikiversity_urls', [])
    if not wikiversity_urls:
        print("❌ Error: No Wikiversity URLs configured")
        return 1
    
    comparator.extract_wikiversity_citations(wikiversity_urls)
    
    # Compare citations
    print("🔍 Comparing citations...")
    threshold = config.get('similarity_threshold', 0.8)
    results = comparator.compare_citations(threshold)
    
    # Generate outputs
    output_formats = config.get('output_formats', ['json'])
    
    if 'json' in output_formats:
        print("💾 Saving JSON report...")
        with open('results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    if 'markdown' in output_formats:
        print("📝 Saving Markdown report...")
        save_markdown_report(results)
    
    if 'csv' in output_formats:
        print("📊 Saving CSV report...")
        save_csv_report(results)
    
    # Print summary
    summary = results['summary']
    print(f"\n✅ Comparison complete!")
    print(f"📊 Summary:")
    print(f"   • Total citations found: {summary['total_wikiversity_citations']}")
    print(f"   • Already in Zotero: {summary['found_in_zotero']}")
    print(f"   • Missing from Zotero: {summary['missing_from_zotero']}")
    print(f"   • Need manual review: {summary['potential_matches']}")
    
    # Set GitHub Actions output
    if os.getenv('GITHUB_ACTIONS'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"missing_count={summary['missing_from_zotero']}\n")
            f.write(f"total_count={summary['total_wikiversity_citations']}\n")
    
    return 0

if __name__ == "__main__":
    exit(main())
