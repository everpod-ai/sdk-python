"""The Everpod API's Python client: the operations a key can call
(https://everpod.ai/docs/api) and nothing else. Standard library only.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, List, Optional, TypedDict

__version__ = "0.1.0"
__all__ = ["Everpod", "EverpodError", "Pod", "PodSubscription", "__version__"]

DEFAULT_BASE_URL = "https://everpod.ai"


class PodSubscription(TypedDict):
    status: str
    current_period_end: Optional[str]  # when the paid period ends
    cancel_at_period_end: bool  # whether the subscription is set to end then


class Pod(TypedDict):
    """A pod. What each status means: https://everpod.ai/docs/api"""

    id: str
    name: str  # the name of the pod's agent
    harness: str  # the agent software the pod runs
    status: str  # awaiting_payment, building, setup_delayed, ready, needs_attention, stopped
    created_at: str
    url: Optional[str]  # the pod's page on everpod.ai; None until the pod is paid for
    pay_url: Optional[str]  # where the pod's owner pays, while the status is awaiting_payment
    plan: Optional[str]  # None until the pod is paid for
    subscription: Optional[PodSubscription]  # None until the pod is paid for


class EverpodError(Exception):
    """What the API refused, or what stopped the request reaching it.

    ``message`` is the API's own sentence, written to be passed on to the
    account's owner; ``code`` and ``status`` are the refusal's
    (https://everpod.ai/docs/api).
    """

    def __init__(self, message: str, *, code: Optional[str] = None, status: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class Everpod:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        opener: Optional[Callable[..., Any]] = None,
    ):
        if not api_key:
            raise EverpodError(
                "An Everpod API key is needed: Everpod(api_key=...). The account's owner "
                "makes one at https://everpod.ai/account/keys.",
                code="missing_api_key",
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._open = opener or urllib.request.urlopen

    def list_pods(self) -> List[Pod]:
        """The pods on the account, oldest first."""
        return self._request("GET", "/pods")["pods"]

    def get_pod(self, pod_id: str) -> Pod:
        """One pod by its id."""
        return self._request("GET", "/pods/" + urllib.parse.quote(str(pod_id), safe=""))["pod"]

    def start_pod(self, name: str) -> Pod:
        """Start a pod under the name its owner wants for their agent.

        Nothing is charged: the pod stays unpaid until its owner pays at
        ``pay_url``.
        """
        return self._request("POST", "/pods", {"name": name})["pod"]

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "User-Agent": f"everpod-sdk-python/{__version__}",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/api/v1{path}", data=data, headers=headers, method=method
        )
        try:
            with self._open(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as refused:
            try:
                error = json.loads(refused.read().decode("utf-8")).get("error")
            except Exception:
                error = None
            # The API's refusals carry a code and a sentence; anything else that
            # answers in its place is reported by its status alone.
            if not isinstance(error, dict):
                error = {}
            raise EverpodError(
                error.get("message") or f"Everpod answered {refused.code}.",
                code=error.get("code") or "http_error",
                status=refused.code,
            ) from None
        except (urllib.error.URLError, OSError) as failed:
            reason = getattr(failed, "reason", failed)
            raise EverpodError(
                f"The request to Everpod did not complete: {reason}", code="network_error"
            ) from failed
