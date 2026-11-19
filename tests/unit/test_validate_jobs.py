import sys

from scraper import validate_jobs


def test_main_checks_all_urls_and_deletes_only_own_prefix(monkeypatch):
    docs = [
        {"url": validate_jobs.BOARD_PREFIX + "dead"},
        {"url": "https://www.ejobs.ro/job/x"},
        {"url": validate_jobs.BOARD_PREFIX + "ok"},
    ]
    monkeypatch.setattr(sys, "argv", [
        "validate_jobs", "37633940", "--mode", "content", "--delete"])
    monkeypatch.setattr(validate_jobs, "query_solr",
                        lambda cif: {"numFound": len(docs), "docs": docs})
    monkeypatch.setattr(validate_jobs, "validate_by_content", lambda url: {
        "url": url, "status": "active" if url.endswith("ok") else "expired"})

    deleted = []
    monkeypatch.setattr(validate_jobs, "delete_job_by_url", lambda url: deleted.append(url))

    assert validate_jobs.main() == 0
    assert deleted == [validate_jobs.BOARD_PREFIX + "dead"]
