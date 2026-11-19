# VERTATEL INTERNATIONAL S.R.L. — GitHub Pages

This folder is published by GitHub Pages. It shows the company's current
openings, read live from the peviitor API, plus the CI test reports.

- `index.html` — the dashboard. Reads `company.json` at runtime; the constants
  near the top of its `<script>` are the fallback if that file is missing.
- `company.json` — regenerated on every scrape by `scraper/index.py` (a copy of
  `scraper/config/company.json`).
- `jobs.md` — generated on every scrape (company info + all current jobs).
- `test-results/` — HTML reports pushed by CI; its `index.html` links to the
  pre-scrape unit/integration and post-scrape e2e reports.

Only `index.html` and this README are edited by hand. The generated files are
refreshed by `.github/workflows/job-seeker-ro-spider.yml` and
`.github/workflows/automation-testing.yml`.
