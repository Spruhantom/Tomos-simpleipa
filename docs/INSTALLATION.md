# Installation and development

## Development environment

Requirements: Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test,freeipa]"
python -m unittest discover -s tests -v
simpleipa plan examples/server.json
```

## FreeIPA server

For the guided Rocky Linux / AlmaLinux server installation, see [Server setup](SERVER-SETUP.md). Always run the non-destructive preflight first and back up the host before installation.

The guided installer requires explicit confirmation and invokes the upstream interactive FreeIPA installer. It does not save administrator passwords or silently change firewall, SELinux or DNS settings.

## Ubuntu / Debian client enrolment

For the guided Linux client workflow, see [Client enrolment](CLIENT-ENROLMENT.md).
Run the non-destructive preflight first. Enrolment requires root and explicit
confirmation, installs the distribution's `freeipa-client` package, verifies
LDAP SRV discovery and invokes the upstream interactive client installer.
SimpleIPA never receives or stores the enrolment password.
