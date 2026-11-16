"""Validated certificate request and response models.

Private keys must remain with the requesting client. SimpleIPA accepts only a
PKCS#10 certificate signing request (CSR), never a private key.
"""
from __future__ import annotations

import base64
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


_CSR_BEGIN = "-----BEGIN CERTIFICATE REQUEST-----"
_CSR_END = "-----END CERTIFICATE REQUEST-----"


class CertificateRequest(BaseModel):
    principal: str = Field(min_length=3, max_length=255)
    csr: str = Field(min_length=100, max_length=65536)

    @field_validator("principal")
    @classmethod
    def validate_principal(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9._/@-]+", value) or value.startswith("/") or value.endswith("@"):
            raise ValueError("Enter a valid FreeIPA user, service or host principal")
        return value

    @field_validator("csr")
    @classmethod
    def validate_csr_pem(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(_CSR_BEGIN) or not value.endswith(_CSR_END):
            raise ValueError("CSR must be a PEM-encoded PKCS#10 certificate request")
        body = value[len(_CSR_BEGIN):-len(_CSR_END)]
        encoded = "".join(body.split())
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ValueError("CSR contains invalid PEM base64 data") from exc
        if len(decoded) < 64:
            raise ValueError("CSR content is too short")
        return value


class CertificateRecord(BaseModel):
    serial_number: str
    subject: Optional[str] = None
    principal: Optional[str] = None
    status: Optional[str] = None
    issued_on: Optional[str] = None
    expires_on: Optional[str] = None


class CertificateRequestResult(BaseModel):
    serial_number: str
    request_id: Optional[str] = None
    subject: Optional[str] = None
    certificate: Optional[str] = None
