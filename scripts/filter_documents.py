#!/usr/bin/env python3
"""Script to filter documents based on patterns."""
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.filtering.document_finder import DocumentFinder
from src.utils.config_loader import (
    load_config,
    get_paths_config,
    get_filtering_config
)
from src.utils.logger import setup_logger

logger = setup_logger()


def main():
    """Main function to filter documents."""
    # Load configuration
    config = load_config()
    
    paths_config = get_paths_config(config)
    filtering_config = get_filtering_config(config)
    
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    
    # Get paths from config
    tenders_dir = paths_config.get('tenders_dir', 'data/tenders')
    output_dir = paths_config.get('output_dir', 'data/output')
    output_file = filtering_config.get('output_file', 'filtered_documents.txt')
    
    # Initialize document finder
    document_finder = DocumentFinder(
        base_path=str(project_root),
        tenders_dir=tenders_dir,
        documents_file='documents.json'
    )
    
    # Extract file names
    logger.info("Extracting file names from documents.json files...")
    file_data = document_finder.extract_file_names()
    logger.info(f"Found {len(file_data)} documents")
    
    # Get pattern name from command line or config
    pattern_name = sys.argv[1] if len(sys.argv) > 1 else "kosztorys"
    
    # Find matching files
    logger.info(f"Filtering documents using pattern: {pattern_name}")
    matching_files = document_finder.find_matching_files(file_data, pattern_name=pattern_name)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file_path = output_path / output_file
    
    # Write results
    if matching_files:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for file_path in matching_files:
                f.write(f"{file_path}\n")
        logger.info(f"Found {len(matching_files)} matching files. Results written to {output_file_path}")
    else:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(f"No files matching pattern '{pattern_name}' found.\n")
        logger.info(f"No matching files found. Output written to {output_file_path}")


if __name__ == "__main__":
    main()

