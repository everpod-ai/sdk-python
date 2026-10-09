# Everpod SDK for Python

The official Python client for the [Everpod API](https://everpod.ai/docs/api).

Everpod is an easy way to get your own always-on, persistent cloud computer for AI agents, working in minutes: as a developer pod with your pick of Claude Code, Codex, OpenCode, Pi, Hermes and OpenClaw installed, or with OpenClaw set up and run for you. A key lets an agent or an app you trust see your pods and start a new one for you, which you then pay for on everpod.ai. It can't pay, change or cancel a plan, delete anything, open your agent's control panel, or reach a developer pod's machine.

If you are connecting an agent such as Claude Code or Codex, you do not need this library: point it at Everpod's MCP server, as the [API reference](https://everpod.ai/docs/api) shows.

## Install

```
pip install everpod-ai
```

Python 3.9 or later. No dependencies.

## Use

To make a key, open [everpod.ai/account/keys](https://everpod.ai/account/keys) and sign in with your email address and the code we send you. If you have no account yet, signing in makes one. Give the key to the library from an environment variable.

```python
import os

from everpod_ai import Everpod

everpod = Everpod(os.environ["EVERPOD_API_KEY"])

# Start an OpenClaw pod under the name you want for its agent. Nothing is
# charged: the pod stays unpaid until you open pay_url in a browser and pay there.
pod = everpod.start_pod("Otto")
print(pod["status"], pod["pay_url"])

# Or a developer pod: the machine's name, your username on it, which
# coding agents come installed (any of claude, codex, opencode, pi, hermes and openclaw; Claude Code and Codex when left out) and its size (s, m or
# l; the S when left out).
machine = everpod.start_pod("atlas", kind="developer", login="alex", agents=["claude", "codex"], size="m")

# The pods on your account, oldest first.
pods = everpod.list_pods()

# One pod by its id: how to check whether it has been paid for, and whether it is ready.
same = everpod.get_pod(pod["id"])
```

While your account has an unpaid pod, starting another returns that same pod, changed to the name and kind now asked for.

A pod's fields and what each status means are in the [API reference](https://everpod.ai/docs/api).

## When a request is refused

A refusal raises an `EverpodError`. Its `message` is the API's own sentence, which says what happened and what to do next; `code` and `status` are the refusal's.

```python
from everpod_ai import EverpodError

try:
    everpod.get_pod(pod_id)
except EverpodError as error:
    print(error.code, error.status, error.message)
```

## Questions

[support@everpod.ai](mailto:support@everpod.ai)

## License

MIT
