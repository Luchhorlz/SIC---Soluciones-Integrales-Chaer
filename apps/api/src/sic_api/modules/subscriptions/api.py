import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import AdminPrincipal, ProviderPrincipal
from sic_api.modules.providers.repository import SqlAlchemyProviderRepository
from sic_api.modules.users.repository import SqlAlchemyUserRepository
from sic_api.settings import get_settings

from .billing import BillingProviderError, MercadoPagoBillingProvider
from .repository import SqlAlchemySubscriptionRepository, SubscriptionConflictError, SubscriptionPlanNotFoundError
from .schemas import ProviderSubscriptionPage, SubscriptionCheckoutView, SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanView, WebhookReceipt
from .security import InvalidWebhookSignatureError, validate_mercadopago_signature
from .service import BillingConfiguration, BillingConfigurationError, BillingEventProcessingError, MercadoPagoWebhookService, ProviderSubscriptionService, SubscriptionAdminService

provider_router = APIRouter(prefix="/v1/provider/subscription", tags=["provider-subscription"])
admin_router = APIRouter(prefix="/v1/admin/subscription-plans", tags=["admin-subscriptions"])
webhook_router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


def billing_provider() -> MercadoPagoBillingProvider | None:
    settings = get_settings()
    if not settings.mercadopago_access_token:
        return None
    return MercadoPagoBillingProvider(settings.mercadopago_access_token, settings.mercadopago_api_base_url, timeout_seconds=5.0)


def provider_subscription_service(session: AsyncSession) -> ProviderSubscriptionService:
    settings = get_settings()
    billing = billing_provider()
    return ProviderSubscriptionService(
        SqlAlchemySubscriptionRepository(session),
        billing,
        BillingConfiguration(configured=bool(settings.mercadopago_access_token and settings.mercadopago_webhook_secret), back_url=settings.mercadopago_success_url),
    )


async def provider_id_for_user(session: AsyncSession, user_id: UUID) -> UUID:
    profile = await SqlAlchemyProviderRepository(session).get_by_user(user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider onboarding is required")
    return profile.id


@provider_router.get("", response_model=ProviderSubscriptionPage)
async def get_provider_subscription(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderSubscriptionPage:
    return await provider_subscription_service(session).page(await provider_id_for_user(session, principal.user_id))


@provider_router.post("/checkout", response_model=SubscriptionCheckoutView)
async def create_provider_subscription_checkout(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> SubscriptionCheckoutView:
    provider_id = await provider_id_for_user(session, principal.user_id)
    contact = await SqlAlchemyUserRepository(session).get_billing_contact(principal.user_id)
    if contact is None or not contact.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="An active provider identity is required")
    try:
        return await provider_subscription_service(session).checkout(provider_id, contact.email)
    except BillingConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except SubscriptionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except BillingProviderError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@admin_router.get("", response_model=list[SubscriptionPlanView])
async def list_subscription_plans(_principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> list[SubscriptionPlanView]:
    return await SubscriptionAdminService(SqlAlchemySubscriptionRepository(session)).list_plans()


@admin_router.post("", response_model=SubscriptionPlanView, status_code=status.HTTP_201_CREATED)
async def create_subscription_plan(payload: SubscriptionPlanCreate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> SubscriptionPlanView:
    try:
        return await SubscriptionAdminService(SqlAlchemySubscriptionRepository(session)).create_plan(payload)
    except SubscriptionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@admin_router.patch("/{plan_id}", response_model=SubscriptionPlanView)
async def update_subscription_plan(plan_id: UUID, payload: SubscriptionPlanUpdate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> SubscriptionPlanView:
    try:
        return await SubscriptionAdminService(SqlAlchemySubscriptionRepository(session)).update_plan(plan_id, payload)
    except SubscriptionPlanNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found") from error


@webhook_router.post("/mercado-pago", response_model=WebhookReceipt)
async def receive_mercadopago_webhook(request: Request, session: AsyncSession = Depends(get_session)) -> WebhookReceipt:
    settings = get_settings()
    billing = billing_provider()
    if not settings.mercadopago_webhook_secret or billing is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mercado Pago webhooks are not configured")
    resource_id = request.query_params.get("data.id")
    try:
        validate_mercadopago_signature(
            signature=request.headers.get("x-signature"),
            request_id=request.headers.get("x-request-id"),
            data_id=resource_id,
            secret=settings.mercadopago_webhook_secret,
            tolerance_seconds=settings.mercadopago_webhook_tolerance_seconds,
        )
    except InvalidWebhookSignatureError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Mercado Pago webhook signature") from error
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook body") from error
    if not isinstance(payload, dict) or resource_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")
    try:
        result = await MercadoPagoWebhookService(SqlAlchemySubscriptionRepository(session), billing).process(
            payload=payload,
            raw_body=raw_body,
            resource_id=resource_id,
            request_id=request.headers.get("x-request-id"),
        )
    except BillingEventProcessingError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Verified billing event could not be processed") from error
    return WebhookReceipt(status=result)
