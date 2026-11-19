# Project Files

## Python Files — scraper/

| File | Description |
|------|-------------|
| `scraper/index.py` | Main scraper - full workflow: resolve company via CUIScan/CUIFirma → query ANOFM (by CIF), jobRapid.ro (by name) and eJobs.ro (company page), dedupe URLs → transform → GET-check live URLs (max 5 in flight, soft-404 aware, canary) → upsert to peviitor v1 API → delete stale → generate `docs/jobs.md`. Entry point: `python3 -m scraper.index` |
| `scraper/api.py` | Peviitor v1 API client - `query_solr`, `upsert_company`, `upsert_jobs`, `delete_job_by_url`, `map_with_concurrency`, `_request_with_retry` (no CIF-wide delete) |
| `scraper/anaf.py` | Company data module - CUIScan (details by CIF) + CUIFirma (brand search), cache fallback (`scraper/anaf_cache.json`), plus `search_anofm` (job postings by CIF) |
| `scraper/job_validator.py` | Shared validation primitives - `validate_by_head`, `validate_by_content`, `validate_by_browser`, `DEFAULT_EXPIRED_KEYWORDS`. Content check strips `<script>`/`<style>` |
| `scraper/validate_jobs.py` | CLI job URL validator (`--mode head|content|browser`, `--dry-run`, `--delete`) with bounded concurrency. Entry point: `python3 -m scraper.validate_jobs` |
| `scraper/markdown_generator.py` | Generates `docs/jobs.md` and `docs/company.json` |
| `scraper/company.py` | Resolves company identity via CUIScan/CUIFirma; company status is config-only and never gates scraping or deletes jobs |

## Config — scraper/config/

| File | Description |
|------|-------------|
| `scraper/config/company.json` | **Single source of truth for company identity** (`id`, `company`, `brand`, `location`, `website`, `career`, `scraperFile`). `scraperFile` must be the GitHub Actions workflow URL |
| `scraper/config/scraper.json` | API config - `apiBase`, `apiPath`, three job URL prefixes, `ejobsCompanyUrl` |

## Test Files — tests/

| File | Description |
|------|-------------|
| `tests/conftest.py` | Fixtures: config loaders, mocked API responses, lowered timeouts |
| `tests/unit/test_index.py` | Unit tests - `map_to_job_model`, `transform_jobs_for_solr`, URL dedupe, live-URL drop, canary, main |
| `tests/unit/test_api.py` | Unit tests - query/upsert/delete, retry/backoff, bounded concurrency |
| `tests/unit/test_anaf.py` | Unit tests - CUIScan fetch, CUIFirma search, cache fallback |
| `tests/unit/test_config.py` | Unit tests - company/scraper config shape |
| `tests/unit/test_job_validator.py` | Unit tests - head/content/browser validation |
| `tests/unit/test_validate_jobs.py` | Unit tests - CLI validation and prefix-scoped deletion |
| `tests/integration/test_company_real.py` | Live integration - CUIScan/CUIFirma + peviitor API (skip-safe) |
| `tests/e2e/test_scraper.py` | E2E - live ANOFM scrape (skip-safe) |
| `tests/consistency/test_repo.py` | Verifies repo is public, has the workflows, and required topics |

## Markdown Files — ai/

| File | Description |
|------|-------------|
| `ai/AGENTS.md` | Rules for AI agents working on this project |
| `ai/BRANCH.md` | Branch strategy |
| `ai/INSTRUCTIONS.md` | How to run the scraper, validate URLs, run tests |
| `ai/ISSUES.md` | Issue tracking rule (issue for every code change) + triage |
| `ai/MAINTENANCE.md` | Full maintenance workflow (issues, health summary, verification) |
| `ai/JOB_MODEL.md` | Job schema definition (peviitor) |
| `ai/COMPANY_MODEL.md` | Company schema definition (peviitor) |
| `ai/PUBLIC.md` | Public repo URLs |
| `ai/ROBOTS.md` | Scraping policy and polite-crawl rules |
| `ai/TOPICS.md` | Applied GitHub topics |
| `ai/UPDATE-REPO-ABOUT.md` | Repo description/website maintenance |
| `ai/VERIFY.md` | Step-by-step verification checklist |
| `ai/files.md` | This file - documents the role of each project file |

## Configuration / Infrastructure Files

| File | Description |
|------|-------------|
| `requirements.txt` | Python dependencies (requests, bs4, pytest) |
| `pytest.ini` | Pytest configuration |
| `.gitignore` | Ignores `.venv/`, `__pycache__/`, `scraper/jobs.json`, `scraper/anaf_cache.json`, `tmp/` |
| `CHANGELOG.md` | Version history and notable changes |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security policy and vulnerability reporting |
| `.github/workflows/job-seeker-ro-spider.yml` | Daily scraping workflow (scheduled + dispatch) |
| `.github/workflows/automation-testing.yml` | Runs unit/consistency tests on every push |
| `.github/workflows/job-deep-validate.yml` | Manual deep job-URL validation |
| `.github/workflows/job-recovery-from-disaster.yml` | Rebuild from backup on demand |
| `.github/workflows/automation-template-sync-check.yml` | Weekly template-sync check |

## Data Files

| File | Description |
|------|-------------|
| `scraper/jobs.json` | Scraped jobs cache (gitignored) |
| `scraper/anaf_cache.json` | CUIScan company cache (gitignored; not shared between CI runs) |
| `docs/jobs.md` | Scraped jobs in markdown (regenerated on each scrape, served on GitHub Pages) |
| `docs/company.json` | Static copy of `scraper/config/company.json` (regenerated) |
| `docs/index.html` | GitHub Pages site root (served from `docs/` on `main`, built automatically) |

## Notes

- All operations go through the peviitor v1 API — no direct Solr access.
- CIF `37633940` is shared with other peviitor scrapers; stale-deletion is
  scoped to the ANOFM, jobRapid.ro and eJobs.ro job prefixes only.
- `.env` is ignored and not used by the current code (all API access goes
  through `api.peviitor.ro`).
- Full workflow: resolve company (CUIScan/CUIFirma + Peviitor) → query three
  sources → dedupe → transform → GET-check live URLs → upsert → delete stale →
  generate `docs/jobs.md`.
