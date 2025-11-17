#!/usr/bin/env python3
"""Script to fetch tenders by category from the API."""
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.client import APIClient
from src.api.tender_fetcher import TenderFetcher
from src.storage.file_manager import FileManager
from src.utils.config_loader import (
    load_config,
    load_env_vars,
    get_api_config,
    get_paths_config,
)
from src.utils.logger import setup_logger

logger = setup_logger()


def main():
    """Main function to fetch tenders."""
    # Load configuration
    load_env_vars()
    config = load_config()
    
    api_config = get_api_config(config)
    paths_config = get_paths_config(config)
    
    # Initialize components
    api_client = APIClient(
        base_url=api_config.get('base_url', ''),
        rate_limit=api_config.get('rate_limit', 10),
        timeout=api_config.get('timeout', 30)
    )
    
    tender_fetch_cfg = config.get('tender_fetch', {})
    pagination_cfg = tender_fetch_cfg.get('pagination', {})

    tender_fetcher = TenderFetcher(
        api_client=api_client,
        search_endpoint=api_config.get('endpoints', {}).get('search_tenders', '/api/Search/SearchTenders'),
        province_param=tender_fetch_cfg.get('province_param', 'organizationProvince'),
        page_size=pagination_cfg.get('page_size', 50),
        sorting_column=pagination_cfg.get('sorting_column', 'InitiationDate'),
        sorting_direction=pagination_cfg.get('sorting_direction', 'DESC'),
    )
    
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    file_manager = FileManager(
        base_path=str(project_root),
        tenders_dir=paths_config.get('tenders_dir', 'data/tenders')
    )
    
    # Get categories from command line or config
    if len(sys.argv) > 1:
        categories = sys.argv[1:]
    else:
        # Default: fetch all categories or prompt user
        logger.warning("No categories specified. Please provide categories as command line arguments.")
        logger.info("Usage: python scripts/fetch_tenders.py <category1> <category2> ...")
        return
    
    logger.info(f"Fetching tenders for categories (provinces): {categories}")
    
    # Fetch tenders for each category
    for category in categories:
        logger.info(f"Processing category: {category}")
        tenders = tender_fetcher.fetch_tenders_by_category(category)
        
        # Save each tender
        for tender in tenders:
            tender_id = tender.get('objectId') or tender.get('id')
            if not tender_id:
                logger.warning(f"Skipping tender without ID: {tender}")
                continue
            
            file_manager.save_tender_json(tender_id, tender)
            logger.debug(f"Saved tender: {tender_id}")
        
        logger.info(f"Saved {len(tenders)} tenders for category {category}")


if __name__ == "__main__":
    main()

