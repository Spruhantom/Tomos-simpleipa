"""Validated DNS request and response models."""
from __future__ import annotations

import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _domain(value: str) -> str:
    value = value.rstrip(".").lower()
    if len(value) > 253 or not value:
        raise ValueError("DNS domain must be 1-253 characters")
    labels = value.split(".")
    if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
        raise ValueError("Enter a valid DNS domain name")
    return value


class DNSZoneCreate(BaseModel):
    name: str = Field(min_length=3, max_length=253)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _domain(value)


class DNSZoneRecord(BaseModel):
    name: str


class DNSRecordCreate(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    record_type: Literal["A", "AAAA", "CNAME", "TXT"]
    value: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_record_name(cls, value: str) -> str:
        if value == "@":
            return value
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?", value):
            raise ValueError("Use a single DNS label or @ for the zone apex")
        return value.lower()

    @field_validator("value")
    @classmethod
    def validate_record_value(cls, value: str, info):
        record_type = info.data.get("record_type")
        if record_type == "A":
            try:
                if ipaddress.ip_address(value).version != 4:
                    raise ValueError
            except ValueError as exc:
                raise ValueError("A records require a valid IPv4 address") from exc
        elif record_type == "AAAA":
            try:
                if ipaddress.ip_address(value).version != 6:
                    raise ValueError
            except ValueError as exc:
                raise ValueError("AAAA records require a valid IPv6 address") from exc
        elif record_type == "CNAME":
            return _domain(value)
        elif record_type == "TXT":
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                raise ValueError("TXT values cannot contain control characters")
        return value


class DNSRecord(BaseModel):
    name: str
    record_type: str
    value: str
