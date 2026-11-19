"""Unit tests for the two secondary job sources."""

from scraper import ejobs, jobrapid


def test_ejobs_parse_deduplicates_hydration_cards():
    card = (
        '<li data-testid="b2c-job-card-123">'
        '<a href="/user/locuri-de-munca/123" data-testid="b2c-job-card-title-link">'
        '<span>Engineer</span></a>'
        '<div class="job-card-content-top__date">19 nov. 2026</div>'
        '<div class="job-card-content-middle__info">Bucuresti</div>'
        '<div class="job-card-content-middle__salary">8000 - 10000</div>'
        '</li>'
    )
    jobs = ejobs.parse_company_jobs(card + card)
    assert len(jobs) == 1
    assert jobs[0]["url"] == "https://www.ejobs.ro/user/locuri-de-munca/123"
    assert jobs[0]["title"] == "Engineer"
    assert jobs[0]["location"] == ["Bucuresti"]
    assert jobs[0]["salary"] == "8000-10000 RON"
    assert jobs[0]["date"] == "2026-11-19T00:00:00Z"


def test_jobrapid_parse_job_posting():
    html = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Developer","url":"https://www.jobrapid.ro/locuri-de-munca/1",
     "jobLocation":{"address":{"addressLocality":"Măgurele"}},
     "datePosted":"2026-11-19","baseSalary":{"currency":"RON","value":{"value":9000}}}
    </script>
    """
    job = jobrapid.parse_job_posting(html, "https://www.jobrapid.ro/locuri-de-munca/1")
    assert job["title"] == "Developer"
    assert job["location"] == ["Măgurele"]
    assert job["date"] == "2026-11-19T00:00:00Z"
    assert job["salary"] == "9000-9000 RON"


def test_jobrapid_ignores_other_jsonld_types():
    assert jobrapid.parse_job_posting(
        '<script type="application/ld+json">{"@type":"Organization"}</script>', "https://x") is None
