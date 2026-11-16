# Ubuntu / Debian FreeIPA client enrolment

SimpleIPA provides a guarded wrapper around the distribution's supported
`ipa-client-install` command. It does not implement Kerberos or SSSD itself.

## Supported targets

- Ubuntu
- Debian

Use a supported, fully updated client with a stable fully qualified hostname
inside the FreeIPA identity DNS domain. Configure a synchronised system clock
and DNS so the client can resolve the FreeIPA server and its LDAP SRV record.

## 1. Prepare DNS and hostname

For example:

- FreeIPA server: `ipa.example.test`
- Identity domain: `example.test`
- Client hostname: `client.example.test`
- Kerberos realm: `EXAMPLE.TEST`

Ensure the client's resolver uses DNS that can discover
`_ldap._tcp.example.test` and resolve `ipa.example.test`. Do not hard-code
temporary DNS changes into the SimpleIPA workflow.

## 2. Run non-destructive preflight

Install SimpleIPA from a reviewed checkout, set the client's FQDN, then run:

```bash
simpleipa client preflight \
  --hostname client.example.test \
  --server ipa.example.test \
  --domain example.test \
  --realm EXAMPLE.TEST
```

Preflight checks that the OS is Ubuntu or Debian, the current hostname matches,
the FreeIPA server resolves, `apt-get` is available and the system clock is
synchronised. It does not install packages or change the host.

## 3. Enrol the client

After correcting every failed preflight item, run:

```bash
sudo simpleipa client enrol \
  --hostname client.example.test \
  --server ipa.example.test \
  --domain example.test \
  --realm EXAMPLE.TEST
```

The command repeats preflight, asks for explicit confirmation, updates package
indexes, installs `freeipa-client` and `dnsutils`, and verifies the LDAP SRV
record before launching the upstream interactive `ipa-client-install`.

Enter the enrolment principal and password only in the FreeIPA installer prompt.
SimpleIPA does not accept, log or save those credentials. The installer makes
system changes to SSSD, Kerberos and NSS configuration; review the prompts and
use a tested backup or rebuild path before enrolling production clients.

## 4. Verify enrolment

After the installer completes, verify a known directory identity:

```bash
id <username>
getent passwd <username>
systemctl status sssd
```

A successful installer exit does not prove that every user/group policy,
sudo rule, SSH key or DNS feature is configured. Those workflows are separate
roadmap items.

## Current limitations

- This is an interactive enrolment wrapper, not unattended fleet provisioning.
- It does not configure client networking, DNS resolvers, firewall rules or time
  services.
- It does not issue or store enrolment tokens.
- The actual Ubuntu/Debian client VM enrolment still needs to be exercised in the
  disposable KVM/libvirt integration lab.
