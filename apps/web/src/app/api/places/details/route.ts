import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { signAddressSelection } from "@/lib/address-selection-token";
import { getAddressDetails, GooglePlacesError } from "@/lib/google-places";
import { consumePlacesQuota } from "@/lib/places-rate-limit";

export async function POST(request: Request) {
  if (!process.env.GOOGLE_MAPS_API_KEY) return NextResponse.json({ error: "Google Places todavía no está configurado." }, { status: 503 });
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return NextResponse.json({ error: "Necesitás iniciar sesión." }, { status: 401 });
  if (!consumePlacesQuota(`${session.user.id}:${session.internalSessionId}`)) return NextResponse.json({ error: "Realizaste demasiadas búsquedas. Esperá un momento." }, { status: 429 });
  try {
    const body = await request.json() as { placeId?: unknown; sessionToken?: unknown };
    if (typeof body.placeId !== "string" || typeof body.sessionToken !== "string") return NextResponse.json({ error: "La selección no es válida." }, { status: 400 });
    const address = await getAddressDetails(body.placeId, body.sessionToken);
    const selectionToken = await signAddressSelection({ userId: session.user.id, sessionId: session.internalSessionId, address });
    return NextResponse.json({ address, selectionToken });
  } catch (error) {
    if (error instanceof GooglePlacesError) return NextResponse.json({ error: error.publicMessage }, { status: error.statusCode });
    return NextResponse.json({ error: "No pudimos confirmar esa dirección." }, { status: 400 });
  }
}
