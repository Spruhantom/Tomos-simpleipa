#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LAB_DIR"

if ! command -v vagrant >/dev/null || ! vagrant plugin list | grep -q vagrant-libvirt; then
  echo "Install Vagrant and the vagrant-libvirt provider first." >&2
  exit 2
fi

case "${1:-up}" in
  up)
    if [[ ! -f .lab-secrets ]]; then
      umask 077
      printf 'export IPA_TEST_ADMIN_PASSWORD=%q\n' "$(openssl rand -hex 24)" > .lab-secrets
      printf 'export IPA_TEST_DS_PASSWORD=%q\n' "$(openssl rand -hex 24)" >> .lab-secrets
    fi
    # shellcheck disable=SC1091
    source .lab-secrets
    export IPA_TEST_ADMIN_PASSWORD IPA_TEST_DS_PASSWORD
    export SIMPLEIPA_TEST_SERVER_BOX="${SIMPLEIPA_TEST_SERVER_BOX:-generic/rocky9}"
    export SIMPLEIPA_TEST_CLIENT_BOX="${SIMPLEIPA_TEST_CLIENT_BOX:-generic/ubuntu2204}"
    vagrant up --provider=libvirt
    ;;
  status)
    vagrant status
    ;;
  destroy)
    vagrant destroy -f
    rm -f .lab-secrets
    ;;
  *)
    echo "Usage: $0 [up|status|destroy]" >&2
    exit 2
    ;;
esac
