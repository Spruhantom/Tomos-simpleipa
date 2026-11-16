import argparse
import json
import sys
from pathlib import Path

from .planner import build_plan, ConfigurationError
from .server_setup import ServerConfig, preflight, install_server, server_health


def _server_config(args):
    realm = args.realm or args.domain.upper()
    return ServerConfig(args.hostname, args.domain, realm, args.setup_dns)


def _add_server_options(parser):
    parser.add_argument("--hostname", required=True, help="Server FQDN, e.g. ipa.example.test")
    parser.add_argument("--domain", required=True, help="Identity DNS domain, e.g. example.test")
    parser.add_argument("--realm", help="Kerberos realm (defaults to DOMAIN in uppercase)")
    parser.add_argument("--setup-dns", action="store_true", help="Install and configure the integrated DNS service")


def _print_checks(checks):
    for check in checks:
        marker = "PASS" if check.ok else "FAIL"
        print(f"[{marker}] {check.name}: {check.detail}")
    return 0 if all(check.ok for check in checks) else 2


def main(argv=None):
    parser = argparse.ArgumentParser(prog="simpleipa")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="validate configuration and print a dry-run plan")
    plan.add_argument("config", type=Path)

    server = sub.add_parser("server", help="Rocky/AlmaLinux FreeIPA server operations")
    server_sub = server.add_subparsers(dest="server_command", required=True)
    check = server_sub.add_parser("preflight", help="check server prerequisites without changing the host")
    _add_server_options(check)
    install = server_sub.add_parser("install", help="guided FreeIPA server installation")
    _add_server_options(install)
    health = server_sub.add_parser("health", help="check FreeIPA service health")

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            config = json.loads(args.config.read_text(encoding="utf-8"))
            result = build_plan(config)
            print(json.dumps({
                "mode": "dry-run", "role": result.role, "platform": result.platform,
                "features": list(result.features), "actions": list(result.actions),
                "system_modified": False,
            }, indent=2))
            return 0

        if args.command == "server" and args.server_command in {"preflight", "install"}:
            config = _server_config(args)
            checks = preflight(config)
            status = _print_checks(checks)
            if status:
                return status
            if args.server_command == "preflight":
                print("Preflight complete. No system changes were made.")
                return 0
            print("\nFreeIPA will now be installed using the vendor interactive installer.")
            print("You will be prompted locally for Directory Manager and IPA admin passwords.")
            print("This tool does not collect or save those passwords.")
            answer = input("Continue with package installation and setup? [y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Cancelled; no changes were made.")
                return 1
            install_server(config, confirm=True, preflight_checks=checks)
            print("FreeIPA installer completed. Run 'simpleipa server health' to verify services.")
            return 0

        if args.command == "server" and args.server_command == "health":
            return _print_checks(server_health())

    except (OSError, json.JSONDecodeError, ConfigurationError, ValueError,
            RuntimeError, PermissionError) as exc:
        print(f"simpleipa: error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
