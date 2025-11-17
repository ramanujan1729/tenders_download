"""Module for fetching tenders from the API."""
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.api.client import APIClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TenderFetcher:
    """Fetch tenders by category (province) from the search endpoint."""

    def __init__(
        self,
        api_client: APIClient,
        search_endpoint: str = "/api/Search/SearchTenders",
        province_param: str = "organizationProvince",
        page_size: int = 50,
        sorting_column: str = "InitiationDate",
        sorting_direction: str = "DESC",
    ):
        """
        Initialize TenderFetcher.
        
        Args:
            api_client: APIClient instance
            search_endpoint: API endpoint for searching tenders
            province_param: Query parameter used to pass the province/category
            page_size: Number of records per page
            sorting_column: Sorting column name
            sorting_direction: Sorting direction ("ASC"/"DESC")
        """
        self.api_client = api_client
        self.search_endpoint = search_endpoint
        self.province_param = province_param
        self.page_size = page_size
        self.sorting_column = sorting_column
        self.sorting_direction = sorting_direction

    def fetch_tenders_by_category(
        self,
        category: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch tenders for a specific category.
        
        Args:
            category: Category identifier
            limit: Maximum number of tenders to fetch (None for all)
            offset: Offset for pagination
            
        Returns:
            List of tender dictionaries
        """
        all_tenders = []
        page_number = 1
        
        logger.info(f"Fetching tenders for category: {category}")
        
        while True:
            params = {
                self.province_param: category,
                'PageNumber': page_number,
                'PageSize': self.page_size,
                'SortingColumnName': self.sorting_column,
                'SortingDirection': self.sorting_direction,
            }

            if limit is not None:
                remaining = limit - len(all_tenders)
                if remaining <= 0:
                    break
                params['PageSize'] = min(params['PageSize'], remaining)
            
            try:
                response = self.api_client.get_json(self.search_endpoint, params=params)
                
                # Handle different response formats
                if isinstance(response, list):
                    tenders = response
                elif isinstance(response, dict):
                    tenders = response.get('data', response.get('tenders', []))
                    
                    if not tenders:
                        break
                else:
                    logger.warning(f"Unexpected response format: {type(response)}")
                    break
                
                if not tenders:
                    break
                
                all_tenders.extend(tenders)
                logger.info(f"Fetched {len(tenders)} tenders (total: {len(all_tenders)})")
                
                if len(tenders) < params['PageSize']:
                    break
                
                page_number += 1
                
            except Exception as e:
                logger.error(f"Error fetching tenders: {str(e)}")
                break
        
        logger.info(f"Total tenders fetched: {len(all_tenders)}")
        return all_tenders

    def fetch_all_categories(self, categories: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch tenders for multiple categories.
        
        Args:
            categories: List of category identifiers
            
        Returns:
            Dictionary mapping category to list of tenders
        """
        result = {}
        
        for category in tqdm(categories, desc="Fetching categories"):
            tenders = self.fetch_tenders_by_category(category)
            result[category] = tenders
        
        return result

