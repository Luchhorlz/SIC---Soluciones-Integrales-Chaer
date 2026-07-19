from uuid import uuid4

import pytest
from fastapi import HTTPException

from sic_api.main import app
from sic_api.modules.identity.permissions import Principal, get_document_reviewer_principal
from sic_api.modules.media.storage import FileValidationError, validate_private_document


def test_private_document_accepts_content_signature_not_extension() -> None:
    content = b"%PDF-1.7\nprivate-test\n%%EOF"
    result = validate_private_document(content, "matricula.exe", "application/pdf", 1024)
    assert result.mime_type == "application/pdf"
    assert result.extension == ".pdf"
    assert len(result.sha256) == 64


def test_private_document_rejects_spoofed_or_executable_content() -> None:
    with pytest.raises(FileValidationError):
        validate_private_document(b"MZ" + b"0" * 100, "matricula.pdf", "application/pdf", 1024)
    with pytest.raises(FileValidationError):
        validate_private_document(b"%PDF-1.7\n%%EOF", "matricula.pdf", "image/png", 1024)


def test_private_document_size_limit_is_enforced() -> None:
    with pytest.raises(FileValidationError):
        validate_private_document(b"%PDF-1.7\n" + b"0" * 100 + b"%%EOF", "matricula.pdf", "application/pdf", 32)


@pytest.mark.anyio
async def test_document_reviewer_role_is_required() -> None:
    with pytest.raises(HTTPException) as error:
        await get_document_reviewer_principal(Principal(user_id=uuid4(), roles=frozenset({"PROVIDER"}), session_id="test"))
    assert error.value.status_code == 403


@pytest.mark.anyio
@pytest.mark.parametrize("role", ["ADMIN", "DOCUMENT_REVIEWER"])
async def test_document_reviewer_roles_are_accepted(role: str) -> None:
    principal = Principal(user_id=uuid4(), roles=frozenset({role}), session_id="test")
    assert await get_document_reviewer_principal(principal) is principal


def test_document_api_has_private_upload_and_review_transitions() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/v1/provider/documents"]
    assert "get" in paths["/v1/provider/documents"]
    assert "post" in paths["/v1/admin/documents/{document_id}/approve"]
    assert "post" in paths["/v1/admin/documents/{document_id}/observe"]
    assert "post" in paths["/v1/admin/documents/{document_id}/reject"]
    assert all("delete" not in methods for path, methods in paths.items() if "documents" in path)
