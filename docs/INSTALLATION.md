# Development installation

Requirements: Python 3.11 or newer.

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
simpleipa plan examples/server.json
```

The current planner is dry-run only. It does not install FreeIPA, alter host configuration, or enrol clients.
