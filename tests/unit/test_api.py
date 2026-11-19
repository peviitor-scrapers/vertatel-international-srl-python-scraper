import tests.conftest  # noqa: F401  (sys.path setup)
import unittest.mock as mock

import pytest

import scraper.api as api


def test_query_solr_returns_docs(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"success": True, "total": 2, "data": [{"url": "u1"}]}
    result = api.query_solr("37633940")
    assert result["numFound"] == 2
    assert result["docs"] == [{"url": "u1"}]


def test_query_solr_throws_on_http_error(mock_get):
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.query_solr("37633940")


def test_query_solr_missing_data_returns_empty(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"success": False}
    result = api.query_solr("37633940")
    assert result["numFound"] == 0
    assert result["docs"] == []


def test_upsert_jobs_keeps_cif(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"success": True, "count": 1}
    api.upsert_jobs([{"url": "u", "cif": "37633940"}])
    sent = mock_post.call_args.kwargs["json"]
    assert sent[0]["cif"] == "37633940"


def test_upsert_jobs_throws_on_http_error(mock_post):
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.upsert_jobs([{"url": "u", "cif": "37633940"}])


def test_delete_job_by_url(mock_delete):
    mock_delete.return_value.status_code = 200
    mock_delete.return_value.json.return_value = {"success": True}
    api.delete_job_by_url("https://example.com/job")
    assert mock_delete.call_args.kwargs["json"] == {"url": "https://example.com/job"}


def test_delete_job_by_url_404_is_silent(mock_delete):
    mock_delete.return_value.status_code = 404
    api.delete_job_by_url("https://example.com/job")


def test_delete_job_by_url_throws_on_http_error(mock_delete):
    mock_delete.return_value.status_code = 500
    mock_delete.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.delete_job_by_url("https://example.com/job")


def test_upsert_company_keeps_id(mock_put):
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = {"success": True}
    api.upsert_company({"id": "37633940", "company": "VERTATEL INTERNATIONAL S.R.L."})
    sent = mock_put.call_args.kwargs["json"]
    assert sent["id"] == "37633940"


def test_upsert_company_throws_on_http_error(mock_put):
    mock_put.return_value.status_code = 500
    mock_put.return_value.text = "boom"
    with pytest.raises(RuntimeError, match="500"):
        api.upsert_company({"id": "37633940", "company": "VERTATEL INTERNATIONAL S.R.L."})


def test_check_url_head(mock_head):
    mock_head.return_value.ok = True
    mock_head.return_value.status_code = 200
    result = api.check_url("https://example.com")
    assert result["valid"] is True


def test_check_url_failure(mock_head):
    mock_head.return_value.ok = False
    mock_head.return_value.status_code = 404
    result = api.check_url("https://example.com")
    assert result["valid"] is False


def test_check_url_redirect_invalid(mock_head):
    mock_head.return_value.ok = True
    mock_head.return_value.status_code = 302
    result = api.check_url("https://example.com")
    assert result["valid"] is False


BOARD = "https://mediere.anofm.ro/app/module/mediere/job/"


def test_run_verification_read_only_by_default(monkeypatch, capsys):
    monkeypatch.setattr(api, "query_solr", lambda cif: {
        "numFound": 2,
        "docs": [
            {"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"},
            {"url": "https://www.ejobs.ro/job/x", "location": [], "workmode": None, "title": "B"},
        ],
    })
    monkeypatch.setattr(api, "check_url", lambda url: {"url": url, "status": 404, "valid": False})
    delete_mock = mock.Mock()
    monkeypatch.setattr(api, "delete_job_by_url", delete_mock)

    api.run_verification("37633940")

    delete_mock.assert_not_called()
    assert "nothing deleted" in capsys.readouterr().out


def test_run_verification_delete_scoped_to_prefix(monkeypatch):
    docs = [
        {"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"},
        {"url": "https://www.ejobs.ro/job/x", "location": [], "workmode": None, "title": "B"},
        {"url": BOARD + "ok1", "location": [], "workmode": None, "title": "C"},
    ]
    monkeypatch.setattr(api, "query_solr", lambda cif: {"numFound": len(docs), "docs": docs})

    def _check(url):
        valid = url.endswith("ok1")
        return {"url": url, "status": 200 if valid else 404, "valid": valid}

    monkeypatch.setattr(api, "check_url", _check)
    delete_mock = mock.Mock()
    monkeypatch.setattr(api, "delete_job_by_url", delete_mock)

    api.run_verification("37633940", delete=True, prefix=BOARD)

    assert delete_mock.call_count == 1
    assert delete_mock.call_args.args[0] == BOARD + "dead1"


def test_run_verification_delete_requires_prefix(monkeypatch):
    monkeypatch.setattr(api, "query_solr", lambda cif: {
        "numFound": 1,
        "docs": [{"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"}],
    })
    monkeypatch.setattr(api, "check_url", lambda url: {"url": url, "status": 404, "valid": False})
    delete_mock = mock.Mock()
    monkeypatch.setattr(api, "delete_job_by_url", delete_mock)

    api.run_verification("37633940", delete=True, prefix=None)

    delete_mock.assert_not_called()


def test_run_verification_delete_passes_only_url(monkeypatch):
    deleted = []
    monkeypatch.setattr(api, "query_solr", lambda cif: {
        "numFound": 1,
        "docs": [{"url": BOARD + "dead1", "location": [], "workmode": None, "title": "A"}],
    })
    monkeypatch.setattr(api, "check_url", lambda url: {"url": url, "status": 404, "valid": False})
    monkeypatch.setattr(api, "delete_job_by_url", lambda url: deleted.append(url))

    api.run_verification("37633940", delete=True, prefix=BOARD)

    assert deleted == [BOARD + "dead1"]


def test_query_solr_retries_transient_failure(monkeypatch, mock_get):
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)
    mock_get.side_effect = [
        mock.Mock(status_code=500, text="boom"),
        mock.Mock(status_code=200, json=lambda: {"success": True, "total": 1, "data": [{"url": "u"}]}),
    ]
    result = api.query_solr("37633940")
    assert result["numFound"] == 1
    assert mock_get.call_count == 2


def test_map_with_concurrency_preserves_order():
    assert api.map_with_concurrency([1, 2, 3], lambda item, i: item * 2, limit=2) == [2, 4, 6]


def test_cif_wide_delete_helper_removed():
    assert not hasattr(api, "delete_jobs_by_cif")
