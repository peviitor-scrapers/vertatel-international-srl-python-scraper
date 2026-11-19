"""
VERTATEL INTERNATIONAL S.R.L. Scraper

Collects job postings published by VERTATEL INTERNATIONAL S.R.L. (CIF
37633940) on ANOFM (mediere.anofm.ro), jobRapid.ro and eJobs.ro, and
publishes them to peviitor.ro via the v1 API.
"""

import datetime
import json
import pathlib
import sys

from .anaf import search_anofm
from .api import delete_job_by_url, map_with_concurrency, query_solr, upsert_company, upsert_jobs
from .company import validate_and_get_company
from .config import company_config, scraper_config
from .ejobs import search_ejobs
from .jobrapid import search_jobrapid
from .job_validator import validate_by_content
from .markdown_generator import generate_jobs_markdown

COMPANY_CIF = company_config["id"]
JOB_DETAILS_PREFIX = scraper_config["jobDetailsPrefix"]
JOBRAPID_PREFIX = scraper_config.get("jobRapidPrefix") or "https://www.jobrapid.ro/locuri-de-munca/"
EJOBS_PREFIX = scraper_config.get("ejobsPrefix") or "https://www.ejobs.ro/user/locuri-de-munca/"
OWN_PREFIXES = (JOB_DETAILS_PREFIX, JOBRAPID_PREFIX, EJOBS_PREFIX)
JOBRAPID_COMPANY = company_config.get("brand") or company_config["company"]
EJOBS_COMPANY_URL = scraper_config.get("ejobsCompanyUrl")
COMPANY_NAME = None

LIVE_CHECK_CONCURRENCY = 5
DELETE_CONCURRENCY = 3


def map_to_job_model(raw_job, cif, company_name=None):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job = {
        "url": raw_job["url"],
        "title": raw_job["title"],
        "company": company_name or COMPANY_NAME,
        "cif": cif,
        "date": raw_job.get("date") or now,
        "status": "scraped",
    }
    if raw_job.get("location"):
        job["location"] = raw_job["location"]
    if raw_job.get("salary"):
        job["salary"] = raw_job["salary"]
    return job


def transform_jobs_for_solr(payload):
    company = (payload.get("company") or "").upper()
    jobs = []
    for job in payload.get("jobs", []):
        locations = [loc for loc in (job.get("location") or []) if loc]
        jobs.append({**job, "location": locations or ["România"]})
    return {**payload, "company": company, "jobs": jobs}


def drop_dead_urls(jobs):
    """GET-check every job with bounded concurrency and drop soft-404s.

    A 200 response can still be a "no longer available" page; validate_by_content
    scans the visible body for the shared expiry keywords.
    """
    checks = map_with_concurrency(
        jobs, lambda job, _: validate_by_content(job["url"]), limit=LIVE_CHECK_CONCURRENCY)
    alive = []
    for job, result in zip(jobs, checks):
        if result["status"] == "active":
            alive.append(job)
        else:
            reason = result.get("error") or f"HTTP {result.get('http_status', 0)}"
            print(f"  dropped \"{job['title']}\" ({job['url']}): live URL check failed — {reason}")
    if len(alive) < len(jobs):
        print(f"  {len(jobs) - len(alive)}/{len(jobs)} job(s) failed live URL validation and were dropped")
    return alive


def _validated_company():
    try:
        return validate_and_get_company()
    except Exception as err:
        print(f"CUIScan validation failed ({err}) — using config identity")
        return {
            "cif": company_config["id"],
            "company": company_config["company"],
            "address": (company_config.get("location") or ["România"])[0],
        }


