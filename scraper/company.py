"""
Company Validation Module

Resolves company identity via CUIScan/CUIFirma. Company status is a config
value only: it never gates scraping or triggers job deletion.
"""

from .anaf import get_company_from_anaf_with_fallback
from .config import company_config


def get_company_data(cif=None, cached=None):
    """Fetches company data via CUIScan (with cache fallback)."""
    cif = cif or company_config["id"]
    return get_company_from_anaf_with_fallback(cif, cached=cached)


def validate_and_get_company(cif=None, cached=None):
    """Resolves the company's legal name and address via CUIScan.

    Falls back to the committed company config when CUIScan is unreachable, so
    scheduled scrapes do not fail on network hiccups.
    """
    cif = cif or company_config["id"]
    try:
        company = get_company_data(cif, cached=cached)
    except RuntimeError:
        company = {
            "cif": cif,
            "denumire": company_config["company"],
            "adresa": ", ".join(company_config.get("location") or []),
        }

    company_name = company.get("denumire")
    if not company_name:
        raise RuntimeError("CUIScan returned no company name")

    return {
        "company": company_name,
        "cif": str(cif),
        "address": company.get("adresa") or None,
    }
