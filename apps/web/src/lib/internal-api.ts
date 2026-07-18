import { SignJWT } from "jose";

type SyncedUser = {
  id: string;
  email: string;
  name: string;
  roles: string[];
  status: string;
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
