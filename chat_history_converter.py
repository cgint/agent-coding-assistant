#!/usr/bin/env python3
"""
Self-contained chat history converter for UV Python.
- Converts all chat_history_ask-*.json in history_ask/ to markdown and HTML.
- Outputs to same directory as input files (history_ask/).
- Uses proper markdown library for HTML rendering.
"""
# /// script
# dependencies = [
#     "markdown>=3.4.0",
# ]
# requires-python = ">=3.11"
# ///
import json
from pathlib import Path
from datetime import datetime
from html import escape as html_escape
from typing import Any

# Import markdown library
import markdown

INPUT_DIR = Path('history_ask')
OUTPUT_DIR = INPUT_DIR  # Output to same directory as input
MD_OVERVIEW = OUTPUT_DIR / 'chat_history_overview.md'
HTML_OVERVIEW = OUTPUT_DIR / 'chat_history_overview.html'

# --- Utility functions ---
def discover_files():
    files = list(INPUT_DIR.glob('chat_history_ask-*.json'))
    return files

def parse_chat_history(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get('entries', [])
        return entries
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

def extract_timestamp_from_filename(filename: Path) -> datetime | None:
    # Format: chat_history_ask-YYYYMMDD_HHMMSS.json
    try:
        base = filename.name.replace('chat_history_ask-', '').replace('.json', '')
        dt = datetime.strptime(base, '%Y%m%d_%H%M%S')
        return dt
    except Exception:
        return None

def sort_files_chronologically(files: list[Path]) -> list[Path]:
    files_with_ts = [(f, extract_timestamp_from_filename(f)) for f in files]
    # Only keep files with valid timestamps
    files_with_ts = [x for x in files_with_ts if x[1] is not None]
    # Sort by datetime (guaranteed not None)
    files_with_ts.sort(key=lambda x: x[1] if x[1] is not None else datetime.min)
    return [x[0] for x in files_with_ts]

def format_timestamp(ts: str) -> str:
    try:
        return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
    except Exception:
        return ts

# --- Markdown Generation ---
def generate_markdown_session(entries: list[dict[str, Any]], session_name: str) -> str:
    md = [f'# Chat History - {session_name}\n']
    for entry in entries:
        if not entry.get('user_visible_entry', True):
            md.append('<details>')
            md.append(f'<summary>🔧 Tool Call - {format_timestamp(entry.get("timestamp_start", ""))} (Hidden)</summary>\n')
            md.append(f'**Query:** {entry.get("query", "")}')
            md.append(f'\n**Answer:** {entry.get("answer", "")}')
            md.append('</details>\n')
        else:
            md.append(f'**User Query:**\n> {entry.get("query", "")}\n')
            md.append(f'**Assistant Response:**\n{entry.get("answer", "")}\n')
    return '\n'.join(md)

# --- HTML Generation ---
def generate_html(all_entries: list[dict[str, Any]]) -> str:
    html = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
        '<title>Chat History - Complete Archive</title>',
        '<style>',
        'body { font-family: Arial, sans-serif; margin: 40px; }',
        '.entry { margin: 20px 0; border: 1px solid #ddd; }',
        '.entry-header { background: #f5f5f5; padding: 10px; cursor: pointer; }',
        '.entry-content { padding: 15px; display: none; }',
        '.user-visible { border-left: 4px solid #007bff; }',
        '.hidden-entry { border-left: 4px solid #6c757d; opacity: 0.8; }',
        '.timestamp { color: #666; font-size: 0.9em; }',
        '</style>',
        '<script>',
        'function toggleEntry(id) {',
        '  var content = document.getElementById(id);',
        '  content.style.display = content.style.display === "none" ? "block" : "none";',
        '}',
        '</script>',
        '</head>',
        '<body>',
        '<h1>Chat History - Complete Archive</h1>'
    ]
    # Table of Contents
    toc: dict[str, int] = {}
    for entry in all_entries:
        date = entry['timestamp_start'][:10]
        toc.setdefault(date, 0)
        toc[date] += 1
    html.append('<h2>Table of Contents</h2>')
    html.append('<ul>')
    for date, count in sorted(toc.items()):
        html.append(f'<li><a href="#{date}">{date}</a> ({count} entries)</li>')
    html.append('</ul>')
    # Entries by date
    last_date = None
    entry_id = 0
    for entry in all_entries:
        date = entry['timestamp_start'][:10]
        if date != last_date:
            html.append(f'<h2 id="{date}">{date}</h2>')
            last_date = date
        entry_id += 1
        eid = f'entry{entry_id}'
        if not entry.get('user_visible_entry', True):
            html.append('<div class="entry hidden-entry">')
            html.append(f'<div class="entry-header" onclick="toggleEntry(\'{eid}\')">🔧 Tool Call - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} (Click to expand)</div>')
            html.append(f'<div class="entry-content" id="{eid}" style="display:none;">')
            html.append(f'<strong>Query:</strong> {html_escape(entry.get("query", ""))}<br/>')
            html.append(f'<strong>Answer:</strong> {html_escape(entry.get("answer", ""))}')
            html.append('</div></div>')
        else:
            html.append('<div class="entry user-visible">')
            html.append(f'<div class="entry-header">User Query - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} </div>')
            html.append('<div class="entry-content" style="display:block;">')
            html.append(f'<strong>Query:</strong> {html_escape(entry.get("query", ""))}<br/>')
            html.append(f'<strong>Answer:</strong> {html_escape(entry.get("answer", ""))}')
            html.append('</div></div>')
    html.append('</body></html>')
    return '\n'.join(html)

