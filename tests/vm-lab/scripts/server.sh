#!/usr/bin/env bash
set -Eeuo pipefail

: "${IPA_TEST_ADMIN_PASSWORD:?missing disposable lab admin password}"
: "${IPA_TEST_DS_PASSWORD:?missing disposable lab Directory Manager password}"

hostnamectl set-hostname ipa.example.test
grep -q 'ipa.example.test' /etc/hosts || echo '192.168.56.10 ipa.example.test ipa' >> /etc/hosts

dnf -y install ipa-server ipa-server-dns chrony bind-utils python3 python3-pip
systemctl enable --now chronyd
python3 -m pip install --disable-pip-version-check /vagrant

# Exercise SimpleIPA's non-destructive host preflight before installing IPA.
simpleipa server preflight --hostname ipa.example.test --domain example.test --realm EXAMPLE.TEST

# This unattended command is deliberately restricted to the disposable VM lab.
# Passwords are generated per run, never committed, and the VM is destroyed after
# the test. Production installation continues to use SimpleIPA's interactive path.
ipa-server-install --unattended \
  --hostname=ipa.example.test \
  --ip-address=192.168.56.10 \
  --domain=example.test \
  --realm=EXAMPLE.TEST \
  --ds-password="$IPA_TEST_DS_PASSWORD" \
  --admin-password="$IPA_TEST_ADMIN_PASSWORD" \
  --setup-dns --no-forwarders --no-reverse --no-ntp

# Authenticate locally and exercise the core identity, DNS and CA interfaces.
printf '%s\n' "$IPA_TEST_ADMIN_PASSWORD" | kinit admin
klist
dig @127.0.0.1 _ldap._tcp.example.test SRV +short | grep -q .
ipa ca-show ipa
ipa user-show admin
ipa user-add vm-lab-user --first=VM --last=Integration
simpleipa server health
