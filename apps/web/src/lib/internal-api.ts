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
