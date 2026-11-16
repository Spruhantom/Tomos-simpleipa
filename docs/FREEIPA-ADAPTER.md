# FreeIPA adapter and administrator authentication

## Administrator authentication

The API supports one bootstrap administrator account configured using:
- `SIMPLEIPA_ADMIN_USERNAME`
- `SIMPLEIPA_ADMIN_PASSWORD_HASH` — Argon2id hash, never a plaintext password
- `SIMPLEIPA_JWT_SECRET` — at least 32 characters of high-entropy secret material

Generate a password hash with:

```bash
python -c 'from pwdlib import PasswordHash; print(PasswordHash.recommended().hash(input("Admin password: ")))'
```

The login endpoint issues a signed HS256 bearer token with a 15-minute lifetime, issuer and audience validation. Management endpoints reject missing, malformed and expired tokens. Use TLS end-to-end, protect the secret with the host's secret manager, rate-limit login attempts at the reverse proxy, and rotate the signing secret to revoke outstanding sessions. The dashboard keeps the token in component memory only.

This is a single local bootstrap administrator, not yet a multi-user RBAC/SSO system. Production deployments should integrate the organisation's OIDC provider and map identity-provider groups to explicit SimpleIPA roles before wider rollout.

## FreeIPA connection

Install the native Kerberos development prerequisites first, then the optional Python dependencies. On Rocky Linux/AlmaLinux use `sudo dnf install krb5-devel gcc python3-devel`; on Ubuntu/Debian use `sudo apt install libkrb5-dev gcc python3-dev`. Then run `python -m pip install -e ".[freeipa]"`. Configure:
- `SIMPLEIPA_FREEIPA_URL=https://ipa.example.test`
- `SIMPLEIPA_FREEIPA_CA_BUNDLE=/path/to/ca-chain.pem` (optional; system trust is used otherwise)
- `SIMPLEIPA_TIMEOUT=10` (optional)

The adapter uses the host's Kerberos credential cache through SPNEGO and requires mutual authentication. The FreeIPA API is accessed over HTTPS with certificate verification enabled. It never accepts a directory password from the dashboard. Certificate requests submit a PEM CSR using FreeIPA's Dogtag CA JSON-RPC interface; the API never receives private keys. See [Certificate management](CERTIFICATE-MANAGEMENT.md). Ensure the service runs under a dedicated, least-privilege Kerberos principal with only the required user/group permissions and a managed credential cache.

If the FreeIPA URL is not configured, the API stays fail-closed with HTTP 503. The adapter supports listing and creating users and groups, DNS zones, and A/AAAA/CNAME/TXT records. DNS writes use FreeIPA JSON-RPC methods (`dnszone_add` and `dnsrecord_add`); SimpleIPA never writes LDAP or BIND files directly. DNS zone and record deletion are intentionally not available in this first increment. Certificate request/list operations use `cert_request` and `cert_find`; Dogtag enforces CSR signatures, principals and certificate profiles. The configured Kerberos principal needs the corresponding CA request/search privileges. Validate exact API behaviour, DNSSEC defaults and returned record shapes against a disposable FreeIPA test domain before production use.

## Limitations

- No live FreeIPA server was available in CI, so no real LDAP/Kerberos/DNS integration test is claimed.
- FreeIPA error responses are deliberately sanitised before returning to dashboard clients.
- Network calls have finite timeouts and TLS verification cannot be disabled.
