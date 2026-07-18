import { SignJWT } from "jose";
import type { components } from "@/generated/api-schema";

type SyncedUser = components["schemas"]["SyncedUser"];
export type UserAddress = components["schemas"]["AddressView"];
export type CatalogService = components["schemas"]["ServiceView"];
export type CatalogSubcategory = components["schemas"]["SubcategoryView"];
export type CatalogCategory = components["schemas"]["CategoryView"];

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
