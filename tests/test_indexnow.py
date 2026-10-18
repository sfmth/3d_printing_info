"""Exercise project scoping, Git selection, and receipts without network access."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

SPEC = importlib.util.spec_from_file_location("notify_indexnow", Path(__file__).resolve().parents[1] / "scripts/notify_indexnow.py")
indexnow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(indexnow)


def xml(paths):
    return '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(
        f'<url><loc>{indexnow.SITE}{path}</loc></url>' for path in paths) + '</urlset>'


class ScopeTests(unittest.TestCase):
    def test_project_home_and_nested_directory_mapping(self):
        self.assertEqual(indexnow.url_file(indexnow.SITE), "index.html")
        self.assertEqual(indexnow.url_file(indexnow.SITE + "materials/"), "materials/index.html")
        self.assertEqual(indexnow.url_file(indexnow.SITE + "materials/pla.html"), "materials/pla.html")

    def test_reject_other_hosts_project_prefixes_and_path_escapes(self):
        bad = ["https://other.example/3d_printing_info/", "https://sfmth.github.io/3d_printing_info_other/",
               "http://sfmth.github.io/3d_printing_info/", "https://sfmth.github.io/elsewhere/",
               indexnow.SITE + "../other.html", indexnow.SITE + "%2e%2e/other.html",
               indexnow.SITE + "materials%2fpla.html", indexnow.SITE + "materials//pla.html",
               indexnow.SITE + "materials\\pla.html", indexnow.SITE + "pla.html?sort=1",
               indexnow.SITE + "pla.html#section", indexnow.SITE + "sitemap.xml"]
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                indexnow.url_file(url)

    def test_empty_and_duplicate_sitemaps_fail(self):
        for source in [xml([]), xml(["", ""])]:
            with self.assertRaises(ValueError):
                indexnow.sitemap(source)


class GitSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "IndexNow Test")
        for path in ("index.html", "materials/index.html", "materials/pla.html", "materials/old.html"):
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text("<html>original</html>")
        (self.repo / "sitemap.xml").write_text(xml(["", "materials/", "materials/pla.html", "materials/old.html"]))
        (self.repo / (indexnow.KEY + ".txt")).write_text(indexnow.KEY + "\n")
        self.base = self.commit()
        self.state = self.repo / "private" / "checkpoint.json"
        self.report = self.repo / "private" / "report.json"

    def run_git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self):
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "fixture")
        return self.run_git("rev-parse", "HEAD")

    def checkpoint(self):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text(json.dumps({"site": indexnow.SITE, "key": indexnow.KEY, "commit": self.base}))

    def execute(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                patch.dict(indexnow.os.environ, {"GITHUB_OUTPUT": "", "GITHUB_STEP_SUMMARY": ""}):
            result = indexnow.execute(self.repo, self.state, self.report, **kwargs)
        return result, json.loads(self.report.read_text())

    def test_initial_bootstrap_and_explicit_full_resubmission(self):
        urls, mode = indexnow.select_urls(self.repo, None, self.base)
        self.assertEqual(len(urls), 4)
        self.assertEqual(mode, "bootstrap-no-checkpoint")
        self.assertEqual(indexnow.select_urls(self.repo, self.base, self.base, True)[1], "manual-full-sitemap")

    def test_only_changed_added_and_removed_pages_are_selected(self):
        (self.repo / "materials/pla.html").write_text("<html>changed</html>")
        (self.repo / "materials/new.html").write_text("<html>new</html>")
        (self.repo / "materials/old.html").unlink()
        (self.repo / "README.md").write_text("maintenance")
        (self.repo / "sitemap.xml").write_text(xml(["", "materials/", "materials/pla.html", "materials/new.html"]))
        head = self.commit()
        urls, mode = indexnow.select_urls(self.repo, self.base, head)
        self.assertEqual(urls, [indexnow.SITE + "materials/" + name + ".html" for name in ("new", "old", "pla")])
        self.assertEqual(mode, "changed-and-removed-pages")

    def test_directory_html_change_uses_canonical_directory_url(self):
        (self.repo / "materials/index.html").write_text("<html>changed</html>")
        head = self.commit()
        self.assertEqual(indexnow.select_urls(self.repo, self.base, head)[0], [indexnow.SITE + "materials/"])

    def test_rollback_compares_against_latest_acknowledged_commit(self):
        (self.repo / "materials/pla.html").write_text("<html>newer content</html>")
        (self.repo / "materials/new.html").write_text("<html>newer page</html>")
        (self.repo / "materials/old.html").unlink()
        (self.repo / "sitemap.xml").write_text(xml(["", "materials/", "materials/pla.html", "materials/new.html"]))
        newer = self.commit()
        self.run_git("checkout", "--detach", self.base)
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text(json.dumps({"site": indexnow.SITE, "key": indexnow.KEY, "commit": newer}))
        with patch.object(indexnow, "receipt", return_value=(200, "received")) as submit:
            code, report = self.execute(submit=True)
        expected = [indexnow.SITE + "materials/" + name + ".html" for name in ("new", "old", "pla")]
        self.assertEqual(code, 0)
        self.assertEqual(report["baseline_commit"], newer)
        self.assertEqual(report["selection"], "changed-and-removed-pages")
        self.assertEqual(submit.call_args.args[0]["urlList"], expected)
        self.assertEqual(indexnow.read_checkpoint(self.state), self.base)

    def test_docs_assets_and_lastmod_only_do_not_resubmit_all_pages(self):
        (self.repo / "README.md").write_text("docs changed")
        (self.repo / "style.css").write_text("body { color: black }")
        (self.repo / "sitemap.xml").write_text((self.repo / "sitemap.xml").read_text().replace("</loc>", "</loc><lastmod>2026-10-18</lastmod>"))
        head = self.commit()
        self.assertEqual(indexnow.select_urls(self.repo, self.base, head)[0], [])

    def test_generated_footer_date_alone_is_ignored_but_source_dates_are_not(self):
        footer = '<footer><span>Catalog values retain their original source dates. Page revision: 2026-10-17.</span></footer>'
        (self.repo / "index.html").write_text('<p>Source checked: 2026-10-17</p>' + footer)
        base = self.commit()
        (self.repo / "index.html").write_text('<p>Source checked: 2026-10-17</p>' + footer.replace("2026-10-17", "2026-10-18"))
        head = self.commit()
        self.assertEqual(indexnow.select_urls(self.repo, base, head)[0], [])
        (self.repo / "index.html").write_text('<p>Source checked: 2026-10-18</p>' + footer.replace("2026-10-17", "2026-10-18"))
        head = self.commit()
        self.assertEqual(indexnow.select_urls(self.repo, base, head)[0], [indexnow.SITE])

    def test_unavailable_checkpoint_history_bootstraps(self):
        urls, mode = indexnow.select_urls(self.repo, "1" * 40, self.base)
        self.assertEqual(len(urls), 4)
        self.assertEqual(mode, "bootstrap-unavailable-history")

    def test_missing_or_out_of_scope_page_aborts(self):
        (self.repo / "materials/pla.html").unlink()
        with self.assertRaises(ValueError):
            indexnow.select_urls(self.repo, None, self.base)
        (self.repo / "sitemap.xml").write_text(xml(["../other.html"]))
        with self.assertRaises(ValueError):
            indexnow.select_urls(self.repo, None, self.base)

    def test_invalid_or_other_site_checkpoint_is_ignored(self):
        self.checkpoint()
        state = json.loads(self.state.read_text())
        for field, value in [("site", "https://other.example/"), ("key", "wrong"), ("commit", 123), ("commit", "bad")]:
            self.state.write_text(json.dumps({**state, field: value}))
            self.assertIsNone(indexnow.read_checkpoint(self.state))

    def test_dry_run_never_calls_network_or_writes_checkpoint(self):
        with patch.object(indexnow, "receipt") as submit:
            code, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "dry-run")
        self.assertFalse(self.state.exists())
        submit.assert_not_called()

    def test_success_receipts_advance_checkpoint_without_claiming_indexing(self):
        for http, status in [(200, "received"), (202, "received-key-validation-pending")]:
            with self.subTest(http=http), patch.object(indexnow, "receipt", return_value=(http, status)) as submit:
                code, report = self.execute(submit=True, force_all=True)
                payload = submit.call_args.args[0]
            self.assertEqual(code, 0)
            self.assertEqual(payload["keyLocation"], indexnow.KEY_LOCATION)
            self.assertEqual(payload["host"], "sfmth.github.io")
            self.assertEqual(report["status"], status)
            self.assertEqual(report["http_status"], http)
            self.assertEqual(indexnow.read_checkpoint(self.state), self.base)

    def test_provider_and_network_errors_keep_checkpoint_for_next_deploy(self):
        self.checkpoint()
        (self.repo / "index.html").write_text("<html>updated</html>")
        self.commit()
        saved = self.state.read_bytes()
        for error in [HTTPError(indexnow.ENDPOINT, 429, "rate limited", {}, None),
                      HTTPError(indexnow.ENDPOINT, 503, "temporary outage", {}, None),
                      URLError("timeout"), ValueError("deployed key mismatch")]:
            with self.subTest(error=str(error)), patch.object(indexnow, "receipt", side_effect=error):
                code, report = self.execute(submit=True)
            self.assertEqual(code, 1)
            self.assertEqual(report["status"], "error")
            self.assertFalse(report["checkpoint_advanced"])
            self.assertEqual(self.state.read_bytes(), saved)
            self.assertEqual(report["urls"], [indexnow.SITE])
        # A later deployment still selects the missed page and can acknowledge it.
        with patch.object(indexnow, "receipt", return_value=(200, "received")):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 0)
        self.assertTrue(report["checkpoint_advanced"])

    def test_no_change_deployment_advances_checkpoint_without_network(self):
        (self.repo / "README.md").write_text("maintenance")
        head = self.commit()
        self.checkpoint()
        with patch.object(indexnow, "receipt") as submit:
            code, report = self.execute(submit=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "no-changed-pages")
        self.assertEqual(indexnow.read_checkpoint(self.state), head)
        submit.assert_not_called()


class HTTPTests(unittest.TestCase):
    def response(self, status=200, key=indexnow.KEY):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = key.encode()
        return response

    def test_key_is_verified_before_post_and_receipt_status_preserved(self):
        for status, label in [(200, "received"), (202, "received-key-validation-pending")]:
            opener = MagicMock()
            opener.open.side_effect = [self.response(), self.response(status)]
            with patch.object(indexnow, "build_opener", return_value=opener):
                self.assertEqual(indexnow.receipt({"urlList": [indexnow.SITE]}), (status, label))
            calls = opener.open.call_args_list
            self.assertEqual(calls[0].args[0].full_url, indexnow.KEY_LOCATION)
            self.assertEqual(calls[1].args[0].full_url, indexnow.ENDPOINT)
            self.assertEqual(calls[1].args[0].get_method(), "POST")

    def test_wrong_key_prevents_post(self):
        opener = MagicMock()
        opener.open.return_value = self.response(key="wrong")
        with patch.object(indexnow, "build_opener", return_value=opener), self.assertRaises(ValueError):
            indexnow.receipt({})
        self.assertEqual(opener.open.call_count, 1)

    def test_redirects_are_not_followed(self):
        self.assertIsNone(indexnow.NoRedirects().redirect_request(None, None, 302, "redirect", {}, "https://elsewhere.example/"))


if __name__ == "__main__":
    unittest.main()
