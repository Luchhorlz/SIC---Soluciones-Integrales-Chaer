import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { verifyAddressSelection } from "@/lib/address-selection-token";
import { fetchStaticMap, GoogleStaticMapError } from "@/lib/google-static-map";
import { consumePlacesQuota } from "@/lib/places-rate-limit";

export async function POST(request: Request) {
  if (!process.env.GOOGLE_MAPS_API_KEY || !process.env.GOOGLE_MAPS_URL_SIGNING_SECRET) return NextResponse.json({ error: "El mapa todavía no está configurado." }, { status: 503 });
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return NextResponse.json({ error: "Necesitás iniciar sesión." }, { status: 401 });
  if (!consumePlacesQuota(`${session.user.id}:${session.internalSessionId}`)) return NextResponse.json({ error: "Realizaste demasiadas solicitudes. Esperá un momento." }, { status: 429 });
  try {
    const body = await request.json() as { selectionToken?: unknown };
    if (typeof body.selectionToken !== "string") return NextResponse.json({ error: "La selección no es válida." }, { status: 400 });
    const { address } = await verifyAddressSelection(body.selectionToken, { userId: session.user.id, sessionId: session.internalSessionId });
    const map = await fetchStaticMap(address.latitude, address.longitude);
    return new Response(map.bytes, { status: 200, headers: { "content-type": map.contentType, "cache-control": "private, no-store", "x-content-type-options": "nosniff" } });
  } catch (error) {
    if (error instanceof GoogleStaticMapError) return NextResponse.json({ error: error.publicMessage }, { status: error.statusCode });
    return NextResponse.json({ error: "No pudimos cargar el mapa." }, { status: 400 });
  }
}
