"""
Company Data Module — CUIScan + CUIFirma

Strategy:
- get_company_from_anaf: CUIScan only (company details by CIF).
- search_company: CUIFirma only (brand search).
- get_company_from_anaf_with_fallback: CUIScan → cached data.
"""

import json
import pathlib

import requests

CUISCAN_API_URL = "https://cuiscan.ro/api.php"
CUISFIRMA_SEARCH_URL = "https://www.cuifirma.ro/api/search"

HEADERS = {"User-Agent": "job_seeker_ro_spider"}
CACHE_FILE = pathlib.Path(__file__).resolve().parent / "anaf_cache.json"


class _NoCompanyData(RuntimeError):
    pass


# ============================================================================
# HELPERS
# ============================================================================

def _fetch_json(url, **kwargs):
    res = requests.get(url, headers=HEADERS, timeout=10, **kwargs)
    res.raise_for_status()
    data = res.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"API error for {url}: {data.get('error')}")
    return data


def _read_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_cache(cache):
    try:
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


# ============================================================================
# ANOFM SEARCH
# ============================================================================

def search_anofm(cif):
    """Searches ANOFM for job postings by employer tax code."""
    jobs = []
    try:
        print(f"Searching ANOFM by CIF: {cif}")
        payload = {
            "current": 1,
            "rowCount": 250,
            "sort": {"created_at": "desc"},
            "employer_tax_code": str(cif),
        }
        res = requests.post(
            "https://mediere.anofm.ro/api/entity/vw_public_job_posting",
            json=payload,
            headers={"User-Agent": "job_seeker_ro_spider", "Content-Type": "application/json"},
            timeout=10,
        )
        if res.status_code != 200:
            print(f"  ANOFM returned {res.status_code}")
            return jobs
        data = res.json()
        for row in data.get("rows") or []:
            parts = [p.strip() for p in (row.get("address_locality_name") or "").split(">")]
            location = parts[-1] if len(parts) > 1 else (parts[0] if parts else "")
            job = {
                "url": f"https://mediere.anofm.ro/app/module/mediere/job/{row.get('id')}",
                "title": row.get("occupation"),
            }
            if location:
                job["location"] = [location]
            jobs.append(job)
        print(f"  Found {len(jobs)} jobs on ANOFM")
    except Exception as err:
        print(f"  ANOFM error: {err}")
    return jobs


# ============================================================================
# SEARCH
# ============================================================================

def search_company(brand_name):
    """Searches CUIFirma by brand name. Returns a list of company dicts."""
    try:
        data = _fetch_json(f"{CUISFIRMA_SEARCH_URL}?q={brand_name}")
        results = data.get("data") or data.get("results") or []
        return [
            {
                "cui": str(row.get("cui")),
                "name": row.get("name"),
                "statusLabel": row.get("status_label") or "",
            }
            for row in results
        ]
    except Exception:
        return []


# ============================================================================
# FETCH BY CIF
# ============================================================================

def get_company_from_anaf(cif):
    """Fetches company data from CUIScan by CIF.

    Network/HTTP failures return None so the caller can use its cache; an empty
    or nameless response raises, because scraping cannot proceed without a
    verified legal name.
    """
    try:
        data = _fetch_json(f"{CUISCAN_API_URL}?action=company&cui={cif}")
    except Exception:
        return None
    if not data or not data.get("denumire"):
        raise _NoCompanyData("CUIScan returned no data or company name")
    return {
        "cif": str(data.get("cui") or cif),
        "denumire": data.get("denumire"),
        "adresa": data.get("adresa"),
        "nrRegCom": data.get("nrRegCom"),
        "codCaen": str(data.get("codCaen") or ""),
        "dataInregistrare": data.get("dataInregistrare"),
    }


def get_company_from_anaf_with_fallback(cif, cached=None):
    """Returns fresh CUIScan data, falling back to cached data on network errors."""
    cache = cached if cached is not None else _read_cache()
    company = get_company_from_anaf(cif)
    if company:
        cache[str(cif)] = company
        _write_cache(cache)
        return company

    cached_company = cache.get(str(cif))
    if cached_company:
        return cached_company

    raise RuntimeError(f"CUIScan failed and no cached data available for CIF {cif}")
