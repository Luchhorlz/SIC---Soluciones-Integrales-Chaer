import "server-only";

import { createHmac } from "node:crypto";

export class GoogleStaticMapError extends Error {
  constructor(public readonly publicMessage: string, public readonly statusCode = 502) {
    super(publicMessage);
  }
}

function apiKey(): string {
  const value = process.env.GOOGLE_MAPS_API_KEY?.trim();
  if (!value) throw new GoogleStaticMapError("Google Maps todavía no está configurado.", 503);
  return value;
}

function signingSecret(): Buffer {
  const value = process.env.GOOGLE_MAPS_URL_SIGNING_SECRET?.trim();
  if (!value) throw new GoogleStaticMapError("La firma privada del mapa todavía no está configurada.", 503);
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const decoded = Buffer.from(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="), "base64");
  if (decoded.length < 16) throw new GoogleStaticMapError("La firma privada del mapa no es válida.", 503);
  return decoded;
}

function signedUrl(latitude: number, longitude: number): string {
  const url = new URL("https://maps.googleapis.com/maps/api/staticmap");
  url.searchParams.set("center", `${latitude.toFixed(6)},${longitude.toFixed(6)}`);
  url.searchParams.set("zoom", "17");
  url.searchParams.set("size", "640x360");
  url.searchParams.set("scale", "1");
  url.searchParams.set("maptype", "roadmap");
  url.searchParams.set("language", "es");
  url.searchParams.set("region", "AR");
  url.searchParams.set("key", apiKey());
  const resource = `${url.pathname}${url.search}`;
  url.searchParams.set("signature", createHmac("sha1", signingSecret()).update(resource).digest("base64url"));
  return url.toString();
}

export async function fetchStaticMap(latitude: number, longitude: number): Promise<{ bytes: ArrayBuffer; contentType: string }> {
  let response: Response;
  try {
    response = await fetch(signedUrl(latitude, longitude), { cache: "no-store", signal: AbortSignal.timeout(5000) });
  } catch {
    throw new GoogleStaticMapError("Google Maps no respondió a tiempo.", 504);
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.startsWith("image/")) throw new GoogleStaticMapError("No pudimos cargar el mapa.", response.status === 429 ? 429 : 502);
  return { bytes: await response.arrayBuffer(), contentType };
}
