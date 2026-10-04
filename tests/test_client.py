"""Unit tests for the client: what it sends and how it reads what comes back,
against an opener that answers from a script. Nothing here reaches a network.

    python tests/test_client.py
"""

import io
import json
import os
import sys
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from everpod_ai import Everpod, EverpodError, __version__  # noqa: E402

POD = {
    "id": "5f0c1a52-8f1e-4d0b-9a57-3f6f2f7c1e9a",
    "name": "Otto",
    "harness": "openclaw",
    "status": "awaiting_payment",
    "created_at": "2026-10-03T09:12:44.512345+00:00",
    "url": None,
    "pay_url": "https://everpod.ai/create?pod=5f0c1a52-8f1e-4d0b-9a57-3f6f2f7c1e9a",
    "plan": None,
    "subscription": None,
}


class Answer(io.BytesIO):
    """A response the client can use as a context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Scripted:
    """An opener that records each request and answers ``status`` with ``body``."""

    def __init__(self, status, body):
        self.status = status
        self.raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append((request, timeout))
        if self.status >= 400:
            raise urllib.error.HTTPError(
                request.full_url, self.status, "refused", hdrs=None, fp=io.BytesIO(self.raw)
            )
        return Answer(self.raw)


def client(opener, **extra):
    return Everpod("everpod_test", opener=opener, **extra)


class ClientTests(unittest.TestCase):
    def test_no_key_says_where_a_key_is_made(self):
        with self.assertRaises(EverpodError) as raised:
            Everpod("")
        self.assertEqual(raised.exception.code, "missing_api_key")
        self.assertIn("/account/keys", raised.exception.message)

    def test_list_pods_asks_the_list_route_with_the_key(self):
        opener = Scripted(200, {"pods": [POD]})
        self.assertEqual(client(opener).list_pods(), [POD])
        request, timeout = opener.calls[0]
        self.assertEqual(request.full_url, "https://everpod.ai/api/v1/pods")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer everpod_test")
        self.assertEqual(request.get_header("User-agent"), f"everpod-sdk-python/{__version__}")
        self.assertIsNone(request.data)
        self.assertEqual(timeout, 30.0)

    def test_get_pod_escapes_its_id(self):
        opener = Scripted(200, {"pod": POD})
        self.assertEqual(client(opener).get_pod(POD["id"]), POD)
        self.assertEqual(opener.calls[0][0].full_url, f"https://everpod.ai/api/v1/pods/{POD['id']}")
        client(opener).get_pod("a/b")
        self.assertEqual(opener.calls[1][0].full_url, "https://everpod.ai/api/v1/pods/a%2Fb")

    def test_start_pod_posts_the_name_as_json(self):
        opener = Scripted(201, {"pod": POD})
        self.assertEqual(client(opener).start_pod("Otto"), POD)
        request = opener.calls[0][0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"name": "Otto"})

    def test_a_base_url_with_a_trailing_slash(self):
        opener = Scripted(200, {"pods": []})
        client(opener, base_url="http://localhost:3111/").list_pods()
        self.assertEqual(opener.calls[0][0].full_url, "http://localhost:3111/api/v1/pods")

    def test_a_refusal_carries_the_apis_code_status_and_sentence(self):
        opener = Scripted(
            404, {"error": {"code": "not_found", "message": "No pod with that id on this account."}}
        )
        with self.assertRaises(EverpodError) as raised:
            client(opener).get_pod("nope")
        self.assertEqual(raised.exception.code, "not_found")
        self.assertEqual(raised.exception.status, 404)
        self.assertEqual(raised.exception.message, "No pod with that id on this account.")

    def test_an_answer_that_is_not_the_apis_json_still_says_its_status(self):
        opener = Scripted(502, b"<html>bad gateway</html>")
        with self.assertRaises(EverpodError) as raised:
            client(opener).list_pods()
        self.assertEqual(raised.exception.code, "http_error")
        self.assertEqual(raised.exception.status, 502)
        self.assertIn("502", raised.exception.message)

    def test_a_json_answer_of_another_shape_still_says_its_status(self):
        opener = Scripted(403, {"ok": False, "error": "forbidden"})
        with self.assertRaises(EverpodError) as raised:
            client(opener).list_pods()
        self.assertEqual(raised.exception.code, "http_error")
        self.assertEqual(raised.exception.status, 403)

    def test_a_request_that_never_completes_is_a_network_error(self):
        def failing(request, timeout=None):
            raise urllib.error.URLError("no route to host")

        with self.assertRaises(EverpodError) as raised:
            client(failing).list_pods()
        self.assertEqual(raised.exception.code, "network_error")
        self.assertIsInstance(raised.exception.__cause__, urllib.error.URLError)


if __name__ == "__main__":
    unittest.main()
