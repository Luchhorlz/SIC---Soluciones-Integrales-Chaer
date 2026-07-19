import os
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from sic_api.db.session import SessionFactory
from sic_api.modules.catalog.models import Service
from sic_api.modules.documents.models import DocumentReview, DocumentStatus, ProviderDocument, ReviewActorKind, ServiceDocumentRequirement
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.media.models import MediaFile, MediaScanStatus
from sic_api.modules.provider_services.models import PricingType, ProviderService, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderProfile
from sic_api.modules.users.models import User, UserRole, UserRoleName

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL integration runs in CI")


@pytest.mark.anyio
async def test_approval_satisfies_only_matching_service_and_expiry_is_audited() -> None:
    user_id = uuid4()
    provider_id = uuid4()
    media_id = uuid4()
    document_id = uuid4()
    requirement_id = uuid4()
    offer_id = uuid4()
    async with SessionFactory() as session:
        try:
            service = await session.scalar(select(Service).where(Service.is_active.is_(True)).limit(1))
            assert service is not None
            session.add(User(id=user_id, google_subject=f"document-test-{user_id}", email=f"document-{user_id}@example.invalid", name="Document test"))
            await session.flush()
            session.add(UserRole(user_id=user_id, role=UserRoleName.PROVIDER))
            session.add(ProviderProfile(id=provider_id, user_id=user_id, display_name="Prestador documental", slug=f"prestador-documental-{user_id.hex}", profile_completeness=20))
            await session.flush()
            session.add(ProviderService(id=offer_id, provider_id=provider_id, service_id=service.id, status=ProviderServiceStatus.PENDING_DOCUMENTS, headline="Oferta documental", description="Oferta usada para validar requisitos documentales específicos.", pricing_type=PricingType.QUOTE, price_currency="ARS"))
            session.add(ServiceDocumentRequirement(id=requirement_id, service_id=service.id, document_type="MATRICULA_TEST", label="Matrícula de prueba", is_required=True, jurisdiction_type="NONE", requires_expiration=True))
            session.add(MediaFile(id=media_id, owner_user_id=user_id, storage_bucket="test-private", object_key=f"documents/{user_id}/{media_id}.pdf", original_filename="matricula.pdf", mime_type="application/pdf", byte_size=24, sha256=uuid4().hex + uuid4().hex, scan_status=MediaScanStatus.CLEAN))
            await session.flush()
            session.add(ProviderDocument(id=document_id, provider_id=provider_id, document_type="MATRICULA_TEST", holder_name="Prestador documental", expires_at=date.today() + timedelta(days=30), media_file_id=media_id, status=DocumentStatus.APPROVED))
            await session.commit()

            repository = SqlAlchemyDocumentRepository(session)
            assert (await repository.readiness(provider_id, service.id)).ready is True

            document = await session.get(ProviderDocument, document_id)
            assert document is not None
            document.expires_at = date.today() - timedelta(days=1)
            await session.commit()
            expired_provider_ids = await repository.expire_approved()
            assert expired_provider_ids == [provider_id]
            readiness = await repository.readiness(provider_id, service.id)
            assert readiness.ready is False
            assert readiness.expired is True
            review = await session.scalar(select(DocumentReview).where(DocumentReview.document_id == document_id))
            assert review is not None
            assert review.actor_kind == ReviewActorKind.SYSTEM
            assert review.previous_status == DocumentStatus.APPROVED
            assert review.new_status == DocumentStatus.EXPIRED
        finally:
            await session.rollback()
            await session.execute(delete(DocumentReview).where(DocumentReview.document_id == document_id))
            await session.execute(delete(ProviderDocument).where(ProviderDocument.id == document_id))
            await session.execute(delete(ServiceDocumentRequirement).where(ServiceDocumentRequirement.id == requirement_id))
            await session.execute(delete(MediaFile).where(MediaFile.id == media_id))
            await session.execute(delete(ProviderService).where(ProviderService.id == offer_id))
            await session.execute(delete(ProviderProfile).where(ProviderProfile.id == provider_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
