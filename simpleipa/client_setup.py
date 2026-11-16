"""Guided FreeIPA client enrolment for Ubuntu and Debian.

Preflight is read-only. Enrolment requires root and explicit confirmation,
installs the distribution client packages, validates IPA DNS discovery, and
hands credentials directly to the upstream interactive installer.
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .server_setup import Check, read_os_release


@dataclass(frozen=True)
class ClientConfig:
    hostname: str
    server: str
    domain: str
    realm: str


def _valid_dns_name(value: str) -> bool:
    if not value or len(value) > 253 or value.endswith("."):
        return False
    return all(
        1 <= len(label) <= 63
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in value.split(".")
    )


def validate_config(config: ClientConfig) -> None:
    if not _valid_dns_name(config.hostname):
        raise ValueError("Client hostname must be a fully qualified DNS name")
    if not _valid_dns_name(config.server):
        raise ValueError("FreeIPA server must be a fully qualified DNS name")
    if not _valid_dns_name(config.domain):
        raise ValueError("Identity domain must be a valid DNS name")
    if config.hostname != config.hostname.lower() or config.server != config.server.lower() or config.domain != config.domain.lower():
        raise ValueError("Hostname, server and domain must be lowercase")
    if config.hostname != config.domain and not config.hostname.endswith("." + config.domain):
        raise ValueError("Client hostname must belong to the selected identity domain")
    if not re.fullmatch(r"[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?", config.realm) or "." not in config.realm:
        raise ValueError("Kerberos realm must be an uppercase DNS-style realm")


def preflight(
    config: ClientConfig,
    *,
    os_release_path: str | Path = "/etc/os-release",
    fqdn: Callable[[], str] = socket.getfqdn,
    resolver: Callable[[str], object] = socket.getaddrinfo,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[Check]:
    validate_config(config)
    checks: list[Check] = []
    try:
        release = read_os_release(os_release_path)
        distro = release.get("ID", "").lower()
        supported = distro in {"ubuntu", "debian"}
        checks.append(Check(
            "Operating system", supported,
            f"{release.get('PRETTY_NAME', distro or 'Unknown OS')} — supported: Ubuntu or Debian",
        ))
    except OSError as exc:
        checks.append(Check("Operating system", False, f"Cannot read os-release: {exc}"))

    try:
        current = fqdn().lower().rstrip(".")
        matches = current == config.hostname
        checks.append(Check(
            "System hostname", matches,
            f"Detected {current or 'no FQDN'}; expected {config.hostname}",
        ))
    except OSError as exc:
        checks.append(Check("System hostname", False, f"Could not determine hostname: {exc}"))

    try:
        resolver(config.server)
        checks.append(Check("FreeIPA server DNS", True, f"{config.server} resolves"))
    except (OSError, socket.gaierror) as exc:
        checks.append(Check("FreeIPA server DNS", False, f"{config.server} does not resolve: {exc}"))

    apt = which("apt-get")
    checks.append(Check("Package manager", bool(apt),
                        "apt-get is available" if apt else "apt-get was not found"))

    timedatectl = which("timedatectl")
    if not timedatectl:
        checks.append(Check("Time synchronisation", False, "timedatectl is not available"))
    else:
        try:
            result = run([timedatectl, "show", "-p", "NTPSynchronized", "--value"],
                         check=False, capture_output=True, text=True, timeout=10)
            synced = result.returncode == 0 and result.stdout.strip().lower() == "yes"
            checks.append(Check(
                "Time synchronisation", synced,
                "System clock is synchronised" if synced else
                "Clock is not confirmed synchronised; configure chrony/NTP before enrolment",
            ))
        except (OSError, subprocess.SubprocessError) as exc:
            checks.append(Check("Time synchronisation", False, f"Could not check clock: {exc}"))
    return checks


def enrol_client(
    config: ClientConfig,
    *,
    confirm: bool,
    euid: int | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    preflight_checks: Sequence[Check] | None = None,
) -> None:
    """Install IPA client packages and run the vendor's interactive enrolment."""
    validate_config(config)
    if not confirm:
        raise RuntimeError("Client enrolment requires explicit operator confirmation")
    if (os.geteuid() if euid is None else euid) != 0:
        raise PermissionError("Run client enrolment as root")
    checks = list(preflight_checks) if preflight_checks is not None else preflight(config)
    failed = [check for check in checks if not check.ok]
    if failed:
        raise RuntimeError("Preflight failed: " + "; ".join(c.name for c in failed))

    run(["apt-get", "update"], check=True)
    run(["apt-get", "install", "-y", "freeipa-client", "dnsutils"], check=True)
    discovery = run(
        ["dig", "@"+config.server, "_ldap._tcp."+config.domain, "SRV", "+short"],
        check=False, capture_output=True, text=True, timeout=15,
    )
    if discovery.returncode != 0 or not discovery.stdout.strip():
        raise RuntimeError("FreeIPA LDAP SRV record was not found; check the domain DNS configuration")

    command = [
        "ipa-client-install",
        "--server", config.server,
        "--domain", config.domain,
        "--realm", config.realm,
    ]
    # Keep stdin attached: the upstream installer prompts locally for an
    # enrolment principal and password. SimpleIPA never receives or stores them.
    run(command, check=True)
