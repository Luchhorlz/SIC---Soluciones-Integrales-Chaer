"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { createProviderQuote, providerBookingAction, providerEngagementRequestAction } from "@/lib/internal-api";

function value(formData: FormData, key: string) { return String(formData.get(key) ?? "").trim(); }
function argentinaDateTime(raw: string) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(raw)) throw new Error("Invalid date");
  return new Date(`${raw}:00-03:00`).toISOString();
}
async function providerSession() {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("PROVIDER")) throw new Error("Provider role required");
  return { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
}
function refresh() { revalidatePath("/prestador/solicitudes"); revalidatePath("/prestador/contrataciones"); revalidatePath("/cuenta/contrataciones"); }

export async function markRequestViewed(formData: FormData) {
  try { await providerEngagementRequestAction({ ...await providerSession(), requestId: value(formData, "request_id"), action: "view" }); }
  catch { redirect("/prestador/solicitudes?error=request"); }
  refresh(); redirect("/prestador/solicitudes?status=viewed");
}

export async function declineProviderRequest(formData: FormData) {
  try { await providerEngagementRequestAction({ ...await providerSession(), requestId: value(formData, "request_id"), action: "decline" }); }
  catch { redirect("/prestador/solicitudes?error=request"); }
  refresh(); redirect("/prestador/solicitudes?status=declined");
}

export async function quoteProviderRequest(formData: FormData) {
  try {
    await createProviderQuote({ ...await providerSession(), requestId: value(formData, "request_id"), body: { amount: Number(value(formData, "amount")), currency: "ARS", description: value(formData, "description"), valid_until: argentinaDateTime(value(formData, "valid_until")) } });
  } catch { redirect("/prestador/solicitudes?error=quote"); }
  refresh(); redirect("/prestador/solicitudes?status=quoted");
}

export async function acceptDirectRequest(formData: FormData) {
  try {
    await providerEngagementRequestAction({ ...await providerSession(), requestId: value(formData, "request_id"), action: "accept", body: { starts_at: argentinaDateTime(value(formData, "starts_at")), ends_at: argentinaDateTime(value(formData, "ends_at")) } });
  } catch { redirect("/prestador/solicitudes?error=booking"); }
  refresh(); redirect("/prestador/contrataciones?status=booked");
}

export async function updateProviderBooking(formData: FormData) {
  const raw = value(formData, "action");
  const action = raw === "confirm" || raw === "start" || raw === "complete" || raw === "no-show" ? raw : "cancel";
  try { await providerBookingAction({ ...await providerSession(), bookingId: value(formData, "booking_id"), action }); }
  catch { redirect("/prestador/contrataciones?error=booking"); }
  refresh(); redirect(`/prestador/contrataciones?status=${action}`);
}
