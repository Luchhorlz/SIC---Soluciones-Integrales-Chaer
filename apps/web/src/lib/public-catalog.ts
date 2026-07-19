import "server-only";

import fallbackCatalog from "@/data/taxonomy.json";

export type PublicService = {
  name: string;
  slug: string;
  description: string | null;
  allows_fixed_price: boolean;
  allows_quote: boolean;
  allows_urgent: boolean;
};

export type PublicSubcategory = {
  name: string;
  slug: string;
  description: string | null;
  position: number;
  services: PublicService[];
};

export type PublicCategory = {
  name: string;
  slug: string;
  description: string | null;
  icon_key: string;
  position: number;
  subcategories: PublicSubcategory[];
};

export type PublicCatalog = { version: number; categories: PublicCategory[] };

const apiUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8001";
const fallback = fallbackCatalog as unknown as PublicCatalog;

export async function getPublicCatalog(): Promise<PublicCatalog> {
  try {
    const response = await fetch(`${apiUrl}/v1/catalog/categories`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) return fallback;
    const categories = (await response.json()) as PublicCategory[];
    return { version: fallback.version, categories };
  } catch {
    return fallback;
  }
}

export function findCategory(catalog: PublicCatalog, slug: string) {
  return catalog.categories.find((item) => item.slug === slug);
}

export function findSubcategory(catalog: PublicCatalog, categorySlug: string, subcategorySlug: string) {
  return findCategory(catalog, categorySlug)?.subcategories.find((item) => item.slug === subcategorySlug);
}

export function findService(catalog: PublicCatalog, slug: string) {
  for (const category of catalog.categories) {
    for (const subcategory of category.subcategories) {
      const service = subcategory.services.find((item) => item.slug === slug);
      if (service) return { category, subcategory, service };
    }
  }
  return null;
}

function normalizedTerms(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z0-9]+/).filter((term) => term.length >= 2);
}

export function searchCatalog(catalog: PublicCatalog, query: string, limit = 24) {
  const terms = normalizedTerms(query);
  if (!terms.length) return [];
  const matches: Array<{ category: PublicCategory; subcategory: PublicSubcategory; service: PublicService; score: number }> = [];
  for (const category of catalog.categories) {
    for (const subcategory of category.subcategories) {
      for (const service of subcategory.services) {
        const serviceText = normalizedTerms(`${service.name} ${service.slug}`).join(" ");
        const subcategoryText = normalizedTerms(`${subcategory.name} ${subcategory.slug}`).join(" ");
        const categoryText = normalizedTerms(`${category.name} ${category.slug}`).join(" ");
        if (!terms.every((term) => serviceText.includes(term) || subcategoryText.includes(term) || categoryText.includes(term))) continue;
        const score = terms.reduce((total, term) => total + (serviceText.includes(term) ? 0 : subcategoryText.includes(term) ? 1 : 2), 0);
        matches.push({ category, subcategory, service, score });
      }
    }
  }
  return matches.sort((a, b) => a.score - b.score || a.service.name.localeCompare(b.service.name, "es")).slice(0, limit);
}
