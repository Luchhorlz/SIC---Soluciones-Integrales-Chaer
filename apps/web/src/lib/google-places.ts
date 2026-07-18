import "server-only";

const placesBaseUrl = "https://places.googleapis.com/v1";
const autocompleteFieldMask = [
  "suggestions.placePrediction.placeId",
  "suggestions.placePrediction.text.text",
  "suggestions.placePrediction.structuredFormat.mainText.text",
  "suggestions.placePrediction.structuredFormat.secondaryText.text",
].join(",");
const detailsFieldMask = "id,formattedAddress,addressComponents,location";

export type PlaceSuggestion = {
  placeId: string;
  text: string;
  mainText: string;
  secondaryText: string;
};

export type NormalizedGoogleAddress = {
  google_place_id: string;
  formatted_address: string;
  street: string;
  street_number: string;
  city: string;
  administrative_area: string | null;
  province: string;
  postal_code: string | null;
  country_code: string;
  latitude: number;
  longitude: number;
};

type GoogleText = { text?: string };
type GooglePrediction = {
  placeId?: string;
  text?: GoogleText;
  structuredFormat?: { mainText?: GoogleText; secondaryText?: GoogleText };
};
type GoogleAddressComponent = { longText?: string; shortText?: string; types?: string[] };
type GooglePlace = {
  id?: string;
  formattedAddress?: string;
  addressComponents?: GoogleAddressComponent[];
  location?: { latitude?: number; longitude?: number };
};

export class GooglePlacesError extends Error {
  constructor(public readonly publicMessage: string, public readonly statusCode = 502) {
    super(publicMessage);
  }
}

function apiKey(): string {
  const value = process.env.GOOGLE_MAPS_API_KEY?.trim();
  if (!value) throw new GooglePlacesError("Google Places todavía no está configurado.", 503);
  return value;
}

function countryCode(): string {
  const value = (process.env.GOOGLE_MAPS_COUNTRY_RESTRICTION ?? "AR").trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(value)) throw new GooglePlacesError("La restricción geográfica no es válida.", 503);
  return value;
}

function validSessionToken(value: string): boolean {
  return /^[A-Za-z0-9_-]{16,128}$/.test(value);
}

async function googleFetch(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, { ...init, cache: "no-store", signal: AbortSignal.timeout(5000) });
  } catch {
    throw new GooglePlacesError("Google Places no respondió a tiempo. Intentá nuevamente.", 504);
  }
}

export async function autocompleteAddresses(input: string, sessionToken: string): Promise<PlaceSuggestion[]> {
  const query = input.trim();
  if (query.length < 3 || query.length > 200) throw new GooglePlacesError("Ingresá al menos tres caracteres.", 400);
  if (!validSessionToken(sessionToken)) throw new GooglePlacesError("La sesión de búsqueda no es válida.", 400);
  const country = countryCode();
  const response = await googleFetch(`${placesBaseUrl}/places:autocomplete`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-goog-api-key": apiKey(),
      "x-goog-fieldmask": autocompleteFieldMask,
    },
    body: JSON.stringify({ input: query, includedRegionCodes: [country.toLowerCase()], languageCode: "es-AR", regionCode: country.toLowerCase(), sessionToken }),
  });
  if (!response.ok) throw new GooglePlacesError("No pudimos buscar direcciones en este momento.", response.status === 429 ? 429 : 502);
  const payload = await response.json() as { suggestions?: Array<{ placePrediction?: GooglePrediction }> };
  return (payload.suggestions ?? []).flatMap(({ placePrediction }) => {
    const placeId = placePrediction?.placeId?.trim();
    const text = placePrediction?.text?.text?.trim();
    if (!placeId || !text) return [];
    return [{
      placeId,
      text,
      mainText: placePrediction?.structuredFormat?.mainText?.text?.trim() || text,
      secondaryText: placePrediction?.structuredFormat?.secondaryText?.text?.trim() || "",
    }];
  }).slice(0, 5);
}

function component(components: GoogleAddressComponent[], type: string, short = false): string {
  const match = components.find((item) => item.types?.includes(type));
  return (short ? match?.shortText : match?.longText)?.trim() ?? "";
}

export async function getAddressDetails(placeId: string, sessionToken: string): Promise<NormalizedGoogleAddress> {
  const normalizedPlaceId = placeId.trim();
  if (!/^[A-Za-z0-9_-]{5,255}$/.test(normalizedPlaceId)) throw new GooglePlacesError("La dirección seleccionada no es válida.", 400);
  if (!validSessionToken(sessionToken)) throw new GooglePlacesError("La sesión de búsqueda no es válida.", 400);
  const url = new URL(`${placesBaseUrl}/places/${encodeURIComponent(normalizedPlaceId)}`);
  url.searchParams.set("sessionToken", sessionToken);
  url.searchParams.set("languageCode", "es-AR");
  url.searchParams.set("regionCode", countryCode().toLowerCase());
  const response = await googleFetch(url.toString(), {
    headers: { "x-goog-api-key": apiKey(), "x-goog-fieldmask": detailsFieldMask },
  });
  if (!response.ok) throw new GooglePlacesError("No pudimos confirmar esa dirección.", response.status === 429 ? 429 : 502);
  const place = await response.json() as GooglePlace;
  const components = place.addressComponents ?? [];
  const country = component(components, "country", true).toUpperCase();
  const street = component(components, "route");
  const streetNumber = component(components, "street_number");
  const city = component(components, "locality") || component(components, "administrative_area_level_2") || component(components, "sublocality");
  const administrativeArea = component(components, "administrative_area_level_2") || null;
  const province = component(components, "administrative_area_level_1");
  const latitude = place.location?.latitude;
  const longitude = place.location?.longitude;
  if (country !== countryCode()) throw new GooglePlacesError("Seleccioná una dirección dentro de Argentina.", 422);
  if (!place.id || !place.formattedAddress || !street || !streetNumber || !city || !province || !Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    throw new GooglePlacesError("Elegí una dirección completa que incluya calle y altura.", 422);
  }
  return {
    google_place_id: place.id,
    formatted_address: place.formattedAddress,
    street,
    street_number: streetNumber,
    city,
    administrative_area: administrativeArea,
    province,
    postal_code: component(components, "postal_code") || null,
    country_code: country,
    latitude: latitude as number,
    longitude: longitude as number,
  };
}
