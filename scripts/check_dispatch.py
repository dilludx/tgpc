#!/usr/bin/env python3
"""
Check TGPC dispatch list page for new files.
Compares with current dispatchlist.html and sends email if new files found.
"""

import os
import re
import json
import sys
import argparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
NOTIFICATION_EMAIL = "dinesh.io@outlook.com"
DISPATCH_SOURCE_URL = "https://www.pharmacycouncil.telangana.gov.in/site/dispatchListOfRegCert"
DISPATCHLIST_HTML_PATH = Path(__file__).parent.parent / "docs" / "dispatchlist.html"


def parse_date_from_filename(filename: str) -> str:
    """Extract date from various filename formats and return DL format."""
    filename_lower = filename.lower()

    patterns = [
        (r'(\d{2})\.(\d{2})\.(\d{4})', r'\1\2\3'),
        (r'(\d{2})-(\d{2})-(\d{4})', r'\1\2\3'),
        (r'(\d{2})-(\d{2})-(\d{2})', r'\1\2\3'),
        (r'(\d)\.(\d{2})\.(\d{4})', r'0\1\2\3'),
        (r'(\d)-(\d{2})-(\d{4})', r'0\1\2\3'),
        (r'(\d)\.(\d{2})\.(\d{2})', r'0\1\2\3'),
        (r'(\d)-(\d{2})-(\d{2})', r'0\1\2\3'),
    ]

    for pattern, replacement in patterns:
        match = re.search(pattern, filename)
        if match:
            parts = list(match.groups())
            if len(parts[2]) == 2:
                parts[2] = "20" + parts[2]
            result = parts[0] + parts[1] + parts[2]
            return result

    return None


def convert_to_dl_format(filename: str) -> str:
    """Convert 'Dispatch list 27-04-2026.pdf' → 'DL27042026.pdf'."""
    date_part = parse_date_from_filename(filename)
    if date_part:
        return f"DL{date_part}.pdf"
    return None


def extract_pdf_links_from_source(html_content: str) -> set:
    """Extract all PDF filenames from source page."""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()

    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().endswith('.pdf'):
            filename = href.split('/')[-1]
            dl_name = convert_to_dl_format(filename)
            if dl_name:
                links.add(dl_name)

    return links


def extract_existing_files_from_html(html_path: Path) -> set:
    """Extract existing filenames from dispatchlist.html."""
    if not html_path.exists():
        print(f"Warning: {html_path} not found. Returning empty set.")
        return set()

    content = html_path.read_text(encoding='utf-8')

    pattern = r"'(DL\d+\.pdf)'"
    matches = re.findall(pattern, content)
    return set(matches)


def scrape_source_page() -> set:
    """Fetch dispatch list page and extract PDF links."""
    print(f"Fetching: {DISPATCH_SOURCE_URL}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    response = requests.get(DISPATCH_SOURCE_URL, headers=headers, timeout=30)
    response.raise_for_status()

    return extract_pdf_links_from_source(response.text)


def send_email(new_files: list) -> bool:
    """Send notification email via Resend API."""
    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY not set")
        return False

    files_list = "\n".join([f"• {f}" for f in new_files])

    payload = {
        "from": "TGPC Dispatch <onboarding@resend.dev>",
        "to": [NOTIFICATION_EMAIL],
        "subject": "TGPC - Dispatch Lists",
        "html": f"""
        <h2>New dispatch files detected on TGPC</h2>
        <p>The following new dispatch files were found:</p>
        <ul>
            {''.join([f'<li>{f}</li>' for f in new_files])}
        </ul>
        <p>
            <a href="{DISPATCH_SOURCE_URL}">View source page</a>
        </p>
        """
    }

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=30
    )

    if response.status_code == 200:
        print(f"Email sent to {NOTIFICATION_EMAIL}")
        return True
    else:
        print(f"Failed to send email: {response.status_code} - {response.text}")
        return False


def get_date_from_dl_filename(filename: str) -> str:
    """Extract date from DL format like 'DL01012026.pdf' -> '2026-01-01'."""
    match = re.search(r'DL(\d{8})\.pdf', filename)
    if match:
        date_str = match.group(1)
        year = date_str[4:8]
        month = date_str[2:4]
        day = date_str[0:2]
        return f"{year}-{month}-{day}"
    return None


def get_latest_date_from_files(filenames: set) -> str:
    """Get the latest date from a set of DL format filenames."""
    dates = []
    for f in filenames:
        date = get_date_from_dl_filename(f)
        if date:
            dates.append(date)
    return max(dates) if dates else None


def check_for_new_files() -> list:
    """Main check function."""
    print("=" * 50)
    print("Checking TGPC dispatch list for new files...")
    print("=" * 50)

    try:
        source_files = scrape_source_page()
        print(f"Source files found: {len(source_files)}")
    except Exception as e:
        print(f"Error fetching source page: {e}")
        sys.exit(1)

    existing_files = extract_existing_files_from_html(DISPATCHLIST_HTML_PATH)
    print(f"Existing files in dispatchlist.html: {len(existing_files)}")

    # Get the latest date from existing files
    latest_existing_date = get_latest_date_from_files(existing_files)
    print(f"Latest date in dispatchlist.html: {latest_existing_date}")

    # Filter source files to only those with dates after the latest existing date
    new_files = []
    if latest_existing_date:
        for f in source_files:
            file_date = get_date_from_dl_filename(f)
            if file_date and file_date > latest_existing_date:
                new_files.append(f)
    else:
        # No existing files, all source files are new
        new_files = list(source_files)

    new_files = sorted(new_files)
    print(f"New files detected (after {latest_existing_date}): {len(new_files)}")

    if new_files:
        print("\nNew files:")
        for f in new_files:
            print(f"  • {f}")

        success = send_email(new_files)
        if success:
            print(f"\nEmail notification sent for {len(new_files)} new files")
            return new_files
        else:
            print("\nFailed to send email notification")
            return []
    else:
        print("\nNo new files detected. No email sent.")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check TGPC dispatch list for new files")
    parser.add_argument("--dry-run", action="store_true", help="Show new files without sending email")
    args = parser.parse_args()

    new_files = check_for_new_files()

    if args.dry_run:
        print("\n[DRY RUN] Would send email for:", new_files)

    sys.exit(0 if new_files or args.dry_run else 0)