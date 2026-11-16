# Architecture

## Design rule
SimpleIPA is an orchestration and usability layer around FreeIPA, not a replacement identity protocol implementation. FreeIPA remains authoritative for LDAP-backed identity, Kerberos, certificate services and supported DNS integration.

## Components
1. Configuration engine: validates desired state, resolves feature dependencies and emits dry-run plans.
2. Server adapter: guarded Rocky/AlmaLinux preflight and guided invocation of the supported FreeIPA installer.
3. Client adapter: configures supported Ubuntu/Debian IPA clients using distribution packages and SSSD.
4. API: authenticated management boundary for the dashboard.
5. Dashboard: React/TypeScript UI; must call the API, never manipulate LDAP directly.
6. SMB adapter: separate client and Samba domain-member workflows; no assumption that FreeIPA is an AD DC.

## Initial feature modules
- User/group management
- DNS management
- Certificate management
- Linux client management
- SSH public-key management
- Sudo policy management

SMB client and Samba file-server integration remain optional modules.

## Server installation lifecycle
Prepare host -> preflight OS/hostname/DNS/time/package manager -> explicit operator confirmation -> install distribution packages -> run upstream interactive `ipa-server-install` -> inspect `ipactl status`. No passwords are accepted by SimpleIPA, and no unattended installer mode is used.

## Execution lifecycle
Discover -> validate -> resolve dependencies -> dry-run -> explicit approval -> backup -> apply -> health-check -> audit.
A failed apply must stop safely; rollback is only claimed where an adapter can prove it.

## API direction
Versioned REST API under /api/v1. All write operations require authenticated administrator identity, role-based authorisation, CSRF protection where cookie sessions are used, request validation and audit events.
