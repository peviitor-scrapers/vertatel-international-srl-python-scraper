"""
validate_jobs.py — CLI job URL validator.

Usage:
  python -m scraper.validate_jobs <CIF> [--mode head|content] [--dry-run] [--delete]
"""

import argparse
import sys

from .api import delete_job_by_url, map_with_concurrency, query_solr
from .job_validator import validate_by_browser, validate_by_content, validate_by_head
from .config import company_config, scraper_config


BOARD_PREFIX = scraper_config.get("jobDetailsPrefix") or f"{scraper_config['apiBase']}/apply/jobs/details/"
OWN_PREFIXES = tuple(
    prefix for prefix in (
        BOARD_PREFIX,
        scraper_config.get("jobRapidPrefix"),
        scraper_config.get("ejobsPrefix"),
    ) if prefix
)


def _is_own_url(url):
    return any(url.startswith(prefix) for prefix in OWN_PREFIXES)


def main():
    parser = argparse.ArgumentParser(description="Validate job URLs from SOLR by CIF")
    parser.add_argument("cif", nargs="?", default=company_config["id"],
                        help="Company CIF (default from config)")
    parser.add_argument("--mode", default="head", choices=["head", "content", "browser"])
    parser.add_argument("--dry-run", action="store_true", help="Do not delete anything")
    parser.add_argument("--delete", action="store_true", help="Delete invalid jobs")
    args = parser.parse_args()

    result = query_solr(args.cif)
    docs = result["docs"]
    print(f"Total jobs in SOLR for CIF {args.cif}: {result['numFound']}")

    def _check(job):
        url = job.get("url", "")
        if args.mode == "content":
            check = validate_by_content(url)
        elif args.mode == "browser":
            check = validate_by_browser(url)
        else:
            check = validate_by_head(url)
        return url, check

    checks = map_with_concurrency(docs, lambda job, _: _check(job))
    invalid = []
    for i, (url, check) in enumerate(checks, start=1):
        flag = {"active": "OK", "expired": "EXPIRED", "error": "ERROR"}.get(check["status"], check["status"])
        print(f"[{i}/{len(docs)}] {flag} - {url}")
        if check["status"] != "active":
            invalid.append(url)

    if not invalid:
        print("\n✅ All URLs valid")
        return 0

    print(f"\n⚠️ {len(invalid)} invalid URL(s)")
    if args.dry_run:
        print("Dry run — nothing deleted.")
        return 0
    if args.delete:
        deletable = [u for u in invalid if _is_own_url(u)]
        skipped = [u for u in invalid if not _is_own_url(u)]
        if skipped:
            print(f"  ⚠️ Skipping {len(skipped)} invalid URL(s) from other sources (outside our job prefixes).")
        if not deletable:
            print("  ✅ No invalid job URLs from this scraper to delete.")
            return 0
        def _delete(url):
            try:
                delete_job_by_url(url)
                print(f"  Deleted: {url}")
            except Exception as err:
                print(f"  ⚠️ Failed to delete {url}: {err}")

        map_with_concurrency(deletable, lambda url, _: _delete(url), limit=3)
        return 0

    print("Use --delete to remove them, or --dry-run to preview.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
