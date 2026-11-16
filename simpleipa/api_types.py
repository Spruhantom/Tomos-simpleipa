"""Shared types and errors used by the directory adapter."""
from .api import DirectoryUnavailable, DuplicateEntry, GroupCreate, GroupRecord, UserCreate, UserRecord

__all__ = ["DirectoryUnavailable", "DuplicateEntry", "GroupCreate", "GroupRecord", "UserCreate", "UserRecord"]
