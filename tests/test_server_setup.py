import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock

from simpleipa.server_setup import (
    Check, ServerConfig, install_server, preflight, server_health, validate_config,
)


class ServerSetupTests(unittest.TestCase):
    def setUp(self):
        self.config = ServerConfig(
            hostname="ipa.example.test", domain="example.test", realm="EXAMPLE.TEST"
        )

    def test_valid_config(self):
        validate_config(self.config)

    def test_rejects_hostname_outside_domain(self):
        with self.assertRaises(ValueError):
            validate_config(ServerConfig("ipa.other.test", "example.test", "EXAMPLE.TEST"))

    def test_rejects_non_fqdn(self):
        with self.assertRaises(ValueError):
            validate_config(ServerConfig("ipa", "example.test", "EXAMPLE.TEST"))

    def test_preflight_accepts_rocky_with_dns_and_synced_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / "os-release"
            release.write_text('ID="rocky"\nPRETTY_NAME="Rocky Linux 9"\n')
            checks = preflight(
                self.config,
                os_release_path=release,
                fqdn=lambda: "ipa.example.test",
                resolver=lambda host: [(host,)],
                which=lambda name: f"/usr/bin/{name}",
                run=lambda *a, **kw: CompletedProcess(a[0], 0, stdout="yes\n", stderr=""),
            )
        self.assertTrue(all(c.ok for c in checks), checks)

    def test_preflight_rejects_unsupported_os(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / "os-release"
            release.write_text('ID="ubuntu"\nPRETTY_NAME="Ubuntu"\n')
            checks = preflight(
                self.config, os_release_path=release,
                fqdn=lambda: "ipa.example.test", resolver=lambda host: None,
                which=lambda name: f"/usr/bin/{name}",
                run=lambda *a, **kw: CompletedProcess(a[0], 0, stdout="yes", stderr=""),
            )
        self.assertFalse(next(c for c in checks if c.name == "Operating system").ok)

    def test_install_requires_confirmation(self):
        with self.assertRaises(RuntimeError):
            install_server(self.config, confirm=False, euid=0)

    def test_install_requires_root(self):
        with self.assertRaises(PermissionError):
            install_server(self.config, confirm=True, euid=1000, preflight_checks=[])

    def test_install_uses_interactive_freeipa_installer(self):
        runner = Mock()
        checks = [Check("test", True, "ok")]
        install_server(self.config, confirm=True, euid=0, run=runner, preflight_checks=checks)
        self.assertEqual(runner.call_args_list[0].args[0], ["dnf", "install", "-y", "ipa-server"])
        command = runner.call_args_list[1].args[0]
        self.assertEqual(command[:2], ["ipa-server-install", "--hostname"])
        self.assertNotIn("--unattended", command)

    def test_dns_option_adds_dns_package_and_flag(self):
        runner = Mock()
        config = ServerConfig("ipa.example.test", "example.test", "EXAMPLE.TEST", True)
        install_server(config, confirm=True, euid=0, run=runner,
                       preflight_checks=[Check("test", True, "ok")])
        self.assertIn("ipa-server-dns", runner.call_args_list[0].args[0])
        self.assertIn("--setup-dns", runner.call_args_list[1].args[0])

    def test_health_check_detects_failed_service(self):
        checks = server_health(
            which=lambda name: "/usr/sbin/ipactl",
            run=lambda *a, **kw: CompletedProcess(a[0], 1, stdout="Directory Server is not running", stderr=""),
        )
        self.assertFalse(checks[0].ok)


if __name__ == "__main__":
    unittest.main()
