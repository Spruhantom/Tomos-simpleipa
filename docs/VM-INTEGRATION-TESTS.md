# Disposable FreeIPA VM integration lab

This lab runs a real FreeIPA server and a real Linux client in disposable VMs. It complements, but does not replace, the mocked unit tests and GitHub-hosted CI. It is not run automatically on GitHub-hosted runners because those runners do not provide a configured libvirt hypervisor.

## Host requirements

- Linux host with hardware virtualisation enabled (VT-x/AMD-V)
- libvirt/KVM and its network services
- Vagrant and the `vagrant-libvirt` provider
- At least 10 GB free RAM recommended, 30 GB free disk and internet access for box/package downloads
- Repository checkout on the host

The lab defaults to Rocky Linux 9 plus Ubuntu 22.04. It can be switched to AlmaLinux 9 or Debian 12 using environment variables. Use a fresh lab for each combination.

## Run Rocky Linux + Ubuntu

From the repository root:

```bash
cd tests/vm-lab
./run.sh up
```

The runner generates random, throwaway IPA administrator and Directory Manager passwords in a mode-0600 local file ignored by Git. The server VM runs SimpleIPA's non-destructive preflight, installs FreeIPA with integrated DNS using the upstream unattended installer, verifies the LDAP SRV record, Kerberos ticket acquisition, CA visibility, user operations and SimpleIPA service health. The client VM resolves the IPA DNS SRV record, runs the interactive IPA client installer, and verifies SSSD identity lookup.

The unattended server install is intentionally confined to these disposable test VMs. The production SimpleIPA installer remains interactive and does not accept or persist passwords. Do not reuse lab credentials or run this harness on a production host.

## Test AlmaLinux + Ubuntu

Destroy the existing lab first, then run:

```bash
./run.sh destroy
SIMPLEIPA_TEST_SERVER_BOX=generic/alma9 ./run.sh up
```

## Test Rocky Linux + Debian

```bash
./run.sh destroy
SIMPLEIPA_TEST_CLIENT_BOX=generic/debian12 ./run.sh up
```

To test AlmaLinux + Debian, set both variables.

## Inspect and clean up

```bash
./run.sh status
./run.sh destroy
```

Destroy removes both VMs and the local generated password file. If provisioning fails, inspect the VM with `vagrant ssh ipa-server` or `vagrant ssh ipa-client`, fix the underlying issue, then re-run `vagrant provision` after sourcing the ignored `.lab-secrets` file and exporting its variables.

## What this proves

A successful run is an end-to-end smoke test for:
- Rocky/AlmaLinux FreeIPA package installation and server initialisation
- Integrated DNS LDAP SRV publication and client-side DNS discovery
- Kerberos administrator authentication
- Dogtag CA visibility
- User creation and SSSD identity lookup after client enrolment
- SimpleIPA's FreeIPA service health command

It does not yet validate replica deployment, certificate issuance/renewal, backups/restores, firewall traversal outside the private lab network, upgrades or production hardening. Record the exact server/client box versions and the Vagrant output for each supported combination.