def main(root=None):
    root = root or pathlib.Path(__file__).resolve().parents[1]

    print("=== Step 1: Get existing jobs from SOLR ===")
    existing_result = query_solr(COMPANY_CIF)
    existing_count = existing_result["numFound"]
    existing_urls = {doc.get("url") for doc in existing_result["docs"]
                     if doc.get("url") and any(doc["url"].startswith(prefix) for prefix in OWN_PREFIXES)}
    print(f"Found {existing_count} existing jobs in SOLR ({len(existing_urls)} from tracked sources)")

    print("=== Step 2: Validate company via CUIScan/CUIFirma ===")
    validated = _validated_company()
    global COMPANY_NAME
    COMPANY_NAME = validated["company"]

    print("=== Step 3: Scrape VERTATEL INTERNATIONAL S.R.L. jobs ===")
    anofm_jobs = search_anofm(validated["cif"])
    jobrapid_jobs = search_jobrapid(JOBRAPID_COMPANY)
    ejobs_jobs = search_ejobs(EJOBS_COMPANY_URL)
    print(f"Jobs scraped from ANOFM: {len(anofm_jobs)}")
    print(f"Jobs scraped from jobRapid: {len(jobrapid_jobs)}")
    print(f"Jobs scraped from eJobs: {len(ejobs_jobs)}")

    raw_jobs = []
    known_urls = set()
    for job in anofm_jobs + jobrapid_jobs + ejobs_jobs:
        if job["url"] in known_urls:
            continue
        raw_jobs.append(job)
        known_urls.add(job["url"])
    if len(raw_jobs) != len(anofm_jobs) + len(jobrapid_jobs) + len(ejobs_jobs):
        print(f"Removed {len(anofm_jobs) + len(jobrapid_jobs) + len(ejobs_jobs) - len(raw_jobs)} duplicate URL(s)")

    jobs = [map_to_job_model(job, validated["cif"]) for job in raw_jobs]
    payload = {
        "source": "mediere.anofm.ro, jobrapid.ro, ejobs.ro",
        "scrapedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "company": COMPANY_NAME,
        "cif": validated["cif"],
        "jobs": jobs,
    }

    transformed = transform_jobs_for_solr(payload)
    transformed["jobs"] = drop_dead_urls(transformed["jobs"])
    print(f"Jobs with valid locations: {len(transformed['jobs'])}")
    if not transformed["jobs"]:
        print("Canary: no live jobs after URL validation — aborting before any write")
        return

    try:
        upsert_company({
            "id": validated["cif"],
            "company": validated["company"],
            "brand": company_config.get("brand"),
            "status": company_config.get("status") or "activ",
            "location": [validated["address"]] if validated.get("address") else company_config["location"],
            "website": company_config.get("website"),
            "career": company_config.get("career"),
            "scraperFile": company_config.get("scraperFile"),
            "lastScraped": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        })
    except Exception as err:
        print(f"Note: Could not upsert company: {err}")

    jobs_path = root / "scraper" / "jobs.json"
    jobs_path.parent.mkdir(parents=True, exist_ok=True)
    jobs_path.write_text(json.dumps(transformed, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved scraper/jobs.json")

    company_data = {
        "id": validated["cif"],
        "company": transformed["company"],
        "brand": company_config.get("brand"),
        "status": company_config.get("status") or "activ",
        "location": [validated["address"]] if validated.get("address") else company_config["location"],
        "website": company_config.get("website"),
        "career": company_config.get("career"),
        "lastScraped": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    }
    markdown = generate_jobs_markdown(company_data, transformed["jobs"])
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "jobs.md").write_text(markdown, encoding="utf-8")
    print("Saved docs/jobs.md")

    src_company = pathlib.Path(__file__).resolve().parent / "config" / "company.json"
    (root / "docs" / "company.json").write_text(src_company.read_text(encoding="utf-8"), encoding="utf-8")

    print("\n=== Step 4: Upsert jobs to SOLR ===")
    upsert_jobs(transformed["jobs"])

    scraped_urls = {job["url"] for job in transformed["jobs"]}
    stale_urls = [url for url in existing_urls if url not in scraped_urls]
    if stale_urls:
        print(f"\n=== Step 4.5: Delete {len(stale_urls)} stale job(s) ===")

        def _delete_stale(url):
            try:
                delete_job_by_url(url)
            except Exception as err:
                print(f"  Failed to delete: {url} — {err}")

        map_with_concurrency(stale_urls, lambda url, _: _delete_stale(url), limit=DELETE_CONCURRENCY)
    else:
        print("\nNo stale jobs to delete")

    print("\n=== Step 5: Summary ===")
    final_result = query_solr(COMPANY_CIF)
    print(f"Jobs existing in SOLR before scrape: {existing_count}")
    print(f"Jobs scraped from ANOFM: {len(anofm_jobs)}")
    print(f"Jobs scraped from jobRapid: {len(jobrapid_jobs)}")
    print(f"Jobs scraped from eJobs: {len(ejobs_jobs)}")
    print(f"Jobs published after live validation: {len(transformed['jobs'])}")
    print(f"Stale jobs attempted: {len(stale_urls)}")
    print(f"Jobs in SOLR after scrape: {final_result['numFound']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print("Scraper failed:", err)
        sys.exit(1)
