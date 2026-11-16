# VM lab quick start

Run `../../docs/VM-INTEGRATION-TESTS.md` from the repository documentation for requirements, supported box combinations, test coverage and cleanup.

Quick start from the repository root:

```bash
cd tests/vm-lab
./run.sh up
./run.sh status
./run.sh destroy
```

Defaults: Rocky Linux 9 server + Ubuntu 22.04 client. Override with `SIMPLEIPA_TEST_SERVER_BOX=generic/alma9` or `SIMPLEIPA_TEST_CLIENT_BOX=generic/debian12`.
