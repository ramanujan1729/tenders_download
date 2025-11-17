"""Base API client for tender website."""
import os
import time
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.logger import get_logger

logger = get_logger(__name__)


class APIClient:
    """Base API client with rate limiting and error handling."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        rate_limit: float = 10.0,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the API
            api_key: API key for authentication
            api_secret: API secret for authentication
            rate_limit: Maximum requests per second
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv('API_KEY')
        self.api_secret = api_secret or os.getenv('API_SECRET')
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.min_request_interval = 1.0 / rate_limit
        self.last_request_time = 0.0
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Add authentication if provided
        if self.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})

    def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """
        Make an HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            params: URL parameters
            data: Form data
            json_data: JSON data
            
        Returns:
            Response object
            
        Raises:
            requests.RequestException: If request fails
        """
        self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make a GET request."""
        return self._make_request('GET', endpoint, params=params)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Make a POST request."""
        return self._make_request('POST', endpoint, json_data=json_data)

    def get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request and return JSON response.
        
        Args:
            endpoint: API endpoint
            params: URL parameters
            
        Returns:
            JSON response as dictionary
        """
        response = self.get(endpoint, params=params)
        return response.json()

