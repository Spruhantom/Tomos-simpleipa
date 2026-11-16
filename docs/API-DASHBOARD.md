# API and dashboard foundation

## API

The FastAPI application is created by `simpleipa.api:create_app`. It exposes:

- `GET /health` — unauthenticated process health check
- `GET /api/v1/users` and `POST /api/v1/users`
- `GET /api/v1/groups` and `POST /api/v1/groups`

Management routes require a bearer token configured in `SIMPLEIPA_API_TOKEN`. If no token is configured, management requests fail closed with HTTP 503. Invalid tokens receive HTTP 401. Duplicate usernames/group names receive HTTP 409 and invalid payloads receive HTTP 422.

The default provider is intentionally unconfigured and returns HTTP 503. `MemoryDirectory` is a test-only adapter used by unit tests; it is not selected by the application default and is not persistent. No FreeIPA writes are implemented yet. A production adapter must use supported FreeIPA interfaces, narrowly scoped service credentials, audit events and explicit authorization.

## Dashboard

The React/Vite dashboard currently provides a connection panel and read-only user/group listings. Set `VITE_SIMPLEIPA_API_URL` to the API origin when running the dashboard separately. The API must be configured with an administrator token; the token is held only in the current page's component state and is not persisted.

The dashboard does not yet create, edit or delete identities. Production deployment still needs a proper administrator sign-in/session flow, CSRF protections where cookie sessions are used, TLS, rate limiting, audit logging and deployment hardening.

## Development

API dependencies are installed with the project. Dashboard dependencies are installed from `dashboard/package.json` using npm.
