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

    def test_pair_manifest_paths_and_hashes_stay_within_comparison_scope(self):
        pages = {"compare/": "c" * 64,
                 "compare/materials/asa-vs-pla.html": "a" * 64,
                 "compare/materials/pla/": "d" * 64,
                 "compare/printers/": "b" * 64,
                 "compare/printers/bambu-a1/": "e" * 64}
        self.assertEqual(indexnow.pair_hashes(json.dumps({"version": 1, "pages": pages})),
                         {indexnow.SITE + path: value for path, value in pages.items()})
        for invalid in [None, {"version": True, "pages": {}}, {"version": 2, "pages": {}},
                        {"version": 1, "pages": []},
                        *({"version": 1, "pages": {path: "a" * 64}} for path in
                          ["materials/pla.html", "compare/other/", "compare/materials/../escape.html",
                           "compare/materials/pla.html?view=1", "compare/materials//pla.html"]),
                        {"version": 1, "pages": {"compare/materials/": "not-a-hash"}}]:
            with self.subTest(manifest=invalid), self.assertRaises(ValueError):
                indexnow.pair_hashes(json.dumps(invalid))


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

    def pair_fixture(self):
        """Only the manifest and sitemap are committed; pair HTML is build output."""
        paths = ["compare/", "compare/materials/", "compare/materials/pla/",
                 "compare/materials/asa-vs-pla.html"]
        for path in paths:
            target = self.repo / indexnow.url_file(indexnow.SITE + path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<html>generated pair content</html>")
        (self.repo / ".gitignore").write_text("compare/\n")
        manifest = self.repo / indexnow.PAIR_MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        pages = {path: "a" * 64 for path in paths}
        manifest.write_text(json.dumps({"version": 1, "pages": pages}))
        (self.repo / "sitemap.xml").write_text(xml(["", "materials/", "materials/pla.html",
                                                  "materials/old.html", *paths]))
        return self.commit(), manifest, pages

    def test_manifest_only_change_selects_ignored_pair_and_index_without_duplicates(self):
        baseline, manifest, pages = self.pair_fixture()
        for relative in pages:
            (self.repo / indexnow.url_file(indexnow.SITE + relative)).write_text("<html>updated pair</html>")
        manifest.write_text(json.dumps({"version": 1, "pages": {path: "b" * 64 for path in pages}}))
        head = self.commit()
        self.assertEqual(self.run_git("diff", "--name-only", baseline, head), indexnow.PAIR_MANIFEST)
        urls, mode = indexnow.select_urls(self.repo, baseline, head)
        self.assertEqual(urls, sorted(indexnow.SITE + path for path in pages))
        self.assertEqual(mode, "changed-and-removed-pages")

    def test_unchanged_pair_hashes_and_lastmod_only_do_not_select_pair_pages(self):
        baseline, _, _ = self.pair_fixture()
        sitemap = self.repo / "sitemap.xml"
        sitemap.write_text(sitemap.read_text().replace("</loc>", "</loc><lastmod>2026-10-31</lastmod>"))
        head = self.commit()
        self.assertEqual(indexnow.select_urls(self.repo, baseline, head)[0], [])

    def test_new_pair_manifest_and_sitemap_additions_are_deduplicated(self):
        head, _, pages = self.pair_fixture()
        urls, _ = indexnow.select_urls(self.repo, self.base, head)
        self.assertEqual(urls, sorted(indexnow.SITE + path for path in pages))

    def test_manifest_hash_outside_current_sitemap_is_not_submitted(self):
        baseline, manifest, pages = self.pair_fixture()
        pages["compare/materials/not-published.html"] = "b" * 64
        manifest.write_text(json.dumps({"version": 1, "pages": pages}))
        head = self.commit()
        self.assertEqual(indexnow.select_urls(self.repo, baseline, head)[0], [])

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

    def large_selection(self, size=12049):
        return [indexnow.SITE + f"compare/materials/left-{i}-vs-right.html" for i in range(size)]

    def test_large_dry_run_plans_batches_without_network_or_checkpoint(self):
        urls = self.large_selection()
        with patch.object(indexnow, "select_urls", return_value=(urls, "bootstrap-no-checkpoint")), \
                patch.object(indexnow, "receipt") as submit:
            code, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(report["url_count"], len(urls))
        self.assertEqual(report["urls"], urls)
        self.assertEqual(report["batch_count"], 2)
        self.assertEqual([batch["url_count"] for batch in report["batches"]], [10000, 2049])
        self.assertTrue(all(batch["status"] == "dry-run" for batch in report["batches"]))
        self.assertEqual(report["accepted_url_count"], 0)
        self.assertFalse(self.state.exists())
        submit.assert_not_called()

    def test_large_selection_submits_each_url_once_and_waits_for_all_receipts(self):
        urls = self.large_selection()
        self.checkpoint()
        (self.repo / "index.html").write_text("<html>new commit</html>")
        head = self.commit()
        saved = self.state.read_bytes()
        observed_payloads = []

        def accepted(payload):
            self.assertEqual(self.state.read_bytes(), saved, "checkpoint must wait for the last receipt")
            observed_payloads.append(payload)
            return (200, "received") if len(observed_payloads) == 1 else (202, "received-key-validation-pending")

        with patch.object(indexnow, "select_urls", return_value=(urls, "changed-and-removed-pages")), \
                patch.object(indexnow, "receipt", side_effect=accepted):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 0)
        self.assertEqual([len(p["urlList"]) for p in observed_payloads], [10000, 2049])
        self.assertEqual([url for p in observed_payloads for url in p["urlList"]], urls)
        self.assertTrue(all(p["host"] == "sfmth.github.io" and p["key"] == indexnow.KEY
                            and p["keyLocation"] == indexnow.KEY_LOCATION for p in observed_payloads))
        self.assertEqual(report["status"], "received-key-validation-pending")
        self.assertEqual(report["http_status"], 202)
        self.assertEqual(report["accepted_batches"], 2)
        self.assertEqual(report["accepted_url_count"], len(urls))
        self.assertEqual([batch["http_status"] for batch in report["batches"]], [200, 202])
        self.assertEqual(indexnow.read_checkpoint(self.state), head)

    def test_partial_batch_failure_keeps_checkpoint_and_stops_remaining_requests(self):
        urls = self.large_selection(20001)
        self.checkpoint()
        saved = self.state.read_bytes()
        failure = HTTPError(indexnow.ENDPOINT, 429, "rate limited", {}, None)
        with patch.object(indexnow, "select_urls", return_value=(urls, "changed-and-removed-pages")), \
                patch.object(indexnow, "receipt", side_effect=[(200, "received"), failure]) as submit:
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertEqual(submit.call_count, 2)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["url_count"], len(urls))
        self.assertEqual(report["urls"], urls)
        self.assertEqual(report["batch_count"], 3)
        self.assertEqual(report["accepted_batches"], 1)
        self.assertEqual(report["accepted_url_count"], 10000)
        self.assertEqual([batch["status"] for batch in report["batches"]],
                         ["received", "error", "not-submitted"])
        self.assertEqual(report["batches"][1]["http_status"], 429)
        self.assertFalse(report["checkpoint_advanced"])
        self.assertEqual(self.state.read_bytes(), saved)

    def test_exact_request_limit_does_not_create_an_empty_batch(self):
        urls = self.large_selection(10000)
        with patch.object(indexnow, "select_urls", return_value=(urls, "manual-full-sitemap")), \
                patch.object(indexnow, "receipt", return_value=(200, "received")) as submit:
            code, report = self.execute(submit=True)
        self.assertEqual(code, 0)
        self.assertEqual(submit.call_count, 1)
        self.assertEqual(report["batch_count"], 1)
        self.assertEqual(report["accepted_url_count"], 10000)

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
