"""Module for fetching detailed tender information by ID."""
from typing import Dict, Any, Optional

from src.api.client import APIClient
from src.utils.logger import get_logger


logger = get_logger(__name__)


class TenderDetailsFetcher:
    """Fetch tender detail payloads for specific IDs."""

    def __init__(
        self,
        api_client: APIClient,
        details_endpoint: str = "/api/Search/GetTender",
        tender_param_name: str = "tenderId",
    ):
        """
        Initialize TenderDetailsFetcher.

        Args:
            api_client: APIClient instance
            details_endpoint: Endpoint or template for retrieving tender info. Supports
                              `{tenderId}` placeholder or bare endpoint requiring query param.
            tender_param_name: Name of the tenderId query parameter
        """
        self.api_client = api_client
        self.details_endpoint = details_endpoint
        self.tender_param_name = tender_param_name

    def fetch_tender(self, tender_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single tender detail payload."""
        try:
            if "{tenderId}" in self.details_endpoint:
                endpoint = self.details_endpoint.format(tenderId=tender_id)
                response = self.api_client.get_json(endpoint)
            else:
                response = self.api_client.get_json(
                    self.details_endpoint,
                    params={self.tender_param_name: tender_id},
                )

            if not isinstance(response, dict):
                logger.warning(
                    "Unexpected tender detail response format for %s: %s",
                    tender_id,
                    type(response),
                )
                return None

            return response
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error fetching tender %s: %s", tender_id, exc)
            return None

