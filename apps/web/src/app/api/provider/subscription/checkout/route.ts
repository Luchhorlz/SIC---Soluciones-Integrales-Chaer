import { NextResponse } from "next/server";

import { auth } from "@/auth";
import { createProviderSubscriptionCheckout } from "@/lib/internal-api";

function safeCheckoutUrl(value: string): URL | null {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !["mercadopago.com.ar", "www.mercadopago.com.ar"].includes(url.hostname.toLowerCase())) return null;
    return url;
  } catch {
    return null;
  }
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("PROVIDER")) {
    return NextResponse.redirect(new URL("/ingresar", request.url), 303);
  }
  try {
    const checkout = await createProviderSubscriptionCheckout({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId });
    const destination = safeCheckoutUrl(checkout.checkout_url);
    if (!destination) throw new Error("Unexpected checkout URL");
    return NextResponse.redirect(destination, 303);
  } catch {
    return NextResponse.redirect(new URL("/prestador/suscripcion?error=checkout", request.url), 303);
  }
}
