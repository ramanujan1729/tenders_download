"""Document finder module for filtering documents based on patterns."""
import os
import json
from typing import Iterable, Tuple, List
from pathlib import Path
from tqdm import tqdm

from src.filtering.patterns import get_pattern


class DocumentFinder:
    """Find documents matching specific patterns in tender folders."""

    def __init__(self, base_path: str, tenders_dir: str = "tenders", documents_file: str = "documents.json"):
        """
        Initialize DocumentFinder.
        
        Args:
            base_path: Base path where tenders directory is located
            tenders_dir: Name of the tenders directory (relative to base_path)
            documents_file: Name of the documents JSON file in each tender folder
        """
        self.base_path = base_path
        self.tenders_dir = tenders_dir
        self.documents_file = documents_file
        self.tenders_path = os.path.join(self.base_path, self.tenders_dir)

    def extract_file_names(self) -> List[Tuple[str, str]]:
        """
        Extract file names from all documents.json files in tender folders.
        
        Returns:
            List of tuples (file_name, folder_path) for all documents
        """
        file_data = []
        if not os.path.exists(self.tenders_path):
            print(f"Tenders directory not found: {self.tenders_path}")
            return file_data
            
        for tender_folder in tqdm(os.listdir(self.tenders_path), desc="Processing tenders"):
            tender_folder_path = os.path.join(self.tenders_path, tender_folder)
            if os.path.isdir(tender_folder_path):
                documents_file_path = os.path.join(tender_folder_path, self.documents_file)
                if os.path.exists(documents_file_path):
                    with open(documents_file_path, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            for document in data:
                                if "fileName" in document and isinstance(document["fileName"], str):
                                    file_data.append((document["fileName"], tender_folder_path))
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON from {documents_file_path}")
        return file_data

    def find_matching_files(self, file_data: Iterable[Tuple[str, str]], pattern_name: str = "kosztorys") -> List[Path]:
        """
        Find files matching a specific pattern.
        
        Args:
            file_data: Iterable of (file_name, folder_path) tuples
            pattern_name: Name of the pattern to use for matching
            
        Returns:
            Sorted list of Path objects for matching files
        """
        pattern = get_pattern(pattern_name)
        matching_files = set()

        for file_name, folder_path in file_data:
            if not file_name or not folder_path:
                continue
            if pattern.search(file_name):
                matching_files.add(Path(folder_path) / Path(file_name))

        return sorted(matching_files)

    def find_kosztorys_files(self, file_data: Iterable[Tuple[str, str]]) -> List[Path]:
        """
        Find files containing 'kosztorys' pattern (backward compatibility method).
        
        Args:
            file_data: Iterable of (file_name, folder_path) tuples
            
        Returns:
            Sorted list of Path objects for matching files
        """
        return self.find_matching_files(file_data, pattern_name="kosztorys")

