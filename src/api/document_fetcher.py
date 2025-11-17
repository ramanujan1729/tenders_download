"""Module for fetching documents for tenders."""
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.api.client import APIClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentFetcher:
    """Fetch documents for specific tenders."""

    def __init__(
        self,
        api_client: APIClient,
        documents_endpoint: str = "/api/tenders/{tenderId}/documents",
        tender_param_name: str = "tenderId",
    ):
        """
        Initialize DocumentFetcher.
        
        Args:
            api_client: APIClient instance
            documents_endpoint: Endpoint or template for documents (supports {tenderId} placeholder
                               or plain endpoint requiring query parameter)
            tender_param_name: Name of the tenderId query parameter (used when endpoint has no placeholder)
        """
        self.api_client = api_client
        self.documents_endpoint = documents_endpoint
        self.tender_param_name = tender_param_name

    def fetch_documents(self, tender_id: str) -> List[Dict[str, Any]]:
        """
        Fetch documents for a specific tender.
        
        Args:
            tender_id: Tender identifier
            
        Returns:
            List of document dictionaries
        """
        try:
            if "{tenderId}" in self.documents_endpoint:
                endpoint = self.documents_endpoint.format(tenderId=tender_id)
                response = self.api_client.get_json(endpoint)
            else:
                response = self.api_client.get_json(
                    self.documents_endpoint,
                    params={self.tender_param_name: tender_id},
                )
            
            # Handle different response formats
            if isinstance(response, list):
                documents = response
            elif isinstance(response, dict):
                documents = response.get('data', response.get('documents', []))
            else:
                logger.warning(f"Unexpected response format for tender {tender_id}: {type(response)}")
                return []
            
            logger.debug(f"Fetched {len(documents)} documents for tender {tender_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching documents for tender {tender_id}: {str(e)}")
            return []

    def fetch_documents_batch(self, tender_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch documents for multiple tenders.
        
        Args:
            tender_ids: List of tender identifiers
            
        Returns:
            Dictionary mapping tender_id to list of documents
        """
        result = {}
        
        for tender_id in tqdm(tender_ids, desc="Fetching documents"):
            documents = self.fetch_documents(tender_id)
            result[tender_id] = documents
        
        return result

