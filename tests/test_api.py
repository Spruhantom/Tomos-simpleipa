import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from simpleipa.api import MemoryDirectory, create_app, require_admin


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = MemoryDirectory()
        self.app = create_app(self.directory)
        self.app.dependency_overrides[require_admin] = lambda: object()
        self.client = TestClient(self.app)

    def test_health_is_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_create_and_list_user(self):
        payload = {"username": "alex", "given_name": "Alex", "family_name": "Example"}
        created = self.client.post("/api/v1/users", json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["username"], "alex")
        listed = self.client.get("/api/v1/users")
        self.assertEqual([u["username"] for u in listed.json()], ["alex"])

    def test_duplicate_user_returns_conflict(self):
        payload = {"username": "alex", "given_name": "Alex", "family_name": "Example"}
        self.client.post("/api/v1/users", json=payload)
        response = self.client.post("/api/v1/users", json=payload)
        self.assertEqual(response.status_code, 409)

    def test_create_group(self):
        response = self.client.post("/api/v1/groups", json={"name": "engineering"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "engineering")

    def test_invalid_username_rejected(self):
        response = self.client.post("/api/v1/users", json={
            "username": "not a username", "given_name": "A", "family_name": "B"
        })
        self.assertEqual(response.status_code, 422)

    def test_default_app_fails_closed_without_provider(self):
        from simpleipa.api import app as default_app
        default_client = TestClient(default_app)
        default_app.dependency_overrides[require_admin] = lambda: object()
        response = default_client.get("/api/v1/users")
        self.assertEqual(response.status_code, 503)
        default_app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
