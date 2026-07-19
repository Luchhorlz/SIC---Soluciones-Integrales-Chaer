"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { reviewAdminDocument, saveAdminDocumentRequirement } from "@/lib/internal-api";

function value(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
}

async function reviewerSession(requireAdmin = false) {
  const session = await auth();
  const roles = session?.user?.roles ?? [];
  const allowed = roles.includes("ADMIN") || (!requireAdmin && roles.includes("DOCUMENT_REVIEWER"));
  if (!session?.user?.id || !session.internalSessionId || !allowed) throw new Error("Document review role required");
  return { userId: session.user.id, roles, sessionId: session.internalSessionId };
}

export async function saveRequirement(formData: FormData) {
  try {
    const session = await reviewerSession(true);
    await saveAdminDocumentRequirement({
      ...session,
      body: {
        service_id: value(formData, "service_id"),
        document_type: value(formData, "document_type").toUpperCase(),
        label: value(formData, "label"),
        is_required: formData.get("is_required") === "on",
        jurisdiction_type: value(formData, "jurisdiction_type").toUpperCase() || "NONE",
        requires_expiration: formData.get("requires_expiration") === "on",
        instructions: value(formData, "instructions") || null,
      },
    });
    revalidatePath("/admin/documentos");
  } catch {
    redirect("/admin/documentos?error=requirement");
  }
  redirect("/admin/documentos?status=requirement");
}

export async function applyReviewAction(formData: FormData) {
  const action = value(formData, "action");
  if (!["review", "approve", "observe", "reject", "suspend", "rescan"].includes(action)) redirect("/admin/documentos?error=action");
  try {
    const session = await reviewerSession();
    await reviewAdminDocument({
      ...session,
      documentId: value(formData, "document_id"),
      action: action as "review" | "approve" | "observe" | "reject" | "suspend" | "rescan",
      body: { reason: value(formData, "reason") || null, internal_notes: value(formData, "internal_notes") || null },
    });
    revalidatePath("/admin/documentos");
    revalidatePath("/prestador/documentacion");
    revalidatePath("/prestador/servicios");
  } catch {
    redirect("/admin/documentos?error=action");
  }
  redirect("/admin/documentos?status=review");
}
