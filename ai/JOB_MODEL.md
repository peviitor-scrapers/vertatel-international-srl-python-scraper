# Job Model

Standardized job document published to peviitor SOLR.

## Fields

| Field           | Required | Description                                                        |
|-----------------|----------|--------------------------------------------------------------------|
| `url`           | yes      | Canonical job URL (valid HTTP/HTTPS)                               |
| `title`         | yes      | Position title — max 200 chars, no HTML, trimmed whitespace        |
| `company`       | no       | Full legal name, UPPERCASE, diacritics allowed; must match `Company.company` case-insensitively |
| `cif`           | no       | Company CIF, as-is (8 digits, no zero-padding)                     |
| `location`      | no       | Array of Romanian cities (diacritics accepted)                     |
| `tags`          | no       | Lowercase keywords, max 20 entries, NO diacritics                  |
| `workmode`      | no       | `remote` / `on-site` / `hybrid`                                     |
| `date`          | no       | ISO 8601 (`YYYY-MM-DDThh:mm:ssZ`)                                   |
| `status`        | no       | `scraped`                                                           |
| `vdate`         | no       | Validation date (ISO). Set only when status becomes `tested` or `verified` |
| `expirationdate`| no       | Expiration date (ISO), at most `vdate` + 30 days or from the job page |
| `salary`        | no       | Salary info as string, e.g. `"5000-8000 RON"` (not an array)        |

## Status flow

`scraped` → (`tested` OR `verified`) → `published`

| Status    | Meaning                                                           |
|-----------|-------------------------------------------------------------------|
| scraped   | Newly scraped, not validated yet                                  |
| tested    | URL works, job exists but incomplete details                      |
| verified  | Fully scraped with all details                                    |
| published | Imported from jobs core                                           |

## Location rules

- Location comes from ANOFM (`address_locality_name`), jobRapid JSON-LD or the eJobs card (first source wins after dedupe).
- If no location is returned, it falls back to `["România"]`.
- The scraper does not geocode or filter non-Romanian cities.

## Workmode rules

This scraper does not set `workmode`; the three sources do not expose it consistently.

## Example

```json
{
  "url": "https://mediere.anofm.ro/app/module/mediere/job/123456",
  "title": "Lucrător comercial",
  "company": "VERTATEL INTERNATIONAL S.R.L.",
  "cif": "37633940",
  "location": ["Măgurele"],
  "date": "2026-08-03T00:00:00Z",
  "status": "scraped"
}
```
