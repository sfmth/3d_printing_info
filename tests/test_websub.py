"""Exercise feed selection and WebSub publication receipts without network access."""
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
from urllib.parse import parse_qs

SPEC = importlib.util.spec_from_file_location("notify_websub", Path(__file__).resolve().parents[1] / "scripts/notify_websub.py")
websub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(websub)


def feed_bytes(filename, title="3D Printing Info"):
    links = (f'<atom:link rel="self" type="{websub.FEEDS[filename]}" href="{websub.SITE}{filename}"/>'
             f'<atom:link rel="hub" href="{websub.HUB}"/>')
    if filename == "feed.xml":
        return (f'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
                f'<channel><title>{title}</title>{links}</channel></rss>').encode()
    return (f'<atom:feed xmlns:atom="http://www.w3.org/2005/Atom">'
            f'<atom:title>{title}</atom:title>{links}</atom:feed>').encode()


def response(url, data=b"", status=200):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status = status
    result.geturl.return_value = url
    result.read.return_value = data
    return result


class DiscoveryTests(unittest.TestCase):
    def test_correct_rss_and_atom_discovery(self):
        for filename in websub.FEEDS:
            websub.validate_feed(feed_bytes(filename), filename, websub.feed_url(filename))

    def test_refuse_wrong_self_hub_or_format(self):
        url = websub.SITE + "feed.xml"
        valid = feed_bytes("feed.xml")
        bad = [valid.replace(url.encode(), (url + "?tracking=1").encode()),
               valid.replace(websub.HUB.encode(), b"https://other.example/"),
               valid.replace(b'application/rss+xml', b'application/atom+xml'),
               valid.replace(b'rel="hub"', b'rel="alternate"'),
               valid.replace(b'<channel>', b'<channel><atom:link rel="hub" href="https://pubsubhubbub.appspot.com/"/>'),
               valid.replace(b'version="2.0"', b'version="1.0"'),
               b'<!DOCTYPE rss [<!ENTITY local "value">]>' + valid]
        for source in bad:
            with self.subTest(source=source), self.assertRaises(ValueError):
                websub.validate_feed(source, "feed.xml", url)
        with self.assertRaises(ValueError):
            websub.validate_feed(valid, "feed.xml", "https://other.example/feed.xml")
        with self.assertRaises(ValueError):
            websub.validate_feed(valid, "feed.xml", url, "https://other.example/")

    def test_only_canonical_project_feed_files(self):
        for filename in ["../feed.xml", "feed.xml?secret=1", "https://other.example/feed.xml", "elsewhere.xml"]:
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                websub.feed_url(filename)

    def test_publication_form_encodes_repeated_url_values(self):
        urls = [websub.SITE + "feed.xml", websub.SITE + "atom.xml"]
        encoded = websub.publication_form(urls)
        self.assertEqual(parse_qs(encoded.decode()), {"hub.mode": ["publish"], "hub.url": urls})
        self.assertIn(b"https%3A%2F%2F", encoded)
        # Form encoding must never interpret an ampersand within a value as a field.
        escaped = parse_qs(websub.publication_form([urls[0] + "?a=1&b=two words"]).decode())
        self.assertEqual(escaped["hub.url"], [urls[0] + "?a=1&b=two words"])
        self.assertNotIn("b", escaped)

    def test_redirect_handler_refuses_changed_destinations(self):
        self.assertIsNone(websub.NoRedirects().redirect_request(None, None, 302, "", {}, "https://other.example/"))


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "user.name", "WebSub Test")
        for filename in websub.FEEDS:
            (self.repo / filename).write_bytes(feed_bytes(filename))
        self.base = self.commit()
        self.report = self.repo / "reports" / "websub.json"

    def run_git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True,
                                       stderr=subprocess.DEVNULL).strip()

    def commit(self):
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "fixture")
        return self.run_git("rev-parse", "HEAD")

    def update(self, *filenames):
        for filename in filenames:
            (self.repo / filename).write_bytes(feed_bytes(filename, "Updated catalog"))
        self.commit()

    def execute(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = websub.execute(self.repo, self.report, **kwargs)
        return code, json.loads(self.report.read_text())

    def public_responses(self, filenames):
        return [response(websub.feed_url(filename), (self.repo / filename).read_bytes())
                for filename in filenames]

    def test_bootstrap_dry_run_is_network_free(self):
        with patch.object(websub, "build_opener") as build:
            code, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "dry-run")
        self.assertEqual(report["selection"], "bootstrap-unavailable-history")
        self.assertEqual(report["urls"], [websub.SITE + "feed.xml", websub.SITE + "atom.xml"])
        build.assert_not_called()

    def test_asset_only_deployment_does_not_publish(self):
        (self.repo / "style.css").write_text("body { color: black; }")
        self.commit()
        with patch.object(websub, "build_opener") as build:
            code, report = self.execute(submit=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "no-changed-feeds")
        self.assertEqual(report["feed_count"], 0)
        self.assertEqual(report["notification"]["status"], "not-sent")
        build.assert_not_called()

    def test_only_changed_feed_selected(self):
        self.update("atom.xml")
        code, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(report["urls"], [websub.SITE + "atom.xml"])
        self.assertEqual(report["selection"], "changed-committed-feeds")

    def test_explicit_push_baseline_covers_feed_change_before_asset_only_tip(self):
        self.update("feed.xml")
        (self.repo / "style.css").write_text("body { color: navy; }")
        self.commit()
        code, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(report["urls"], [])
        code, report = self.execute(baseline_ref=self.base)
        self.assertEqual(code, 0)
        self.assertEqual(report["baseline_commit"], self.base)
        self.assertEqual(report["urls"], [websub.SITE + "feed.xml"])

    def test_local_generation_must_match_deployed_commit(self):
        (self.repo / "feed.xml").write_bytes(feed_bytes("feed.xml", "Uncommitted edit"))
        with patch.object(websub, "build_opener") as build:
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertIn("differs from commit", report["error"])
        build.assert_not_called()

    def test_uncommitted_first_build_can_preview_but_not_submit(self):
        self.run_git("rm", "feed.xml", "atom.xml")
        (self.repo / "index.html").write_text("<h1>Catalog</h1>")
        self.commit()
        for filename in websub.FEEDS:
            (self.repo / filename).write_bytes(feed_bytes(filename))
        code, report = self.execute()
        self.assertEqual(code, 0)
        self.assertEqual(report["selection"], "bootstrap-uncommitted-feeds")
        self.assertFalse(report["feeds"][0]["local_matches_commit"])
        with patch.object(websub, "build_opener") as build:
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertIn("must be committed", report["error"])
        build.assert_not_called()

    def test_public_verified_bytes_then_one_form_post_accepts_empty_204(self):
        self.update(*websub.FEEDS)
        opener = MagicMock()
        opener.open.side_effect = [*self.public_responses(websub.FEEDS), response(websub.HUB, status=204)]
        with patch.object(websub, "build_opener", return_value=opener):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "notification-received")
        self.assertEqual(report["notification"], {"status": "received", "http_status": 204})
        self.assertEqual(opener.open.call_count, 3)
        for call in opener.open.call_args_list:
            self.assertLessEqual(call.kwargs["timeout"], 20)
        request = opener.open.call_args_list[-1].args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, websub.HUB)
        self.assertEqual(request.get_header("Content-type"), "application/x-www-form-urlencoded")
        self.assertEqual(parse_qs(request.data.decode()), {"hub.mode": ["publish"], "hub.url": report["urls"]})
        for feed in report["feeds"]:
            self.assertEqual(feed["sha256"], feed["public_sha256"])
            self.assertEqual(feed["status"], "notification-received")
            self.assertEqual(feed["notification_http_status"], 204)
        self.assertIn("does not confirm", report["receipt_note"])

    def test_stale_second_public_feed_preserves_partial_verification_and_denies_post(self):
        self.update(*websub.FEEDS)
        opener = MagicMock()
        opener.open.side_effect = [*self.public_responses(["feed.xml"]),
                                    response(websub.SITE + "atom.xml", feed_bytes("atom.xml"))]
        with patch.object(websub, "build_opener", return_value=opener):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertEqual(opener.open.call_count, 2)
        self.assertEqual(report["notification"]["status"], "not-sent")
        self.assertEqual(report["feeds"][0]["status"], "verified")
        self.assertEqual(report["feeds"][1]["status"], "verification-error")
        self.assertNotEqual(report["feeds"][1]["public_sha256"], report["feeds"][1]["sha256"])
        self.assertTrue(all(call.args[0].get_method() == "GET" for call in opener.open.call_args_list))

    def test_public_fetch_failure_never_posts_or_retries(self):
        self.update(*websub.FEEDS)
        opener = MagicMock()
        opener.open.side_effect = HTTPError(websub.SITE + "feed.xml", 503, "Unavailable", {}, None)
        with patch.object(websub, "build_opener", return_value=opener):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(report["feeds"][0]["public_http_status"], 503)
        self.assertEqual(report["feeds"][1]["status"], "not-verified")
        self.assertEqual(report["notification"]["status"], "not-sent")

    def test_redirected_public_feed_never_posts(self):
        self.update("feed.xml")
        opener = MagicMock()
        opener.open.return_value = response("https://other.example/feed.xml", (self.repo / "feed.xml").read_bytes())
        with patch.object(websub, "build_opener", return_value=opener):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertIn("changed URL", report["error"])
        self.assertEqual(opener.open.call_count, 1)

    def test_hub_failure_has_exact_status_and_no_post_retry(self):
        self.update(*websub.FEEDS)
        opener = MagicMock()
        opener.open.side_effect = [*self.public_responses(websub.FEEDS),
                                    HTTPError(websub.HUB, 503, "Unavailable", {}, None)]
        with patch.object(websub, "build_opener", return_value=opener):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual(report["notification"]["http_status"], 503)
        self.assertEqual(report["notification"]["status"], "error")
        self.assertTrue(all(feed["status"] == "verified" for feed in report["feeds"]))

    def test_uncertain_post_transport_failure_is_not_retried(self):
        self.update("feed.xml")
        opener = MagicMock()
        opener.open.side_effect = [*self.public_responses(["feed.xml"]), URLError("connection lost")]
        with patch.object(websub, "build_opener", return_value=opener):
            code, report = self.execute(submit=True)
        self.assertEqual(code, 1)
        self.assertEqual(opener.open.call_count, 2)
        self.assertEqual(report["notification"]["status"], "error")
        self.assertIsNone(report["notification"]["http_status"])


if __name__ == "__main__":
    unittest.main()
