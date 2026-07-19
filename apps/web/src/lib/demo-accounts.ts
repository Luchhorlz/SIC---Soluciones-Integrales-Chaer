import "server-only";

import { timingSafeEqual } from "node:crypto";

import { isDemoMode } from "@/lib/auth-config";

export type DemoAccount = {
  username: "admin" | "cliente" | "servicio";
  password: string;
  id: string;
  name: string;
  email: string;
  roles: string[];
  redirectTo: string;
  description: string;
};

export const demoAccounts: readonly DemoAccount[] = [
  { username: "admin", password: "admin", id: "10000000-0000-4000-8000-000000000001", name: "Administración Demo", email: "admin@demo.sic.invalid", roles: ["ADMIN"], redirectTo: "/admin/catalogo", description: "Catálogo, documentos y moderación" },
  { username: "cliente", password: "cliente", id: "10000000-0000-4000-8000-000000000002", name: "Cliente Demo", email: "cliente@demo.sic.invalid", roles: ["CLIENT"], redirectTo: "/cuenta", description: "Búsqueda, favoritos y contrataciones" },
  { username: "servicio", password: "servicio", id: "10000000-0000-4000-8000-000000000003", name: "Prestador Demo", email: "servicio@demo.sic.invalid", roles: ["PROVIDER"], redirectTo: "/prestador/panel", description: "Perfil, servicios y solicitudes" },
] as const;

function equal(left: string, right: string) {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
}

export function authenticateDemoAccount(username: unknown, password: unknown) {
  if (!isDemoMode() || typeof username !== "string" || typeof password !== "string") return null;
  return demoAccounts.find((account) => equal(account.username, username.trim().toLowerCase()) && equal(account.password, password)) ?? null;
}

export function demoAccountById(id: string) {
  return demoAccounts.find((account) => account.id === id) ?? null;
}
