"""
Core utilities for TGPC system.
Combines configuration, logging, and exception handling.
"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# --- Exceptions ---

class TGPCError(Exception):
    """Base exception for all TGPC-related errors."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

# --- Configuration ---

@dataclass
class Config:
    """Configuration for TGPC system."""
    
    # API Settings
    base_url: str = "https://www.pharmacycouncil.telangana.gov.in"
    connect_timeout: int = 20
    read_timeout: int = 180
    max_retries: int = 3
    proxy_url: Optional[str] = None
    
    # Tor Settings
    use_tor: bool = False
    tor_socks_port: int = 9050
    tor_control_port: int = 9051
    tor_password: Optional[str] = None
    
    # Rate Limiting
    min_delay: float = 3.0
    max_delay: float = 8.0
    long_break_after: int = 100
    long_break_duration: int = 60
    
    # Storage
    data_directory: str = "data"
    
    # User Agent
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration."""
        proxy_url = (
            os.environ.get("TGPC_PROXY_URL")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
            or None
        )
        
        return cls(
            proxy_url=proxy_url,
            use_tor=os.getenv('TGPC_USE_TOR', '').lower() in ('true', '1', 'yes'),
            tor_socks_port=int(os.getenv('TGPC_TOR_SOCKS_PORT', str(cls.tor_socks_port))),
            tor_control_port=int(os.getenv('TGPC_TOR_CONTROL_PORT', str(cls.tor_control_port))),
            tor_password=os.getenv('TGPC_TOR_PASSWORD'),
        )

# --- Logging ---

def setup_logging(name: str = "tgpc") -> logging.Logger:
    """Set up minimal logging."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    return logger
