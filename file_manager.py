"""File management module for creating directories and saving JSON files."""
import os
import json
from pathlib import Path
from typing import Dict, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manage file operations for tender data."""

    def __init__(self, base_path: str, tenders_dir: str = "tenders"):
        """
        Initialize FileManager.
        
        Args:
            base_path: Base path for data storage (project root)
            tenders_dir: Name of the tenders directory (relative to base_path)
        """
        self.base_path = Path(base_path)
        self.tenders_dir = Path(tenders_dir)
        self.tenders_path = self.base_path / self.tenders_dir

    def create_tender_folder(self, tender_id: str) -> Path:
        """
        Create a folder for a specific tender.
        
        Args:
            tender_id: Tender identifier
            
        Returns:
            Path to the created tender folder
        """
        tender_folder = self.tenders_path / tender_id
        tender_folder.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created/verified tender folder: {tender_folder}")
        return tender_folder

    def save_tender_json(self, tender_id: str, tender_data: Dict[str, Any], filename: str = "tender.json") -> Path:
        """
        Save tender JSON data to file.
        
        Args:
            tender_id: Tender identifier
            tender_data: Tender data dictionary
            filename: Name of the JSON file (default: tender.json)
            
        Returns:
            Path to the saved file
        """
        tender_folder = self.create_tender_folder(tender_id)
        file_path = tender_folder / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tender_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Saved tender JSON: {file_path}")
        return file_path

    def save_documents_json(self, tender_id: str, documents: list, filename: str = "documents.json") -> Path:
        """
        Save documents JSON data to file.
        
        Args:
            tender_id: Tender identifier
            documents: List of document dictionaries
            filename: Name of the JSON file (default: documents.json)
            
        Returns:
            Path to the saved file
        """
        tender_folder = self.create_tender_folder(tender_id)
        file_path = tender_folder / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"Saved documents JSON: {file_path}")
        return file_path

    def load_tender_json(self, tender_id: str, filename: str = "tender.json") -> Dict[str, Any]:
        """
        Load tender JSON data from file.
        
        Args:
            tender_id: Tender identifier
            filename: Name of the JSON file
            
        Returns:
            Tender data dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.tenders_path / tender_id / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Tender file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_documents_json(self, tender_id: str, filename: str = "documents.json") -> list:
        """
        Load documents JSON data from file.
        
        Args:
            tender_id: Tender identifier
            filename: Name of the JSON file
            
        Returns:
            List of document dictionaries
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.tenders_path / tender_id / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Documents file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def document_metadata_exists(self, tender_id: str, filename: str = "documents.json") -> bool:
        """Check whether documents.json exists for a tender."""
        return (self.tenders_path / tender_id / filename).exists()

    def tender_folder_exists(self, tender_id: str) -> bool:
        """
        Check if a tender folder exists.
        
        Args:
            tender_id: Tender identifier
            
        Returns:
            True if folder exists, False otherwise
        """
        tender_folder = self.tenders_path / tender_id
        return tender_folder.exists() and tender_folder.is_dir()

    def list_tender_ids(self, pattern: str = "*") -> list:
        """
        List tender IDs stored locally, optionally filtered by glob pattern.
        
        Args:
            pattern: Glob pattern to match tender folder names
            
        Returns:
            Sorted list of folder names matching the pattern
        """
        if not self.tenders_path.exists():
            return []
        tender_ids = [
            path.name
            for path in self.tenders_path.glob(pattern)
            if path.is_dir()
        ]
        return sorted(tender_ids)

