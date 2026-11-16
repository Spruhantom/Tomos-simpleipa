import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from simpleipa.api import MemoryDirectory, create_app
from simpleipa.dns_types import DNSRecordCreate, DNSZoneCreate
from simpleipa.freeipa import FreeIPADirectory


class DNSValidationTests(unittest.TestCase):
    def test_zone_is_normalised(self):
        self.assertEqual(DNSZoneCreate(name="Example.TEST.").name, "example.test")

    def test_invalid_zone_rejected(self):
        with self.assertRaises(ValueError):
            DNSZoneCreate(name="bad zone")

    def test_a_record_requires_ipv4(self):
        with self.assertRaises(ValueError):
            DNSRecordCreate(name="host", record_type="A", value="2001:db8::1")

    def test_aaaa_record_requires_ipv6(self):
        with self.assertRaises(ValueError):
            DNSRecordCreate(name="host", record_type="AAAA", value="192.0.2.10")

    def test_cname_target_is_normalised(self):
        record = DNSRecordCreate(name="www", record_type="CNAME", value="Web.Example.TEST.")
        self.assertEqual(record.value, "web.example.test")

    def test_record_name_rejects_multiple_labels(self):
        with self.assertRaises(ValueError):
            DNSRecordCreate(name="www.example", record_type="A", value="192.0.2.10")


class DNSAPITests(unittest.TestCase):
    def setUp(self):
        self.directory = MemoryDirectory()
        self.client = TestClient(create_app(self.directory))
        self.env = patch.dict(os.environ, {
            "SIMPLEIPA_ADMIN_USERNAME": "admin",
            "SIMPLEIPA_ADMIN_PASSWORD_HASH": PasswordHash.recommended().hash("correct horse battery staple"),
            "SIMPLEIPA_JWT_SECRET": "test-secret-material-at-least-32-characters",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "correct horse battery staple"
        })
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_dns_end_to_end(self):
        zone = self.client.post("/api/v1/dns/zones", headers=self.headers, json={"name": "example.test"})
        self.assertEqual(zone.status_code, 201)
        record = self.client.post("/api/v1/dns/zones/example.test/records", headers=self.headers, json={
            "name": "www", "record_type": "A", "value": "192.0.2.20"
        })
        self.assertEqual(record.status_code, 201)
        records = self.client.get("/api/v1/dns/zones/example.test/records?name=www", headers=self.headers)
        self.assertEqual(records.status_code, 200)
        self.assertEqual(records.json()[0]["value"], "192.0.2.20")

    def test_dns_routes_require_authentication(self):
        self.assertEqual(self.client.get("/api/v1/dns/zones").status_code, 401)

    def test_invalid_dns_record_rejected(self):
        response = self.client.post("/api/v1/dns/zones/example.test/records", headers=self.headers, json={
            "name": "www", "record_type": "A", "value": "not-an-ip"
        })
        self.assertEqual(response.status_code, 422)

    def test_duplicate_zone_conflict(self):
        payload = {"name": "example.test"}
        self.client.post("/api/v1/dns/zones", headers=self.headers, json=payload)
        response = self.client.post("/api/v1/dns/zones", headers=self.headers, json=payload)
        self.assertEqual(response.status_code, 409)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, body):
        self.body = body
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.body)


class FreeIPADNSTests(unittest.TestCase):
    def test_zone_find_and_add_use_freeipa_json_rpc(self):
        session = FakeSession({"result": {"result": [{"idnsname": ["example.test"]}]}})
        adapter = FreeIPADirectory("https://ipa.example.test", session=session)
        self.assertEqual(adapter.list_dns_zones(), [{"name": "example.test"}])
        self.assertEqual(session.calls[0][1]["json"]["method"], "dnszone_find")
        adapter.create_dns_zone("example.test")
        self.assertEqual(session.calls[1][1]["json"]["method"], "dnszone_add")
        self.assertEqual(session.calls[1][1]["json"]["params"][0], ["example.test"])

    def test_record_create_maps_record_type_to_freeipa_option(self):
        session = FakeSession({"result": {"result": {}}})
        adapter = FreeIPADirectory("https://ipa.example.test", session=session)
        data = DNSRecordCreate(name="www", record_type="A", value="192.0.2.10")
        adapter.create_dns_record("example.test", data)
        payload = session.calls[0][1]["json"]
        self.assertEqual(payload["method"], "dnsrecord_add")
        self.assertEqual(payload["params"][0], ["example.test", "www"])
        self.assertEqual(payload["params"][1], {"a_rec": "192.0.2.10"})


if __name__ == "__main__":
    unittest.main()
