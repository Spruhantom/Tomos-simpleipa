"""Typed directory records and provider errors shared by API and adapters."""
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    given_name: str = Field(min_length=1, max_length=128)
    family_name: str = Field(min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=254)


class UserRecord(UserCreate):
    id: str


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=512)


class GroupRecord(GroupCreate):
    id: str


class DirectoryError(Exception):
    pass


class DirectoryUnavailable(DirectoryError):
    pass


class DuplicateEntry(DirectoryError):
    pass
