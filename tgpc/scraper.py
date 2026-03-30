"""
Core scraping logic for TGPC system.
Handles data extraction, rate limiting, and parsing.
"""

import time
import random
import re
from datetime import datetime
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
    """Pharmacist record data model."""
    registration_number: str
    name: str
    father_name: str
    category: str
    serial_number: Optional[int] = None
    
    # Detailed fields (Not included in basic rx.json)
    validity_date: Optional[str] = None
    education: Optional[List[Dict[str, str]]] = None
    work_experience: Optional[Dict[str, str]] = None
    photo_base64: Optional[str] = None  # Temporary storage during scrap
    photo_path: Optional[str] = None    # Relative local path

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
        """Convert to detailed dictionary for rxdetails.json."""
        data = {
            "validity_date": self.validity_date,
            "education": self.education,
            "work_experience": self.work_experience,
            "photo_path": self.photo_path
        }
        return {k: v for k, v in data.items() if v}

# --- Rate Limiter ---

class RateLimiter:
    """Simple adaptive rate limiter."""
    
    def __init__(self, config: Config):
        self.min_delay = config.min_delay
        self.max_delay = config.max_delay
        self.current_delay = config.min_delay
        self.consecutive_failures = 0

    def wait(self):
        """Wait for the calculated delay."""
        delay = self.current_delay * random.uniform(0.8, 1.2)
        time.sleep(delay)

    def record_result(self, success: bool):
        """Adjust delay based on success/failure."""
        if success:
            self.consecutive_failures = 0
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
        else:
            self.consecutive_failures += 1
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)

# --- Scraper ---

class Scraper:
    """Main scraper class."""

    def __init__(self):
        self.config = Config.load()
        self.rate_limiter = RateLimiter(self.config)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.config.user_agent})
        
        self.urls = {
            'total': f"{self.config.base_url}/pharmacy/srchpharmacisttotal",
            'search': f"{self.config.base_url}/pharmacy/getsearchpharmacist"
        }

    @staticmethod
    def _normalize_header(text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip().lower()

    @staticmethod
    def _cell_text(cell) -> str:
        return " ".join(cell.stripped_strings)

    @staticmethod
    def _parse_date_value(value: str) -> Optional[str]:
        cleaned = value.strip()
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%B-%Y"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=30))
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry and rate limiting."""
        self.rate_limiter.wait()
        try:
            response = self.session.request(method, url, timeout=self.config.timeout, **kwargs)
            response.raise_for_status()
            self.rate_limiter.record_result(True)
            return response
        except Exception as e:
            self.rate_limiter.record_result(False)
            raise TGPCError(f"Request failed: {url}", e)

    def get_total_count(self) -> int:
        """Get total number of pharmacists."""
        try:
            response = self._request("GET", self.urls['total'])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find table
            table = soup.find('table', attrs={'id': 'tablesorter-demo'})
            if not table:
                tables = soup.find_all('table')
                if not tables:
                    raise TGPCError("No tables found")
                table = tables[0]

            # Count rows
            rows = [r for r in table.find_all('tr') if r.find_all('td')]
            
            # Try to extract serial numbers for better accuracy
            serials = []
            for row in rows:
                try:
                    serials.append(int(row.find_all('td')[0].get_text(strip=True)))
                except (ValueError, IndexError):
                    pass
            
            count = len(set(serials)) if serials else len(rows)
            logger.info(f"Total count: {count}")
            return count
            
        except Exception as e:
            raise TGPCError("Failed to get total count", e)

    def extract_basic_records(self) -> List[PharmacistRecord]:
        """Extract all basic records."""
        logger.info("Extracting basic records...")
        response = self._request("GET", self.urls['total'])
        soup = BeautifulSoup(response.content, 'html.parser')
        
        records = []
        table = soup.find('table', attrs={'id': 'tablesorter-demo'}) or soup.find('table')
        
        if not table:
            return []

        for row in table.find_all('tr')[1:]: # Skip header
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

    def extract_detailed_info(self, reg_no: str) -> Optional[PharmacistRecord]:
        """Extract detailed info for a single pharmacist."""
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

            # Initialize record with dummy basic data (will be merged later)
            record = PharmacistRecord(
                registration_number=reg_no, 
                name="", father_name="", category=""
            )

            basic_headers = []
            basic_values = {}

            # 1. Parse Image
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
            if img and img.get('src'):
                src = img['src']
                if 'base64' in src:
                    record.photo_base64 = src.split(',')[-1]

            # 2. Parse Main Info table
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
                record.category = basic_values.get('category', '')
                validity_date = self._parse_date_value(basic_values.get('validity', ''))
                if validity_date:
                    record.validity_date = validity_date

            # 3. Fallback validity parsing from full text
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

            # 4. Parse Education
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
                                'qualification': row_map.get('qualification') or row_map.get('category', ''),
                                'university': row_map.get('board/university') or row_map.get('university', ''),
                                'year': row_map.get('year') or row_map.get('to', ''),
                            }
                            optional_fields = {
                                'college name': 'college_name',
                                'college address': 'college_address',
                                'from': 'from',
                                'to': 'to',
                                'ht no': 'hall_ticket_number',
                            }
                            for header, key in optional_fields.items():
                                value = row_map.get(header, '')
                                if value:
                                    education[key] = value
                            edu_list.append(education)
                    record.education = edu_list or None

            # 5. Parse working / studying information
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
                        'address': row_map.get('address', ''),
                        'state': row_map.get('state', ''),
                        'district': row_map.get('district', ''),
                        'pin_code': row_map.get('pin code', ''),
                    }
                    if any(work_info.values()):
                        record.work_experience = work_info
                    break

            return record

        except Exception as e:
            logger.error(f"Failed to extract details for {reg_no}: {e}")
            return None
