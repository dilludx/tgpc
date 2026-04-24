"""
Core scraping logic for TGPC system.
Simple, clean scraper for local use only.
"""

import time
import random
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from tgpc.utils import Config, TGPCError, setup_logging

logger = setup_logging("tgpc.scraper")

# --- Models ---

@dataclass
class PharmacistRecord:
    registration_number: str
    name: str
    father_name: str
    category: str
    serial_number: Optional[int] = None

    gender: Optional[str] = None
    validity_date: Optional[str] = None
    status: Optional[str] = None

    education: Optional[List[Dict[str, str]]] = None
    work_experience: Optional[Dict[str, str]] = None

    def to_dict(self):
        """Convert to dictionary, strictly maintaining the 5-field schema for rx.json."""
        return {
            "registration_number": self.registration_number,
            "name": self.name,
            "father_name": self.father_name,
            "category": self.category,
            "serial_number": self.serial_number
        }
    
    def to_detailed_dict(self):
        """Convert to detailed dictionary for individual enrichment JSON files."""
        return {
            "serial_number": self.serial_number,
            "registration_number": self.registration_number,
            "name": self.name,
            "father_name": self.father_name,
            "gender": self.gender or "",
            "validity_date": self.validity_date or "",
            "category": self.category,
            "status": self.status or "",
            "education": self.education or [],
            "work_experience": self.work_experience or {
                "Address": "",
                "State": "",
                "District": "",
                "Pin code": ""
            }
        }

# --- Rate Limiter ---

class RateLimiter:
    def __init__(self, config: Config):
        self.min_delay = config.min_delay
        self.max_delay = config.max_delay
        self.current_delay = config.min_delay
        self.consecutive_failures = 0

    def wait(self):
        delay = self.current_delay * random.uniform(0.8, 1.2)
        time.sleep(delay)

    def record_result(self, success: bool):
        if success:
            self.consecutive_failures = 0
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
        else:
            self.consecutive_failures += 1
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)

# --- Scraper ---

