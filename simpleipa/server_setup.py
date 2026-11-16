"""Guided, fail-closed FreeIPA server setup for Rocky Linux and AlmaLinux.

This module performs preflight checks and invokes the supported interactive
ipa-server-install program. It never writes passwords or unattended secrets.
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


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ServerConfig:
    hostname: str
    domain: str
    realm: str
    setup_dns: bool = False


def _valid_dns_name(value: str) -> bool:
    if not value or len(value) > 253 or value.endswith("."):
        return False
    labels = value.split(".")
    return len(labels) >= 2 and all(
        1 <= len(label) <= 63
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    )


def validate_config(config: ServerConfig) -> None:
    hostname = config.hostname.strip().lower()
    domain = config.domain.strip().lower()
    realm = config.realm.strip().upper()
    if not _valid_dns_name(hostname):
        raise ValueError("Server hostname must be a fully qualified DNS name")
    if not _valid_dns_name(domain):
        raise ValueError("Domain must be a valid fully qualified DNS name")
    if not re.fullmatch(r"[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?", realm) or "." not in realm:
        raise ValueError("Kerberos realm must be a valid uppercase DNS-style realm")
    if hostname != config.hostname or domain != config.domain or realm != config.realm:
        raise ValueError("Hostname/domain must be lowercase and realm uppercase")
    if hostname != domain and not hostname.endswith("." + domain):
        raise ValueError("Server hostname must belong to the selected identity domain")


def read_os_release(path: str | Path = "/etc/os-release") -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


def preflight(
    config: ServerConfig,
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
        supported = distro in {"rocky", "almalinux"}
        checks.append(Check("Operating system", supported,
                            f"{release.get('PRETTY_NAME', distro or 'Unknown OS')} — supported: Rocky Linux or AlmaLinux"))
    except OSError as exc:
        checks.append(Check("Operating system", False, f"Cannot read os-release: {exc}"))

    try:
        current = fqdn().lower().rstrip(".")
        matches = current == config.hostname
        checks.append(Check("System hostname", matches,
                            f"Detected {current or 'no FQDN'}; expected {config.hostname}"))
    except OSError as exc:
        checks.append(Check("System hostname", False, f"Could not determine hostname: {exc}"))

    try:
        resolver(config.hostname)
        checks.append(Check("Forward DNS", True, f"{config.hostname} resolves"))
    except (OSError, socket.gaierror) as exc:
        checks.append(Check("Forward DNS", False, f"{config.hostname} does not resolve: {exc}"))

    dnf_path = which("dnf")
    checks.append(Check("Package manager", bool(dnf_path),
                        "dnf is available" if dnf_path else "dnf was not found"))

    timedatectl = which("timedatectl")
    if not timedatectl:
        checks.append(Check("Time synchronisation", False, "timedatectl is not available"))
    else:
        try:
            result = run([timedatectl, "show", "-p", "NTPSynchronized", "--value"],
                         check=False, capture_output=True, text=True, timeout=10)
            synced = result.returncode == 0 and result.stdout.strip().lower() == "yes"
            checks.append(Check("Time synchronisation", synced,
                                "System clock is synchronised" if synced else
                                "Clock is not confirmed synchronised; configure chrony/NTP before installation"))
        except (OSError, subprocess.SubprocessError) as exc:
            checks.append(Check("Time synchronisation", False, f"Could not check clock: {exc}"))
    return checks


def install_server(
    config: ServerConfig,
    *,
    confirm: bool,
    euid: int | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    preflight_checks: Sequence[Check] | None = None,
) -> None:
    """Install packages and hand over to FreeIPA's interactive installer."""
    validate_config(config)
    if not confirm:
        raise RuntimeError("Installation requires explicit operator confirmation")
    if (os.geteuid() if euid is None else euid) != 0:
        raise PermissionError("Run the server installation as root")
    checks = list(preflight_checks) if preflight_checks is not None else preflight(config)
    failed = [check for check in checks if not check.ok]
    if failed:
        raise RuntimeError("Preflight failed: " + "; ".join(c.name for c in failed))

    packages = ["ipa-server"]
    if config.setup_dns:
        packages.append("ipa-server-dns")
    run(["dnf", "install", "-y", *packages], check=True)
    command = [
        "ipa-server-install",
        "--hostname", config.hostname,
        "--domain", config.domain,
        "--realm", config.realm,
    ]
    if config.setup_dns:
        command.append("--setup-dns")
    # Keep stdin attached: FreeIPA prompts for directory/admin passwords and
    # DNS forwarder choices. No password is accepted by this wrapper.
    run(command, check=True)


def server_health(
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[Check]:
    ipactl = which("ipactl")
    if not ipactl:
        return [Check("FreeIPA services", False, "ipactl is not installed")]
    try:
        result = run([ipactl, "status"], check=False, capture_output=True,
                     text=True, timeout=30)
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        healthy = result.returncode == 0 and "not running" not in output.lower()
        return [Check("FreeIPA services", healthy,
                      "ipactl reports services running" if healthy else
                      (output.strip() or "ipactl reported a service failure"))]
    except (OSError, subprocess.SubprocessError) as exc:
        return [Check("FreeIPA services", False, f"Health check failed: {exc}")]
