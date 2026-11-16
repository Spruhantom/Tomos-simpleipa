"""Authenticated management API with a fail-closed FreeIPA provider boundary."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

from .api_types import (
    DirectoryError, DirectoryUnavailable, DuplicateEntry,
    GroupCreate, GroupRecord, UserCreate, UserRecord,
)
from .freeipa import FreeIPADirectory
from .dns_types import DNSRecord, DNSRecordCreate, DNSZoneCreate
from .certificate_types import CertificateRecord, CertificateRequest, CertificateRequestResult


password_hasher = PasswordHash.recommended()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


class DirectoryProvider(Protocol):
    def list_users(self) -> list[UserRecord]: ...
    def create_user(self, data: UserCreate) -> UserRecord: ...
    def list_groups(self) -> list[GroupRecord]: ...
    def create_group(self, data: GroupCreate) -> GroupRecord: ...
    def list_dns_zones(self): ...
    def create_dns_zone(self, name: str): ...
    def list_dns_records(self, zone: str, name: str = "@"): ...
    def create_dns_record(self, zone: str, data: DNSRecordCreate): ...
    def list_certificates(self) -> list[CertificateRecord]: ...
    def request_certificate(self, data: CertificateRequest) -> CertificateRequestResult: ...


class UnconfiguredDirectory:
    def _unavailable(self):
        raise DirectoryUnavailable("No FreeIPA directory provider is configured")

    def list_users(self):
        self._unavailable()

    def create_user(self, data):
        self._unavailable()

    def list_groups(self):
        self._unavailable()

    def create_group(self, data):
        self._unavailable()

    def list_dns_zones(self):
        self._unavailable()

    def create_dns_zone(self, name):
        self._unavailable()

    def list_dns_records(self, zone, name="@"):
        self._unavailable()

    def create_dns_record(self, zone, data):
        self._unavailable()

    def list_certificates(self):
        self._unavailable()

    def request_certificate(self, data):
        self._unavailable()


class MemoryDirectory:
    """In-memory provider for tests only; never selected in production."""

    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.groups: dict[str, GroupRecord] = {}
        self.dns_zones: set[str] = set()
        self.dns_records: dict[tuple[str, str, str, str], DNSRecord] = {}
        self.certificates: dict[str, CertificateRecord] = {}

    def list_users(self):
        return list(self.users.values())

    def create_user(self, data: UserCreate):
        if data.username in {u.username for u in self.users.values()}:
            raise DuplicateEntry("A user with that username already exists")
        record = UserRecord(id=str(uuid4()), **data.model_dump())
        self.users[record.id] = record
        return record

    def list_groups(self):
        return list(self.groups.values())

    def create_group(self, data: GroupCreate):
        if data.name in {g.name for g in self.groups.values()}:
            raise DuplicateEntry("A group with that name already exists")
        record = GroupRecord(id=str(uuid4()), **data.model_dump())
        self.groups[record.id] = record
        return record

    def list_dns_zones(self):
        return [{"name": name} for name in sorted(self.dns_zones)]

    def create_dns_zone(self, name: str):
        if name in self.dns_zones:
            raise DuplicateEntry("That DNS zone already exists")
        self.dns_zones.add(name)
        return {"name": name}

    def list_dns_records(self, zone: str, name: str = "@"):
        if zone not in self.dns_zones:
            raise DirectoryUnavailable("DNS zone was not found")
        return [record for (z, n, _t, _v), record in self.dns_records.items() if z == zone and n == name]

    def create_dns_record(self, zone: str, data: DNSRecordCreate):
        if zone not in self.dns_zones:
            raise DirectoryUnavailable("DNS zone was not found")
        key = (zone, data.name, data.record_type, data.value)
        if key in self.dns_records:
            raise DuplicateEntry("That DNS record already exists")
        record = DNSRecord(name=data.name, record_type=data.record_type, value=data.value)
        self.dns_records[key] = record
        return record

    def list_certificates(self):
        return list(self.certificates.values())

    def request_certificate(self, data: CertificateRequest):
        # Test provider only: a stable fake serial makes API behaviour testable.
        serial = str(1001 + len(self.certificates))
        record = CertificateRecord(
            serial_number=serial, subject=f"CSR for {data.principal}",
            principal=data.principal, status="REQUESTED",
        )
        self.certificates[serial] = record
        return {"serial_number": serial, "request_id": None, "subject": record.subject, "certificate": None}


class Principal(BaseModel):
    subject: str


def _jwt_settings() -> tuple[str, str]:
    secret = os.getenv("SIMPLEIPA_JWT_SECRET", "")
    username = os.getenv("SIMPLEIPA_ADMIN_USERNAME", "")
    password_hash = os.getenv("SIMPLEIPA_ADMIN_PASSWORD_HASH", "")
    if len(secret) < 32 or not username or not password_hash:
        raise HTTPException(status_code=503, detail="Administrator authentication is not configured securely")
    return secret, username


def require_admin(authorization: str | None = Header(default=None)) -> Principal:
    secret, _ = _jwt_settings()
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        claims = jwt.decode(
            token, secret, algorithms=["HS256"], issuer="simpleipa",
            audience="simpleipa-admin",
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    return Principal(subject=str(claims["sub"]))


def create_app(directory: DirectoryProvider | None = None) -> FastAPI:
    app = FastAPI(title="SimpleIPA Management API", version="0.3.0")
    if directory is not None:
        app.state.directory = directory
    elif os.getenv("SIMPLEIPA_FREEIPA_URL"):
        app.state.directory = FreeIPADirectory.from_environment()
    else:
        app.state.directory = UnconfiguredDirectory()

    def get_directory() -> DirectoryProvider:
        return app.state.directory

    def map_directory_error(error: DirectoryError):
        if isinstance(error, DirectoryUnavailable):
            raise HTTPException(status_code=503, detail=str(error)) from error
        if isinstance(error, DuplicateEntry):
            raise HTTPException(status_code=409, detail=str(error)) from error
        raise HTTPException(status_code=502, detail="Directory operation failed") from error

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "simpleipa-api"}

    @app.post("/api/v1/auth/login")
    def login(data: LoginRequest):
        secret, username = _jwt_settings()
        stored_hash = os.getenv("SIMPLEIPA_ADMIN_PASSWORD_HASH", "")
        if data.username != username or not password_hasher.verify(data.password, stored_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {"sub": username, "iss": "simpleipa", "aud": "simpleipa-admin",
             "iat": now, "exp": now + timedelta(minutes=15)},
            secret, algorithm="HS256",
        )
        return {"access_token": token, "token_type": "bearer", "expires_in": 900}

    @app.get("/api/v1/users", response_model=list[UserRecord])
    def list_users(_: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.list_users()
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.post("/api/v1/users", response_model=UserRecord, status_code=201)
    def create_user(data: UserCreate, _: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.create_user(data)
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.get("/api/v1/groups", response_model=list[GroupRecord])
    def list_groups(_: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.list_groups()
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.post("/api/v1/groups", response_model=GroupRecord, status_code=201)
    def create_group(data: GroupCreate, _: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.create_group(data)
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.get("/api/v1/dns/zones")
    def list_dns_zones(_: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.list_dns_zones()
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.post("/api/v1/dns/zones", status_code=201)
    def create_dns_zone(data: DNSZoneCreate, _: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.create_dns_zone(data.name)
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.get("/api/v1/dns/zones/{zone}/records", response_model=list[DNSRecord])
    def list_dns_records(zone: str, name: str = "@", _: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.list_dns_records(zone, name)
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.post("/api/v1/dns/zones/{zone}/records", response_model=DNSRecord, status_code=201)
    def create_dns_record(zone: str, data: DNSRecordCreate, _: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.create_dns_record(zone, data)
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.get("/api/v1/certificates", response_model=list[CertificateRecord])
    def list_certificates(_: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.list_certificates()
        except DirectoryError as exc:
            map_directory_error(exc)

    @app.post("/api/v1/certificates/requests", response_model=CertificateRequestResult, status_code=201)
    def request_certificate(data: CertificateRequest, _: Principal = Depends(require_admin), db: DirectoryProvider = Depends(get_directory)):
        try:
            return db.request_certificate(data)
        except DirectoryError as exc:
            map_directory_error(exc)

    return app


app = create_app()
