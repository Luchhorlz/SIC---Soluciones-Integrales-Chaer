from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import MediaFile, MediaScanStatus


class DuplicateMediaError(ValueError):
    pass


class MediaRepository(Protocol):
    async def find_duplicate(self, owner_user_id: UUID, sha256: str) -> MediaFile | None: ...
    async def create(self, item: MediaFile) -> MediaFile: ...
    async def get(self, media_id: UUID) -> MediaFile | None: ...
    async def set_scan_status(self, media_id: UUID, status: MediaScanStatus, message: str | None = None) -> MediaFile: ...


class SqlAlchemyMediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_duplicate(self, owner_user_id: UUID, sha256: str) -> MediaFile | None:
        return await self.session.scalar(select(MediaFile).where(MediaFile.owner_user_id == owner_user_id, MediaFile.sha256 == sha256))

    async def create(self, item: MediaFile) -> MediaFile:
        self.session.add(item)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise DuplicateMediaError("This exact file was already uploaded") from error
        await self.session.refresh(item)
        return item

    async def get(self, media_id: UUID) -> MediaFile | None:
        return await self.session.get(MediaFile, media_id)

    async def set_scan_status(self, media_id: UUID, status: MediaScanStatus, message: str | None = None) -> MediaFile:
        item = await self.session.get(MediaFile, media_id)
        if item is None:
            raise LookupError("Media file not found")
        item.scan_status = status
        item.scan_message = message[:240] if message else None
        await self.session.commit()
        await self.session.refresh(item)
        return item
