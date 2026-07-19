import "server-only";

export function isDemoMode() {
  return process.env.DEMO_MODE?.trim().toLowerCase() === "true" && process.env.APP_ENV?.trim().toLowerCase() !== "production";
}

export function isGoogleAuthConfigured() {
  return Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET);
}

export function isApplicationAuthConfigured() {
  return Boolean(process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET && (isDemoMode() || isGoogleAuthConfigured()));
}
