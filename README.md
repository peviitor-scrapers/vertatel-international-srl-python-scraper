[![Oportunitati si Cariere](https://github.com/peviitor-scrapers/vertatel-international-srl-python-scraper/actions/workflows/job-seeker-ro-spider.yml/badge.svg)](https://github.com/peviitor-scrapers/vertatel-international-srl-python-scraper/actions/workflows/job-seeker-ro-spider.yml)
[![Automation Tests](https://github.com/peviitor-scrapers/vertatel-international-srl-python-scraper/actions/workflows/automation-testing.yml/badge.svg)](https://github.com/peviitor-scrapers/vertatel-international-srl-python-scraper/actions/workflows/automation-testing.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fpeviitor.ro&label=peviitor.ro)](https://peviitor.ro)
[![API](https://img.shields.io/website?url=https%3A%2F%2Fapi.peviitor.ro%2F&label=api.peviitor.ro)](https://api.peviitor.ro/)
[![GitHub Pages](https://img.shields.io/github/deployments/peviitor-scrapers/vertatel-international-srl-python-scraper/github-pages?label=GitHub%20Pages)](https://peviitor-scrapers.github.io/vertatel-international-srl-python-scraper/)

# job_seeker_ro_spider — VERTATEL INTERNATIONAL S.R.L. Scraper

**job_seeker_ro_spider** — a scraper for VERTATEL INTERNATIONAL S.R.L. jobs in Romania. It collects postings from ANOFM, jobRapid.ro and eJobs.ro and publishes them to [peviitor.ro](https://peviitor.ro) through the Peviitor v1 API.

> **Derived scraper.** This repository follows the Python scraper template used in the peviitor.ro ecosystem.

## Overview

The project automates the daily collection of VERTATEL INTERNATIONAL jobs in Romania, keeping the peviitor.ro board up to date with the latest career opportunities.

## Features

- Extracts jobs from ANOFM (`mediere.anofm.ro`) by CIF
- Extracts jobs from jobRapid.ro and from the eJobs.ro company page
- Deduplicates job URLs across all three sources before publishing
- Validates the company via CUIScan (legal name and address, by CIF) and CUIFirma (brand search)
- **Company cache** — does not hit the APIs on every scrape
- **Stale cache / config fallback** when CUIScan is unavailable
- Cross-validates against the Peviitor API
- **Live URL validation** — GET-checks every job with bounded concurrency and drops soft-404s
- **Canary** — aborts before any write when no live jobs remain
- Deletes stale jobs (present on peviitor.ro but not in the current scrape), scoped to this scraper's URL prefixes
- Stores to the Peviitor API (job core + company core)
- Generates `docs/jobs.md` automatically — accessible on GitHub Pages
- **Company identity in a single file** (`scraper/config/company.json`)
- GitHub Actions: daily scrape + automated testing (unit, integration, e2e, consistency)
- Identifies itself through the User-Agent: `job_seeker_ro_spider`

## Sources

- **ANOFM** — `https://mediere.anofm.ro/app/module/mediere/jobs` (filtered by CIF `37633940`)
- **jobRapid** — `https://www.jobrapid.ro/companie/vertatel-international-227507.html`
- **eJobs** — `https://www.ejobs.ro/company/sc-vertatel-international-srl/48117`

## Local setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests/unit tests/consistency   # offline checks
.venv/bin/python -m scraper.index                         # full scrape + publish
.venv/bin/python -m scraper.validate_jobs 37633940 --mode content --dry-run
```

## License

Copyright (c) 2026 Alexandra Ifrim

Licensed under the [MIT License](LICENSE).

## Managed By

This project is managed by [ASOCIATIA OPORTUNITATI SI CARIERE](https://oportunitatisicariere.ro) and used as a web scraper for the [peviitor.ro](https://peviitor.ro) job board project.

## Disclaimer

This scraper is designed for educational purposes and legitimate job data aggregation for the Romanian job market.
