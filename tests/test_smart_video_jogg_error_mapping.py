"""HTTP error propagation contracts for the Smart Video Jogg bridge."""

from __future__ import annotations

import time
import unittest
from pathlib import Path

import httpx


from smartvideo_test_runtime import RUNTIME_ROOT  # noqa: F401

from backend.api.jogg import _jogg_capability_error  # noqa: E402
from backend.services.jogg_runtime import (  # noqa: E402
    InMemoryCredentialStore,
    JoggPluginClient,
    JoggUpstreamError,
)


class SmartVideoJoggErrorMappingTests(unittest.TestCase):
    def test_client_preserves_upstream_payment_required(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual("/plugin/v1/audio/tts/synthesize", request.url.path)
            return httpx.Response(
                402,
                json={
                    "code": 40200,
                    "error": "insufficient_credit",
                    "message": "insufficient API credit",
                },
            )

        client = JoggPluginClient(
            base_url="https://jogg.test",
            credential_store=InMemoryCredentialStore.with_tokens(
                "access-token",
                "refresh-token",
                expires_at=time.time() + 3600,
            ),
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        with self.assertRaises(JoggUpstreamError) as raised:
            client.synthesize_tts("test", idempotency_key="tts-error-mapping")

        self.assertEqual(raised.exception.status_code, 402)
        self.assertEqual(raised.exception.error_code, "insufficient_credit")
        self.assertEqual(str(raised.exception), "insufficient API credit")

    def test_loopback_preserves_safe_upstream_4xx(self) -> None:
        mapped = _jogg_capability_error(
            JoggUpstreamError(402, "insufficient_credit", "insufficient API credit")
        )

        self.assertEqual(mapped.status_code, 402)
        self.assertEqual(mapped.detail, "insufficient API credit")

    def test_loopback_keeps_unknown_runtime_failures_as_bad_gateway(self) -> None:
        mapped = _jogg_capability_error(RuntimeError("the request could not be completed"))

        self.assertEqual(mapped.status_code, 502)


if __name__ == "__main__":
    unittest.main()
