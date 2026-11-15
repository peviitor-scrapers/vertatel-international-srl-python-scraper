"""
eJobs.ro Job Source Module

Scrapes a company page on eJobs.ro and extracts the job cards. The page is
server-rendered (Nuxt) and repeats the cards during hydration, so results are
deduplicated by job id.
"""

import html
import re

import requests

BASE_URL = "https://www.ejobs.ro"
HEADERS = {"User-Agent": "job_seeker_ro_spider", "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8"}
TIMEOUT = 15

_CARD_RE = re.compile(r'<li data-testid="b2c-job-card-(\d+)"(.*?)</li>', re.S)
_TITLE_RE = re.compile(r'data-testid="b2c-job-card-title-link"[^>]*>\s*<span>(.*?)</span>', re.S)
_HREF_RE = re.compile(r'<a href="([^"]+)"[^>]*data-testid="b2c-job-card-title-link"')
_DATE_RE = re.compile(r'job-card-content-top__date">([^<]+)')
_LOCATION_RE = re.compile(r'job-card-content-middle__info">([^<]+)<')
_SALARY_RE = re.compile(r'job-card-content-middle__salary">([^<]+)<')

_MONTHS = {
    "ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6,
    "iul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "noi": 11,
    "nov": 11, "dec": 12,
}


def _parse_date(value):
    match = re.match(r"(\d{1,2})\s+([A-Za-zăâîșț]+)\.?\s+(\d{4})", (value or "").strip())
    if not match:
        return None
    day = int(match.group(1))
    month = _MONTHS.get(match.group(2).casefold()[:4].rstrip("."))
    if not month:
        return None
    return f"{int(match.group(3)):04d}-{month:02d}-{day:02d}T00:00:00Z"


def _parse_salary(value):
    match = re.search(r"(\d[\d.\s]*)\s*-\s*(\d[\d.\s]*)", value or "")
    if not match:
        return None
    low = re.sub(r"\D", "", match.group(1))
    high = re.sub(r"\D", "", match.group(2))
    if not low or not high:
        return None
    return f"{low}-{high} RON"


def _parse_locations(value):
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def parse_company_jobs(page_html):
    """Extracts unique job cards from an eJobs company page."""
    jobs = []
    seen = set()
    for match in _CARD_RE.finditer(page_html or ""):
        job_id, block = match.group(1), match.group(2)
        if job_id in seen:
            continue
        title_match = _TITLE_RE.search(block)
        href_match = _HREF_RE.search(block)
        if not title_match or not href_match:
            continue
        seen.add(job_id)

        job = {
            "url": BASE_URL + html.unescape(href_match.group(1)),
            "title": html.unescape(title_match.group(1)).strip(),
        }

        location_match = _LOCATION_RE.search(block)
        if location_match:
            locations = _parse_locations(html.unescape(location_match.group(1)))
            if locations:
                job["location"] = locations

        salary_match = _SALARY_RE.search(block)
        if salary_match:
            salary = _parse_salary(html.unescape(salary_match.group(1)))
            if salary:
                job["salary"] = salary

        date_match = _DATE_RE.search(block)
        if date_match:
            date = _parse_date(html.unescape(date_match.group(1)))
            if date:
                job["date"] = date

        jobs.append(job)
    return jobs


def search_ejobs(company_url):
    """Scrapes the eJobs company page and returns its job postings."""
    jobs = []
    if not company_url:
        return jobs
    try:
        print(f"Searching eJobs: {company_url}")
        res = requests.get(company_url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
    except Exception as err:
        print(f"  eJobs error: {err}")
        return jobs

    jobs = parse_company_jobs(res.text)
    print(f"  Found {len(jobs)} jobs on eJobs")
    return jobs
