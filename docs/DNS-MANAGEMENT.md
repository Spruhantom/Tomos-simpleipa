# DNS management

SimpleIPA exposes authenticated DNS zone and record management through the FreeIPA JSON-RPC adapter. FreeIPA remains authoritative for DNS; SimpleIPA does not write LDAP records directly or edit BIND files.

## API

All routes require the normal 15-minute administrator bearer token.

- `GET /api/v1/dns/zones` — list zones.
- `POST /api/v1/dns/zones` — create a zone, JSON body `{"name":"example.test"}`.
- `GET /api/v1/dns/zones/{zone}/records?name=@` — list records for one owner name. The default `@` selects the zone apex.
- `POST /api/v1/dns/zones/{zone}/records` — create one record. Example: `{"name":"www","record_type":"A","value":"192.0.2.20"}`.

The initial record types are A, AAAA, CNAME and TXT. A/AAAA values are checked as IPv4/IPv6 addresses, CNAME targets are validated DNS names, TXT values reject control characters, and owner names are restricted to one label or `@`. The API deliberately has no record or zone delete endpoint in this first increment.

Duplicate entries return HTTP 409, invalid input returns HTTP 422, and an unavailable/unconfigured provider fails closed. Use the API only over TLS and configure a least-privilege Kerberos principal for FreeIPA.

## Current verification boundary

Unit tests use mocked JSON-RPC transport and an in-memory API provider. They verify request method/parameters, validation, authentication and basic create/list flows. They do not prove behaviour against a live FreeIPA DNS service. Validate zone creation, DNSSEC defaults, record response shape and update semantics in the disposable KVM/libvirt lab before production use.
