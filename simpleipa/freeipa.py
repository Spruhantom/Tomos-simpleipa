"""FreeIPA JSON-RPC adapter authenticated with Kerberos SPNEGO.

The adapter requires HTTPS and mutual Kerberos authentication. It never accepts
a FreeIPA password from the dashboard and never disables certificate checks.
"""
from __future__ import annotations

import os
from typing import Any

from .api_types import DirectoryUnavailable, DuplicateEntry, GroupCreate, GroupRecord, UserCreate, UserRecord


class FreeIPADirectory:
    def __init__(self, base_url: str, *, ca_bundle: str | bool = True, timeout: float = 10.0, session=None):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("FreeIPA URL must use HTTPS")
        if ca_bundle is False:
            raise ValueError("TLS certificate verification cannot be disabled")
        if timeout <= 0 or timeout > 60:
            raise ValueError("timeout must be between 0 and 60 seconds")
        if session is None:
            try:
                import requests
                from requests_gssapi import HTTPSPNEGOAuth, REQUIRED
            except ImportError as exc:
                raise RuntimeError("Install the 'freeipa' optional dependencies to enable FreeIPA") from exc
            session = requests.Session()
            session.auth = HTTPSPNEGOAuth(mutual_authentication=REQUIRED)
        self.base_url = base_url.rstrip("/")
        self.ca_bundle = ca_bundle
        self.timeout = timeout
        self.session = session

    @classmethod
    def from_environment(cls):
        url = os.environ["SIMPLEIPA_FREEIPA_URL"]
        ca = os.getenv("SIMPLEIPA_FREEIPA_CA_BUNDLE") or True
        return cls(url, ca_bundle=ca, timeout=float(os.getenv("SIMPLEIPA_TIMEOUT", "10")))

    def _call(self, method: str, args: list[Any] | None = None, options: dict[str, Any] | None = None):
        payload = {"method": method, "params": [args or [], options or {}], "id": 0}
        try:
            response = self.session.post(
                f"{self.base_url}/ipa/session/json",
                json=payload,
                headers={"Referer": self.base_url + "/", "Accept": "application/json"},
                verify=self.ca_bundle,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise DirectoryUnavailable("Could not securely communicate with the FreeIPA server") from exc
        error = body.get("error")
        if error:
            message = str(error.get("message", "FreeIPA request failed"))
            code = error.get("code")
            if code == 4001 or "already exists" in message.lower():
                raise DuplicateEntry("That directory entry already exists")
            raise DirectoryUnavailable("FreeIPA rejected the directory operation")
        result = body.get("result")
        if not isinstance(result, dict):
            raise DirectoryUnavailable("FreeIPA returned an unexpected response")
        return result.get("result", [])

    @staticmethod
    def _first(value):
        return value[0] if isinstance(value, list) and value else value

    def list_users(self):
        entries = self._call("user_find", [], {"sizelimit": 0})
        return [UserRecord(
            id=str(self._first(e.get("uid"))),
            username=str(self._first(e.get("uid"))),
            given_name=str(self._first(e.get("givenname")) or ""),
            family_name=str(self._first(e.get("sn")) or ""),
            email=self._first(e.get("mail")),
        ) for e in entries]

    def create_user(self, data: UserCreate):
        options = {"givenname": data.given_name, "sn": data.family_name}
        if data.email:
            options["mail"] = data.email
        entry = self._call("user_add", [data.username], options)
        entry = entry if isinstance(entry, dict) else {}
        return UserRecord(
            id=data.username, username=data.username,
            given_name=data.given_name, family_name=data.family_name, email=data.email,
        )

    def list_groups(self):
        entries = self._call("group_find", [], {"sizelimit": 0})
        return [GroupRecord(
            id=str(self._first(e.get("cn"))),
            name=str(self._first(e.get("cn"))),
            description=self._first(e.get("description")),
        ) for e in entries]

    def create_group(self, data: GroupCreate):
        options = {}
        if data.description:
            options["description"] = data.description
        self._call("group_add", [data.name], options)
        return GroupRecord(id=data.name, name=data.name, description=data.description)
