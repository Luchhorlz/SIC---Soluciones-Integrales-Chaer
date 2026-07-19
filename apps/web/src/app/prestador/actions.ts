"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import {
  addProviderPortfolioItem,
  addProviderAvailabilityException,
  createProviderOffer,
  deleteProviderPortfolioItem,
  deleteProviderAvailabilityException,
  onboardProvider,
  pauseProviderOffer,
  pauseProviderProfile,
  replaceProviderAvailability,
  updateProviderProfile,
} from "@/lib/internal-api";

const modalities = ["AT_CLIENT_ADDRESS", "REMOTE", "HYBRID", "AT_PROVIDER_LOCATION", "PICKUP_DELIVERY"] as const;
const pricingTypes = ["FIXED", "FROM", "QUOTE", "HOURLY", "PER_SESSION", "PER_UNIT"] as const;
const coverageModalities = new Set<string>(["AT_CLIENT_ADDRESS", "HYBRID", "PICKUP_DELIVERY"]);

function value(formData: FormData, key: string): string {
  return String(formData.get(key) ?? "").trim();
}

function optionalNumber(formData: FormData, key: string): number | null {
  const raw = value(formData, key);
  return raw ? Number(raw) : null;
}

async function providerSession() {
  const session = await auth();
  if (!session?.user?.id || !session.internalSessionId || !session.user.roles.includes("PROVIDER")) throw new Error("Provider role required");
  return { userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId };
}

function refreshProviderPages() {
  revalidatePath("/onboarding/prestador");
  revalidatePath("/prestador/panel");
  revalidatePath("/prestador/perfil");
  revalidatePath("/prestador/servicios");
}

export async function saveProviderProfile(formData: FormData) {
  const mode = value(formData, "mode");
  try {
    const session = await providerSession();
    const body = {
      display_name: value(formData, "display_name"),
      business_name: value(formData, "business_name") || null,
      bio: value(formData, "bio") || null,
      experience_years: optionalNumber(formData, "experience_years"),
      base_address_id: value(formData, "base_address_id") || null,
    };
    if (mode === "update") await updateProviderProfile({ ...session, body });
    else await onboardProvider({ ...session, body });
    refreshProviderPages();
  } catch {
    redirect(`${mode === "update" ? "/prestador/perfil" : "/onboarding/prestador"}?error=profile`);
  }
  redirect(mode === "update" ? "/prestador/perfil?status=saved" : "/prestador/panel?status=created");
}

export async function toggleProviderProfile(formData: FormData) {
  try {
    const session = await providerSession();
    await pauseProviderProfile({ ...session, paused: value(formData, "paused") === "true" });
    refreshProviderPages();
  } catch {
    redirect("/prestador/panel?error=pause");
  }
  redirect("/prestador/panel?status=updated");
}

export async function createPortfolioItem(formData: FormData) {
  try {
    const session = await providerSession();
    await addProviderPortfolioItem({ ...session, body: { title: value(formData, "title"), description: value(formData, "description"), position: 0 } });
    refreshProviderPages();
  } catch {
    redirect("/prestador/perfil?error=portfolio");
  }
  redirect("/prestador/perfil?status=portfolio");
}

export async function removePortfolioItem(formData: FormData) {
  try {
    const session = await providerSession();
    await deleteProviderPortfolioItem({ ...session, itemId: value(formData, "item_id") });
    refreshProviderPages();
  } catch {
    redirect("/prestador/perfil?error=portfolio");
  }
  redirect("/prestador/perfil?status=portfolio");
}

export async function createOffer(formData: FormData) {
  try {
    const session = await providerSession();
    const selectedModalities = formData.getAll("modalities").map(String).filter((item): item is typeof modalities[number] => modalities.includes(item as typeof modalities[number]));
    const pricing = value(formData, "pricing_type");
    if (!pricingTypes.includes(pricing as typeof pricingTypes[number])) throw new Error("Invalid pricing type");
    const needsCoverage = selectedModalities.some((item) => coverageModalities.has(item));
    const centerAddress = value(formData, "center_address_id");
    const body = {
      service_id: value(formData, "service_id"),
      headline: value(formData, "headline"),
      description: value(formData, "description"),
      pricing_type: pricing as typeof pricingTypes[number],
      price_amount: pricing === "QUOTE" ? null : optionalNumber(formData, "price_amount"),
      estimated_duration_minutes: optionalNumber(formData, "estimated_duration_minutes"),
      guarantee_days: optionalNumber(formData, "guarantee_days"),
      accepts_urgent: formData.get("accepts_urgent") === "on",
      requires_quote_details: formData.get("requires_quote_details") === "on",
      modalities: selectedModalities,
      area: needsCoverage ? { center_address_id: centerAddress, radius_meters: Number(value(formData, "radius_meters")), urgent_radius_meters: optionalNumber(formData, "urgent_radius_meters"), travel_fee_policy: null } : null,
    };
    await createProviderOffer({ ...session, body });
    refreshProviderPages();
  } catch {
    redirect("/prestador/servicios?error=service");
  }
  redirect("/prestador/servicios?status=created");
}

export async function toggleOffer(formData: FormData) {
  try {
    const session = await providerSession();
    await pauseProviderOffer({ ...session, itemId: value(formData, "item_id"), paused: value(formData, "paused") === "true" });
    refreshProviderPages();
  } catch {
    redirect("/prestador/servicios?error=pause");
  }
  redirect("/prestador/servicios?status=updated");
}

export async function saveAvailability(formData: FormData) {
  try {
    const session = await providerSession();
    const days = formData.getAll("days").map(Number).filter((day) => Number.isInteger(day) && day >= 0 && day <= 6);
    const startTime = value(formData, "start_time");
    const endTime = value(formData, "end_time");
    const slot = Number(value(formData, "slot_duration_minutes") || 60);
    await replaceProviderAvailability({ ...session, itemId: value(formData, "item_id"), body: { rules: days.map((day) => ({ day_of_week: day, start_time: startTime, end_time: endTime, timezone: "America/Argentina/Buenos_Aires", slot_duration_minutes: slot, is_active: true })) } });
    refreshProviderPages();
  } catch {
    redirect("/prestador/servicios?error=availability");
  }
  redirect("/prestador/servicios?status=availability");
}

function argentinaDateTime(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error("Invalid local date time");
  return new Date(`${value}:00-03:00`).toISOString();
}

export async function createAvailabilityException(formData: FormData) {
  try {
    const session = await providerSession();
    await addProviderAvailabilityException({ ...session, body: { starts_at: argentinaDateTime(value(formData, "starts_at")), ends_at: argentinaDateTime(value(formData, "ends_at")), reason: value(formData, "reason") || null, is_available_override: false } });
    refreshProviderPages();
  } catch {
    redirect("/prestador/servicios?error=exception");
  }
  redirect("/prestador/servicios?status=exception");
}

export async function removeAvailabilityException(formData: FormData) {
  try {
    const session = await providerSession();
    await deleteProviderAvailabilityException({ ...session, itemId: value(formData, "item_id") });
    refreshProviderPages();
  } catch {
    redirect("/prestador/servicios?error=exception");
  }
  redirect("/prestador/servicios?status=exception");
}
