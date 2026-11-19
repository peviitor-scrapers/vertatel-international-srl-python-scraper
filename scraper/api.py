"""
Peviitor API Module

PURPOSE: Provides interface to Solr database via the peviitor API for
storing and retrieving job listings and company data.

This module handles:
- Querying jobs by company CIF (via peviitor API)
- Querying/upserting company data (via peviitor API)
- Adding/updating (upserting) jobs (via peviitor API)
- Deleting jobs by URL (via peviitor API)

All Solr operations go through the peviitor API — no direct Solr access.

Endpoints mirror the Node.js template (api.peviitor.ro v1):
- GET  /v1/firme/company/?cif=...
- GET  /v1/firme/company/?name=...
- PUT  /v1/firme/company/add/
- GET  /v1/scraper/jobs/?cif=...&rows=...
- POST /v1/scraper/jobs/upload/
- DELETE /v1/scraper/jobs/delete/
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

API_BASE_URL = "https://api.peviitor.ro/v1"
TIMEOUT = 10
HEADERS = {"User-Agent": "job_seeker_ro_spider"}
RETRY_DELAYS = (0.25, 0.5)


def _request_with_retry(call, label):
    """Retries transient API failures; keeps HTTP 4xx (except 429) immediate."""
    last_error = None
    for delay in (0, *RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            res = call()
            if res.status_code == 429 or res.status_code >= 500:
                last_error = RuntimeError(f"API {label} error: {res.status_code} - {res.text}")
                continue
            return res
        except requests.RequestException as err:
            last_error = err
    raise last_error


def map_with_concurrency(items, worker, limit=5):
    """Runs worker over items with bounded concurrency, preserving input order."""
    items = list(items)
    if not items:
        return []
    results = [None] * len(items)
    with ThreadPoolExecutor(max_workers=max(1, min(limit, len(items)))) as pool:
        futures = {pool.submit(worker, item, i): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


# ============================================================================
# COMPANY OPERATIONS
# ============================================================================

def get_company_by_cif(cif):
    """Searches for a company by CIF using the peviitor API."""
    url = f"{API_BASE_URL}/firme/company/?cif={cif}"
    res = _request_with_retry(
        lambda: requests.get(url, headers=HEADERS, timeout=TIMEOUT), "company search")
    data = res.json()
    if not data.get("success"):
        raise RuntimeError(f"API company search failed: {data}")
    rows = data.get("data") or []
    return rows[0] if rows else None


def search_company_by_name(name):
    """Searches for companies by name using the peviitor API."""
    url = f"{API_BASE_URL}/firme/company/?name={name}"
    res = _request_with_retry(
        lambda: requests.get(url, headers=HEADERS, timeout=TIMEOUT), "company search")
    data = res.json()
    if not data.get("success"):
        raise RuntimeError(f"API company search failed: {data}")
    return data.get("data") or []


def upsert_company(company_doc):
    """Upserts a company document via the peviitor API."""
    url = f"{API_BASE_URL}/firme/company/add/"
    payload = {**company_doc, "id": company_doc["id"]}
    res = requests.put(
        url,
        json=payload,
        headers={**HEADERS, "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    if res.status_code != 200:
        raise RuntimeError(f"API company upsert error: {res.status_code} - {res.text}")
    data = res.json()
    if not data.get("success"):
        raise RuntimeError(f"API company upsert failed: {data}")
    print(f"✅ Company \"{company_doc.get('company')}\" upserted via API.")


# ============================================================================
# JOB OPERATIONS
# ============================================================================

def query_solr(cif):
    """Queries jobs from Solr by company CIF via the peviitor API."""
    url = f"{API_BASE_URL}/scraper/jobs/?cif={cif}&rows=500"
    res = _request_with_retry(
        lambda: requests.get(url, headers=HEADERS, timeout=TIMEOUT), "jobs query")
    data = res.json()
    return {
        "numFound": data.get("total", 0),
        "docs": data.get("data") or [],
    }


# ============================================================================
# DELETE OPERATIONS
# ============================================================================

def delete_job_by_url(url):
    """Deletes a single job by its URL via the peviitor API."""
    api_url = f"{API_BASE_URL}/scraper/jobs/delete/"
    res = requests.delete(
        api_url,
        json={"url": url},
        headers={**HEADERS, "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    if res.status_code == 404:
        return
    if res.status_code != 200:
        raise RuntimeError(f"API jobs delete error: {res.status_code} - {res.text}")


# ============================================================================
# UPSERT OPERATIONS
# ============================================================================

def upsert_jobs(jobs):
    """Upserts (adds or updates) jobs via the peviitor API."""
    url = f"{API_BASE_URL}/scraper/jobs/upload/"
    res = requests.post(
        url,
        json=jobs,
        headers={**HEADERS, "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    if res.status_code != 200:
        raise RuntimeError(f"API jobs upload error: {res.status_code} - {res.text}")
    data = res.json()
    print(f"✅ Upserted {data.get('count', len(jobs))} jobs via API.")


# ============================================================================
# URL VALIDATION
# ============================================================================

def check_url(url):
    """Performs a HEAD request and returns status info.

    Redirects (3xx) are treated as invalid — closed jobs are redirected to the
    jobs list instead of returning a real 404.
    """
    try:
        res = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False)
        return {"url": url, "status": res.status_code, "valid": res.status_code == 200}
    except Exception as err:
        return {"url": url, "status": 0, "valid": False, "error": str(err)}


# ============================================================================
# VERIFICATION WORKFLOW
# ============================================================================

def run_verification(cif, delete=False, prefix=None):
    """Checks existing jobs in SOLR and validates URLs.

    Read-only by default. Deletion only happens when ``delete=True`` and
    only for invalid URLs under ``prefix`` (e.g. our board URL prefix), so
    jobs published by other scrapers under a shared CIF are never removed.
    """
    print("=== Verify SOLR Jobs ===\n")
    result = query_solr(cif)
    print(f"Total jobs in SOLR for CIF {cif}: {result['numFound']}")

    print("\nFirst 5 jobs:")
    for i, job in enumerate(result["docs"][:5]):
        loc = ", ".join(job.get("location") or [])
        print(f"{i+1}. {job.get('title')} ({loc}) - {job.get('workmode')}")

    checks = map_with_concurrency(result["docs"], lambda job, _: check_url(job.get("url", "")))
    invalid_urls = []
    for i, (job, res) in enumerate(zip(result["docs"], checks), start=1):
        print(f"[{i}/{result['numFound']}] {res['status'] if res['status'] > 0 else 'ERR'} - {job.get('url')}")
        if not res["valid"]:
            invalid_urls.append(job.get("url"))

    if not invalid_urls:
        print("\n✅ All URLs valid")
        return

    if not delete or not prefix:
        print(f"\n⚠️ {len(invalid_urls)} invalid URL(s) — read-only, nothing deleted.")
        print("Use --delete to remove invalid board URLs (scoped to the board prefix).")
        return

    deletable = [u for u in invalid_urls if u.startswith(prefix)]
    skipped = [u for u in invalid_urls if not u.startswith(prefix)]
    if skipped:
        print(f"\n⚠️ Skipping {len(skipped)} invalid URL(s) from other sources (outside board prefix).")
    if not deletable:
        print("\n✅ No invalid board URLs to delete.")
        return

    print(f"\n⚠️ Deleting {len(deletable)} invalid board URL(s) via API...")
    map_with_concurrency(deletable, lambda url, _: delete_job_by_url(url), limit=3)
    print(f"✅ Deleted {len(deletable)} invalid jobs via API")


# ============================================================================
# STANDALONE MODE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys

    from .config import scraper_config

    parser = argparse.ArgumentParser(
        description="Verify peviitor jobs for a CIF (read-only unless --delete)")
    parser.add_argument("cif", help="Company CIF")
    parser.add_argument("--delete", action="store_true",
                        help="Delete invalid jobs under the board URL prefix")
    args = parser.parse_args()

    prefix = scraper_config.get("jobDetailsPrefix") or f"{scraper_config['apiBase']}/apply/jobs/details/"
    run_verification(args.cif, delete=args.delete, prefix=prefix)
