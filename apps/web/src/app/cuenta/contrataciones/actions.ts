"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { clientBookingAction, clientRequestAction, decideClientQuote, submitClientReview, updateClientReview } from "@/lib/internal-api";

function value(formData: FormData, key: string) { return String(formData.get(key) ?? "").trim(); }
function argentinaDateTime(raw: string) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(raw)) throw new Error("Invalid date");
  return new Date(`${raw}:00-03:00`).toISOString();
}
async function clientSession() {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("CLIENT")) throw new Error("Client role required");
  return { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
}
function done(status: string) { revalidatePath("/cuenta/contrataciones"); redirect(`/cuenta/contrataciones?status=${status}`); }

export async function cancelServiceRequest(formData: FormData) {
  try { await clientRequestAction({ ...await clientSession(), requestId: value(formData, "request_id"), action: "cancel" }); }
  catch { redirect("/cuenta/contrataciones?error=request"); }
  done("request-cancelled");
}

export async function decideQuote(formData: FormData) {
  const action = value(formData, "decision") === "accept" ? "accept" : "reject";
  try {
    const starts = value(formData, "starts_at"); const ends = value(formData, "ends_at");
    await decideClientQuote({ ...await clientSession(), requestId: value(formData, "request_id"), quoteId: value(formData, "quote_id"), action, schedule: action === "accept" && starts && ends ? { starts_at: argentinaDateTime(starts), ends_at: argentinaDateTime(ends) } : undefined });
  } catch { redirect("/cuenta/contrataciones?error=quote"); }
  done(action === "accept" ? "booked" : "quote-rejected");
}

export async function updateClientBooking(formData: FormData) {
  const actionValue = value(formData, "action");
  const action = actionValue === "confirm" || actionValue === "dispute" ? actionValue : "cancel";
  try { await clientBookingAction({ ...await clientSession(), bookingId: value(formData, "booking_id"), action, reason: value(formData, "reason") || undefined }); }
  catch { redirect("/cuenta/contrataciones?error=booking"); }
  done(`booking-${action}`);
}

export async function saveReview(formData: FormData) {
  const rating = Number(value(formData, "rating"));
  const comment = value(formData, "comment");
  if (!Number.isInteger(rating) || rating < 1 || rating > 5 || comment.length < 10 || comment.length > 2000) redirect("/cuenta/contrataciones?error=review");
  try {
    const session = await clientSession();
    const reviewId = value(formData, "review_id");
    if (reviewId) await updateClientReview({ ...session, reviewId, rating, comment });
    else await submitClientReview({ ...session, bookingId: value(formData, "booking_id"), rating, comment });
  } catch {
    redirect("/cuenta/contrataciones?error=review");
  }
  done("review-saved");
}