def generate_html_session(entries: list[dict[str, Any]], session_name: str) -> str:
    md = markdown.Markdown(extensions=['codehilite', 'fenced_code', 'tables'])
    html = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
        f'<title>Chat History - {session_name}</title>',
        '<style>',
        'body { font-family: Arial, sans-serif; margin: 40px; }',
        '.entry { margin: 20px 0; border: 1px solid #ddd; }',
        '.entry-header { background: #f5f5f5; padding: 10px; cursor: pointer; }',
        '.entry-content { padding: 15px; display: none; }',
        '.user-visible { border-left: 4px solid #007bff; }',
        '.hidden-entry { border-left: 4px solid #6c757d; opacity: 0.8; }',
        '.timestamp { color: #666; font-size: 0.9em; }',
        'pre, code { background: #f8f8f8; border-radius: 3px; padding: 2px 4px; }',
        'pre { padding: 10px; overflow-x: auto; }',
        'table { border-collapse: collapse; width: 100%; }',
        'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
        'th { background-color: #f2f2f2; }',
        '</style>',
        '<script>',
        'function toggleEntry(id) {',
        '  var content = document.getElementById(id);',
        '  content.style.display = content.style.display === "none" ? "block" : "none";',
        '}',
        '</script>',
        '</head>',
        '<body>',
        f'<h1>Chat History - {session_name}</h1>'
    ]
    entry_id = 0
    for entry in entries:
        entry_id += 1
        eid = f'entry{entry_id}'
        query_html = md.convert(entry.get("query", ""))
        answer_html = md.convert(entry.get("answer", ""))
        md.reset()  # Reset for next conversion
        if not entry.get('user_visible_entry', True):
            html.append('<div class="entry hidden-entry">')
            html.append(f'<div class="entry-header" onclick="toggleEntry(\'{eid}\')">🔧 Tool Call - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} (Click to expand)</div>')
            html.append(f'<div class="entry-content" id="{eid}" style="display:none;">')
            html.append(f'<strong>Query:</strong> {query_html}<br/>')
            html.append(f'<strong>Answer:</strong> {answer_html}')
            html.append('</div></div>')
        else:
            html.append('<div class="entry user-visible">')
            html.append(f'<div class="entry-header">User Query - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} </div>')
            html.append('<div class="entry-content" style="display:block;">')
            html.append(f'<strong>Query:</strong> {query_html}<br/>')
            html.append(f'<strong>Answer:</strong> {answer_html}')
            html.append('</div></div>')
    html.append('</body></html>')
    return '\n'.join(html)

# --- Main Execution ---
def main() -> None:
    files = discover_files()
    files = sort_files_chronologically(files)
    session_md_files = []
    session_html_files = []
    for file in files:
        session_name = file.name.replace('.json', '')
        md_file = OUTPUT_DIR / f"{session_name}.md"
        html_file = OUTPUT_DIR / f"{session_name}.html"
        if md_file.exists() and html_file.exists():
            session_md_files.append(md_file)
            session_html_files.append(html_file)
            continue
        entries = parse_chat_history(file)
        md_content = generate_markdown_session(entries, session_name)
        html_content = generate_html_session(entries, session_name)
        with open(md_file, 'w', encoding='utf-8') as mdf:
            mdf.write(md_content)
        with open(html_file, 'w', encoding='utf-8') as htmlf:
            htmlf.write(html_content)
        session_md_files.append(md_file)
        session_html_files.append(html_file)
    # Generate overview files
    with open(MD_OVERVIEW, 'w', encoding='utf-8') as f:
        f.write('# Chat History Overview\n\n')
        for mdfile in session_md_files:
            f.write(f'- [{mdfile.name}]({mdfile.name})\n')
    with open(HTML_OVERVIEW, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Chat History Overview</title></head><body>\n')
        f.write('<h1>Chat History Overview</h1><ul>\n')
        for htmlfile in session_html_files:
            f.write(f'<li><a href="{htmlfile.name}">{htmlfile.name}</a></li>\n')
        f.write('</ul></body></html>\n')
    print(f"Conversion complete. Markdown overview: {MD_OVERVIEW}, HTML overview: {HTML_OVERVIEW}")

if __name__ == '__main__':
    main() 