"""Module for downloading document files."""
import os
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from tqdm import tqdm
from urllib.parse import urlparse

from src.api.client import APIClient
from src.storage.file_manager import FileManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentDownloader:
    """Download document files for tenders."""

    def __init__(
        self,
        api_client: APIClient,
        file_manager: FileManager,
        download_endpoint_template: Optional[str] = None,
        attachments_subdir: Optional[str] = None
    ):
        """
        Initialize DocumentDownloader.
        
        Args:
            api_client: APIClient instance for making requests
            file_manager: FileManager instance for managing file paths
            download_endpoint_template: Optional template for download endpoint
                                        (if None, uses document URL directly)
        """
        self.api_client = api_client
        self.file_manager = file_manager
        self.download_endpoint_template = download_endpoint_template
        self.attachments_subdir = attachments_subdir

    def download_document(
        self,
        tender_id: str,
        document: Dict[str, Any],
        overwrite: bool = False
    ) -> Optional[Path]:
        """
        Download a single document file.
        
        Args:
            tender_id: Tender identifier
            document: Document dictionary (should contain 'url' or 'downloadUrl' and 'fileName')
            overwrite: Whether to overwrite existing files
            
        Returns:
            Path to downloaded file, or None if download failed
        """
        # Get file name
        file_name = document.get('fileName') or document.get('name')
        if not file_name:
            logger.warning(f"No filename found for document in tender {tender_id}")
            return None
        file_name = Path(file_name).name  # ensure no nested paths
        
        # Get download URL
        download_url = document.get('url') or document.get('downloadUrl') or document.get('fileUrl')
        if not download_url:
            logger.warning(f"No download URL found for document {file_name} in tender {tender_id}")
            return None
        
        # If download_endpoint_template is provided, construct URL
        if self.download_endpoint_template:
            document_identifier = (
                document.get('id')
                or document.get('objectId')
                or document.get('documentId')
                or ''
            )
            download_url = self.download_endpoint_template.format(
                tenderId=tender_id,
                documentId=document_identifier,
                fileName=file_name
            )
        
        # Get tender folder
        tender_folder = self.file_manager.create_tender_folder(tender_id)

        target_folder = (
            tender_folder / self.attachments_subdir
            if self.attachments_subdir
            else tender_folder
        )
        target_folder.mkdir(parents=True, exist_ok=True)
        file_path = target_folder / file_name
        
        # Check if file already exists
        if file_path.exists() and not overwrite:
            logger.debug(f"File already exists, skipping: {file_path}")
            return file_path
        
        try:
            # Download file
            response = self.api_client.get(download_url)
            response.raise_for_status()
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading {file_name} for tender {tender_id}: {str(e)}")
            return None

    def download_documents_for_tender(
        self,
        tender_id: str,
        documents: List[Dict[str, Any]],
        overwrite: bool = False
    ) -> List[Path]:
        """
        Download all documents for a specific tender.
        
        Args:
            tender_id: Tender identifier
            documents: List of document dictionaries
            overwrite: Whether to overwrite existing files
            
        Returns:
            List of paths to successfully downloaded files
        """
        downloaded_files = []
        
        for document in tqdm(documents, desc=f"Downloading documents for {tender_id}", leave=False):
            file_path = self.download_document(tender_id, document, overwrite=overwrite)
            if file_path:
                downloaded_files.append(file_path)
        
        logger.info(f"Downloaded {len(downloaded_files)}/{len(documents)} documents for tender {tender_id}")
        return downloaded_files

    def download_documents_batch(
        self,
        tender_documents: Dict[str, List[Dict[str, Any]]],
        overwrite: bool = False
    ) -> Dict[str, List[Path]]:
        """
        Download documents for multiple tenders.
        
        Args:
            tender_documents: Dictionary mapping tender_id to list of documents
            overwrite: Whether to overwrite existing files
            
        Returns:
            Dictionary mapping tender_id to list of downloaded file paths
        """
        result = {}
        
        for tender_id, documents in tqdm(tender_documents.items(), desc="Downloading documents"):
            downloaded = self.download_documents_for_tender(tender_id, documents, overwrite=overwrite)
            result[tender_id] = downloaded
        
        return result

