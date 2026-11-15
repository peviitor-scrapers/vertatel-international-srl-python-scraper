"""
jobRapid.ro Job Source Module

Searches jobRapid.ro for postings published by a company and extracts the
JobPosting JSON-LD data from each detail page.

jobRapid mirrors some ANOFM postings ("Preluat din surse externe"), but each
posting has its own URL, so it is kept as a separate secondary source.
"""

import datetime
import html
import json
import re
from urllib.parse import urljoin

import requests

BASE_URL = "https://www.jobrapid.ro"
SEARCH_URL = f"{BASE_URL}/angajare"
HEADERS = {"User-Agent": "job_seeker_ro_spider"}
TIMEOUT = 15

_CARD_RE = re.compile(r"<div class=['\"]container_lista_continut[^'\"]*['\"]([^>]*)>", re.S)
_COMPANY_RE = re.compile(r"data-company=['\"]([^'\"]*)['\"]")
_HREF_RE = re.compile(r"data-href=['\"]([^'\"]*)['\"]")
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)


def _normalize_name(name):
    cleaned = re.sub(r"[^a-z0-9]+", " ", (name or "").casefold())
    tokens = [t for t in cleaned.split() if t not in {"srl", "sa", "s", "r", "l"}]
    return " ".join(tokens)


def _same_company(card_name, company_name):
    return _normalize_name(card_name) == _normalize_name(company_name)


def _extract_company_hrefs(page_html, company_name):
    hrefs = []
    seen = set()
    for match in _CARD_RE.finditer(page_html or ""):
        attrs = match.group(1)
        company_match = _COMPANY_RE.search(attrs)
        href_match = _HREF_RE.search(attrs)
        if not company_match or not href_match:
            continue
        if not _same_company(html.unescape(company_match.group(1)), company_name):
            continue
        href = html.unescape(href_match.group(1))
        if href and href not in seen:
            seen.add(href)
            hrefs.append(href)
    return hrefs


def _to_utc_iso(value):
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_salary(base_salary):
    if not isinstance(base_salary, dict):
        return None
    currency = base_salary.get("currency") or "RON"
    value = base_salary.get("value")
    if isinstance(value, dict):
        amount = value.get("value")
    else:
        amount = value
    if amount in (None, ""):
        return None
    return f"{amount}-{amount} {currency}"


def parse_job_posting(page_html, url):
    """Extracts a job dict from the JobPosting JSON-LD block of a detail page."""
    for match in _JSONLD_RE.finditer(page_html or ""):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict) or data.get("@type") != "JobPosting":
            continue

        job = {
            "url": data.get("url") or url,
            "title": (data.get("title") or "").strip(),
        }
        address = ((data.get("jobLocation") or {}).get("address") or {})
        locality = (address.get("addressLocality") or "").strip()
        region = (address.get("addressRegion") or "").strip()
        if locality:
            job["location"] = [locality]
        elif region:
            job["location"] = [region]

        posted = _to_utc_iso(data.get("datePosted"))
        if posted:
            job["date"] = posted

        salary = _format_salary(data.get("baseSalary"))
        if salary:
            job["salary"] = salary

        return job
    return None


def _fetch_job(href):
    url = urljoin(BASE_URL + "/", href)
    try:
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
    except Exception as err:
        print(f"  jobRapid detail error for {url}: {err}")
        return None
    return parse_job_posting(res.text, url)


def search_jobrapid(company_name):
    """Searches jobRapid.ro by company name and returns its job postings."""
    jobs = []
    try:
        print(f"Searching jobRapid by company: {company_name}")
        res = requests.post(
            SEARCH_URL,
            data={"key": company_name},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        res.raise_for_status()
    except Exception as err:
        print(f"  jobRapid error: {err}")
        return jobs

    hrefs = _extract_company_hrefs(res.text, company_name)
    for href in hrefs:
        job = _fetch_job(href)
        if job:
            jobs.append(job)
    print(f"  Found {len(jobs)} jobs on jobRapid")
    return jobs
