import type { MetadataRoute } from "next";

const publicOrigin = process.env.APP_URL ?? "https://sic.thecottonclub.com.ar";

export default function robots(): MetadataRoute.Robots {
  return { rules: { userAgent: "*", allow: "/", disallow: ["/admin/", "/cuenta/", "/prestador/panel", "/prestador/perfil", "/prestador/servicios", "/prestador/documentacion", "/prestador/suscripcion", "/onboarding/", "/api/"] }, sitemap: `${publicOrigin}/sitemap.xml`, host: publicOrigin };
}
