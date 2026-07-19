import { SignJWT } from "jose";
import type { components } from "@/generated/api-schema";

type SyncedUser = components["schemas"]["SyncedUser"];
export type UserAddress = components["schemas"]["AddressView"];
export type CatalogService = components["schemas"]["ServiceView"];
export type CatalogSubcategory = components["schemas"]["SubcategoryView"];
export type CatalogCategory = components["schemas"]["CategoryView"];
export type ProviderProfile = components["schemas"]["ProviderProfileView"];
export type ProviderOffer = components["schemas"]["ProviderServiceView"];
export type AvailabilityRule = components["schemas"]["AvailabilityRuleView"];
export type AvailabilityException = components["schemas"]["AvailabilityExceptionView"];
export type ProviderRequirement = components["schemas"]["ProviderRequirementView"];
export type ProviderDocument = components["schemas"]["ProviderDocumentView"];
export type AdminDocument = components["schemas"]["AdminDocumentView"];
export type DocumentRequirement = components["schemas"]["RequirementView"];
export type SubscriptionPlan = components["schemas"]["SubscriptionPlanView"];
export type ProviderSubscriptionPage = components["schemas"]["ProviderSubscriptionPage"];
export type SubscriptionCheckout = components["schemas"]["SubscriptionCheckoutView"];
export type ServiceRequest = components["schemas"]["ServiceRequestView"];
export type ServiceBooking = components["schemas"]["BookingView"];
export type ConversationSummary = components["schemas"]["ConversationSummary"];
export type Conversation = components["schemas"]["ConversationView"];
export type NotificationPage = components["schemas"]["NotificationPage"];
export type UserNotification = components["schemas"]["NotificationView"];
export type FavoriteProvider = components["schemas"]["FavoriteProviderView"];
export type ServiceReview = components["schemas"]["ReviewView"];
export type PublicReview = components["schemas"]["PublicReviewView"];

type CatalogCreatePayloads = {
  categories: components["schemas"]["CategoryCreate"];
  subcategories: components["schemas"]["SubcategoryCreate"];
  services: components["schemas"]["ServiceCreate"];
};

type CatalogUpdatePayloads = {
  categories: components["schemas"]["CategoryUpdate"];
  subcategories: components["schemas"]["SubcategoryUpdate"];
  services: components["schemas"]["ServiceUpdate"];
};

const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8001";

function signingKey() {
  const secret = process.env.INTERNAL_API_JWT_SECRET;
  if (!secret || secret.length < 32) throw new Error("INTERNAL_API_JWT_SECRET must contain at least 32 characters");
  return new TextEncoder().encode(secret);
}

async function signInternalToken(subject: string, claims: Record<string, unknown>) {
  return new SignJWT(claims)
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setSubject(subject)
    .setAudience("sic-api")
    .setIssuedAt()
    .setExpirationTime("60s")
    .sign(signingKey());
}

