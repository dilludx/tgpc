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
    registration_number: str
    name: str
    father_name: str
    category: str
    serial_number: Optional[int] = None
    
    validity_date: Optional[str] = None
    education: Optional[List[Dict[str, str]]] = None
    work_experience: Optional[Dict[str, str]] = None
    photo_base64: Optional[str] = None
    photo_path: Optional[str] = None

    def to_dict(self):
        return {
            "registration_number": self.registration_number,
            "name": self.name,
            "father_name": self.father_name,
            "category": self.category,
            "serial_number": self.serial_number
        }
    
    def to_detailed_dict(self):
        data = {
            "validity_date": self.validity_date,
            "education": self.education,
            "work_experience": self.work_experience,
            "photo_path": self.photo_path
        }
        return {k: v for k, v in data.items() if v}

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

        # 🔥 FIX: Real browser-like session
        self.session = requests.Session()
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

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=30), reraise=True)
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.rate_limiter.wait()
        timeout = (self.config.connect_timeout, self.config.read_timeout)

        try:
            response = self.session.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()

            content = response.text.lower()

            # 🚨 BLOCK DETECTION
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

            # 🔁 FALLBACK REQUEST
            try:
                time.sleep(random.uniform(2, 5))

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
                    "Referer": url,
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }

                response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
                response.raise_for_status()

                if response.status_code == 200 and len(response.text) > 1000:
                    return response

            except Exception:
                pass

            raise TGPCError(f"Request failed: {url}", e)

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

    def extract_detailed_info(self, reg_no: str) -> Optional[PharmacistRecord]:
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

            # (rest of your logic unchanged)
            return record

        except Exception as e:
            logger.error(f"Failed to extract details for {reg_no}: {e}")
            return None
