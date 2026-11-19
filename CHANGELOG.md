# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Ported all recent template fixes from `roumasport-nodejs-scraper` (#3):
  CUIScan/CUIFirma are now the only company-data sources; the retired
  `demoanaf.ro` endpoint is gone from code, tests, docs and CI.
- Company status no longer gates scraping or triggers CIF-wide job deletion;
  `status` remains a config value only (#3).
- Bounded-concurrency URL checks/deletions, API retry/backoff, live soft-404
  URL validation before upload, URL dedupe and canary, CI dependency caching
  and a rebase-and-retry loop for generated docs (#3).
- Synced `ai/*.md` and added `docs/README.md` to match the current scraper
  behavior and upstream schemas (#3).

## [1.0.0] - 2026-08-03

### Added
- Python scraper for **VERTATEL INTERNATIONAL S.R.L.** (CIF `37633940`), reading jobs from ANOFM (`mediere.anofm.ro`), jobRapid.ro and eJobs.ro.
- Publisher to peviitor v1 API: company upsert, job upload, stale-job delete.
- Company identity from CUIScan/CUIFirma with cache fallback.
- ANOFM job search mirroring the Node.js template.
- `validate_jobs.py` CLI for head/content URL validation.
- Unit, integration, e2e, and consistency tests.
- GitHub Actions workflows: `job-seeker-ro-spider`, `automation-testing`, deep-validate, recovery.
- GitHub Pages (`docs/`) with generated `jobs.md` and `company.json`.
- AI documentation under `ai/`.

### Fixed
- Location normalization: common spellings (`Bucuresti`, `Turda`, etc.) and case/diacritic variants are no longer dropped to `România`.
- Stale-job deletion is scoped to this scraper's ANOFM, jobRapid.ro and eJobs.ro job URLs, so jobs published by other peviitor scrapers under the same CIF are never removed.
- E2E `EXPECTED_MIN_JOBS` and integration tests reflect ANOFM and CIF `37633940`.