export async function syncGoogleIdentity(identity: { googleSubject: string; email: string; name: string; avatarUrl?: string | null }): Promise<SyncedUser> {
  const token = await signInternalToken(`google:${identity.googleSubject}`, { purpose: "identity-sync" });
  const response = await fetch(`${apiUrl}/v1/identity/sync-google`, {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: JSON.stringify({ google_subject: identity.googleSubject, email: identity.email, name: identity.name, avatar_url: identity.avatarUrl ?? null }),
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error(`Identity sync failed with status ${response.status}`);
  return response.json() as Promise<SyncedUser>;
}

export async function createUserToken(userId: string, roles: string[], sessionId: string) {
  return signInternalToken(userId, { purpose: "user", roles, session_id: sessionId });
}

export async function replaceUserRoles(input: { userId: string; currentRoles: string[]; selectedRoles: string[]; sessionId: string }) {
  const token = await createUserToken(input.userId, input.currentRoles, input.sessionId);
  const response = await fetch(`${apiUrl}/v1/me/roles`, {
    method: "PUT",
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: JSON.stringify({ roles: input.selectedRoles }),
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error(`Role update failed with status ${response.status}`);
  return response.json() as Promise<{ roles: string[] }>;
}

export async function getUserAddresses(input: { userId: string; roles: string[]; sessionId: string }): Promise<UserAddress[]> {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  const response = await fetch(`${apiUrl}/v1/me/addresses`, { headers: { authorization: `Bearer ${token}` }, cache: "no-store", signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`Address list failed with status ${response.status}`);
  return response.json() as Promise<UserAddress[]>;
}

export async function createUserAddress(input: { userId: string; roles: string[]; sessionId: string; address: Record<string, unknown> }): Promise<UserAddress> {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  const response = await fetch(`${apiUrl}/v1/me/addresses`, { method: "POST", headers: { authorization: `Bearer ${token}`, "content-type": "application/json" }, body: JSON.stringify(input.address), cache: "no-store", signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`Address creation failed with status ${response.status}`);
  return response.json() as Promise<UserAddress>;
}

async function adminCatalogRequest(input: { userId: string; roles: string[]; sessionId: string; path?: string; method?: "GET" | "POST" | "PATCH"; body?: Record<string, unknown> }) {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  const response = await fetch(`${apiUrl}/v1/admin/catalog${input.path ?? ""}`, {
    method: input.method ?? "GET",
    headers: { authorization: `Bearer ${token}`, ...(input.body ? { "content-type": "application/json" } : {}) },
    body: input.body ? JSON.stringify(input.body) : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error(`Admin catalog request failed with status ${response.status}`);
  return response;
}

export async function getAdminCatalog(input: { userId: string; roles: string[]; sessionId: string }): Promise<CatalogCategory[]> {
  return (await adminCatalogRequest(input)).json() as Promise<CatalogCategory[]>;
}

export async function createAdminCatalogItem<K extends keyof CatalogCreatePayloads>(input: { userId: string; roles: string[]; sessionId: string; kind: K; body: CatalogCreatePayloads[K] }) {
  return (await adminCatalogRequest({ ...input, path: `/${input.kind}`, method: "POST" })).json();
}

export async function updateAdminCatalogItem<K extends keyof CatalogUpdatePayloads>(input: { userId: string; roles: string[]; sessionId: string; kind: K; id: string; body: CatalogUpdatePayloads[K] }) {
  return (await adminCatalogRequest({ ...input, path: `/${input.kind}/${input.id}`, method: "PATCH" })).json();
}

export async function getCatalogServices(): Promise<CatalogService[]> {
  const response = await fetch(`${apiUrl}/v1/catalog/services`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error(`Catalog services failed with status ${response.status}`);
  return response.json() as Promise<CatalogService[]>;
}

type ProviderRequestInput = {
  userId: string;
  roles: string[];
  sessionId: string;
  path: string;
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  formData?: FormData;
};

async function providerRequest(input: ProviderRequestInput) {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  return fetch(`${apiUrl}/v1/provider${input.path}`, {
    method: input.method ?? "GET",
    headers: { authorization: `Bearer ${token}`, ...(input.body !== undefined ? { "content-type": "application/json" } : {}) },
    body: input.formData ?? (input.body !== undefined ? JSON.stringify(input.body) : undefined),
    cache: "no-store",
    signal: AbortSignal.timeout(input.formData ? 30000 : 5000),
  });
}

type ProviderAuth = { userId: string; roles: string[]; sessionId: string };

export async function getProviderProfile(input: ProviderAuth): Promise<ProviderProfile | null> {
  const response = await providerRequest({ ...input, path: "/profile" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Provider profile failed with status ${response.status}`);
  return response.json() as Promise<ProviderProfile>;
}

export async function onboardProvider(input: ProviderAuth & { body: components["schemas"]["ProviderOnboarding"] }): Promise<ProviderProfile> {
  const response = await providerRequest({ ...input, path: "/onboarding", method: "POST", body: input.body });
  if (!response.ok) throw new Error(`Provider onboarding failed with status ${response.status}`);
  return response.json() as Promise<ProviderProfile>;
}

export async function updateProviderProfile(input: ProviderAuth & { body: components["schemas"]["ProviderProfileUpdate"] }): Promise<ProviderProfile> {
  const response = await providerRequest({ ...input, path: "/profile", method: "PATCH", body: input.body });
  if (!response.ok) throw new Error(`Provider profile update failed with status ${response.status}`);
  return response.json() as Promise<ProviderProfile>;
}

export async function pauseProviderProfile(input: ProviderAuth & { paused: boolean }): Promise<ProviderProfile> {
  const response = await providerRequest({ ...input, path: "/profile/pause", method: "POST", body: { paused: input.paused } });
  if (!response.ok) throw new Error(`Provider profile pause failed with status ${response.status}`);
  return response.json() as Promise<ProviderProfile>;
}

export async function addProviderPortfolioItem(input: ProviderAuth & { body: components["schemas"]["PortfolioItemCreate"] }): Promise<ProviderProfile> {
  const response = await providerRequest({ ...input, path: "/portfolio", method: "POST", body: input.body });
  if (!response.ok) throw new Error(`Portfolio creation failed with status ${response.status}`);
  return response.json() as Promise<ProviderProfile>;
}

export async function deleteProviderPortfolioItem(input: ProviderAuth & { itemId: string }): Promise<ProviderProfile> {
  const response = await providerRequest({ ...input, path: `/portfolio/${input.itemId}`, method: "DELETE" });
  if (!response.ok) throw new Error(`Portfolio deletion failed with status ${response.status}`);
  return response.json() as Promise<ProviderProfile>;
}

export async function getProviderOffers(input: ProviderAuth): Promise<ProviderOffer[]> {
  const response = await providerRequest({ ...input, path: "/services" });
  if (!response.ok) throw new Error(`Provider services failed with status ${response.status}`);
  return response.json() as Promise<ProviderOffer[]>;
}

export async function createProviderOffer(input: ProviderAuth & { body: components["schemas"]["ProviderServiceCreate"] }): Promise<ProviderOffer> {
  const response = await providerRequest({ ...input, path: "/services", method: "POST", body: input.body });
  if (!response.ok) throw new Error(`Provider service creation failed with status ${response.status}`);
  return response.json() as Promise<ProviderOffer>;
}

export async function pauseProviderOffer(input: ProviderAuth & { itemId: string; paused: boolean }): Promise<ProviderOffer> {
  const response = await providerRequest({ ...input, path: `/services/${input.itemId}/pause`, method: "POST", body: { paused: input.paused } });
  if (!response.ok) throw new Error(`Provider service pause failed with status ${response.status}`);
  return response.json() as Promise<ProviderOffer>;
}

export async function replaceProviderAvailability(input: ProviderAuth & { itemId: string; body: components["schemas"]["AvailabilityRulesReplace"] }): Promise<AvailabilityRule[]> {
  const response = await providerRequest({ ...input, path: `/services/${input.itemId}/availability`, method: "PUT", body: input.body });
  if (!response.ok) throw new Error(`Provider availability failed with status ${response.status}`);
  return response.json() as Promise<AvailabilityRule[]>;
}

export async function getProviderAvailabilityExceptions(input: ProviderAuth): Promise<AvailabilityException[]> {
  const response = await providerRequest({ ...input, path: "/availability/exceptions" });
  if (!response.ok) throw new Error(`Provider exceptions failed with status ${response.status}`);
  return response.json() as Promise<AvailabilityException[]>;
}

export async function addProviderAvailabilityException(input: ProviderAuth & { body: components["schemas"]["AvailabilityExceptionCreate"] }): Promise<AvailabilityException> {
  const response = await providerRequest({ ...input, path: "/availability/exceptions", method: "POST", body: input.body });
  if (!response.ok) throw new Error(`Provider exception creation failed with status ${response.status}`);
  return response.json() as Promise<AvailabilityException>;
}

export async function deleteProviderAvailabilityException(input: ProviderAuth & { itemId: string }): Promise<void> {
  const response = await providerRequest({ ...input, path: `/availability/exceptions/${input.itemId}`, method: "DELETE" });
  if (!response.ok) throw new Error(`Provider exception deletion failed with status ${response.status}`);
}

export async function getProviderDocumentRequirements(input: ProviderAuth): Promise<ProviderRequirement[]> {
  const response = await providerRequest({ ...input, path: "/document-requirements" });
  if (!response.ok) throw new Error(`Provider document requirements failed with status ${response.status}`);
  return response.json() as Promise<ProviderRequirement[]>;
}

export async function getProviderDocuments(input: ProviderAuth): Promise<ProviderDocument[]> {
  const response = await providerRequest({ ...input, path: "/documents" });
  if (!response.ok) throw new Error(`Provider documents failed with status ${response.status}`);
  return response.json() as Promise<ProviderDocument[]>;
}

export async function uploadProviderDocument(input: ProviderAuth & { formData: FormData }): Promise<ProviderDocument> {
  const response = await providerRequest({ ...input, path: "/documents", method: "POST", formData: input.formData });
  if (!response.ok) throw new Error(`Provider document upload failed with status ${response.status}`);
  return response.json() as Promise<ProviderDocument>;
}

export async function getProviderDocumentDownload(input: ProviderAuth & { documentId: string }): Promise<{ url: string; expires_in_seconds: number }> {
  const response = await providerRequest({ ...input, path: `/documents/${input.documentId}/download-url` });
  if (!response.ok) throw new Error(`Provider document download failed with status ${response.status}`);
  return response.json() as Promise<{ url: string; expires_in_seconds: number }>;
}

type AdminDocumentAuth = ProviderAuth;

async function adminDocumentRequest(input: AdminDocumentAuth & { path: string; method?: "GET" | "POST"; body?: unknown }) {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  return fetch(`${apiUrl}/v1/admin${input.path}`, {
    method: input.method ?? "GET",
    headers: { authorization: `Bearer ${token}`, ...(input.body !== undefined ? { "content-type": "application/json" } : {}) },
    body: input.body !== undefined ? JSON.stringify(input.body) : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
}

export async function getAdminDocumentRequirements(input: AdminDocumentAuth): Promise<DocumentRequirement[]> {
  const response = await adminDocumentRequest({ ...input, path: "/document-requirements" });
  if (!response.ok) throw new Error(`Admin document requirements failed with status ${response.status}`);
  return response.json() as Promise<DocumentRequirement[]>;
}

export async function saveAdminDocumentRequirement(input: AdminDocumentAuth & { body: components["schemas"]["RequirementUpsert"] }): Promise<DocumentRequirement> {
  const response = await adminDocumentRequest({ ...input, path: "/document-requirements", method: "POST", body: input.body });
  if (!response.ok) throw new Error(`Admin document requirement failed with status ${response.status}`);
  return response.json() as Promise<DocumentRequirement>;
}

export async function getAdminDocuments(input: AdminDocumentAuth): Promise<AdminDocument[]> {
  const response = await adminDocumentRequest({ ...input, path: "/documents" });
  if (!response.ok) throw new Error(`Admin document queue failed with status ${response.status}`);
  return response.json() as Promise<AdminDocument[]>;
}

export async function reviewAdminDocument(input: AdminDocumentAuth & { documentId: string; action: "review" | "approve" | "observe" | "reject" | "suspend" | "rescan"; body?: components["schemas"]["DocumentDecision"] }): Promise<AdminDocument> {
  const response = await adminDocumentRequest({ ...input, path: `/documents/${input.documentId}/${input.action}`, method: "POST", body: input.action === "review" || input.action === "rescan" ? undefined : (input.body ?? {}) });
  if (!response.ok) throw new Error(`Admin document action failed with status ${response.status}`);
  return response.json() as Promise<AdminDocument>;
}

export async function getAdminDocumentDownload(input: AdminDocumentAuth & { documentId: string }): Promise<{ url: string; expires_in_seconds: number }> {
  const response = await adminDocumentRequest({ ...input, path: `/documents/${input.documentId}/download-url` });
  if (!response.ok) throw new Error(`Admin document download failed with status ${response.status}`);
  return response.json() as Promise<{ url: string; expires_in_seconds: number }>;
}

export async function getProviderSubscription(input: ProviderAuth): Promise<ProviderSubscriptionPage> {
  const response = await providerRequest({ ...input, path: "/subscription" });
  if (!response.ok) throw new Error(`Provider subscription failed with status ${response.status}`);
  return response.json() as Promise<ProviderSubscriptionPage>;
}

export async function createProviderSubscriptionCheckout(input: ProviderAuth): Promise<SubscriptionCheckout> {
  const response = await providerRequest({ ...input, path: "/subscription/checkout", method: "POST" });
  if (!response.ok) throw new Error(`Provider subscription checkout failed with status ${response.status}`);
  return response.json() as Promise<SubscriptionCheckout>;
}

async function adminSubscriptionRequest(input: ProviderAuth & { path?: string; method?: "GET" | "POST" | "PATCH"; body?: unknown }) {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  return fetch(`${apiUrl}/v1/admin/subscription-plans${input.path ?? ""}`, {
    method: input.method ?? "GET",
    headers: { authorization: `Bearer ${token}`, ...(input.body !== undefined ? { "content-type": "application/json" } : {}) },
    body: input.body !== undefined ? JSON.stringify(input.body) : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  });
}

export async function getAdminSubscriptionPlans(input: ProviderAuth): Promise<SubscriptionPlan[]> {
  const response = await adminSubscriptionRequest(input);
  if (!response.ok) throw new Error(`Admin subscription plans failed with status ${response.status}`);
  return response.json() as Promise<SubscriptionPlan[]>;
}

export async function createAdminSubscriptionPlan(input: ProviderAuth & { body: components["schemas"]["SubscriptionPlanCreate"] }): Promise<SubscriptionPlan> {
  const response = await adminSubscriptionRequest({ ...input, method: "POST", body: input.body });
  if (!response.ok) throw new Error(`Admin subscription plan creation failed with status ${response.status}`);
  return response.json() as Promise<SubscriptionPlan>;
}

export async function updateAdminSubscriptionPlan(input: ProviderAuth & { planId: string; body: components["schemas"]["SubscriptionPlanUpdate"] }): Promise<SubscriptionPlan> {
  const response = await adminSubscriptionRequest({ ...input, path: `/${input.planId}`, method: "PATCH", body: input.body });
  if (!response.ok) throw new Error(`Admin subscription plan update failed with status ${response.status}`);
  return response.json() as Promise<SubscriptionPlan>;
}

async function responseError(response: Response, fallback: string): Promise<Error> {
  try {
    const body = await response.json() as { detail?: string };
    return new Error(body.detail || fallback);
  } catch {
    return new Error(fallback);
  }
}

async function clientRequest(input: ProviderAuth & { path: string; method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE"; body?: unknown; formData?: FormData }) {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  return fetch(`${apiUrl}/v1/client${input.path}`, {
    method: input.method ?? "GET",
    headers: { authorization: `Bearer ${token}`, ...(input.body !== undefined ? { "content-type": "application/json" } : {}) },
    body: input.formData ?? (input.body !== undefined ? JSON.stringify(input.body) : undefined),
    cache: "no-store",
    signal: AbortSignal.timeout(input.formData ? 30000 : 8000),
  });
}

export async function getClientServiceRequests(input: ProviderAuth): Promise<ServiceRequest[]> {
  const response = await clientRequest({ ...input, path: "/service-requests" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las solicitudes.");
  return response.json() as Promise<ServiceRequest[]>;
}

export async function createClientServiceRequest(input: ProviderAuth & { body: components["schemas"]["ServiceRequestCreate"] }): Promise<ServiceRequest> {
  const response = await clientRequest({ ...input, path: "/service-requests", method: "POST", body: input.body });
  if (!response.ok) throw await responseError(response, "No se pudo enviar la solicitud.");
  return response.json() as Promise<ServiceRequest>;
}

export async function uploadRequestAttachment(input: ProviderAuth & { requestId: string; file: File }): Promise<ServiceRequest> {
  const formData = new FormData();
  formData.set("file", input.file);
  const response = await clientRequest({ ...input, path: `/service-requests/${input.requestId}/attachments`, method: "POST", formData });
  if (!response.ok) throw await responseError(response, "No se pudo adjuntar el archivo.");
  return response.json() as Promise<ServiceRequest>;
}

export async function clientRequestAction(input: ProviderAuth & { requestId: string; action: "cancel" }): Promise<ServiceRequest> {
  const response = await clientRequest({ ...input, path: `/service-requests/${input.requestId}/${input.action}`, method: "POST" });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar la solicitud.");
  return response.json() as Promise<ServiceRequest>;
}

export async function decideClientQuote(input: ProviderAuth & { requestId: string; quoteId: string; action: "accept" | "reject"; schedule?: components["schemas"]["BookingSchedule"] }): Promise<ServiceRequest | ServiceBooking> {
  const path = input.action === "accept"
    ? `/service-requests/${input.requestId}/quotes/accept`
    : `/service-requests/${input.requestId}/quotes/${input.quoteId}/reject`;
  const body = input.action === "accept" ? { quote_id: input.quoteId, schedule: input.schedule ?? null } : undefined;
  const response = await clientRequest({ ...input, path, method: "POST", body });
  if (!response.ok) throw await responseError(response, "No se pudo responder el presupuesto.");
  return response.json() as Promise<ServiceRequest | ServiceBooking>;
}

export async function getClientBookings(input: ProviderAuth): Promise<ServiceBooking[]> {
  const response = await clientRequest({ ...input, path: "/bookings" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las contrataciones.");
  return response.json() as Promise<ServiceBooking[]>;
}

export async function clientBookingAction(input: ProviderAuth & { bookingId: string; action: "confirm" | "cancel" | "dispute"; reason?: string }): Promise<ServiceBooking> {
  const response = await clientRequest({ ...input, path: `/bookings/${input.bookingId}/${input.action}`, method: "POST", body: input.action === "dispute" ? { reason: input.reason } : undefined });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar la contratación.");
  return response.json() as Promise<ServiceBooking>;
}

export async function getProviderServiceRequests(input: ProviderAuth): Promise<ServiceRequest[]> {
  const response = await providerRequest({ ...input, path: "/service-requests" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las solicitudes.");
  return response.json() as Promise<ServiceRequest[]>;
}

export async function providerEngagementRequestAction(input: ProviderAuth & { requestId: string; action: "view" | "decline" | "accept"; body?: components["schemas"]["BookingSchedule"] }): Promise<ServiceRequest | ServiceBooking> {
  const response = await providerRequest({ ...input, path: `/service-requests/${input.requestId}/${input.action}`, method: "POST", body: input.action === "accept" ? (input.body ?? null) : undefined });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar la solicitud.");
  return response.json() as Promise<ServiceRequest | ServiceBooking>;
}

export async function createProviderQuote(input: ProviderAuth & { requestId: string; body: components["schemas"]["QuoteCreate"] }): Promise<ServiceRequest> {
  const response = await providerRequest({ ...input, path: `/service-requests/${input.requestId}/quotes`, method: "POST", body: input.body });
  if (!response.ok) throw await responseError(response, "No se pudo enviar el presupuesto.");
  return response.json() as Promise<ServiceRequest>;
}

export async function getProviderBookings(input: ProviderAuth): Promise<ServiceBooking[]> {
  const response = await providerRequest({ ...input, path: "/bookings" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las contrataciones.");
  return response.json() as Promise<ServiceBooking[]>;
}

export async function providerBookingAction(input: ProviderAuth & { bookingId: string; action: "confirm" | "start" | "complete" | "cancel" | "no-show" }): Promise<ServiceBooking> {
  const response = await providerRequest({ ...input, path: `/bookings/${input.bookingId}/${input.action}`, method: "POST" });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar la contratación.");
  return response.json() as Promise<ServiceBooking>;
}

async function meRequest(input: ProviderAuth & { path: string; method?: "GET" | "POST"; body?: unknown }) {
  const token = await createUserToken(input.userId, input.roles, input.sessionId);
  return fetch(`${apiUrl}/v1/me${input.path}`, {
    method: input.method ?? "GET",
    headers: { authorization: `Bearer ${token}`, ...(input.body !== undefined ? { "content-type": "application/json" } : {}) },
    body: input.body !== undefined ? JSON.stringify(input.body) : undefined,
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
}

export async function getConversations(input: ProviderAuth): Promise<ConversationSummary[]> {
  const response = await meRequest({ ...input, path: "/conversations" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las conversaciones.");
  return response.json() as Promise<ConversationSummary[]>;
}

export async function getConversation(input: ProviderAuth & { requestId: string }): Promise<Conversation> {
  const response = await meRequest({ ...input, path: `/conversations/${input.requestId}` });
  if (!response.ok) throw await responseError(response, "No se pudo cargar la conversación.");
  return response.json() as Promise<Conversation>;
}

export async function sendConversationMessage(input: ProviderAuth & { requestId: string; body: string }): Promise<Conversation> {
  const response = await meRequest({ ...input, path: `/conversations/${input.requestId}/messages`, method: "POST", body: { body: input.body } });
  if (!response.ok) throw await responseError(response, "No se pudo enviar el mensaje.");
  return response.json() as Promise<Conversation>;
}

export async function getNotifications(input: ProviderAuth): Promise<NotificationPage> {
  const response = await meRequest({ ...input, path: "/notifications" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las notificaciones.");
  return response.json() as Promise<NotificationPage>;
}

export async function markNotificationRead(input: ProviderAuth & { notificationId?: string }): Promise<void> {
  const path = input.notificationId ? `/notifications/${input.notificationId}/read` : "/notifications/read-all";
  const response = await meRequest({ ...input, path, method: "POST" });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar la notificación.");
}

export async function getClientFavorites(input: ProviderAuth): Promise<FavoriteProvider[]> {
  const response = await clientRequest({ ...input, path: "/favorites" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar los favoritos.");
  return response.json() as Promise<FavoriteProvider[]>;
}

export async function setClientFavorite(input: ProviderAuth & { providerSlug: string; favorite: boolean }): Promise<void> {
  const response = await clientRequest({ ...input, path: `/favorites/${encodeURIComponent(input.providerSlug)}`, method: input.favorite ? "PUT" : "DELETE" });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar el favorito.");
}

export async function getClientReviews(input: ProviderAuth): Promise<ServiceReview[]> {
  const response = await clientRequest({ ...input, path: "/reviews" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las opiniones.");
  return response.json() as Promise<ServiceReview[]>;
}

export async function submitClientReview(input: ProviderAuth & { bookingId: string; rating: number; comment: string }): Promise<ServiceReview> {
  const response = await clientRequest({ ...input, path: `/reviews/bookings/${input.bookingId}`, method: "POST", body: { rating: input.rating, comment: input.comment } });
  if (!response.ok) throw await responseError(response, "No se pudo enviar la opinión.");
  return response.json() as Promise<ServiceReview>;
}

export async function updateClientReview(input: ProviderAuth & { reviewId: string; rating: number; comment: string }): Promise<ServiceReview> {
  const response = await clientRequest({ ...input, path: `/reviews/${input.reviewId}`, method: "PATCH", body: { rating: input.rating, comment: input.comment } });
  if (!response.ok) throw await responseError(response, "No se pudo actualizar la opinión.");
  return response.json() as Promise<ServiceReview>;
}

export async function getProviderReviews(input: ProviderAuth): Promise<ServiceReview[]> {
  const response = await providerRequest({ ...input, path: "/reviews" });
  if (!response.ok) throw await responseError(response, "No se pudieron cargar las opiniones.");
  return response.json() as Promise<ServiceReview[]>;
}

export async function getAdminReviews(input: ProviderAuth): Promise<ServiceReview[]> {
  const response = await adminDocumentRequest({ ...input, path: "/reviews" });
  if (!response.ok) throw await responseError(response, "No se pudo cargar la moderación de opiniones.");
  return response.json() as Promise<ServiceReview[]>;
}

export async function moderateAdminReview(input: ProviderAuth & { reviewId: string; action: "publish" | "reject" | "hide"; reason?: string }): Promise<ServiceReview> {
  const response = await adminDocumentRequest({
    ...input,
    path: `/reviews/${input.reviewId}/moderate`,
    method: "POST",
    body: { action: input.action, reason: input.reason || null },
  });
  if (!response.ok) throw await responseError(response, "No se pudo moderar la opinión.");
  return response.json() as Promise<ServiceReview>;
}

export async function getPublicReviews(providerSlug: string): Promise<PublicReview[]> {
  try {
    const response = await fetch(`${apiUrl}/v1/providers/${encodeURIComponent(providerSlug)}/reviews`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (!response.ok) return [];
    return response.json() as Promise<PublicReview[]>;
  } catch {
    return [];
  }
}
