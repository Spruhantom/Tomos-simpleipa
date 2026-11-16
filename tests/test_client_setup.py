import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import Mock

from simpleipa.client_setup import ClientConfig, enrol_client, preflight, validate_config
from simpleipa.server_setup import Check


class ClientSetupTests(unittest.TestCase):
    def setUp(self):
        self.config = ClientConfig(
            hostname="client.example.test",
            server="ipa.example.test",
            domain="example.test",
            realm="EXAMPLE.TEST",
        )

    def _preflight(self, distro="ubuntu"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        release = Path(tmp.name) / "os-release"
        release.write_text(f'ID="{distro}"\nPRETTY_NAME="{distro.title()}"\n')
        return preflight(
            self.config,
            os_release_path=release,
            fqdn=lambda: "client.example.test",
            resolver=lambda host: [(host,)],
            which=lambda name: f"/usr/bin/{name}",
            run=lambda *a, **kw: CompletedProcess(a[0], 0, stdout="yes\n", stderr=""),
        )

    def test_valid_config(self):
        validate_config(self.config)

    def test_rejects_client_outside_identity_domain(self):
        with self.assertRaises(ValueError):
            validate_config(ClientConfig(
                "client.other.test", "ipa.example.test", "example.test", "EXAMPLE.TEST"
            ))

    def test_rejects_invalid_realm(self):
        with self.assertRaises(ValueError):
            validate_config(ClientConfig(
                "client.example.test", "ipa.example.test", "example.test", "example.test"
            ))

    def test_preflight_accepts_ubuntu(self):
        checks = self._preflight("ubuntu")
        self.assertTrue(all(check.ok for check in checks), checks)

    def test_preflight_accepts_debian(self):
        checks = self._preflight("debian")
        self.assertTrue(all(check.ok for check in checks), checks)

    def test_preflight_rejects_unsupported_os(self):
        checks = self._preflight("fedora")
        self.assertFalse(next(c for c in checks if c.name == "Operating system").ok)

    def test_enrolment_requires_confirmation(self):
        with self.assertRaises(RuntimeError):
            enrol_client(self.config, confirm=False, euid=0, preflight_checks=[])

    def test_enrolment_requires_root(self):
        with self.assertRaises(PermissionError):
            enrol_client(self.config, confirm=True, euid=1000, preflight_checks=[])

    def test_enrolment_installs_packages_checks_srv_and_runs_interactive_installer(self):
        runner = Mock(side_effect=[
            CompletedProcess(["apt-get", "update"], 0),
            CompletedProcess(["apt-get", "install"], 0),
            CompletedProcess(["dig"], 0, stdout="0 100 389 ipa.example.test.\n"),
            CompletedProcess(["ipa-client-install"], 0),
        ])
        enrol_client(
            self.config, confirm=True, euid=0, run=runner,
            preflight_checks=[Check("test", True, "ok")],
        )
        calls = [call.args[0] for call in runner.call_args_list]
        self.assertEqual(calls[0], ["apt-get", "update"])
        self.assertEqual(calls[1], ["apt-get", "install", "-y", "freeipa-client", "dnsutils"])
        self.assertEqual(calls[2], ["dig", "@ipa.example.test", "_ldap._tcp.example.test", "SRV", "+short"])
        self.assertEqual(calls[3], [
            "ipa-client-install", "--server", "ipa.example.test",
            "--domain", "example.test", "--realm", "EXAMPLE.TEST",
        ])

    def test_enrolment_stops_when_srv_record_is_missing(self):
        runner = Mock(side_effect=[
            CompletedProcess(["apt-get", "update"], 0),
            CompletedProcess(["apt-get", "install"], 0),
            CompletedProcess(["dig"], 0, stdout=""),
        ])
        with self.assertRaisesRegex(RuntimeError, "SRV record"):
            enrol_client(
                self.config, confirm=True, euid=0, run=runner,
                preflight_checks=[Check("test", True, "ok")],
            )
        self.assertEqual(runner.call_count, 3)


if __name__ == "__main__":
    unittest.main()
