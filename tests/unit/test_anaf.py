"""Unit tests for company data integration with mocked HTTP."""

from unittest import mock

import pytest

from scraper import anaf


def test_get_company_from_anaf_cuiscan_only(mock_get):
    mock_get.return_value = mock.Mock(json=lambda: {
        "denumire": "VERTATEL INTERNATIONAL S.R.L.", "cui": "37633940",
        "adresa": "CLUJ-NAPOCA", "activ": True})
    company = anaf.get_company_from_anaf("37633940")
    assert mock_get.call_count == 1
    assert "cuiscan.ro" in mock_get.call_args.args[0]
    assert company["denumire"] == "VERTATEL INTERNATIONAL S.R.L."
    assert company["cif"] == "37633940"
    assert "stareInregistrare" not in company


def test_get_company_from_anaf_returns_none_on_network_failure(mock_get):
    mock_get.side_effect = Exception("network")
    assert anaf.get_company_from_anaf("37633940") is None


def test_get_company_from_anaf_no_data_is_fatal(mock_get):
    mock_get.return_value = mock.Mock(json=lambda: {})
    with pytest.raises(RuntimeError, match="no data"):
        anaf.get_company_from_anaf_with_fallback("37633940", cached={"37633940": {"denumire": "cached"}})


def test_get_company_from_anaf_with_fallback_uses_cache_on_network_failure(mock_get):
    mock_get.side_effect = Exception("network")
    cached = {"37633940": {"denumire": "VERTATEL INTERNATIONAL S.R.L.", "cif": "37633940"}}
    company = anaf.get_company_from_anaf_with_fallback("37633940", cached=cached)
    assert company == cached["37633940"]


def test_search_company_uses_cuifirma_only(mock_get):
    mock_get.return_value = mock.Mock(json=lambda: {
        "results": [{"cui": 37633940, "name": "Vertatel International", "is_active": True}]})
    results = anaf.search_company("Vertatel International")
    assert mock_get.call_count == 1
    assert "cuifirma.ro" in mock_get.call_args.args[0]
    assert results == [{"cui": "37633940", "name": "Vertatel International", "statusLabel": ""}]


def test_search_anofm_parses_rows(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"rows": [
        {"id": "1", "occupation": "Inginer", "address_locality_name": "Cluj > Cluj-Napoca"},
        {"id": "2", "occupation": "Electrician", "address_locality_name": "Bucuresti > Bucuresti"},
    ]}
    jobs = anaf.search_anofm("37633940")
    assert len(jobs) == 2
    assert jobs[0]["url"].endswith("/job/1")
    assert jobs[0]["title"] == "Inginer"
    assert jobs[0]["location"] == ["Cluj-Napoca"]


def test_search_anofm_empty_on_error(mock_post):
    mock_post.side_effect = Exception("network")
    assert anaf.search_anofm("37633940") == []


def test_search_anofm_non_200(mock_post):
    mock_post.return_value.status_code = 500
    assert anaf.search_anofm("37633940") == []


def test_validate_and_get_company_falls_back_to_config(monkeypatch, company_config):
    from scraper import company
    monkeypatch.setattr(company, "get_company_data", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no api")))
    result = company.validate_and_get_company()
    assert result["company"] == company_config["company"]
    assert result["cif"] == company_config["id"]
    assert "status" not in result
