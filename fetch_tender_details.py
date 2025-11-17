#!/usr/bin/env python3
"""Fetch detailed tender info for specific IDs."""

import argparse
import sys
from pathlib import Path
from typing import List
from tqdm import tqdm
# Ensure src is importable
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.client import APIClient
from src.api.tender_details_fetcher import TenderDetailsFetcher
from src.storage.file_manager import FileManager
from src.utils.config_loader import (
    load_config,
    load_env_vars,
    get_api_config,
    get_paths_config,
)
from src.utils.logger import setup_logger


logger = setup_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch tender details for specific IDs and persist tender.json files."
    )
    parser.add_argument(
        "--tender-id",
        action="append",
        dest="tender_ids",
        help="Tender ID to fetch. Can be provided multiple times or as comma-separated lists.",
    )
    parser.add_argument(
        "--tender-ids-file",
        type=str,
        help="Path to a text file containing tender IDs (one per line).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing tender.json files.",
    )
    return parser.parse_args()


def expand_tender_ids(args: argparse.Namespace) -> List[str]:
    tender_ids: List[str] = []

    if args.tender_ids:
        for entry in args.tender_ids:
            if not entry:
                continue
            tender_ids.extend(tid.strip() for tid in entry.split(",") if tid.strip())

    if args.tender_ids_file:
        path = Path(args.tender_ids_file)
        if not path.exists():
            raise FileNotFoundError(f"Tender ID file not found: {path}")
        with open(path, "r", encoding="utf-8") as file:
            tender_ids.extend(line.strip() for line in file if line.strip())

    # Deduplicate preserving order
    seen = set()
    ordered: List[str] = []
    for tender_id in tender_ids:
        if tender_id not in seen:
            seen.add(tender_id)
            ordered.append(tender_id)
    return ordered


def main():
    args = parse_args()
    tender_ids = expand_tender_ids(args)
    if not tender_ids:
        logger.error("No tender IDs provided. Use --tender-id or --tender-ids-file.")
        sys.exit(1)

    load_env_vars()
    config = load_config()
    api_cfg = get_api_config(config)
    paths_cfg = get_paths_config(config)

    api_client = APIClient(
        base_url=api_cfg.get("base_url", ""),
        rate_limit=api_cfg.get("rate_limit", 10),
        timeout=api_cfg.get("timeout", 30),
    )

    details_fetcher = TenderDetailsFetcher(
        api_client=api_client,
        details_endpoint=api_cfg.get("endpoints", {}).get(
            "tender_details", "/api/Search/GetTender"
        ),
        tender_param_name=api_cfg.get("endpoints", {}).get(
            "tender_details_tender_param", "tenderId"
        ),
    )

    file_manager = FileManager(
        base_path=str(project_root),
        tenders_dir=paths_cfg.get("tenders_dir", "data/tenders"),
    )

    processed = 0
    failures = 0

    for tender_id in tqdm(tender_ids, desc="Fetching tender details"):
        logger.info("Fetching tender %s", tender_id)

        if not args.overwrite and file_manager.tender_folder_exists(tender_id):
            try:
                file_manager.load_tender_json(tender_id)
                logger.info("Tender %s already exists. Skipping (use --overwrite to refresh).", tender_id)
                continue
            except FileNotFoundError:
                pass

        tender = details_fetcher.fetch_tender(tender_id)
        if not tender:
            failures += 1
            continue

        file_manager.save_tender_json(tender_id, tender)
        processed += 1
        logger.info("Saved tender.json for %s", tender_id)

    logger.info("Tender detail fetch complete. Saved: %s | Failures: %s", processed, failures)


if __name__ == "__main__":
    main()

