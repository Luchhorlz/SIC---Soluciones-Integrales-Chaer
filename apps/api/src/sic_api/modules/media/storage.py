import asyncio
import hashlib
import socket
import struct
from dataclasses import dataclass
from pathlib import PurePath
from typing import Protocol
from uuid import UUID

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from sic_api.settings import Settings


class FileValidationError(ValueError):
    pass


class StorageUnavailableError(RuntimeError):
    pass


class MalwareDetectedError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedFile:
    content: bytes
    original_filename: str
    mime_type: str
    extension: str
    sha256: str


class PrivateStorage(Protocol):
    async def put(self, key: str, content: bytes, mime_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def presigned_download(self, key: str, filename: str, ttl_seconds: int) -> str: ...


class AntivirusScanner(Protocol):
    async def scan(self, content: bytes) -> str: ...


def validate_private_document(content: bytes, filename: str, declared_mime: str | None, max_bytes: int) -> ValidatedFile:
    if not content:
        raise FileValidationError("The uploaded file is empty")
    if len(content) > max_bytes:
        raise FileValidationError(f"The file exceeds the {max_bytes // (1024 * 1024)} MB limit")
    safe_name = PurePath(filename or "document").name[:255]
    lowered_mime = (declared_mime or "").lower().split(";", 1)[0].strip()
    detected: tuple[str, str] | None = None
    if content.startswith(b"%PDF-") and b"%%EOF" in content[-4096:]:
        detected = ("application/pdf", ".pdf")
    elif content.startswith(b"\x89PNG\r\n\x1a\n") and b"IEND" in content[-64:]:
        detected = ("image/png", ".png")
    elif content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        detected = ("image/jpeg", ".jpg")
    if detected is None:
        raise FileValidationError("Only valid PDF, PNG or JPEG documents are accepted")
    if lowered_mime and lowered_mime not in {detected[0], "image/jpg" if detected[0] == "image/jpeg" else detected[0]}:
        raise FileValidationError("The declared file type does not match its content")
    return ValidatedFile(content=content, original_filename=safe_name, mime_type=detected[0], extension=detected[1], sha256=hashlib.sha256(content).hexdigest())


class S3PrivateStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._internal = self._client(settings.s3_endpoint) if settings.s3_access_key and settings.s3_secret_key else None
        self._presign = self._client(settings.s3_presign_endpoint or settings.s3_endpoint) if settings.s3_access_key and settings.s3_secret_key else None

    def _configured(self):
        if self._internal is None or self._presign is None:
            raise StorageUnavailableError("Private object storage is not configured")
        return self._internal, self._presign

    def _client(self, endpoint: str):
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=self.settings.s3_region,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def _ensure_bucket(self) -> None:
        internal, _ = self._configured()
        try:
            internal.head_bucket(Bucket=self.settings.s3_bucket_private)
        except ClientError as error:
            status_code = int(error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
            if status_code not in {400, 404}:
                raise
            internal.create_bucket(Bucket=self.settings.s3_bucket_private)

    async def put(self, key: str, content: bytes, mime_type: str) -> None:
        def operation() -> None:
            self._ensure_bucket()
            internal, _ = self._configured()
            internal.put_object(Bucket=self.settings.s3_bucket_private, Key=key, Body=content, ContentType=mime_type)
        try:
            await asyncio.to_thread(operation)
        except Exception as error:
            raise StorageUnavailableError("Private object storage rejected the upload") from error

    async def get(self, key: str) -> bytes:
        try:
            internal, _ = self._configured()
            response = await asyncio.to_thread(internal.get_object, Bucket=self.settings.s3_bucket_private, Key=key)
            return await asyncio.to_thread(response["Body"].read)
        except Exception as error:
            raise StorageUnavailableError("Private object storage could not read the file") from error

    async def delete(self, key: str) -> None:
        try:
            internal, _ = self._configured()
            await asyncio.to_thread(internal.delete_object, Bucket=self.settings.s3_bucket_private, Key=key)
        except Exception as error:
            raise StorageUnavailableError("Private object storage could not remove the file") from error

    async def presigned_download(self, key: str, filename: str, ttl_seconds: int) -> str:
        disposition = f'attachment; filename="document{PurePath(filename).suffix.lower()}"'
        try:
            _, presign = self._configured()
            return await asyncio.to_thread(
                presign.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.settings.s3_bucket_private, "Key": key, "ResponseContentDisposition": disposition},
                ExpiresIn=ttl_seconds,
            )
        except Exception as error:
            raise StorageUnavailableError("A private download link could not be generated") from error


class ClamAVScanner:
    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds

    def _scan(self, content: bytes) -> str:
        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as connection:
            connection.settimeout(self.timeout_seconds)
            connection.sendall(b"zINSTREAM\0")
            for offset in range(0, len(content), 64 * 1024):
                chunk = content[offset:offset + 64 * 1024]
                connection.sendall(struct.pack(">I", len(chunk)) + chunk)
            connection.sendall(struct.pack(">I", 0))
            response = bytearray()
            while not response.endswith(b"\0") and len(response) < 4096:
                part = connection.recv(4096)
                if not part:
                    break
                response.extend(part)
        message = response.rstrip(b"\0").decode("utf-8", "replace")
        if message.endswith(" OK"):
            return message
        if message.endswith(" FOUND"):
            raise MalwareDetectedError("The document was rejected by antivirus")
        raise StorageUnavailableError("Antivirus scanning did not return a valid result")

    async def scan(self, content: bytes) -> str:
        try:
            return await asyncio.to_thread(self._scan, content)
        except MalwareDetectedError:
            raise
        except Exception as error:
            raise StorageUnavailableError("Antivirus scanning is temporarily unavailable") from error


def document_object_key(owner_user_id: UUID, media_id: UUID, extension: str) -> str:
    return f"documents/{owner_user_id}/{media_id}{extension}"
