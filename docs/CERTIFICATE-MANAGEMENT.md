# Certificate management

SimpleIPA delegates certificate issuance and lifecycle authority to the FreeIPA Dogtag Certificate Authority. This increment supports authenticated certificate inventory and CSR submission only.

## Request a certificate

Generate a private key and PKCS#10 CSR on the machine that will use the certificate. For example:

```bash
openssl req -new -newkey rsa:3072 -nodes -keyout service.key -out service.csr -subj "/CN=service.example.test"
chmod 600 service.key
```

Keep `service.key` on that machine. Paste only the contents of `service.csr` into the dashboard or submit it to the authenticated API:

- `GET /api/v1/certificates` — list certificates visible to the FreeIPA principal.
- `POST /api/v1/certificates/requests` — submit `{ "principal": "host/service.example.test@EXAMPLE.TEST", "csr": "-----BEGIN CERTIFICATE REQUEST-----..." }`.

The API requires the existing administrator bearer token. The CSR must be PEM encoded and is size limited. FreeIPA/Dogtag remains responsible for cryptographic CSR verification, principal authorisation, profile constraints, SAN policy, issuance and certificate status. A successful request returns the serial number and, when returned by FreeIPA, the issued certificate PEM.

## Security boundaries

- SimpleIPA never receives or stores a private key.
- The API does not accept passwords, keytabs or arbitrary CA profile selection.
- Requests go through the Kerberos-authenticated FreeIPA JSON-RPC adapter over verified HTTPS.
- The FreeIPA service principal must be granted only the required CA request and certificate search privileges.
- PEM envelope validation is not proof that a CSR is cryptographically valid; Dogtag performs authoritative signature and profile checks.
- Certificate listing may be limited by the FreeIPA principal's CA permissions.

## Not included yet

Renewal, revocation, certificate download/storage, automatic key generation, automated host/service principal enrolment and live Dogtag integration tests are not implemented. Revocation is excluded because it is destructive and needs explicit reason codes, permission checks, audit records and confirmation. Validate issuance and returned response shapes against the disposable Rocky/AlmaLinux FreeIPA lab before production use.
