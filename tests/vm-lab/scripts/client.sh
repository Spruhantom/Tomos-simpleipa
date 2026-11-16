#!/usr/bin/env bash
set -Eeuo pipefail

: "${IPA_TEST_ADMIN_PASSWORD:?missing disposable lab admin password}"
hostnamectl set-hostname client.example.test
grep -q 'ipa.example.test' /etc/hosts || echo '192.168.56.10 ipa.example.test ipa' >> /etc/hosts

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y freeipa-client dnsutils expect

# The lab is isolated: point the disposable client at the IPA DNS service.
rm -f /etc/resolv.conf
printf 'search example.test\nnameserver 192.168.56.10\n' > /etc/resolv.conf

for attempt in $(seq 1 60); do
  if dig @192.168.56.10 _ldap._tcp.example.test SRV +short | grep -q .; then
    break
  fi
  sleep 5
done
dig @192.168.56.10 _ldap._tcp.example.test SRV +short | grep -q .

# Drive the supported interactive client installer without placing the password
# in its command line. The password exists only in this disposable provisioner.
expect <<'EXPECT'
set timeout 240
log_user 0
spawn ipa-client-install --server=ipa.example.test --domain=example.test --realm=EXAMPLE.TEST --principal=admin --no-ntp
expect {
  -re {Password for admin@.*:} {
    send -- "$env(IPA_TEST_ADMIN_PASSWORD)\r"
    exp_continue
  }
  -re {Continue to configure.*\[no\]:} {
    send -- "yes\r"
    exp_continue
  }
  eof
}
set result [wait]
exit [lindex $result 3]
EXPECT

systemctl restart sssd
getent passwd vm-lab-user
id vm-lab-user
