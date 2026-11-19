# Instructions

## Project Purpose

This scraper extracts job listings for **VERTATEL INTERNATIONAL S.R.L.** (CIF `37633940`)
from **ANOFM** (`https://mediere.anofm.ro`), **jobRapid.ro** and **eJobs.ro**, and
publishes them to peviitor.ro via the v1 API (`https://api.peviitor.ro/v1`).

ANOFM is the primary source (filtered by CIF); jobRapid and eJobs are secondary
sources matched by company name / company page.

Target: `https://mediere.anofm.ro/api/entity/vw_public_job_posting`
(POST, filtered by `employer_tax_code=37633940`).

## Model Schemas

The job and company models are defined in:
- `ai/JOB_MODEL.md` — job model schema
- `ai/COMPANY_MODEL.md` — company model schema

## Important

These models are **dynamic** and can change over time. They are based on
the official Peviitor Core schemas which may be updated.

## How to Keep Models Updated

When working on this scraper:

1. **Check for updates** in the Peviitor Core repository:
   - Repository: https://github.com/peviitor-ro/peviitor_core
   - Main file: README.md (contains Job and Company model schemas)

2. **When to update**:
   - Before starting new development work
   - If field requirements or validations have changed
   - If new fields have been added

3. **How to update**:
   - Fetch the latest README.md from peviitor_core main branch
   - Compare with current `ai/JOB_MODEL.md` and `ai/COMPANY_MODEL.md`
   - Update local files if there are differences
   - Update `scraper/index.py` mapping logic if field requirements changed

## Technologies

- **Python 3.12** — HTTP requests (`requests`) to ANOFM, jobRapid.ro, eJobs.ro and the Peviitor API
- **Peviitor v1 API** — data storage and retrieval (`api.peviitor.ro/v1`)
- **pytest** — unit / integration / e2e / consistency tests

## Workflow Steps

1. **Start with brand** — `Vertatel International`
2. **Search in CUIFirma** — resolve the brand to a CIF
3. **Get company details from CUIScan** — fetch the legal name and address by CIF
4. **Validate with Peviitor** — verify company exists in peviitor
5. **Check existing jobs** — query peviitor v1 API by CIF to see what jobs exist
6. **Scrape new jobs** — query ANOFM by CIF, jobRapid.ro by company name and the eJobs.ro company page
7. **Transform for API** — validate and fix job data:
   - location: only Romanian cities allowed (fallback `["România"]`)
   - workmode: `remote` / `on-site` / `hybrid`
   - company: uppercase
8. **Check live URLs** — GET-check each job, drop HTTP and soft-404s; abort before any write if nothing survives
9. **Upsert to API** — import/update jobs via peviitor v1 API
10. **Verify URLs** — check existing job URLs from all three sources, delete stale ones

## Running the Scraper

```bash
# Run the full scraper workflow (single command)
python3 -m scraper.index

# Get company details from CUIScan by CIF
python3 -c "from scraper.anaf import get_company_from_anaf; print(get_company_from_anaf('37633940'))"
```

> **Important**: Stale deletion is scoped to this scraper's three job URL
> prefixes (ANOFM, jobRapid.ro and eJobs.ro), so jobs published by other
> scrapers under the shared CIF are preserved.

## Full Workflow (automatic)

When running `python3 -m scraper.index`, the following steps happen automatically:

1. **Check existing jobs count** — query peviitor v1 API by CIF (read-only)
2. **Validate company via CUIScan/CUIFirma** — resolve legal name and address, refresh the company cache
3. **Scrape jobs** — query all three sources, deduplicating URLs
4. **Transform for API** — fix locations (only Romanian cities), normalize workmode
5. **Check live URLs** — bounded GET checks; soft-404 pages are dropped; canary aborts before any write if no jobs remain
6. **Upsert company core** — with `scraperFile` pointing to our workflow
7. **Generate files** — `scraper/jobs.json`, `docs/jobs.md`, `docs/company.json`
8. **Upsert to API** — add/update jobs (API handles duplicates by URL)
9. **Delete stale jobs** — remove jobs no longer published by this scraper
10. **Show Summary** — log job counts

## Workflow Flowchart

```
scraper/config/company.json (single source of truth: CIF, brand, URLs)
    │
    ▼
scraper/index.py
    │
    ▼
query_solr(CIF) - check existing jobs (peviitor v1 API)
    │
    ▼
company.py / anaf.py (resolve company identity)
    ├── CUIScan ──► get company name + address by CIF
    ├── CUIFirma ──► brand search / CIF resolution
    ├── anaf_cache.json ──► fallback if APIs fail
    │
    ▼
search_anofm / search_jobrapid / search_ejobs - URLs deduplicated across sources
    │
    ▼
transform_jobs_for_solr() + drop_dead_urls()
    ├── Filter: keep only Romanian locations
    ├── Fallback: "România" for unknown
    ├── Normalize: uppercase company
    └── GET check: drop HTTP errors and soft-404s (max 5 in flight)
    │
    ▼ (canary: abort before any write if no live jobs)
upsert_jobs() - API handles duplicate by URL
    │
    ▼
delete stale job URLs from our three sources
    │
    ▼
generate_jobs_markdown() → docs/jobs.md
    └── committed to repo by CI
```

