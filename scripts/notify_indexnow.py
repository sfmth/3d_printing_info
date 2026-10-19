#!/usr/bin/env python3
"""Notify IndexNow after deployment; default to a network-free dry run.

Only sitemap URLs under this GitHub Pages project are eligible. The checkpoint
advances after HTTP 200/202 receipt (or a no-change deployment), never on error.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://sfmth.github.io/3d_printing_info/"
KEY = "c6df70c23c3143feab713134fa94bc0f"
KEY_LOCATION = SITE + KEY + ".txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS = 10000
PAGE_REVISION = re.compile(
    r"(<footer><span>Catalog values retain their original source dates\. Page revision: )"
    r"\d{4}-\d{2}-\d{2}(\.</span>)")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True,
                                   stderr=subprocess.DEVNULL).strip()


def url_file(url: str) -> str:
    """Map canonical sitemap URLs to files, rejecting host/path escapes."""
    site, item = urlsplit(SITE), urlsplit(url)
    if (item.scheme != site.scheme or item.netloc != site.netloc
            or item.query or item.fragment or not item.path.startswith(site.path)):
        raise ValueError(f"URL outside project scope: {url}")
    relative = item.path[len(site.path):]
    # Encoded separators/traversal and alternative spellings are unnecessary here.
    if unquote(relative) != relative or "\\" in relative:
        raise ValueError(f"Noncanonical sitemap URL: {url}")
    if any(part in (".", "..", "") for part in relative.rstrip("/").split("/")) and relative:
        raise ValueError(f"Invalid sitemap path: {url}")
    if relative and not (relative.endswith("/") or relative.endswith(".html")):
        raise ValueError(f"Not a public HTML URL: {url}")
    return str(PurePosixPath(relative) / "index.html") if not relative or relative.endswith("/") else relative


def sitemap(text: str) -> dict[str, str]:
    tree = ET.fromstring(text)
    if tree.tag != "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset":
        raise ValueError("Expected a sitemap urlset")
    result = {}
    for loc in tree.findall("{*}url/{*}loc"):
        url = (loc.text or "").strip()
        if url in result:
            raise ValueError(f"Duplicate sitemap URL: {url}")
        result[url] = url_file(url)
    if not result:
        raise ValueError("Sitemap has no content URLs")
    return result


def substantive_html_change(repo: Path, baseline: str, head: str, path: str) -> bool:
    """Ignore only this site's generated revision-date footer, preserving source dates."""
    try:
        before = git(repo, "show", baseline + ":" + path)
        after = git(repo, "show", head + ":" + path)
    except subprocess.CalledProcessError:
        return True
    return PAGE_REVISION.sub(r"\1[revision-date]\2", before) != PAGE_REVISION.sub(r"\1[revision-date]\2", after)


def select_urls(repo: Path, baseline: str | None, head: str, force_all: bool = False) -> tuple[list[str], str]:
    current = sitemap((repo / "sitemap.xml").read_text(encoding="utf-8"))
    missing = [path for path in current.values() if not (repo / path).is_file()]
    if missing:
        raise ValueError(f"Sitemap references missing HTML: {missing[0]}")
    if force_all:
        return sorted(current), "manual-full-sitemap"
    if not baseline:
        return sorted(current), "bootstrap-no-checkpoint"
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise ValueError("Invalid checkpoint commit")
    # A rollback can have a newer/divergent acknowledged baseline; Git can still
    # compare those trees and retain URLs removed by the rollback.
    available = subprocess.run(["git", "cat-file", "-e", baseline + "^{commit}"],
                               cwd=repo, capture_output=True)
    if available.returncode:
        return sorted(current), "bootstrap-unavailable-history"
    try:
        previous = sitemap(git(repo, "show", baseline + ":sitemap.xml"))
    except (subprocess.CalledProcessError, ValueError, ET.ParseError):
        return sorted(current), "bootstrap-unavailable-sitemap"
    changed = set(git(repo, "diff", "--name-only", "--no-renames", "-z", baseline, head, "--").split("\0"))
    urls = set(current) ^ set(previous)
    urls.update(url for url in current.keys() & previous.keys()
                if (current[url] in changed or previous[url] in changed)
                and substantive_html_change(repo, baseline, head, current[url]))
    return sorted(urls), "changed-and-removed-pages"


