# API and dashboard

The API exposes `GET /health`, `POST /api/v1/auth/login`, authenticated user/group list and create endpoints, and authenticated DNS zone/record list and create endpoints. Administrator login uses a configured username, an Argon2id password hash and a 32+ character JWT signing secret. The API issues 15-minute signed bearer tokens and validates signature, issuer, audience and expiry.

DNS routes are documented in [DNS management](DNS-MANAGEMENT.md). The initial supported record types are A, AAAA, CNAME and TXT. Destructive DNS deletion is intentionally not exposed.

Directory access is provider-based. When `SIMPLEIPA_FREEIPA_URL` is configured, the application loads the FreeIPA adapter; otherwise management calls fail closed with HTTP 503. The adapter uses Kerberos SPNEGO with mutual authentication and verified HTTPS. See [FreeIPA adapter and authentication](FREEIPA-ADAPTER.md).

The React/Vite dashboard provides administrator sign-in, user/group listings and creation forms, plus a DNS tab for listing zones and records and creating zones and A/AAAA/CNAME/TXT records. Tokens are held in page memory only and are not persisted in browser storage.

For API development, install `python -m pip install -e ".[test]"` and run `python -m unittest discover -s tests -v`. For the dashboard, run `cd dashboard && npm install && npm run dev`.

This is an initial single-administrator authentication model, not yet a multi-user RBAC/SSO system. Deploy only behind TLS, add login rate limiting at the reverse proxy, protect secrets with a host secret manager, and complete production audit logging before wider deployment.
