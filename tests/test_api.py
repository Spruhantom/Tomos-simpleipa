import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from simpleipa.api import MemoryDirectory, create_app, require_admin
from simpleipa.freeipa import FreeIPADirectory


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = MemoryDirectory()
        self.app = create_app(self.directory)
        self.client = TestClient(self.app)
        self.env = patch.dict(os.environ, {
            "SIMPLEIPA_ADMIN_USERNAME": "admin",
            "SIMPLEIPA_ADMIN_PASSWORD_HASH": PasswordHash.recommended().hash("correct horse battery staple"),
            "SIMPLEIPA_JWT_SECRET": "test-secret-material-at-least-32-characters",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def login(self):
        return self.client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "correct horse battery staple"
        })

    def test_health_is_public(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_login_and_authenticated_user_create(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        created = self.client.post("/api/v1/users", headers={"Authorization": f"Bearer {token}"}, json={
            "username": "alex", "given_name": "Alex", "family_name": "Example"
        })
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["username"], "alex")

    def test_wrong_password_rejected(self):
        response = self.client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        self.assertEqual(response.status_code, 401)

    def test_management_requires_bearer_token(self):
        self.assertEqual(self.client.get("/api/v1/users").status_code, 401)

    def test_expired_or_invalid_token_rejected(self):
        self.assertEqual(self.client.get("/api/v1/users", headers={"Authorization": "Bearer invalid"}).status_code, 401)

    def test_duplicate_user_returns_conflict(self):
        token = self.login().json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"username": "alex", "given_name": "Alex", "family_name": "Example"}
        self.client.post("/api/v1/users", headers=headers, json=payload)
        self.assertEqual(self.client.post("/api/v1/users", headers=headers, json=payload).status_code, 409)

    def test_group_creation(self):
        token = self.login().json()["access_token"]
        response = self.client.post("/api/v1/groups", headers={"Authorization": f"Bearer {token}"}, json={"name": "engineering"})
        self.assertEqual(response.status_code, 201)

    def test_invalid_username_rejected(self):
        token = self.login().json()["access_token"]
        response = self.client.post("/api/v1/users", headers={"Authorization": f"Bearer {token}"}, json={
            "username": "not a username", "given_name": "A", "family_name": "B"
        })
        self.assertEqual(response.status_code, 422)

    def test_unconfigured_directory_fails_closed(self):
        app = create_app()
        client = TestClient(app)
        token = self.login().json()["access_token"]
        response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 503)


class FreeIPATests(unittest.TestCase):
    def test_rejects_plain_http(self):
        with self.assertRaises(ValueError):
            FreeIPADirectory("http://ipa.example.test")

    def test_rejects_disabled_tls_verification(self):
        with self.assertRaises(ValueError):
            FreeIPADirectory("https://ipa.example.test", ca_bundle=False)


if __name__ == "__main__":
    unittest.main()
