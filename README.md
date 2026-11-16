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

The FastAPI management API and React/Vite dashboard now include administrator login, short-lived signed sessions, user/group creation screens and a Kerberos-authenticated FreeIPA JSON-RPC adapter. The adapter requires verified HTTPS and remains fail-closed when no FreeIPA URL is configured. See [FreeIPA adapter and authentication](docs/FREEIPA-ADAPTER.md) for required server configuration and remaining production safeguards.

Install API test dependencies with `python -m pip install -e ".[test,freeipa]"` and run `python -m unittest discover -s tests -v`. For the dashboard, run `cd dashboard && npm install && npm run dev`.

## Rocky Linux / AlmaLinux server setup

A guarded setup workflow is available: `simpleipa server preflight` checks the operating system, hostname, forward DNS, package manager and time synchronisation without changing the host. `simpleipa server install` requires root and explicit confirmation, installs the FreeIPA server packages, then hands over to the upstream interactive `ipa-server-install` so passwords are entered locally and never stored by SimpleIPA. `simpleipa server health` checks `ipactl status`. See [Server setup](docs/SERVER-SETUP.md). A live Rocky/AlmaLinux installation has not yet been validated.

## Security boundaries

- Never collect or store user passwords in configuration files.
- Do not expose FreeIPA LDAP credentials or Kerberos keytabs to the dashboard.
- Dashboard/API operations must use least-privilege service identities and supported FreeIPA interfaces.
- Treat enrolment tokens as short-lived, single-use secrets.
- Keep Samba domain-member functionality distinct from an Active Directory domain controller role.

See [Architecture](docs/ARCHITECTURE.md), [Security design](docs/SECURITY-DESIGN.md), [Installation](docs/INSTALLATION.md) and [Roadmap](docs/ROADMAP.md).
