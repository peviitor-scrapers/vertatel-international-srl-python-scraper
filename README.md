# job_seeker_ro_spider — VERTATEL INTERNATIONAL S.R.L. Scraper

Lightweight scraper for VERTATEL INTERNATIONAL S.R.L. jobs (CIF `37633940`).
It collects postings from ANOFM and jobRapid and publishes them to
[peviitor.ro](https://peviitor.ro) through the Peviitor v1 API.

## Sources

- **ANOFM** — `https://mediere.anofm.ro` (primary, filtered by CIF)
- **jobRapid** — `https://www.jobrapid.ro/companie/vertatel-international-227507.html` (secondary, filtered by company name)

## Run

```bash
python3 -m pip install -r requirements.txt
python3 -m scraper.index
```

The scraper validates the company via ANAF, upserts the company core, collects
ANOFM and jobRapid jobs, upserts them to Solr through the Peviitor API, and
removes stale URLs from the two tracked sources.

## Structure

```
scraper/
  index.py        # scrape + upsert workflow
  api.py          # Peviitor v1 API client
  anaf.py         # ANAF validation + ANOFM search
  jobrapid.py     # jobRapid search + JSON-LD parsing
  company.py      # config loader
  config/
    company.json  # company identity (single source of truth)
    scraper.json  # API config
.github/workflows/job-seeker-ro-spider.yml
```

## License

Copyright (c) 2026 Alexandra Ifrim

Licensed under the [MIT License](LICENSE).
