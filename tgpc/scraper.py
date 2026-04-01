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

try:
    import socks
    import stem
    from stem.control import Controller
    TOR_AVAILABLE = True
except ImportError:
    TOR_AVAILABLE = False

try:
    from tgpc.proxy_pool import get_free_proxy
    PROXY_POOL_AVAILABLE = True
except ImportError:
    PROXY_POOL_AVAILABLE = False

try:
    from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, NewConnectionError
    URF3_AVAILABLE = True
except ImportError:
    URF3_AVAILABLE = False

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
    def __init__(self, config: Config, scraper_instance=None):
        self.min_delay = config.min_delay
        self.max_delay = config.max_delay
        self.current_delay = config.min_delay
        self.consecutive_failures = 0
        self.scraper = scraper_instance
        self.config = config
        self.request_count = 0

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
            
            # Rotate Tor circuit on failures
            if self.config.use_tor and self.consecutive_failures >= 3 and self.scraper:
                self.scraper.rotate_tor_circuit()
                self.consecutive_failures = 0
    
    def count_request(self):
        """Count requests and rotate Tor circuit periodically."""
        self.request_count += 1
        # Rotate Tor circuit every 50 requests to avoid pattern detection
        if self.config.use_tor and self.request_count % 50 == 0 and self.scraper:
            self.scraper.rotate_tor_circuit()

# --- Scraper ---

class Scraper:

    def __init__(self):
        self.config = Config.load()
        self.rate_limiter = RateLimiter(self.config, scraper_instance=self)

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
        self.proxies = None
        # Try Tor first if enabled
        if self.config.use_tor:
            if not TOR_AVAILABLE:
                logger.warning("Tor requested but required packages not installed. Install with: pip install requests[socks] stem")
                self.config.use_tor = False
            else:
                self._setup_tor()
        
        # If Tor failed or not enabled, try regular proxy
        elif self.config.proxy_url:
            self.proxies = {
                "http": self.config.proxy_url,
                "https": self.config.proxy_url,
            }
            self.session.proxies.update(self.proxies)
            self.session.trust_env = False
            logger.info("Using configured TGPC proxy for outbound requests")
        
        # If no proxy configured, try free proxy pool
        elif PROXY_POOL_AVAILABLE:
            self._setup_free_proxy()
        
        # Log final connection method
        if self.config.use_tor:
            logger.info("Connection method: Tor with circuit rotation")
        elif self.proxies:
            logger.info("Connection method: HTTP proxy")
        else:
            logger.info("Connection method: Direct connection")
        self.urls = {
            'total': f"{self.config.base_url}/pharmacy/srchpharmacisttotal",
            'search': f"{self.config.base_url}/pharmacy/getsearchpharmacist"
        }
        self.tor_controller = None

    def _setup_tor(self):
        """Setup Tor connection with circuit rotation."""
        try:
            # Configure session to use Tor SOCKS proxy
            self.session.proxies.update({
                'http': f'socks5://127.0.0.1:{self.config.tor_socks_port}',
                'https': f'socks5://127.0.0.1:{self.config.tor_socks_port}'
            })
            
            # Test Tor connection first
            try:
                import requests
                test_response = requests.get(
                    'https://check.torproject.org/',
                    proxies={'https': f'socks5://127.0.0.1:{self.config.tor_socks_port}'},
                    timeout=10
                )
                if 'Congratulations' not in test_response.text:
                    raise Exception("Tor not working properly")
            except Exception as e:
                logger.warning(f"Tor connection test failed: {e}")
                self.session.proxies.clear()
                self.config.use_tor = False
                return
            
            # Try to connect to Tor control port for circuit rotation
            try:
                self.tor_controller = Controller.from_port(
                    port=self.config.tor_control_port
                )
                if self.config.tor_password:
                    self.tor_controller.authenticate(password=self.config.tor_password)
                else:
                    self.tor_controller.authenticate()
                logger.info("Tor control connection established - circuit rotation enabled")
            except Exception as e:
                logger.warning(f"Tor control connection failed: {e}. Circuit rotation disabled.")
                self.tor_controller = None
            
            logger.info("Using Tor for outbound requests")
            
        except Exception as e:
            logger.error(f"Failed to setup Tor: {e}")
            self.session.proxies.clear()
            self.config.use_tor = False

    def rotate_tor_circuit(self):
        """Rotate Tor circuit for new IP."""
        if self.tor_controller:
            try:
                self.tor_controller.signal(stem.Signal.NEWNYM)
                logger.info("Tor circuit rotated - new IP address")
                time.sleep(2)  # Wait for circuit to establish
            except Exception as e:
                logger.warning(f"Failed to rotate Tor circuit: {e}")
        else:
            logger.info("Tor control not available - cannot rotate circuit")

    def _setup_free_proxy(self):
        """Setup free proxy pool for IP anonymity."""
        try:
            import asyncio
            
            # Try to get a working free proxy
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            proxy_dict = loop.run_until_complete(get_free_proxy())
            
            if proxy_dict:
                self.proxies = proxy_dict
                self.session.proxies.update(self.proxies)
                self.session.trust_env = False
                logger.info("Using free proxy pool for IP anonymity")
            else:
                logger.warning("No working free proxies available")
                
        except Exception as e:
            logger.warning(f"Failed to setup free proxy pool: {e}")

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

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=30), reraise=True)
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.rate_limiter.wait()
        self.rate_limiter.count_request()  # Count for Tor circuit rotation
        
        # Use longer timeouts for Tor
        if self.config.use_tor:
            timeout = (60, 300)  # (connect, read) for Tor
        else:
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
            
            # If Tor is timing out, fallback to direct connection
            if self.config.use_tor and "timeout" in str(e).lower():
                logger.warning("Tor timeout detected, falling back to direct connection")
                self.config.use_tor = False
                self.session.proxies.clear()
                self.tor_controller = None
                logger.info("Connection method: Direct connection (fallback)")
                
                # Retry with direct connection
                timeout = (self.config.connect_timeout, self.config.read_timeout)
                try:
                    response = requests.request(method, url, timeout=timeout, **kwargs)
                    response.raise_for_status()
                    self.rate_limiter.record_result(True)
                    return response
                except Exception as retry_e:
                    logger.error(f"Direct connection also failed: {retry_e}")
                    raise retry_e

            # 🔁 FALLBACK REQUEST
            try:
                time.sleep(random.uniform(2, 5))

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
                    "Referer": url,
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                }

                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    proxies=self.proxies,
                    **kwargs,
                )
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
            if img and img.get('src'):
                src = img['src']
                if 'base64' in src:
                    record.photo_base64 = src.split(',')[-1]

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
