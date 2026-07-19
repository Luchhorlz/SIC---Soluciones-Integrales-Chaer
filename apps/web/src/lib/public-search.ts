import "server-only";

import type { ProviderSearchPage, PublicProviderProfile, SearchMode, SearchSort } from "@/lib/public-search-types";
import { isDemoMode } from "@/lib/auth-config";
import { getDemoProvider, searchDemoProviders } from "@/lib/demo-catalog";

export type { SearchMode, SearchSort } from "@/lib/public-search-types";
export { formatOfferPrice, modalityLabel } from "@/lib/public-search-types";

const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8001";

export type SearchInput = {
  q?: string;
  service_slug?: string;
  category_slug?: string;
  subcategory_slug?: string;
  mode?: SearchMode;
  latitude?: number;
  longitude?: number;
  radius_meters?: number;
  available_today?: boolean;
  sort?: SearchSort;
  cursor?: string;
  limit?: number;
};

export async function searchProviders(input: SearchInput): Promise<ProviderSearchPage & { apiUnavailable: boolean; demoData: boolean }> {
  const parameters = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && value !== "") parameters.set(key, String(value));
  }
  try {
    const response = await fetch(`${apiUrl}/v1/search/providers?${parameters}`, { cache: "no-store", signal: AbortSignal.timeout(3500) });
    if (!response.ok) throw new Error("search unavailable");
    const page = (await response.json()) as ProviderSearchPage;
    if (isDemoMode() && page.results.length === 0) return { ...searchDemoProviders(input), apiUnavailable: false, demoData: true };
    return { ...page, apiUnavailable: false, demoData: page.results.some((item) => item.is_demo) };
  } catch {
    if (isDemoMode()) return { ...searchDemoProviders(input), apiUnavailable: false, demoData: true };
    return { results: [], count: 0, next_cursor: null, mode: input.mode ?? "ALL", location_applied: input.latitude !== undefined, apiUnavailable: true, demoData: false };
  }
}

export async function getPublicProvider(slug: string): Promise<{ profile: PublicProviderProfile | null; apiUnavailable: boolean }> {
  try {
    const response = await fetch(`${apiUrl}/v1/providers/${encodeURIComponent(slug)}`, { cache: "no-store", signal: AbortSignal.timeout(3500) });
    if (response.status === 404) return { profile: isDemoMode() ? getDemoProvider(slug) : null, apiUnavailable: false };
    if (!response.ok) throw new Error("provider unavailable");
    return { profile: (await response.json()) as PublicProviderProfile, apiUnavailable: false };
  } catch {
    const demoProfile = isDemoMode() ? getDemoProvider(slug) : null;
    return { profile: demoProfile, apiUnavailable: !demoProfile };
  }
}
