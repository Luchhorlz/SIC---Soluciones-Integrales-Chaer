import type { components } from "@/generated/api-schema";

export type SearchMode = components["schemas"]["SearchMode"];
export type SearchSort = components["schemas"]["SearchSort"];
type ApiOffer = components["schemas"]["PublicProviderOffer"];

// Pydantic documents nullable fields with defaults as optional in OpenAPI,
// although FastAPI's response model always serializes them.
export type PublicOffer = Omit<ApiOffer, "distance_meters" | "approximate_latitude" | "approximate_longitude"> & {
  distance_meters: number | null;
  approximate_latitude: number | null;
  approximate_longitude: number | null;
};
export type ProviderResult = Omit<components["schemas"]["ProviderSearchResult"], "offer"> & { offer: PublicOffer };
export type ProviderSearchPage = Omit<components["schemas"]["ProviderSearchPage"], "results"> & { results: ProviderResult[] };
export type PublicProviderProfile = Omit<components["schemas"]["PublicProviderProfile"], "services"> & { services: PublicOffer[] };

export function formatOfferPrice(offer: PublicOffer) {
  if (offer.pricing_type === "QUOTE" || offer.price_amount === null) return "A cotizar";
  const value = Number(offer.price_amount);
  const amount = new Intl.NumberFormat("es-AR", { style: "currency", currency: offer.price_currency, maximumFractionDigits: 0 }).format(value);
  return offer.pricing_type === "FROM" ? `Desde ${amount}` : amount;
}

export function modalityLabel(modality: string) {
  return ({ AT_CLIENT_ADDRESS: "A domicilio", REMOTE: "Remoto", HYBRID: "Híbrido", AT_PROVIDER_LOCATION: "En local del prestador", PICKUP_DELIVERY: "Retiro y entrega" } as Record<string, string>)[modality] ?? modality;
}
