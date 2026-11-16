# SimpleIPA

A simplified management and installation layer built around FreeIPA. SimpleIPA aims to make identity management approachable through a feature-driven server setup, a simple client enrolment experience and a new administration dashboard.

## Initial support targets

- **Servers:** Rocky Linux and AlmaLinux
- **Clients:** Ubuntu and Debian
- **Core features:** users/groups, DNS, certificates, Linux client management, SSH public keys and sudo rules
- **Optional roadmap:** SMB client access and Samba file-server integration

## Current foundation

- Declarative feature registry and dependency graph
- Configuration validation and dry-run planning CLI
- Server/client role and platform checks
- Example server and client configurations
- Architecture, security and development documentation
- Unit tests

## Development quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
simpleipa plan examples/server.json
```

The planner is **dry-run only**. It does not install packages, change system configuration or enrol machines.

## API and dashboard

The FastAPI management API and React/Vite dashboard now include administrator login, short-lived signed sessions, user/group management, DNS zone and record management, and a Kerberos-authenticated FreeIPA JSON-RPC adapter. The adapter requires verified HTTPS and remains fail-closed when no FreeIPA URL is configured. See [FreeIPA adapter and authentication](docs/FREEIPA-ADAPTER.md) and [DNS management](docs/DNS-MANAGEMENT.md) for configuration, supported record types and remaining production safeguards.

Install API test dependencies with `python -m pip install -e ".[test]"` and run `python -m unittest discover -s tests -v`. For the dashboard, run `cd dashboard && npm install && npm run dev`.

## Rocky Linux / AlmaLinux server setup

A guarded setup workflow is available: `simpleipa server preflight` checks Rocky/AlmaLinux prerequisites without changing the host, and `simpleipa server install` requires root and explicit confirmation before handing over to the interactive `ipa-server-install`. Ubuntu/Debian clients now have `simpleipa client preflight` and `simpleipa client enrol`; the latter installs `freeipa-client`, checks LDAP SRV discovery and launches interactive `ipa-client-install`. Credentials are entered locally and are never stored by SimpleIPA. See [Server setup](docs/SERVER-SETUP.md) and [Client enrolment](docs/CLIENT-ENROLMENT.md). A disposable KVM/libvirt end-to-end lab for Rocky/AlmaLinux plus Ubuntu/Debian is documented in [VM integration tests](docs/VM-INTEGRATION-TESTS.md); it must be run on a Linux host with libvirt before a live-install result can be claimed.

## Security boundaries

- Never collect or store user passwords in configuration files.
- Do not expose FreeIPA LDAP credentials or Kerberos keytabs to the dashboard.
- Dashboard/API operations must use least-privilege service identities and supported FreeIPA interfaces.
- Treat enrolment tokens as short-lived, single-use secrets.
- Keep Samba domain-member functionality distinct from an Active Directory domain controller role.

See [Architecture](docs/ARCHITECTURE.md), [Security design](docs/SECURITY-DESIGN.md), [Installation](docs/INSTALLATION.md) and [Roadmap](docs/ROADMAP.md).
