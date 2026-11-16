import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from simpleipa.api import MemoryDirectory, create_app
from simpleipa.certificate_types import CertificateRequest
from simpleipa.freeipa import FreeIPADirectory


# Structurally valid PEM envelope for boundary tests; FreeIPA performs the
# authoritative PKCS#10 signature and profile validation.
CSR = "-----BEGIN CERTIFICATE REQUEST-----\n" + ("A" * 128) + "\n-----END CERTIFICATE REQUEST-----"


class CertificateValidationTests(unittest.TestCase):
    def test_accepts_pem_csr_and_normalises_principal_whitespace(self):
        request = CertificateRequest(principal=" host/ipa.example.test@EXAMPLE.TEST ", csr=CSR)
        self.assertEqual(request.principal, "host/ipa.example.test@EXAMPLE.TEST")

    def test_rejects_non_pem_csr(self):
        with self.assertRaises(ValueError):
            CertificateRequest(principal="user@example.test", csr="not a CSR")

    def test_rejects_invalid_base64_csr(self):
        with self.assertRaises(ValueError):
            CertificateRequest(principal="user@example.test", csr="-----BEGIN CERTIFICATE REQUEST-----\n!!!!\n-----END CERTIFICATE REQUEST-----")

    def test_rejects_invalid_principal(self):
        with self.assertRaises(ValueError):
            CertificateRequest(principal="bad principal", csr=CSR)


class CertificateAPITests(unittest.TestCase):
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

    def test_certificate_routes_require_authentication(self):
        self.assertEqual(self.client.get("/api/v1/certificates").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/certificates/requests", json={}).status_code, 401)

    def test_request_and_list_certificate(self):
        response = self.client.post("/api/v1/certificates/requests", headers=self.headers, json={
            "principal": "host/ipa.example.test@EXAMPLE.TEST", "csr": CSR
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["serial_number"], "1001")
        listing = self.client.get("/api/v1/certificates", headers=self.headers)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()[0]["serial_number"], "1001")

    def test_invalid_csr_rejected_before_provider_call(self):
        response = self.client.post("/api/v1/certificates/requests", headers=self.headers, json={
            "principal": "user@example.test", "csr": "not pem"
        })
        self.assertEqual(response.status_code, 422)


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


class FreeIPACertificateTests(unittest.TestCase):
    def test_certificate_request_uses_freeipa_ca_rpc(self):
        session = FakeSession({"result": {"result": {
            "serial_number": ["1234"], "request_id": ["77"],
            "subject": ["CN=ipa.example.test"], "certificate": ["-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----"]
        }}})
        adapter = FreeIPADirectory("https://ipa.example.test", session=session)
        result = adapter.request_certificate(CertificateRequest(principal="host/ipa.example.test@EXAMPLE.TEST", csr=CSR))
        payload = session.calls[0][1]["json"]
        self.assertEqual(payload["method"], "cert_request")
        self.assertEqual(payload["params"][0], [CSR])
        self.assertEqual(payload["params"][1]["principal"], "host/ipa.example.test@EXAMPLE.TEST")
        self.assertEqual(result["serial_number"], "1234")

    def test_certificate_find_normalises_result_rows(self):
        session = FakeSession({"result": {"result": {"count": 1, "result": [{
            "serial_number": ["1234"], "subject": ["CN=ipa.example.test"],
            "status": ["VALID"], "not_before": ["20261116000000Z"], "not_after": ["20271116000000Z"]
        }]}}})
        adapter = FreeIPADirectory("https://ipa.example.test", session=session)
        rows = adapter.list_certificates()
        self.assertEqual(rows[0]["serial_number"], "1234")
        self.assertEqual(rows[0]["status"], "VALID")


if __len__ == 0:
    pass
