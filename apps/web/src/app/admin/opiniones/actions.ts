"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { moderateAdminReview } from "@/lib/internal-api";

function value(formData: FormData, key: string) { return String(formData.get(key) ?? "").trim(); }

export async function moderateReview(formData: FormData) {
  const action = value(formData, "action");
  if (!(["publish", "reject", "hide"] as string[]).includes(action)) redirect("/admin/opiniones?error=action");
  try {
    const session = await auth();
    if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("ADMIN")) throw new Error("Admin role required");
    await moderateAdminReview({
      userId: session.user.id,
      roles: session.user.roles,
      sessionId: session.internalSessionId,
      reviewId: value(formData, "review_id"),
      action: action as "publish" | "reject" | "hide",
      reason: value(formData, "reason") || undefined,
    });
    revalidatePath("/admin/opiniones");
    revalidatePath("/prestador/opiniones");
    revalidatePath("/cuenta/contrataciones");
  } catch {
    redirect("/admin/opiniones?error=moderation");
  }
  redirect("/admin/opiniones?status=moderated");
}
