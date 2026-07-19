import type { MetadataRoute } from "next";

import { getPublicCatalog } from "@/lib/public-catalog";

const publicOrigin = process.env.APP_URL ?? "https://sic.thecottonclub.com.ar";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const catalog = await getPublicCatalog();
  const entries: MetadataRoute.Sitemap = ["", "/servicios"].map((path) => ({ url: `${publicOrigin}${path}`, changeFrequency: "weekly", priority: path ? 0.9 : 1 }));
  for (const category of catalog.categories) {
    entries.push({ url: `${publicOrigin}/categoria/${category.slug}`, changeFrequency: "weekly", priority: 0.8 });
    for (const subcategory of category.subcategories) {
      entries.push({ url: `${publicOrigin}/categoria/${category.slug}/${subcategory.slug}`, changeFrequency: "weekly", priority: 0.7 });
      for (const service of subcategory.services) entries.push({ url: `${publicOrigin}/servicio/${service.slug}`, changeFrequency: "weekly", priority: 0.6 });
    }
  }
  return entries;
}
