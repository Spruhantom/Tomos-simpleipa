# Rocky Linux / AlmaLinux server setup

SimpleIPA's server installer is a guarded wrapper around the distribution's supported FreeIPA installer. It does not implement LDAP, Kerberos or the certificate authority itself.

## Supported target

- Rocky Linux
- AlmaLinux

Use a clean, fully updated host with a static address, a stable fully qualified hostname, working forward and reverse DNS, and correctly synchronised time. Choose a dedicated identity domain and Kerberos realm before beginning. Avoid installing the first server into a domain that already has an IPA deployment.

## 1. Prepare the host

As an administrator, configure:
- A static IP address and the intended FQDN (for example `ipa.example.test`)
- Forward and reverse DNS records that resolve consistently
- Chrony/NTP and a synchronised system clock
- Required network routes and firewall access for the FreeIPA services you intend to use

Do not disable SELinux or the firewall to make installation pass. Review the current FreeIPA/RHEL documentation for the exact ports required by your topology and enabled services.

## 2. Run a non-destructive preflight

Install SimpleIPA from a reviewed checkout and run:

```bash
simpleipa server preflight \
  --hostname ipa.example.test \
  --domain example.test \
  --realm EXAMPLE.TEST
```

Add `--setup-dns` if this host will provide the integrated IPA DNS service. Preflight checks the OS family, current FQDN, forward DNS, dnf availability and time synchronisation. It does not install packages or change the host.

## 3. Guided installation

After resolving every failed preflight item, run:

```bash
sudo simpleipa server install \
  --hostname ipa.example.test \
  --domain example.test \
  --realm EXAMPLE.TEST
```

The command displays the checks again and requires an explicit confirmation. It installs `ipa-server` (and `ipa-server-dns` when requested), then launches `ipa-server-install` with a real interactive terminal. FreeIPA prompts locally for Directory Manager and IPA administrator passwords and any DNS forwarder choices. SimpleIPA does not accept, log or save those secrets, and deliberately does not use unattended mode.

Installation is a significant host change. Take a tested system backup first. If the upstream installer fails part-way through, stop and use the official FreeIPA recovery/uninstall guidance; SimpleIPA does not claim automatic rollback.

## 4. Verify services

Run:

```bash
simpleipa server health
```

This calls `ipactl status` and reports whether FreeIPA services are running. It is a service-status check, not a complete external DNS, Kerberos, TLS or client-enrolment acceptance test.

## Current limitations

- This is an initial guided wrapper, not a fully automated deployment orchestrator.
- No changes are made to firewall rules, DNS zones, SELinux policy or network configuration.
- The target host must already meet FreeIPA's supported OS/version, DNS, time and network requirements.
- A live Rocky/AlmaLinux test installation has not yet been performed.
- Client enrolment, replica deployment, backup/restore automation and full post-install integration tests remain future work.