def read_checkpoint(path: Path) -> str | None:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("site") == SITE and state.get("key") == KEY:
            commit = state.get("commit")
            if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit):
                return commit
    except (OSError, ValueError, AttributeError):
        pass
    return None


def receipt(payload: dict) -> tuple[int, str]:
    """Verify the deployed public key before making one POST; never follow redirects."""
    opener = build_opener(NoRedirects())
    request = Request(KEY_LOCATION, headers={"User-Agent": "3d-printing-info-IndexNow/1.0"})
    with opener.open(request, timeout=15) as response:
        if response.status != 200 or response.read(1024).decode("utf-8").strip() != KEY:
            raise ValueError("Deployed IndexNow key did not match; notification was not sent")
    request = Request(ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST",
                      headers={"Content-Type": "application/json; charset=utf-8",
                               "User-Agent": "3d-printing-info-IndexNow/1.0"})
    with opener.open(request, timeout=20) as response:
        status = response.status
    if status == 200:
        return status, "received"
    if status == 202:
        return status, "received-key-validation-pending"
    raise ValueError(f"Unexpected IndexNow HTTP status: {status}")


def execute(repo: Path, state_file: Path, report_file: Path, submit: bool = False,
            force_all: bool = False) -> int:
    report = {"site": SITE, "endpoint": ENDPOINT, "keyLocation": KEY_LOCATION,
              "time": datetime.now(timezone.utc).isoformat(), "submit": submit,
              "status": "error", "checkpoint_advanced": False, "url_count": 0, "urls": []}
    exit_code = 0
    try:
        head = git(repo, "rev-parse", "HEAD")
        baseline = read_checkpoint(state_file)
        report.update(commit=head, baseline_commit=baseline)
        if (repo / (KEY + ".txt")).read_text(encoding="utf-8").strip() != KEY:
            raise ValueError("Local IndexNow key file did not match")
        urls, mode = select_urls(repo, baseline, head, force_all)
        if len(urls) > MAX_URLS:
            raise ValueError(f"IndexNow request exceeds {MAX_URLS} URLs; add batching first")
        report.update(urls=urls, url_count=len(urls), selection=mode)
        if not submit:
            report["status"] = "dry-run"
        elif not urls:
            report["status"] = "no-changed-pages"
        else:
            status, result = receipt({"host": urlsplit(SITE).hostname, "key": KEY,
                                      "keyLocation": KEY_LOCATION, "urlList": urls})
            report.update(status=result, http_status=status)
        if submit and report["status"] in ("received", "received-key-validation-pending", "no-changed-pages"):
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps({"site": SITE, "key": KEY, "commit": head}) + "\n", encoding="utf-8")
            report["checkpoint_advanced"] = True
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as error:
        exit_code = 1
        report["error"] = str(error)
        if isinstance(error, HTTPError):
            report["http_status"] = error.code
        print(f"IndexNow notification failed: {error}", file=sys.stderr)
    finally:
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"IndexNow: {report['status']}; {report['url_count']} URLs; report: {report_file}")
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"checkpoint={str(report['checkpoint_advanced']).lower()}\n")
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write(f"### IndexNow notification\n\nStatus: **{report['status']}**. "
                              f"Selected URLs: **{report['url_count']}**. "
                              f"Selection: `{report.get('selection', 'unavailable')}`.\n\n"
                              "HTTP 200 acknowledges receipt; HTTP 202 also leaves key validation pending. "
                              "Neither confirms crawling, indexing, rankings, or LLM citations. "
                              "See the IndexNow report artifact for the submitted URLs and any error.\n")
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--submit", action="store_true", help="Send notification; omitted by default")
    parser.add_argument("--all", action="store_true", help="Explicitly resubmit the full current sitemap")
    args = parser.parse_args()
    return execute(args.repo, args.state_file, args.report, args.submit, args.all)


if __name__ == "__main__":
    sys.exit(main())