class Scraper:

    def __init__(self):
        self.config = Config.load()
        self.rate_limiter = RateLimiter(self.config)

        # Simple browser session with connection pooling
        self.session = requests.Session()
        
        # Configure adapter with connection pooling and faster DNS via Cloudflare
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,  # Number of connection pools to cache
            pool_maxsize=10,      # Maximum number of connections in pool
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": self.config.base_url,
        })
        
        self.urls = {
            'total': f"{self.config.base_url}/pharmacy/srchpharmacisttotal",
            'search': f"{self.config.base_url}/pharmacy/getsearchpharmacist"
        }
        
        logger.info("Simple scraper initialized - direct connection only")

    def health_check(self, timeout: int = 10) -> bool:
        """Quick health check to detect if connection is blocked."""
        try:
            response = self.session.get(
                self.urls['total'],
                timeout=timeout
            )
            
            if response.status_code != 200:
                logger.warning(f"Health check failed: status {response.status_code}")
                return False
            
            content = response.text.lower()
            blocked_indicators = [
                "access denied",
                "forbidden",
                "captcha",
                "blocked",
                "suspicious",
                "security check",
                "unusual traffic"
            ]
            
            for indicator in blocked_indicators:
                if indicator in content:
                    logger.warning(f"Health check failed: blocked indicator '{indicator}'")
                    return False
            
            if len(response.text) < 1000:
                logger.warning(f"Health check failed: too small response ({len(response.text)} bytes)")
                return False
            
            logger.info("Health check passed - connection OK")
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    @staticmethod
    def _normalize_header(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip().lower()

    @staticmethod
    def _cell_text(cell) -> str:
        return " ".join(cell.stripped_strings)

    @staticmethod
    def _parse_date_value(value: str) -> Optional[str]:
        """Return date value as-is from source (no conversion)."""
        if not value or value.strip() == '-' or value.strip() == '':
            return None
        return value.strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Simple direct request - no proxies, no Tor."""
        self.rate_limiter.wait()
        timeout = (self.config.connect_timeout, self.config.read_timeout)

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()

            content = response.text.lower()

            # Basic block detection
            if (
                response.status_code != 200
                or "access denied" in content
                or "forbidden" in content
                or "captcha" in content
                or len(response.text) < 1000
            ):
                raise Exception("Blocked response")
            
            self.rate_limiter.record_result(True)
            return response

        except Exception as e:
            self.rate_limiter.record_result(False)
            raise e

    def extract_basic_records(self) -> List[PharmacistRecord]:
        logger.info("Extracting basic records...")
        response = self._request("GET", self.urls['total'])
        soup = BeautifulSoup(response.content, 'html.parser')
        
        records = []
        table = soup.find('table', attrs={'id': 'tablesorter-demo'}) or soup.find('table')
        
        if not table:
            return []

        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
                
            try:
                records.append(PharmacistRecord(
                    serial_number=int(cells[0].get_text(strip=True)) if cells[0].get_text(strip=True).isdigit() else None,
                    registration_number=cells[1].get_text(strip=True),
                    name=cells[2].get_text(strip=True),
                    father_name=cells[3].get_text(strip=True),
                    category=cells[4].get_text(strip=True)
                ))
            except Exception:
                continue
                
        logger.info(f"Extracted {len(records)} records")
        return records

    def extract_detailed_info(self, reg_no: str, img_dir: Path = None) -> Optional[PharmacistRecord]:
        try:
            logger.info(f"Enriching {reg_no}...")
            response = self._request("POST", self.urls['search'], data={
                'registration_no': reg_no,
                'submit': 'Submit'
            })

            if 'No Records Found' in response.text:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')

            if not tables:
                return None

            record = PharmacistRecord(registration_number=reg_no, name="", father_name="", category="")

            basic_headers = []
            basic_values = {}

            img = soup.find('img', id=re.compile(r'imgPhoto', re.I))
            if not img:
                info_table = next(
                    (
                        table for table in tables
                        if 'registration no' in [self._normalize_header(th.get_text(" ", strip=True)) for th in table.find_all('th')]
                    ),
                    None,
                )
                if info_table:
                    img = info_table.find('img')

            if img and img.get('src') and img_dir:
                src = img['src']
                import base64

                if 'base64' in src:
                    # Extract MIME type from data URI
                    if src.startswith('data:'):
                        mime_type = src.split(';')[0].split(':')[1]  # e.g., "image/jpeg"
                        base64_data = src.split(',')[-1]
                        image_bytes = base64.b64decode(base64_data)

                        # Get file extension from MIME type
                        ext_map = {
                            'image/jpeg': 'jpg',
                            'image/jpg': 'jpg',
                            'image/png': 'png',
                            'image/webp': 'webp',
                            'image/gif': 'gif'
                        }
                        ext = ext_map.get(mime_type.lower(), 'jpg')

                        # Save image with registration number as filename
                        photo_path = img_dir / f"{reg_no}.{ext}"
                        with open(photo_path, 'wb') as f:
                            f.write(image_bytes)
                        logger.info(f"Saved photo from base64: {photo_path.name}")

                elif src.startswith('/') or src.startswith('http'):
                    # Download photo from relative or absolute URL
                    try:
                        photo_url = src if src.startswith('http') else f"{self.config.base_url}{src}"
                        photo_response = self._request("GET", photo_url)
                        if photo_response.status_code == 200:
                            # Get format from Content-Type header
                            content_type = photo_response.headers.get('Content-Type', 'image/jpeg')
                            ext_map = {
                                'image/jpeg': 'jpg',
                                'image/jpg': 'jpg',
                                'image/png': 'png',
                                'image/webp': 'webp',
                                'image/gif': 'gif'
                            }
                            ext = ext_map.get(content_type.lower(), 'jpg')

                            # Save image with registration number as filename
                            photo_path = img_dir / f"{reg_no}.{ext}"
                            with open(photo_path, 'wb') as f:
                                f.write(photo_response.content)
                            logger.info(f"Saved photo from URL: {photo_path.name}")
                    except Exception as e:
                        logger.warning(f"Failed to download photo from {src}: {e}")

            for table in tables:
                headers = [self._normalize_header(th.get_text(" ", strip=True)) for th in table.find_all('th')]
                if 'registration no' in headers and 'name' in headers:
                    data_row = next((row for row in table.find_all('tr') if row.find_all('td')), None)
                    if data_row:
                        cells = [self._cell_text(cell) for cell in data_row.find_all('td')]
                        basic_headers = headers
                        basic_values = {
                            basic_headers[i]: cells[i]
                            for i in range(min(len(basic_headers), len(cells)))
                        }
                    break

            if basic_values:
                record.registration_number = basic_values.get('registration no') or reg_no
                record.name = basic_values.get('name', '')
                record.father_name = basic_values.get('father name', '')
                record.gender = basic_values.get('gender', '')
                record.category = basic_values.get('category', '')
                record.status = basic_values.get('status', '')
                # Try multiple possible header names for validity
                validity_date = None
                for key in ['validity', 'valid upto', 'valid up to', 'validity date']:
                    validity_date = self._parse_date_value(basic_values.get(key, ''))
                    if validity_date:
                        record.validity_date = validity_date
                        break

            main_text = soup.get_text()
            if not record.validity_date:
                validity_match = re.search(
                    r'Valid\s*(?:Upto|Up\s*to)\s*[:\-]?\s*([0-9]{2}(?:[-/][0-9]{2}(?:[-/][0-9]{4})|-[A-Za-z]{3}-[0-9]{4}))',
                    main_text,
                    re.I,
                )
                if validity_match:
                    parsed_date = self._parse_date_value(validity_match.group(1).replace('/', '-'))
                    if parsed_date:
                        record.validity_date = parsed_date

            for table in tables:
                headers = [self._normalize_header(th.get_text(" ", strip=True)) for th in table.find_all('th')]
                if any('qualification' in h for h in headers) or (
                    'category' in headers and any('board/university' in h or 'university' in h for h in headers)
                ):
                    edu_list = []
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = [self._cell_text(cell) for cell in row.find_all(['th', 'td'])]
                        if len(cols) >= 2:
                            row_map = {
                                headers[i]: cols[i]
                                for i in range(min(len(headers), len(cols)))
                            }
                            education = {
                                'Category': row_map.get('category') or row_map.get('qualification', ''),
                                'Board/University': row_map.get('board/university') or row_map.get('university', ''),
                                'College Name': row_map.get('college name', ''),
                                'College Address': row_map.get('college address', ''),
                                'From': row_map.get('from', ''),
                                'To': row_map.get('to', ''),
                                'HT No': row_map.get('ht no', ''),
                            }
                            edu_list.append(education)
                    record.education = edu_list

            record.work_experience = {
                "Address": "",
                "State": "",
                "District": "",
                "Pin code": ""
            }

            for table in tables:
                headers = [self._normalize_header(th.get_text(" ", strip=True)) for th in table.find_all('th')]
                if 'address' in headers and 'state' in headers and 'district' in headers:
                    data_row = next((row for row in table.find_all('tr')[1:] if row.find_all('td')), None)
                    if not data_row:
                        continue

                    cols = [self._cell_text(cell) for cell in data_row.find_all('td')]
                    row_map = {
                        headers[i]: cols[i]
                        for i in range(min(len(headers), len(cols)))
                    }
                    work_info = {
                        'Address': row_map.get('address', ''),
                        'State': row_map.get('state', ''),
                        'District': row_map.get('district', ''),
                        'Pin code': row_map.get('pin code', ''),
                    }
                    record.work_experience = work_info
                    break

            return record

        except Exception as e:
            logger.error(f"Failed to extract details for {reg_no}: {e}")
            return None
