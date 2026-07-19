import Link from "next/link";

import { toggleFavorite } from "@/app/favorite-actions";
import { auth } from "@/auth";
import { getClientFavorites, type FavoriteProvider } from "@/lib/internal-api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Prestadores favoritos | SIC" };

function initials(name: string) { return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase(); }

export default async function FavoritesPage({ searchParams }: { searchParams: Promise<{ favorite?: string; error?: string }> }) {
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_GOOGLE_SECRET && process.env.AUTH_SECRET && process.env.INTERNAL_API_JWT_SECRET);
  const session = configured ? await auth() : null; let favorites: FavoriteProvider[] = []; let unavailable = false;
  if (session?.user?.roles.includes("CLIENT")) { try { favorites = await getClientFavorites({ userId: session.user.id, roles: session.user.roles, sessionId: session.internalSessionId }); } catch { unavailable = true; } }
  const query = await searchParams;
  return <><div className="account-top"><div><p className="eyebrow">TU SELECCIÓN</p><h1>Favoritos</h1><p>Guardá prestadores visibles para encontrarlos rápidamente.</p></div><Link className="primary small" href="/buscar">Buscar prestadores</Link></div>{!configured && <div className="preview-notice account-preview">Vista previa: los favoritos reales requieren autenticación y PostgreSQL.</div>}{query.favorite && <div className="form-success account-preview">Tus favoritos se actualizaron correctamente.</div>}{(unavailable || query.error) && <div className="form-error account-preview">No pudimos actualizar tus favoritos.</div>}<section className="favorite-grid">{favorites.length ? favorites.map((item) => <article key={item.id}><div className="favorite-avatar">{initials(item.display_name)}</div><div><small>{item.is_identity_verified ? "✓ Identidad verificada" : "Prestador SIC"}</small><h2><Link href={`/prestador/${item.provider_slug}`}>{item.display_name}</Link></h2>{item.business_name && <p>{item.business_name}</p>}<b>★ {item.rating_average.toFixed(1)} <span>({item.rating_count})</span></b><div><Link className="primary" href={`/prestador/${item.provider_slug}`}>Ver perfil</Link><form action={toggleFavorite}><input type="hidden" name="provider_slug" value={item.provider_slug} /><input type="hidden" name="return_path" value="/cuenta/favoritos" /><button className="secondary" name="favorite" value="false">Quitar</button></form></div></div></article>) : <div className="engagement-empty"><span>♡</span><h3>Todavía no guardaste favoritos</h3><p>En los perfiles públicos podés guardar prestadores que continúen habilitados y visibles.</p><Link className="secondary" href="/buscar">Explorar prestadores</Link></div>}</section></>;
}
