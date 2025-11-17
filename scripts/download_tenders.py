#!/usr/bin/env python3
"""Fetch tenders per province and store both raw dumps and tender.json files."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests  # type: ignore[import]

# Ensure src is importable
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.file_manager import FileManager
from src.utils.config_loader import load_config, load_env_vars, get_paths_config
from src.utils.logger import setup_logger

logger = setup_logger()


def parse_args() -> argparse.Namespace:
    """CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Download tender listings per province.")
    parser.add_argument(
        "--province",
        action="append",
        help="Province name to fetch (default: all configured). Can be provided multiple times.",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        help="Override pagination start page.",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        help="Override pagination end page (inclusive).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        help="Override pagination page size.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        help="Override delay between page requests (seconds).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Override request timeout (seconds).",
    )
    parser.add_argument(
        "--get-all",
        action="store_true",
        help="Ignore filters and fetch everything.",
    )
    parser.add_argument(
        "--use-filters",
        action="store_true",
        help="Force usage of filters even if config default is get_all.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Override raw tenders output directory.",
    )
    parser.add_argument(
        "--max-provinces",
        type=int,
        help="Limit number of provinces processed (useful for quick tests).",
    )
    return parser.parse_args()


def load_settings(config: Dict[str, any], args: argparse.Namespace) -> Tuple[Dict, Dict, List[str], str]:
    """Pull tender-fetch settings from config and apply CLI overrides."""
    fetch_cfg = config.get("tender_fetch", {})
    pagination_cfg = fetch_cfg.get("pagination", {})

    pagination = {
        "start_page": args.start_page or pagination_cfg.get("start_page", 1),
        "end_page": args.end_page if args.end_page is not None else pagination_cfg.get("end_page"),
        "page_size": args.page_size or pagination_cfg.get("page_size", 50),
        "delay_seconds": args.delay or pagination_cfg.get("delay_seconds", 0.5),
        "province_pause_seconds": pagination_cfg.get("province_pause_seconds", 2.5),
        "request_timeout": args.timeout or pagination_cfg.get("request_timeout", 30),
        "sorting_column": pagination_cfg.get("sorting_column", "PublicationDate"),
        "sorting_direction": pagination_cfg.get("sorting_direction", "DESC"),
    }

    # Determine whether to use filters
    get_all_default = fetch_cfg.get("get_all", True)
    if args.get_all:
        get_all = True
    elif args.use_filters:
        get_all = False
    else:
        get_all = get_all_default

    filters = fetch_cfg.get("filters", {})

    provinces = fetch_cfg.get("provinces", [])
    if args.province:
        selected = set(name.lower() for name in args.province)
        provinces = [p for p in provinces if p.lower() in selected]
    if args.max_provinces and provinces:
        provinces = provinces[: args.max_provinces]

    return (
        {"get_all": get_all, "filters": filters},
        pagination,
        provinces,
        fetch_cfg.get("province_param", "organizationProvince"),
    )


def fetch_page(url: str, params: Dict[str, any], timeout: int) -> List[Dict]:
    """Execute a single page fetch."""
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Some endpoints may return {data: [...], total: X}
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
    logger.warning("Unexpected response format from %s: %s", url, type(data))
    return []


def fetch_tenders_for_province(
    province_name: str,
    search_url: str,
    province_param: str,
    fetch_settings: Dict[str, any],
    pagination: Dict[str, any],
) -> List[Dict]:
    """Fetch tenders for a single province."""
    base_params = {
        "PageSize": pagination["page_size"],
        "SortingColumnName": pagination.get("sorting_column", "PublicationDate"),
        "SortingDirection": pagination.get("sorting_direction", "DESC"),
    }

    if not fetch_settings["get_all"]:
        base_params.update(fetch_settings["filters"])

    all_tenders: List[Dict] = []
    page_number = pagination["start_page"]
    start_time = time.time()

    logger.info("Fetching province %s starting at page %s", province_name, page_number)

    while True:
        params = base_params.copy()
        params["PageNumber"] = page_number
        params[province_param] = province_name
        try:
            page_items = fetch_page(
                search_url,
                params=params,
                timeout=pagination["request_timeout"],
            )
        except requests.HTTPError as exc:
            logger.error("HTTP error for province %s page %s: %s", province_name, page_number, exc)
            break
        except requests.RequestException as exc:
            logger.error("Request error for province %s page %s: %s", province_name, page_number, exc)
            break

        if not page_items:
            logger.info("No results on page %s (province %s). Stopping.", page_number, province_name)
            break

        all_tenders.extend(page_items)
        logger.info(
            "Province %s page %s returned %s records (total so far: %s)",
            province_name,
            page_number,
            len(page_items),
            len(all_tenders),
        )

        if len(page_items) < pagination["page_size"]:
            logger.info(
                "Last page reached for province %s (returned %s < %s).",
                province_name,
                len(page_items),
                pagination["page_size"],
            )
            break

        if pagination["end_page"] and page_number >= pagination["end_page"]:
            logger.warning("Reached configured END_PAGE (%s) for province %s", pagination["end_page"], province_name)
            break

        page_number += 1
        time.sleep(pagination["delay_seconds"])

    elapsed = time.time() - start_time
    logger.info(
        "Province %s finished: %s records in %.1fs (%.1f rec/s)",
        province_name,
        len(all_tenders),
        elapsed,
        len(all_tenders) / elapsed if elapsed else 0,
    )

    return all_tenders


