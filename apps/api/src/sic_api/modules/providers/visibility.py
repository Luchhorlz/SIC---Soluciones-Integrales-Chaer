import enum
from dataclasses import dataclass

from sic_api.modules.provider_services.models import ProviderModality, ProviderServiceStatus

from .models import ProviderProfileStatus, SubscriptionVisibilityStatus


class VisibilityCode(str, enum.Enum):
    VISIBLE = "VISIBLE"
    USER_INACTIVE = "USER_INACTIVE"
    NO_ACTIVE_SUBSCRIPTION = "NO_ACTIVE_SUBSCRIPTION"
    PROFILE_NOT_APPROVED = "PROFILE_NOT_APPROVED"
    PROFILE_PAUSED = "PROFILE_PAUSED"
    SERVICE_PAUSED = "SERVICE_PAUSED"
    NO_MODALITY = "NO_MODALITY"
    DOCUMENT_PENDING = "DOCUMENT_PENDING"
    DOCUMENT_EXPIRED = "DOCUMENT_EXPIRED"
    NO_SERVICE_AREA = "NO_SERVICE_AREA"
    ADMIN_SUSPENDED = "ADMIN_SUSPENDED"


@dataclass(frozen=True)
class ProviderVisibilityContext:
    user_active: bool
    profile_status: ProviderProfileStatus
    profile_paused: bool
    subscription_status: SubscriptionVisibilityStatus
    service_status: ProviderServiceStatus
    modalities: frozenset[ProviderModality]
    has_service_area: bool
    documents_ready: bool
    documents_expired: bool = False


@dataclass(frozen=True)
class ProviderVisibilityResult:
    visible: bool
    code: VisibilityCode


class ProviderVisibilityService:
    coverage_modalities = frozenset({ProviderModality.AT_CLIENT_ADDRESS, ProviderModality.HYBRID, ProviderModality.PICKUP_DELIVERY})

    def evaluate(self, context: ProviderVisibilityContext) -> ProviderVisibilityResult:
        if not context.user_active:
            return ProviderVisibilityResult(False, VisibilityCode.USER_INACTIVE)
        if context.profile_status in {ProviderProfileStatus.SUSPENDED, ProviderProfileStatus.BLOCKED}:
            return ProviderVisibilityResult(False, VisibilityCode.ADMIN_SUSPENDED)
        if context.profile_paused:
            return ProviderVisibilityResult(False, VisibilityCode.PROFILE_PAUSED)
        if context.profile_status != ProviderProfileStatus.APPROVED:
            return ProviderVisibilityResult(False, VisibilityCode.PROFILE_NOT_APPROVED)
        if context.subscription_status not in {SubscriptionVisibilityStatus.ACTIVE, SubscriptionVisibilityStatus.AUTHORIZED}:
            return ProviderVisibilityResult(False, VisibilityCode.NO_ACTIVE_SUBSCRIPTION)
        if context.service_status != ProviderServiceStatus.ACTIVE:
            return ProviderVisibilityResult(False, VisibilityCode.SERVICE_PAUSED)
        if not context.modalities:
            return ProviderVisibilityResult(False, VisibilityCode.NO_MODALITY)
        if context.modalities & self.coverage_modalities and not context.has_service_area:
            return ProviderVisibilityResult(False, VisibilityCode.NO_SERVICE_AREA)
        if context.documents_expired:
            return ProviderVisibilityResult(False, VisibilityCode.DOCUMENT_EXPIRED)
        if not context.documents_ready:
            return ProviderVisibilityResult(False, VisibilityCode.DOCUMENT_PENDING)
        return ProviderVisibilityResult(True, VisibilityCode.VISIBLE)
