import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { autocompleteAddresses, GooglePlacesError } from "@/lib/google-places";
import { consumePlacesQuota } from "@/lib/places-rate-limit";

export async function POST(request: Request) {
  if (!process.env.GOOGLE_MAPS_API_KEY) return NextResponse.json({ error: "Google Places todavía no está configurado." }, { status: 503 });
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId) return NextResponse.json({ error: "Necesitás iniciar sesión." }, { status: 401 });
  if (!consumePlacesQuota(`${session.user.id}:${session.internalSessionId}`)) return NextResponse.json({ error: "Realizaste demasiadas búsquedas. Esperá un momento." }, { status: 429 });
  try {
    const body = await request.json() as { input?: unknown; sessionToken?: unknown };
    if (typeof body.input !== "string" || typeof body.sessionToken !== "string") return NextResponse.json({ error: "La búsqueda no es válida." }, { status: 400 });
    return NextResponse.json({ suggestions: await autocompleteAddresses(body.input, body.sessionToken) });
  } catch (error) {
    if (error instanceof GooglePlacesError) return NextResponse.json({ error: error.publicMessage }, { status: error.statusCode });
    return NextResponse.json({ error: "No pudimos procesar la búsqueda." }, { status: 400 });
  }
}
