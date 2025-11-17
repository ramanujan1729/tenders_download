"""High-level service for downloading tender documents."""
from typing import Iterable, List, Dict, Any, Optional

from src.api.document_fetcher import DocumentFetcher
from src.storage.document_downloader import DocumentDownloader
from src.storage.file_manager import FileManager
from src.utils.logger import get_logger


logger = get_logger(__name__)


class DocumentDownloadService:
    """Service orchestrating document metadata retrieval and file downloads."""

    def __init__(
        self,
        document_fetcher: DocumentFetcher,
        document_downloader: DocumentDownloader,
        file_manager: FileManager,
    ):
        self.document_fetcher = document_fetcher
        self.document_downloader = document_downloader
        self.file_manager = file_manager

    def download_for_tender(
        self,
        tender_id: str,
        overwrite: bool = False,
        save_metadata: bool = True,
        use_cached_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Download documents for a single tender ID."""
        summary: Dict[str, Any] = {
            "tender_id": tender_id,
            "documents_found": 0,
            "documents_downloaded": 0,
            "status": "pending",
        }

        try:
            documents: Optional[List[Dict[str, Any]]] = None

            if use_cached_metadata:
                try:
                    documents = self.file_manager.load_documents_json(tender_id)
                    logger.debug("Loaded cached documents.json for tender %s", tender_id)
                except FileNotFoundError:
                    documents = None

            if documents is None:
                documents = self.document_fetcher.fetch_documents(tender_id)

            if not documents:
                self._write_no_attachments_marker(tender_id)
                summary["status"] = "no_documents"
                logger.info("No documents returned for tender %s", tender_id)
                return summary

            summary["documents_found"] = len(documents)

            if save_metadata:
                self.file_manager.save_documents_json(tender_id, documents)

            downloaded_paths = self.document_downloader.download_documents_for_tender(
                tender_id,
                documents,
                overwrite=overwrite,
            )
            summary["documents_downloaded"] = len(downloaded_paths)
            summary["status"] = "completed"
            logger.info(
                "Downloaded %s/%s documents for tender %s",
                summary["documents_downloaded"],
                summary["documents_found"],
                tender_id,
            )
            return summary

        except Exception as exc:  # pylint: disable=broad-except
            summary["status"] = "error"
            summary["error"] = str(exc)
            logger.exception("Error downloading documents for tender %s", tender_id)
            return summary

    def download_document_info(
        self,
        tender_id: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetch document metadata for a tender and write documents.json without downloading files.
        """
        summary = {
            "tender_id": tender_id,
            "documents_found": 0,
            "status": "pending",
        }

        try:
            if not overwrite:
                try:
                    self.file_manager.load_documents_json(tender_id)
                    summary["status"] = "skipped_existing"
                    return summary
                except FileNotFoundError:
                    pass

            documents = self.document_fetcher.fetch_documents(tender_id)
            if not documents:
                self._write_no_attachments_marker(tender_id)
                summary["status"] = "no_documents"
                return summary

            self.file_manager.save_documents_json(tender_id, documents)
            summary["documents_found"] = len(documents)
            summary["status"] = "completed"
            return summary

        except Exception as exc:  # pylint: disable=broad-except
            summary["status"] = "error"
            summary["error"] = str(exc)
            logger.exception("Error fetching metadata for tender %s", tender_id)
            return summary

    def download_for_batch(
        self,
        tender_ids: Iterable[str],
        overwrite: bool = False,
        use_cached_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """Download documents for a batch of tender IDs."""
        results: List[Dict[str, Any]] = []
        for tender_id in tender_ids:
            if not tender_id:
                continue
            results.append(
                self.download_for_tender(
                    tender_id,
                    overwrite=overwrite,
                    use_cached_metadata=use_cached_metadata,
                )
            )
        return results

    def discover_local_tender_ids(self, pattern: str = "*") -> List[str]:
        """Return tender IDs available locally, matching an optional glob pattern."""
        return self.file_manager.list_tender_ids(pattern)

    def download_for_existing_tenders(
        self,
        pattern: str = "*",
        overwrite: bool = False,
        use_cached_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """Download documents for all locally stored tenders matching pattern."""
        tender_ids = self.discover_local_tender_ids(pattern)
        if not tender_ids:
            logger.warning(
                "No local tender folders found in %s using pattern '%s'",
                self.file_manager.tenders_path,
                pattern,
            )
            return []
        logger.info(
            "Discovered %s local tenders (pattern '%s')",
            len(tender_ids),
            pattern,
        )
        return self.download_for_batch(
            tender_ids,
            overwrite=overwrite,
            use_cached_metadata=use_cached_metadata,
        )

    def _write_no_attachments_marker(self, tender_id: str) -> None:
        """Create a no_attachments marker file inside the tender folder."""
        tender_folder = self.file_manager.create_tender_folder(tender_id)
        marker_path = tender_folder / "no_attachments"
        marker_path.touch(exist_ok=True)

