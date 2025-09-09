"""Base Datadog client with common functionality."""
import httpx
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class BaseDatadogClient(ABC):
    """Base class for Datadog API clients with common functionality."""
    
    def __init__(self, timeout: float = 30.0):
        """Initialize the HTTP client."""
        self.client = httpx.AsyncClient(timeout=timeout)
        self._api_key = settings.datadog_api_key
        self._app_key = settings.datadog_app_key
        self._service_name = settings.DATADOG_SERVICE_NAME
    
    def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """Get standard Datadog API headers."""
        headers = {
            "DD-API-KEY": self._api_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if self._app_key:
            headers["DD-APPLICATION-KEY"] = self._app_key
        return headers
    
    def _is_api_available(self) -> bool:
        """Check if API keys are available."""
        return bool(self._api_key and self._app_key)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with error handling."""
        try:
            response = await self.client.request(method, url, **kwargs)
            return response
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    @abstractmethod
    async def fetch_data(self, **kwargs):
        """Abstract method to fetch data from Datadog API."""
        pass
