"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { createAdminCatalogItem, updateAdminCatalogItem } from "@/lib/internal-api";

type CatalogKind = "categories" | "subcategories" | "services";

function slugify(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function text(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
}

async function adminSession() {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("ADMIN")) throw new Error("Administrator role required");
  return session;
}

export async function createCatalogItem(formData: FormData) {
  const kind = text(formData, "kind") as CatalogKind;
  if (!["categories", "subcategories", "services"].includes(kind)) redirect("/admin/catalogo?error=invalid-kind");
  let succeeded = false;
  try {
    const session = await adminSession();
    const name = text(formData, "name");
    const common = {
      code: text(formData, "code").toUpperCase().replace(/[^A-Z0-9]+/g, "_"),
      name,
      slug: text(formData, "slug") || slugify(name),
      description: text(formData, "description") || null,
      icon_key: text(formData, "icon_key"),
      is_active: true,
    };
    const body = kind === "categories"
      ? { ...common, position: Number(text(formData, "position") || 0) }
      : kind === "subcategories"
        ? { ...common, category_id: text(formData, "category_id"), position: Number(text(formData, "position") || 0) }
        : { ...common, subcategory_id: text(formData, "subcategory_id"), allows_fixed_price: formData.get("allows_fixed_price") === "on", allows_quote: formData.get("allows_quote") === "on", allows_urgent: formData.get("allows_urgent") === "on" };
    await createAdminCatalogItem({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, kind, body });
    succeeded = true;
  } catch {
    succeeded = false;
  }
  if (succeeded) {
    revalidatePath("/admin/catalogo");
    redirect("/admin/catalogo?status=created");
  }
  redirect("/admin/catalogo?error=create-failed");
}

export async function toggleCatalogItem(formData: FormData) {
  const kind = text(formData, "kind") as CatalogKind;
  const id = text(formData, "id");
  if (!["categories", "subcategories", "services"].includes(kind) || !id) redirect("/admin/catalogo?error=invalid-item");
  let succeeded = false;
  try {
    const session = await adminSession();
    await updateAdminCatalogItem({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId, kind, id, body: { is_active: text(formData, "next_active") === "true" } });
    succeeded = true;
  } catch {
    succeeded = false;
  }
  if (succeeded) {
    revalidatePath("/admin/catalogo");
    redirect("/admin/catalogo?status=updated");
  }
  redirect("/admin/catalogo?error=update-failed");
}
