"""
Dispatch PDF scraper for TGPC system.
Scrapes the dispatch list page and downloads PDF files.
"""

import re
import requests
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
from bs4 import BeautifulSoup

from tgpc.utils import setup_logging

logger = setup_logging("tgpc.dispatch")


class DispatchScraper:
    """Scraper for TGPC dispatch list PDFs."""

    DISPATCH_URL = "https://www.pharmacycouncil.telangana.gov.in/site/dispatchListOfRegCert"
    BASE_PDF_URL = "https://www.pharmacycouncil.telangana.gov.in/pdf/Dispatch%20list%20of%20Registration%20Certificates/"

    def __init__(self):
        self.session = requests.Session()

    def fetch_dispatch_page(self) -> str:
        """Fetch the dispatch list page HTML."""
        try:
            response = self.session.get(self.DISPATCH_URL, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch dispatch page: {e}")
            raise

    def parse_pdf_links(self, html: str) -> List[Tuple[str, str]]:
        """
        Parse PDF links from the dispatch page.
        
        Returns:
            List of tuples (filename, url)
        """
        soup = BeautifulSoup(html, 'html.parser')
        pdf_links = []
        
        # Find all <a> tags with "Click here" text
        for link in soup.find_all('a'):
            if 'Click here' in link.get_text():
                # Get the parent paragraph to extract the date
                parent = link.find_parent('p')
                if parent:
                    text = parent.get_text()
                    # Extract date from text like "Dispatch list of Registration Certificates on 01.02.2019"
                    date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
                    if date_match:
                        date_str = date_match.group(1)
                        href = link.get('href')
                        
                        # Convert relative URL to absolute
                        if href.startswith('/'):
                            url = f"https://www.pharmacycouncil.telangana.gov.in{href}"
                        else:
                            url = href
                        
                        # Convert date to local naming convention
                        try:
                            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                            year = date_obj.year
                            month = date_obj.strftime("%b").upper()
                            day = date_obj.strftime("%d")
                            
                            # Extract filename from URL to handle suffixes (_c, _d, etc.)
                            url_filename = url.split("/")[-1]
                            
                            # Handle different URL formats
                            # Old format: DD.MM.YYYY Dispatch List.pdf
                            # New format: Dispatch list DD-MM-YYYY.pdf
                            # Suffixes: _c.pdf, _d.pdf, etc.
                            
                            if "Dispatch List" in url_filename:
                                # Old format: 01.02.2019 Dispatch List.pdf
                                # Convert to DL2019FEB01.pdf
                                base_filename = f"DL{year}{month}{day}.pdf"
                            elif "Dispatch list" in url_filename:
                                # New format: Dispatch list 04-07-2023.pdf
                                # Extract date part and convert
                                date_match = re.search(r'(\d{2}-\d{2}-\d{4})', url_filename)
                                if date_match:
                                    date_part = date_match.group(1)
                                    date_obj_new = datetime.strptime(date_part, "%d-%m-%Y")
                                    year = date_obj_new.year
                                    month = date_obj_new.strftime("%b").upper()
                                    day = date_obj_new.strftime("%d")
                                    base_filename = f"DL{year}{month}{day}.pdf"
                                else:
                                    continue
                            else:
                                continue
                            
                            # Handle suffixes (_c, _d, etc.)
                            suffix_match = re.search(r'(_[a-z])\.pdf$', url_filename, re.IGNORECASE)
                            if suffix_match:
                                suffix = suffix_match.group(1).lower()
                                base_filename = base_filename.replace(".pdf", f"{suffix}.pdf")
                            
                            pdf_links.append((base_filename, url))
                            
                        except Exception as e:
                            logger.warning(f"Failed to parse date {date_str}: {e}")
                            continue
        
        logger.info(f"Found {len(pdf_links)} PDF links")
        return pdf_links

    def download_pdf(self, url: str, dest_path: Path) -> bool:
        """Download a PDF file to the destination path."""
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded: {dest_path.name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to download {dest_path.name}: {e}")
            return False

    def sync_pdfs(self, dest_dir: Path) -> Tuple[int, int]:
        """
        Sync PDFs from TGPC to local directory.
        
        Args:
            dest_dir: Destination directory for PDFs
            
        Returns:
            Tuple of (new_downloaded, total_local)
        """
        html = self.fetch_dispatch_page()
        pdf_links = self.parse_pdf_links(html)
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        existing_files = {f.name for f in dest_dir.glob("*.pdf")}
        
        new_downloaded = 0
        for filename, url in pdf_links:
            dest_path = dest_dir / filename
            if filename not in existing_files:
                if self.download_pdf(url, dest_path):
                    new_downloaded += 1
            else:
                logger.debug(f"Already exists: {filename}")
        
        # Count total local files
        total_local = len(list(dest_dir.glob("*.pdf")))
        
        logger.info(f"Sync complete: {new_downloaded} new, {total_local} total")
        return new_downloaded, total_local
