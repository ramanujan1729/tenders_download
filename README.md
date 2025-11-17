# Tender Analysis Project

A Python project for fetching, processing, and analyzing tender data from public procurement APIs.

## Project Structure

```
TenderParser/
├── src/                  # Source code modules (api, storage, filtering, services, utils)
├── scripts/              # Executable scripts / CLI tools
├── notebooks/            # Exploratory notebooks and client reports
├── data/                 # Managed data folders (configured via config.yaml)
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add any API authentication variables the EZamowienia API requires:
   ```bash
   cp .env.example .env
   ```

3. Configure `config.yaml`:
   - `api.base_url` – should remain `https://ezamowienia.gov.pl/mp-readmodels`, matching the official Swagger definitions.[^swagger]
   - `api.endpoints` – relative paths/params from the Swagger spec for tender listings, document metadata (`documents` + `documents_tender_param`), and direct downloads.
   - `paths.*` – Output folders for per-tender data, attachments, raw tender dumps, and reports.
   - `tender_fetch` – Provinces, pagination, delays, and filters used by `download_tenders.py`.
   - `filtering` – Regex patterns and output filenames for `filter_documents.py`.

## End-to-End Workflow

1. **Fetch tender listings per province**
   ```bash
   python scripts/download_tenders.py
   ```
   - Reads province list, pagination, and filters from `config.yaml`.
   - Builds URLs like `https://ezamowienia.gov.pl/mp-readmodels/api/Search/SearchTenders?organizationProvince=łódzkie&...` automatically based on province names.[^lodzkie]
   - Saves province-level JSON/JSONL dumps under `paths.raw_tenders_dir`.
   - Creates/updates per-tender folders under `paths.tenders_dir` and writes `tender.json`.
   - Useful flags: `--province mazowieckie`, `--start-page 1`, `--end-page 25`, `--get-all`, `--use-filters`.

2. **Download document metadata + attachments**
   ```bash
   # For all locally stored tenders (auto-discovery)
   python scripts/download_documents.py --auto

   # For explicit tenders
   python scripts/download_documents.py --tender-id ocds-123 --tender-id ocds-456

   # From file list (one ID per line)
   python scripts/download_documents.py --tender-ids-file ids.txt
   ```
   - Uses the new `DocumentDownloadService`, saving `documents.json` and all attachments into each tender folder (default subdir `attachments`).

3. **Filter documents for “kosztorys” (or any pattern)**
- **Fetch single tender details**
  ```bash
  python scripts/fetch_tender_details.py --tender-id ocds-148610-0a1d5e67-f33f-11ee-ac52-ee29f86ffd4f
  python scripts/fetch_tender_details.py --tender-ids-file ids.txt
  ```
  - Uses the `api.endpoints.tender_details` endpoint (defaults to `/api/Search/GetTender`) and saves/upserts `tender.json` per ID.

   ```bash
   python scripts/filter_documents.py            # default pattern 'kosztorys'
   python scripts/filter_documents.py custom     # use pattern name defined in filtering.patterns
   ```
   - Outputs the matched file paths to `paths.output_dir/filter_documents.txt` (configurable).

4. **Analyse / report**
   - `notebooks/analysis/tender_analysis.ipynb` – general analysis playground.
   - `notebooks/reports/client_reports.ipynb` – client-facing summaries.

## Scripts Overview

- `scripts/download_tenders.py` – province-based harvesting with pagination, filtering, statistics, and per-tender persistence.
- `scripts/download_documents.py` – flexible downloader (single ID, batch IDs, auto-glob) backed by the service layer.
- `scripts/filter_documents.py` – re-usable filtering tool that consumes the stored `documents.json`.
- `scripts/fetch_tenders.py` – minimal sample using `src/api/tender_fetcher.py` for category-based fetches (keep for experimentation).
- `scripts/fetch_tender_details.py` – grab tender details for explicitly provided IDs (single or batch).

Each script exposes `--help` for the full list of CLI options.

## Modules

- **api/**: API interaction modules for fetching tenders and documents
- **services/**: Higher-level orchestration (e.g., `DocumentDownloadService`)
- **storage/**: File management and document downloading
- **filtering/**: Document filtering logic
- **utils/**: Configuration loading and logging utilities

[^swagger]: https://ezamowienia.gov.pl/mp-readmodels/swagger/index.html
[^lodzkie]: https://ezamowienia.gov.pl/mp-readmodels/api/Search/SearchTenders?organizationProvince=%C5%82%C3%B3dzkie&SortingColumnName=InitiationDate&SortingDirection=DESC
