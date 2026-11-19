# Robots.txt & scraping policy

Checked per derived company. If a source's `robots.txt` disallows the exact
paths this scraper reads, continuing live scraping needs an explicit owner
decision (site permission or a different source); this document records the
finding, it does not silently override it.

## What this scraper reads

| Source | Paths |
|--------|-------|
| ANOFM (primary) | `POST https://mediere.anofm.ro/api/entity/vw_public_job_posting` filtered by CIF; `https://mediere.anofm.ro/app/module/mediere/job/<id>` (referenced and GET-checked before upload) |
| jobRapid.ro | `POST https://www.jobrapid.ro/angajare` (company name) + detail pages under `https://www.jobrapid.ro/locuri-de-munca/` (GET-checked before upload) |
| eJobs.ro | company page `https://www.ejobs.ro/company/sc-vertatel-international-srl/48117` + job pages under `https://www.ejobs.ro/user/locuri-de-munca/` (GET-checked before upload) |
| Company data | `https://cuiscan.ro/api.php?action=company&cui=CIF`, `https://www.cuifirma.ro/api/search?q=BRAND` |
| Peviitor API | `https://api.peviitor.ro/v1/*` |

No robots.txt disallow has been recorded for the sources above. Recheck before
adding or changing a source.

## Politeness (current behavior)

| Measure | Value | Where |
|---------|-------|-------|
| Requests | max 5 in flight | `scraper/api.py` / `scraper/index.py` — `map_with_concurrency` |
| Delay between pages | none (the old fixed sleep was removed) | `scraper/index.py` |
| Timeout | 10 s | `scraper/api.py`, `scraper/anaf.py` |
| API reads | 3 attempts with backoff for transient failures | `scraper/api.py` |
| User-Agent | `job_seeker_ro_spider` | identifies the scraper in server logs |
| Volume | one search per source + one GET per unique job URL before upload | URL checks are bounded and deduplicated |

No assets downloaded, no JS rendered, no links followed outside the job-URL
prefixes of the three sources. Never bypass a login or authentication wall.
