# Company Model

Company document published to the peviitor company core (`/v1/firme/company/`).

## Source of truth

`scraper/config/company.json` — never edit other copies; they are generated.

## Fields

| Field        | Type   | Description                                                        |
|--------------|--------|--------------------------------------------------------------------|
| `id`         | string | CIF (8 digits, no RO prefix)                                       |
| `company`    | string | Legal name from Trade Register (UPPERCASE, diacritics required)    |
| `brand`      | string | Public brand name                                                  |
| `group`      | string | Parent company group (optional)                                    |
| `status`     | string | `activ` / `suspendat` / `inactiv` / `radiat`. Config value only — this scraper never deletes jobs or the company based on status (#3) |
| `location`   | array  | Romanian cities/addresses (diacritics accepted)                    |
| `website`    | array  | Company website (canonical HTTP/HTTPS URL, no trailing slash)      |
| `career`     | array  | Careers/board URL (canonical HTTP/HTTPS URL, no trailing slash)    |
| `lastScraped`| string | Date of last scrape (ISO 8601)                                     |
| `scraperFile`| string | GitHub Actions workflow URL (no raw)                               |

## Notes

- Fields marked `array` are multi-valued arrays stored as arrays in SOLR.
- `website` and `career` should be canonical URLs without a trailing slash.
- `scraperFile` must be the full workflow URL, not the raw file URL.

## Upsert behavior

`upsert_company` passes the CIF **as-is** (no zero-padding, per AGENTS.md
commandment 2) and PUTs to `/v1/firme/company/add/`. The live
address/location from CUIScan takes precedence over the static
config when available.

## Example

```json
{
  "id": "37633940",
  "company": "VERTATEL INTERNATIONAL S.R.L.",
  "brand": "Vertatel International",
  "status": "activ",
  "location": ["Măgurele"],
  "website": [],
  "career": ["https://mediere.anofm.ro/app/module/mediere/jobs"],
  "scraperFile": "https://github.com/peviitor-scrapers/vertatel-international-srl-python-scraper/actions/workflows/job-seeker-ro-spider.yml"
}
```

`website` is empty because VERTATEL INTERNATIONAL S.R.L. has no public website;
`career` lists ANOFM, jobRapid.ro and eJobs.ro, the three job sources.
