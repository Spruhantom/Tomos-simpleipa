# Security design baseline

- TLS for all dashboard/API traffic; secure cookies and modern session controls.
- No passwords, keytabs, private keys or enrolment secrets in logs or configuration exports.
- Short-lived, single-use enrolment credentials; bind enrolment to expected host identity.
- Least-privilege service identities; no browser-to-LDAP access.
- Validate and authorise every object-level operation.
- Audit administrative changes with actor, target, timestamp and outcome.
- Back up supported configuration and directory state before disruptive operations.
- Do not silently disable SELinux, firewalls, certificate validation or time checks.
- Treat DNS and time synchronisation as authentication-critical prerequisites.
