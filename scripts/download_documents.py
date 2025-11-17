#!/usr/bin/env python3
"""Flexible document download utility."""

import argparse
import sys
from pathlib import Path
from typing import List

# Ensure src is on path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.client import APIClient
from src.api.document_fetcher import DocumentFetcher
from src.services.document_service import DocumentDownloadService
from src.storage.document_downloader import DocumentDownloader
from src.storage.file_manager import FileManager
from src.utils.config_loader import (
    get_api_config,
    get_paths_config,
    load_config,
    load_env_vars,
)
from src.utils.logger import setup_logger


logger = setup_logger()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Download tender documents via API using several modes."
    )
    parser.add_argument(
        "--tender-id",
        action="append",
        dest="tender_ids",
        help="Tender ID to download (can be provided multiple times or as comma-separated lists).",
    )
    parser.add_argument(
        "--tender-ids-file",
        type=str,
        help="Path to a text file containing tender IDs (one per line).",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically detect tender IDs by globbing folders inside the tenders directory.",
    )
    parser.add_argument(
        "--glob-pattern",
        type=str,
        default="*",
        help="Glob pattern applied when --auto is used (default: '*').",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files instead of skipping them.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only fetch documents.json metadata (no attachment downloads).",
    )
    parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Always call the API even if documents.json already exists.",
    )
    args = parser.parse_args()

    if not args.auto and not args.tender_ids and not args.tender_ids_file:
        parser.error(
            "You must specify at least one mode: --tender-id, --tender-ids-file, or --auto."
        )
    return args


def expand_tender_ids(args: argparse.Namespace) -> List[str]:
    """Collect tender IDs from CLI flags."""
    tender_ids: List[str] = []

    if args.tender_ids:
        for entry in args.tender_ids:
            if not entry:
                continue
            tender_ids.extend(
                tid.strip() for tid in entry.split(",") if tid.strip()
            )

    if args.tender_ids_file:
        path = Path(args.tender_ids_file)
        if not path.exists():
            raise FileNotFoundError(f"Tender ID file not found: {path}")
        with open(path, "r", encoding="utf-8") as file:
            tender_ids.extend(line.strip() for line in file if line.strip())

    # Deduplicate while preserving order
    seen = set()
    unique_ids: List[str] = []
    for tender_id in tender_ids:
        if tender_id not in seen:
            seen.add(tender_id)
            unique_ids.append(tender_id)
    return unique_ids


def main():
    """Entry point."""
    args = parse_args()

    load_env_vars()
    config = load_config()
    api_config = get_api_config(config)
    paths_config = get_paths_config(config)

    api_client = APIClient(
        base_url=api_config.get("base_url", ""),
        rate_limit=api_config.get("rate_limit", 10),
        timeout=api_config.get("timeout", 30),
    )

    document_fetcher = DocumentFetcher(
        api_client=api_client,
        documents_endpoint=api_config.get("endpoints", {}).get(
            "documents", "/api/tenders/{tenderId}/documents"
        ),
        tender_param_name=api_config.get("endpoints", {}).get(
            "documents_tender_param", "tenderId"
        ),
    )

    file_manager = FileManager(
        base_path=str(project_root),
        tenders_dir=paths_config.get("tenders_dir", "data/tenders"),
    )

    document_downloader = DocumentDownloader(
        api_client=api_client,
        file_manager=file_manager,
        attachments_subdir=paths_config.get("attachments_subdir"),
        download_endpoint_template=api_config.get("endpoints", {}).get(
            "download", None
        ),
    )

    service = DocumentDownloadService(
        document_fetcher=document_fetcher,
        document_downloader=document_downloader,
        file_manager=file_manager,
    )

    results = []
    if args.metadata_only:
        target_ids = []
        if args.auto:
            logger.info(
                "Metadata-only auto mode: discovering tender folders under %s (pattern '%s').",
                file_manager.tenders_path,
                args.glob_pattern,
            )
            target_ids = service.discover_local_tender_ids(args.glob_pattern)
        else:
            target_ids = expand_tender_ids(args)

        if not target_ids:
            logger.warning("No tender IDs provided or discovered for metadata fetch.")
            return

        for tender_id in target_ids:
            result = service.download_document_info(
                tender_id,
                overwrite=args.overwrite or args.ignore_cache,
            )
            results.append(result)

    else:
        if args.auto:
            logger.info(
                "Auto mode enabled. Discovering tender folders under %s (pattern '%s').",
                file_manager.tenders_path,
                args.glob_pattern,
            )
            results = service.download_for_existing_tenders(
                pattern=args.glob_pattern,
                overwrite=args.overwrite,
                use_cached_metadata=not args.ignore_cache,
            )
        else:
            tender_ids = expand_tender_ids(args)
            if not tender_ids:
                logger.warning("No tender IDs resolved from provided options.")
                return
            logger.info("Downloading documents for %s tender(s).", len(tender_ids))
            results = service.download_for_batch(
                tender_ids,
                overwrite=args.overwrite,
                use_cached_metadata=not args.ignore_cache,
            )

    completed = sum(1 for item in results if item.get("status") == "completed")
    errors = [item for item in results if item.get("status") == "error"]
    no_docs = sum(1 for item in results if item.get("status") == "no_documents")

    logger.info("Document download summary:")
    logger.info("  Completed: %s", completed)
    logger.info("  No documents: %s", no_docs)
    logger.info("  Errors: %s", len(errors))
    if errors:
        for item in errors:
            logger.error(
                "Tender %s failed: %s",
                item.get("tender_id"),
                item.get("error"),
            )


if __name__ == "__main__":
    main()

