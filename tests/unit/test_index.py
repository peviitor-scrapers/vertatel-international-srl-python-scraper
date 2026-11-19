"""Unit tests for the ANOFM + jobRapid + eJobs index pipeline."""

import json

from scraper import index


def test_map_to_job_model_adds_company_and_status():
    index.COMPANY_NAME = "VERTATEL INTERNATIONAL S.R.L."
    raw = {
        "url": "https://mediere.anofm.ro/app/module/mediere/job/1",
        "title": "Lucrător comercial",
        "location": ["Măgurele"],
        "salary": "5000-8000 RON",
    }
    job = index.map_to_job_model(raw, "37633940")
    assert job["company"] == "VERTATEL INTERNATIONAL S.R.L."
    assert job["cif"] == "37633940"
    assert job["status"] == "scraped"
    assert job["location"] == ["Măgurele"]
    assert job["salary"] == "5000-8000 RON"
    assert job["date"]


def test_map_to_job_model_without_location():
    raw = {"url": "https://mediere.anofm.ro/app/module/mediere/job/2",
           "title": "Vânzător"}
    job = index.map_to_job_model(raw, "37633940", company_name="VERTATEL INTERNATIONAL S.R.L.")
    assert "location" not in job
    assert "salary" not in job


def test_transform_jobs_for_solr_uppercases_company():
    jobs = [{"url": "https://x/job", "title": "Test", "location": ["Cluj-Napoca"]}]
    transformed = index.transform_jobs_for_solr({"company": "Vertatel International S.R.L.", "jobs": jobs})
    assert transformed["company"] == "VERTATEL INTERNATIONAL S.R.L."
    assert transformed["jobs"][0]["location"] == ["Cluj-Napoca"]


def test_transform_jobs_for_solr_location_fallback():
    jobs = [{"url": "https://x/job", "title": "Test", "location": []}]
    transformed = index.transform_jobs_for_solr({"company": "VERTATEL INTERNATIONAL S.R.L.", "jobs": jobs})
    assert transformed["jobs"][0]["location"] == ["România"]


def test_transform_jobs_for_solr_missing_location_fallback():
    jobs = [{"url": "https://x/job", "title": "Test"}]
    transformed = index.transform_jobs_for_solr({"company": "VERTATEL INTERNATIONAL S.R.L.", "jobs": jobs})
    assert transformed["jobs"][0]["location"] == ["România"]


def _stub_main(monkeypatch, tmp_path, anofm_jobs, jobrapid_jobs=None, ejobs_jobs=None, existing_docs=None):
    monkeypatch.setattr(index, "query_solr",
                        lambda cif: {"numFound": len(existing_docs or []), "docs": existing_docs or []})
    monkeypatch.setattr(index, "upsert_jobs", lambda jobs: None)
    monkeypatch.setattr(index, "delete_job_by_url", lambda url: None)
    monkeypatch.setattr(index, "upsert_company", lambda cfg: None)
    monkeypatch.setattr(index, "validate_and_get_company", lambda: {
        "company": "VERTATEL INTERNATIONAL S.R.L.", "cif": "37633940", "address": "MĂGURELE"})
    monkeypatch.setattr(index, "search_anofm", lambda cif: anofm_jobs)
    monkeypatch.setattr(index, "search_jobrapid", lambda company: jobrapid_jobs or [])
    monkeypatch.setattr(index, "search_ejobs", lambda url: ejobs_jobs or [])
    monkeypatch.setattr(index, "drop_dead_urls", lambda jobs: jobs)
    return tmp_path


def test_main_writes_summary(tmp_path, monkeypatch):
    fake_jobs = [
        {"url": f"https://mediere.anofm.ro/app/module/mediere/job/{i}",
         "title": f"Job {i}", "location": ["Măgurele"]}
        for i in range(3)
    ]
    root = _stub_main(monkeypatch, tmp_path, fake_jobs)

    index.main(root=root)

    out = tmp_path / "scraper" / "jobs.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 3
    assert data["company"] == "VERTATEL INTERNATIONAL S.R.L."
    assert data["source"] == "mediere.anofm.ro, jobrapid.ro, ejobs.ro"
    assert (tmp_path / "docs" / "jobs.md").exists()
    assert (tmp_path / "docs" / "company.json").exists()


def test_main_dedupes_urls_across_sources(tmp_path, monkeypatch):
    job = {"url": "https://mediere.anofm.ro/app/module/mediere/job/1", "title": "Job"}
    root = _stub_main(monkeypatch, tmp_path, [job], jobrapid_jobs=[dict(job)])

    index.main(root=root)

    data = json.loads((tmp_path / "scraper" / "jobs.json").read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 1


def test_main_canary_aborts_before_any_write(tmp_path, monkeypatch):
    upserted = []
    root = _stub_main(monkeypatch, tmp_path, [])
    monkeypatch.setattr(index, "upsert_jobs", lambda jobs: upserted.append(jobs))
    monkeypatch.setattr(index, "upsert_company", lambda cfg: (_ for _ in ()).throw(AssertionError("no write")))

    index.main(root=root)

    assert upserted == []
    assert not (tmp_path / "scraper" / "jobs.json").exists()


def test_main_stale_deletion_uses_all_own_prefixes(tmp_path, monkeypatch):
    stale = [
        {"url": index.JOB_DETAILS_PREFIX + "dead"},
        {"url": index.EJOBS_PREFIX + "dead"},
        {"url": "https://www.ejobs.ro/job/someone-else"},
    ]
    deleted = []
    live = [{"url": index.JOB_DETAILS_PREFIX + "ok", "title": "Live"}]
    root = _stub_main(monkeypatch, tmp_path, live, existing_docs=stale)
    monkeypatch.setattr(index, "delete_job_by_url", lambda url: deleted.append(url))

    index.main(root=root)

    assert set(deleted) == {index.JOB_DETAILS_PREFIX + "dead", index.EJOBS_PREFIX + "dead"}


def test_drop_dead_urls_drops_soft_404(monkeypatch):
    good = {"url": "https://x/good", "title": "Good"}
    old = {"url": "https://x/old", "title": "Old"}
    monkeypatch.setattr(index, "validate_by_content", lambda url: {
        "url": url, "status": "active" if url.endswith("good") else "expired",
        "http_status": 200, "error": None})

    assert index.drop_dead_urls([good, old]) == [good]
