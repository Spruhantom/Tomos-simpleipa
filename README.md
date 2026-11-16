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

The first FastAPI management API and React/Vite dashboard foundation is under development on `feature/api-dashboard-foundation`. The API exposes versioned user/group listing and creation contracts behind a fail-closed bearer-token gate and a directory-provider interface. The default provider is intentionally unconfigured; no real FreeIPA changes are made yet. The dashboard currently provides read-only directory listings.

Install API test dependencies with `python -m pip install -e ".[test]"` and run `python -m unittest discover -s tests -v`. For the dashboard, run `cd dashboard && npm install && npm run dev`.

## Security boundaries

- Never collect or store user passwords in configuration files.
- Do not expose FreeIPA LDAP credentials or Kerberos keytabs to the dashboard.
- Dashboard/API operations must use least-privilege service identities and supported FreeIPA interfaces.
- Treat enrolment tokens as short-lived, single-use secrets.
- Keep Samba domain-member functionality distinct from an Active Directory domain controller role.

See [Architecture](docs/ARCHITECTURE.md), [Security design](docs/SECURITY-DESIGN.md), [Installation](docs/INSTALLATION.md) and [Roadmap](docs/ROADMAP.md).
