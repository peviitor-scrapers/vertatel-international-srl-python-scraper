"""End-to-end test: live ANOFM scrape for VERTATEL INTERNATIONAL S.R.L.

Skips (rather than fails) when ANOFM is unreachable, so CI does not break on
transient network issues.
"""

import socket

import pytest

from scraper import index


def _anofm_reachable():
    try:
        with socket.create_connection(("mediere.anofm.ro", 443), timeout=5):
            return True
    except OSError:
        return False


def test_scrape_real_anofm():
    if not _anofm_reachable():
        pytest.skip("mediere.anofm.ro not reachable")
    jobs = index.search_anofm(index.COMPANY_CIF)
    assert isinstance(jobs, list)
    for job in jobs:
        assert job["url"].startswith("https://mediere.anofm.ro/app/module/mediere/job/")
        assert job["title"]
    urls = {j["url"] for j in jobs}
    assert len(urls) == len(jobs), "duplicate job URLs found"
