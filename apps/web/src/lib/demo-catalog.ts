import "server-only";

import demoConfig from "@/data/demo-data.json";
import taxonomy from "@/data/taxonomy.json";
import type { ProviderResult, ProviderSearchPage, PublicOffer, PublicProviderProfile, SearchMode } from "@/lib/public-search-types";

type CatalogService = {
  code: string;
  name: string;
  slug: string;
  description: string | null;
  category: { code: string; name: string; slug: string };
  subcategory: { name: string; slug: string };
};

type DemoProvider = { result: ProviderResult; profile: PublicProviderProfile; ordinal: number };

function normalized(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function stableUuid(value: string) {
  const parts: string[] = [];
  for (let seed = 0; seed < 4; seed += 1) {
    let hash = 2166136261 ^ seed;
    for (let index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    parts.push((hash >>> 0).toString(16).padStart(8, "0"));
  }
  const hex = parts.join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-4${hex.slice(13, 16)}-8${hex.slice(17, 20)}-${hex.slice(20, 32)}`;
}

function allServices(): CatalogService[] {
  const services: CatalogService[] = [];
  for (const category of taxonomy.categories) {
    for (const subcategory of category.subcategories) {
      for (const service of subcategory.services) {
        services.push({
          code: service.code,
          name: service.name,
          slug: service.slug,
          description: service.description,
          category: { code: category.code, name: category.name, slug: category.slug },
          subcategory: { name: subcategory.name, slug: subcategory.slug },
        });
      }
    }
  }
  return services.sort((left, right) => left.code.localeCompare(right.code));
}

function displayName(ordinal: number) {
  const firstCount = demoConfig.first_names.length;
  const lastCount = demoConfig.last_names.length;
  const first = demoConfig.first_names[ordinal % firstCount];
  const firstLast = demoConfig.last_names[Math.floor(ordinal / firstCount) % lastCount];
  const secondLast = demoConfig.last_names[(Math.floor(ordinal / (firstCount * lastCount)) + 5) % lastCount];
  return `${first} ${firstLast} ${secondLast}`;
}

function modality(categoryCode: string): PublicOffer["modalities"][number] {
  if (demoConfig.remote_category_codes.includes(categoryCode)) return "REMOTE";
  if (demoConfig.provider_location_category_codes.includes(categoryCode)) return "AT_PROVIDER_LOCATION";
  return "AT_CLIENT_ADDRESS";
}

function buildDemoProviders() {
  const providers: DemoProvider[] = [];
  for (const [serviceIndex, service] of allServices().entries()) {
    for (let slotIndex = 0; slotIndex < demoConfig.providers_per_service; slotIndex += 1) {
      const ordinal = serviceIndex * demoConfig.providers_per_service + slotIndex;
      const slot = slotIndex + 1;
      const name = displayName(ordinal);
      const slug = `demo-${service.slug}-${slot}`;
      const location = demoConfig.locations[ordinal % demoConfig.locations.length];
      const serviceModality = modality(service.category.code);
      const offer: PublicOffer = {
        id: stableUuid(`offer:${service.code}:${slot}`),
        service_id: stableUuid(`service:${service.code}`),
        service_name: service.name,
        service_slug: service.slug,
        subcategory_name: service.subcategory.name,
        subcategory_slug: service.subcategory.slug,
        category_name: service.category.name,
        category_slug: service.category.slug,
        headline: `${service.name.replace(/\.$/, "")} con atención personalizada`,
        description: `Oferta demostrativa para explorar cómo se presenta y solicita ${service.name.replace(/\.$/, "").toLowerCase()} dentro de SIC.`,
        pricing_type: "QUOTE",
        price_amount: null,
        price_currency: "ARS",
        estimated_duration_minutes: 60 + ((ordinal % 4) * 30),
        guarantee_days: null,
        accepts_urgent: false,
        modalities: [serviceModality],
        available_today: false,
        distance_meters: null,
        approximate_latitude: Math.round(location.latitude * 100) / 100,
        approximate_longitude: Math.round(location.longitude * 100) / 100,
      };
      const result: ProviderResult = {
        provider_slug: slug,
        display_name: name,
        business_name: `${service.subcategory.name} · Profesional demo`,
        rating_average: 4.6 + ((ordinal % 4) / 10),
        rating_count: 18 + (ordinal % 83),
        completed_services_count: 24 + (ordinal % 190),
        response_rate: 91 + (ordinal % 9),
        average_response_minutes: 8 + (ordinal % 42),
        profile_completeness: 100,
        is_identity_verified: true,
        is_demo: true,
        offer,
      };
      providers.push({
        ordinal,
        result,
        profile: {
          slug,
          display_name: name,
          business_name: result.business_name,
          bio: `Perfil ficticio de SIC para demostrar la búsqueda de ${service.name.replace(/\.$/, "").toLowerCase()}. No representa a una persona ni una matrícula real.`,
          experience_years: 4 + (ordinal % 17),
          rating_average: result.rating_average,
          rating_count: result.rating_count,
          completed_services_count: result.completed_services_count,
          response_rate: result.response_rate,
          average_response_minutes: result.average_response_minutes,
          profile_completeness: 100,
          is_identity_verified: true,
          is_demo: true,
          documents_verified: true,
          portfolio: [],
          services: [offer],
        },
      });
    }
  }
  if (providers.length !== 4176) throw new Error(`Demo catalog invariant failed: ${providers.length}/4176 providers`);
  return providers;
}

let cache: DemoProvider[] | null = null;
function providers() {
  cache ??= buildDemoProviders();
  return cache;
}

function distanceMeters(latitude: number, longitude: number, offer: PublicOffer) {
  if (offer.approximate_latitude === null || offer.approximate_longitude === null) return null;
  const radians = (degrees: number) => degrees * Math.PI / 180;
  const deltaLatitude = radians(offer.approximate_latitude - latitude);
  const deltaLongitude = radians(offer.approximate_longitude - longitude);
  const a = Math.sin(deltaLatitude / 2) ** 2 + Math.cos(radians(latitude)) * Math.cos(radians(offer.approximate_latitude)) * Math.sin(deltaLongitude / 2) ** 2;
  return Math.round((6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))) / 100) * 100;
}

export function searchDemoProviders(input: {
  q?: string; service_slug?: string; category_slug?: string; subcategory_slug?: string; mode?: SearchMode;
  latitude?: number; longitude?: number; radius_meters?: number; available_today?: boolean; sort?: string; cursor?: string; limit?: number;
}): ProviderSearchPage {
  const terms = normalized(input.q ?? "").split(/[^a-z0-9]+/).filter((term) => term.length >= 2);
  const mode = input.mode ?? "ALL";
  let matches = providers().filter(({ result }) => {
    const offer = result.offer;
    if (input.service_slug && offer.service_slug !== input.service_slug) return false;
    if (input.category_slug && offer.category_slug !== input.category_slug) return false;
    if (input.subcategory_slug && offer.subcategory_slug !== input.subcategory_slug) return false;
    if (input.available_today && !offer.available_today) return false;
    if (mode !== "ALL" && !offer.modalities.includes(mode as PublicOffer["modalities"][number])) return false;
    const searchable = normalized(`${offer.service_name} ${offer.subcategory_name} ${offer.category_name} ${result.display_name}`);
    return terms.every((term) => searchable.includes(term));
  }).map(({ result }) => ({ ...result, offer: { ...result.offer } }));

  if (input.latitude !== undefined && input.longitude !== undefined) {
    matches = matches.map((result) => ({ ...result, offer: { ...result.offer, distance_meters: distanceMeters(input.latitude as number, input.longitude as number, result.offer) } }));
    if (input.radius_meters) matches = matches.filter((result) => result.offer.distance_meters !== null && result.offer.distance_meters <= input.radius_meters!);
  }
  if (input.sort === "RATING") matches.sort((left, right) => right.rating_average - left.rating_average || right.rating_count - left.rating_count);
  if (input.sort === "DISTANCE") matches.sort((left, right) => (left.offer.distance_meters ?? Number.MAX_SAFE_INTEGER) - (right.offer.distance_meters ?? Number.MAX_SAFE_INTEGER));
  const count = matches.length;
  const offset = input.cursor?.startsWith("demo:") ? Number(input.cursor.slice(5)) || 0 : 0;
  const limit = Math.min(Math.max(input.limit ?? 20, 1), 50);
  const results = matches.slice(offset, offset + limit);
  return {
    results,
    count,
    next_cursor: offset + limit < count ? `demo:${offset + limit}` : null,
    mode,
    location_applied: input.latitude !== undefined && input.longitude !== undefined,
  };
}

export function getDemoProvider(slug: string) {
  return providers().find((item) => item.result.provider_slug === slug)?.profile ?? null;
}

export function demoDatasetStats() {
  const dataset = providers();
  return { providers: dataset.length, services: new Set(dataset.map((item) => item.result.offer.service_slug)).size, perService: demoConfig.providers_per_service };
}
