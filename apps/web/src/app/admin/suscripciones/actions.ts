"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { createAdminSubscriptionPlan, updateAdminSubscriptionPlan } from "@/lib/internal-api";

function value(formData: FormData, key: string) {
  return String(formData.get(key) ?? "").trim();
}

export async function saveSubscriptionPlan(formData: FormData) {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("ADMIN")) throw new Error("Administrator role required");
  const planId = value(formData, "plan_id");
  const features = value(formData, "features").split("\n").map((item) => item.trim()).filter(Boolean);
  const shared = { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
  try {
    if (planId) {
      await updateAdminSubscriptionPlan({ ...shared, planId, body: { name: value(formData, "name"), price: value(formData, "price"), currency: value(formData, "currency").toUpperCase(), is_active: formData.get("is_active") === "on", features } });
    } else {
      await createAdminSubscriptionPlan({ ...shared, body: { name: value(formData, "name"), code: value(formData, "code").toUpperCase(), price: value(formData, "price"), currency: value(formData, "currency").toUpperCase(), billing_frequency: "MONTHLY", is_active: formData.get("is_active") === "on", features } });
    }
    revalidatePath("/admin/suscripciones");
    revalidatePath("/prestador/suscripcion");
  } catch {
    redirect("/admin/suscripciones?error=plan");
  }
  redirect("/admin/suscripciones?status=saved");
}