## File Responsibilities

See `ai/files.md` for the full file map. Key files:

| File | Role |
|------|------|
| `scraper/config/company.json` | **Single source of truth** for company identity (CIF, brand, URLs, `scraperFile`) |
| `scraper/config/scraper.json` | API config — `apiBase`, `apiPath`, `jobDetailsPrefix` |
| `scraper/index.py` | Main entry point — validate company → scrape ANOFM/jobRapid/eJobs → transform → upsert → delete stale → generate `docs/jobs.md` |
| `scraper/api.py` | Peviitor v1 API client — query/upsert/delete jobs + company |
| `scraper/anaf.py` | Company data module — CUIScan (details by CIF) + CUIFirma (brand search) + cache fallback, plus `search_anofm` |
| `scraper/job_validator.py` | Shared URL validation primitives (head/content/browser) |
| `scraper/validate_jobs.py` | CLI deep validator (`--mode head|content|browser`, `--delete`) |
| `scraper/markdown_generator.py` | Generates `docs/jobs.md` |
| `tests/unit/*` | Unit tests for index/api/anaf/config/job_validator |
| `tests/integration/test_company_real.py` | Live integration — CUIScan/CUIFirma + ANOFM + peviitor API |
| `tests/e2e/test_scraper.py` | E2E — live ANOFM scrape |
| `tests/consistency/test_repo.py` | Repo identity, root files, workflow naming |

## API Endpoints

- **ANOFM search**: `https://mediere.anofm.ro/api/entity/vw_public_job_posting` — POST by `employer_tax_code`
- **ANOFM job URL**: `https://mediere.anofm.ro/app/module/mediere/job/<id>`
- **CUIScan**: `https://cuiscan.ro/api.php?action=company&cui=CIF` — company details by CIF
- **CUIFirma search**: `https://www.cuifirma.ro/api/search?q=BRAND` — search companies by brand
- **Peviitor v1 API**: `https://api.peviitor.ro/v1/` — all job and company operations go through this API (no direct Solr)

## Rate Limiting & Politeness

The scraper stays polite without fixed per-page sleeps:

| Setting | Value | Where |
|---------|-------|-------|
| Request timeout | 10 s | `scraper/api.py`, `scraper/anaf.py` — `TIMEOUT` |
| Company data | CUIScan / CUIFirma, no retries | `scraper/anaf.py` — cache in `scraper/anaf_cache.json` |
| Concurrency | max 5 in flight | `scraper/api.py` / `scraper/index.py` — `map_with_concurrency` for URL checks and deletes |
| API reads | 3 attempts with backoff on transient failures | `scraper/api.py` — `_request_with_retry` |
| User-Agent | `job_seeker_ro_spider` | Identifies the scraper in server logs |
| Extra requests | One GET per job before upload, reused by validators | `scraper/index.py` / `scraper/validate_jobs.py` |

Respect `robots.txt` when present; do not crawl aggressively.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_REPOSITORY` | Used by consistency tests — format `owner/repo` |
| `GITHUB_TOKEN` | GitHub API token for consistency tests |

`.env` files are not used — all API access goes through `api.peviitor.ro`
and needs no credentials. Never commit secrets or `.env` files.

## Standalone Commands

```bash
# Full scrape + publish
python3 -m scraper.index

# Query jobs in peviitor by CIF (read-only verify; add --delete to remove
# invalid job URLs — deletion is scoped to our three source prefixes, so jobs
# from other scrapers under a shared CIF are never touched)
python3 -m scraper.api 37633940

# Validate job URLs from peviitor by CIF (head/content/browser)
python3 -m scraper.validate_jobs 37633940 --mode head
python3 -m scraper.validate_jobs 37633940 --mode content --dry-run
python3 -m scraper.validate_jobs 37633940 --mode content --delete
```

## Testing

This project requires multiple levels of testing:

1. **Unit Tests** — individual modules in isolation (`tests/unit`)
2. **Integration Tests** — live APIs, skip-safe (`tests/integration`)
3. **E2E Tests** — live ANOFM scrape, skip-safe (`tests/e2e`)
4. **Consistency Tests** — repo identity and conventions (`tests/consistency`)

Run tests:

```bash
python3 -m pytest tests/unit tests/consistency   # offline
python3 -m pytest tests/integration              # live APIs (skip-safe)
python3 -m pytest tests/e2e                      # live source checks (skip-safe)
python3 -m pytest                                # everything
```

## Temporary Files

All temporary/scratch files go in `tmp/` inside the project root — never
outside the project. `tmp/` is in `.gitignore` and will not be committed.

## GitHub Actions

- `job-seeker-ro-spider.yml` — scheduled scrape (cron) + manual dispatch.
- `automation-testing.yml` — runs unit/consistency tests on every push.
- `job-deep-validate.yml` — deep job-URL validation on demand.
- `job-recovery-from-disaster.yml` — rebuild from backup on demand.
- `automation-template-sync-check.yml` — weekly template-sync check.
