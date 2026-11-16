"""Versioned management API. Directory operations are delegated to a provider.

The default provider is deliberately unavailable: the API never silently stores
identities in process memory or pretends to be connected to FreeIPA.
"""
from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    given_name: str = Field(min_length=1, max_length=128)
    family_name: str = Field(min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    groups: list[str] = Field(default_factory=list, max_length=100)


class UserRecord(UserCreate):
    id: str


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=512)


class GroupRecord(GroupCreate):
    id: str


class DirectoryError(Exception):
    """Base class for directory adapter errors."""


class DirectoryUnavailable(DirectoryError):
    pass


class DuplicateEntry(DirectoryError):
    pass


class DirectoryProvider(Protocol):
    def list_users(self) -> list[UserRecord]: ...
    def create_user(self, data: UserCreate) -> UserRecord: ...
    def list_groups(self) -> list[GroupRecord]: ...
    def create_group(self, data: GroupCreate) -> GroupRecord: ...


class UnconfiguredDirectory:
    """Fail-closed placeholder until a supported FreeIPA adapter is configured."""

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


class MemoryDirectory:
    """Test-only provider; never selected by the production app factory."""

    def __init__(self):
        self.users: dict[str, UserRecord] = {}
        self.groups: dict[str, GroupRecord] = {}

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


@dataclass(frozen=True)
class Principal:
    subject: str


def require_admin(authorization: str | None = Header(default=None)) -> Principal:
    configured = os.getenv("SIMPLEIPA_API_TOKEN")
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")
    return Principal(subject="configured-api-admin")


def create_app(directory: DirectoryProvider | None = None) -> FastAPI:
    app = FastAPI(
        title="SimpleIPA Management API",
        version="0.1.0",
        description="Versioned management API; directory operations require an explicit provider.",
    )
    provider = directory or UnconfiguredDirectory()
    app.state.directory = provider

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

    return app


app = create_app()
