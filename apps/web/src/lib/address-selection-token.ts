import "server-only";

import { jwtVerify, SignJWT } from "jose";

import type { NormalizedGoogleAddress } from "@/lib/google-places";

const audience = "sic-address-selection";

export type VerifiedAddressSelection = {
  address: NormalizedGoogleAddress;
  anchorLatitude: number;
  anchorLongitude: number;
};

function signingKey(): Uint8Array {
  const secret = process.env.INTERNAL_API_JWT_SECRET;
  if (!secret || secret.length < 32) throw new Error("INTERNAL_API_JWT_SECRET must contain at least 32 characters");
  return new TextEncoder().encode(secret);
}

function isAddress(value: unknown): value is NormalizedGoogleAddress {
  if (!value || typeof value !== "object") return false;
  const address = value as Record<string, unknown>;
  const strings = ["google_place_id", "formatted_address", "street", "street_number", "city", "province", "country_code"];
  return strings.every((field) => typeof address[field] === "string" && address[field] !== "")
    && typeof address.latitude === "number" && Number.isFinite(address.latitude)
    && typeof address.longitude === "number" && Number.isFinite(address.longitude);
}

export async function signAddressSelection(input: { userId: string; sessionId: string; address: NormalizedGoogleAddress; anchorLatitude?: number; anchorLongitude?: number }): Promise<string> {
  return new SignJWT({
    purpose: "address-selection",
    session_id: input.sessionId,
    address: input.address,
    anchor_latitude: input.anchorLatitude ?? input.address.latitude,
    anchor_longitude: input.anchorLongitude ?? input.address.longitude,
  })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setSubject(input.userId)
    .setAudience(audience)
    .setIssuedAt()
    .setExpirationTime("10m")
    .sign(signingKey());
}

export async function verifyAddressSelection(token: string, input: { userId: string; sessionId: string }): Promise<VerifiedAddressSelection> {
  const { payload } = await jwtVerify(token, signingKey(), { algorithms: ["HS256"], audience, subject: input.userId });
  if (payload.purpose !== "address-selection" || payload.session_id !== input.sessionId || !isAddress(payload.address)
    || typeof payload.anchor_latitude !== "number" || !Number.isFinite(payload.anchor_latitude)
    || typeof payload.anchor_longitude !== "number" || !Number.isFinite(payload.anchor_longitude)) {
    throw new Error("Invalid address selection token");
  }
  return { address: payload.address, anchorLatitude: payload.anchor_latitude, anchorLongitude: payload.anchor_longitude };
}