def save_province_outputs(
    province_name: str,
    tenders: List[Dict],
    raw_dir: Path,
) -> Tuple[Path, Path]:
    """Persist province-level JSON and JSON Lines dumps."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp_fragment = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = province_name.replace(" ", "_")
    json_path = raw_dir / f"tenders_{safe_name}_{timestamp_fragment}.json"
    jsonl_path = raw_dir / f"tenders_{safe_name}_{timestamp_fragment}.jsonl"

    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump(tenders, f_json, ensure_ascii=False, indent=2)

    with open(jsonl_path, "w", encoding="utf-8") as f_jsonl:
        for tender in tenders:
            f_jsonl.write(json.dumps(tender, ensure_ascii=False) + "\n")

    logger.info(
        "Saved province %s dumps: %s records -> %s / %s",
        province_name,
        len(tenders),
        json_path,
        jsonl_path,
    )
    return json_path, jsonl_path


def persist_individual_tenders(tenders: List[Dict], file_manager: FileManager) -> int:
    """Store each tender as tender.json using FileManager."""
    persisted = 0
    for tender in tenders:
        tender_id = tender.get("objectId") or tender.get("id")
        if not tender_id:
            continue
        file_manager.save_tender_json(tender_id, tender)
        persisted += 1
    logger.info("Stored %s per-tender files.", persisted)
    return persisted


def main():
    args = parse_args()
    load_env_vars()
    config = load_config()

    fetch_settings, pagination, provinces, province_param = load_settings(config, args)
    if not provinces:
        logger.error("No provinces configured or matched the selection.")
        sys.exit(1)

    api_cfg = config.get("api", {})
    search_endpoint = api_cfg.get("endpoints", {}).get("search_tenders")
    if not search_endpoint:
        logger.error("Missing api.endpoints.search_tenders in config.")
        sys.exit(1)
    base_url = api_cfg.get("base_url", "").rstrip("/")
    search_url = f"{base_url}{search_endpoint}"

    paths_cfg = get_paths_config(config)
    raw_dir = Path(args.output_dir or paths_cfg.get("raw_tenders_dir", "tender_data"))
    file_manager = FileManager(
        base_path=str(PROJECT_ROOT),
        tenders_dir=paths_cfg.get("tenders_dir", "data/tenders"),
    )

    logger.info(
        "Starting tender fetch at %s for %s province(s). get_all=%s",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        len(provinces),
        fetch_settings["get_all"],
    )

    total_records = 0
    total_persisted = 0

    for index, province_name in enumerate(provinces, start=1):
        logger.info(
            "[%s/%s] Province: %s (%s)",
            index,
            len(provinces),
            province_name,
            search_url,
        )
        tenders = fetch_tenders_for_province(
            province_name,
            search_url,
            province_param,
            fetch_settings,
            pagination,
        )
        if not tenders:
            logger.warning("No tenders returned for province %s.", province_name)
        else:
            save_province_outputs(province_name, tenders, raw_dir)
            total_records += len(tenders)
            total_persisted += persist_individual_tenders(tenders, file_manager)

        if pagination["province_pause_seconds"] > 0 and index < len(provinces):
            time.sleep(pagination["province_pause_seconds"])

    logger.info("Tender fetch complete. Total records: %s | Per-tender files stored: %s", total_records, total_persisted)


if __name__ == "__main__":
    main()

