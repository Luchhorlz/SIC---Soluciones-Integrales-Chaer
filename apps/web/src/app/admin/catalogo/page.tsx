import Link from "next/link";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import manifest from "@/data/taxonomy-manifest.json";
import { getAdminCatalog, type CatalogCategory } from "@/lib/internal-api";

import { createCatalogItem, toggleCatalogItem } from "./actions";

export const metadata = { title: "Administrar catálogo | SIC" };

type SearchParams = Promise<{ status?: string; error?: string }>;

export default async function AdminCatalogPage({ searchParams }: { searchParams: SearchParams }) {
  const configured = Boolean(
    process.env.AUTH_GOOGLE_ID
      && process.env.AUTH_GOOGLE_SECRET
      && process.env.AUTH_SECRET
      && process.env.INTERNAL_API_JWT_SECRET,
  );
  const session = configured ? await auth() : null;
  if (configured && !session?.user) redirect("/ingresar");
  if (configured && !session?.user.roles.includes("ADMIN")) redirect("/cuenta");

  const isAdmin = Boolean(session?.user.roles.includes("ADMIN"));
  let catalog: CatalogCategory[] = [];
  let apiUnavailable = false;
  if (isAdmin && session) {
    try {
      catalog = await getAdminCatalog({
        userId: session.user.id,
        roles: session.user.roles,
        sessionId: session.internalSessionId,
      });
    } catch {
      apiUnavailable = true;
    }
  }

  const params = await searchParams;
  const subcategories = catalog.flatMap((category) => category.subcategories);
  const services = subcategories.flatMap((subcategory) => subcategory.services);
  const disabled = !isAdmin || apiUnavailable;

  return (
    <main className="admin-catalog-page">
      <header className="admin-header">
        <Link className="brand" href="/">
          <span className="brand-mark">S<span>Í</span>C</span>
          <span>Soluciones Integrales Chaer</span>
        </Link>
        <div><span>Administración</span><Link href="/admin/documentos">Documentos</Link><Link href="/admin/opiniones">Opiniones</Link><Link href="/cuenta">Volver a mi cuenta</Link></div>
      </header>

      <section className="admin-catalog-content">
        <div className="admin-title">
          <div>
            <p className="eyebrow">FASE 4 · TAXONOMÍA CANÓNICA</p>
            <h1>Catálogo de servicios</h1>
            <p>Administrá la jerarquía sin eliminar elementos que puedan estar en uso.</p>
          </div>
          <span className="admin-lock">▣ Solo ADMIN</span>
        </div>

        {!configured && <div className="preview-notice admin-notice">Vista previa protegida. Las operaciones se habilitan con sesión administrativa y PostgreSQL.</div>}
        {apiUnavailable && <div className="form-error">La API o PostgreSQL no están disponibles. El seed aprobado permanece intacto.</div>}
        {params.status && <div className="form-success">El catálogo se actualizó correctamente.</div>}
        {params.error && <div className="form-error">No pudimos aplicar el cambio. Revisá códigos, slugs y relaciones.</div>}

        <div className="catalog-stats">
          <article><b>{manifest.categories}</b><span>Categorías aprobadas</span><small>{catalog.length} cargadas</small></article>
          <article><b>{manifest.subcategories}</b><span>Subcategorías aprobadas</span><small>{subcategories.length} cargadas</small></article>
          <article><b>{manifest.services.toLocaleString("es-AR")}</b><span>Servicios aprobados</span><small>{services.length.toLocaleString("es-AR")} cargados</small></article>
          <article><b>v{manifest.version}</b><span>Versión del seed</span><small>{manifest.seed_sha256.slice(0, 10)}</small></article>
        </div>

        <section className="catalog-create-grid" aria-label="Crear elementos del catálogo">
          <form action={createCatalogItem} className="catalog-create-card">
            <input type="hidden" name="kind" value="categories" />
            <h2>Nueva categoría</h2>
            <CatalogTextField label="Nombre" name="name" required />
            <CatalogTextField label="Código estable" name="code" placeholder="CAT_EJEMPLO" required />
            <CatalogTextField label="Slug" name="slug" placeholder="Se genera desde el nombre" />
            <CatalogTextField label="Icon key" name="icon_key" placeholder="category-example" required />
            <CatalogTextField label="Posición" name="position" type="number" min="0" defaultValue="0" />
            <label>Descripción<textarea name="description" rows={2}></textarea></label>
            <button className="primary" disabled={disabled}>Crear categoría</button>
          </form>

          <form action={createCatalogItem} className="catalog-create-card">
            <input type="hidden" name="kind" value="subcategories" />
            <h2>Nueva subcategoría</h2>
            <label>Categoría<select name="category_id" required disabled={disabled}><option value="">Seleccionar</option>{catalog.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <CatalogTextField label="Nombre" name="name" required />
            <CatalogTextField label="Código estable" name="code" placeholder="CAT_XX_SUB_XX" required />
            <CatalogTextField label="Slug" name="slug" />
            <CatalogTextField label="Icon key" name="icon_key" required />
            <CatalogTextField label="Posición" name="position" type="number" min="0" defaultValue="0" />
            <label>Descripción<textarea name="description" rows={2}></textarea></label>
            <button className="primary" disabled={disabled}>Crear subcategoría</button>
          </form>

          <form action={createCatalogItem} className="catalog-create-card">
            <input type="hidden" name="kind" value="services" />
            <h2>Nuevo servicio</h2>
            <label>Subcategoría<select name="subcategory_id" required disabled={disabled}><option value="">Seleccionar</option>{subcategories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <CatalogTextField label="Nombre" name="name" required />
            <CatalogTextField label="Código estable" name="code" placeholder="CAT_XX_SUB_XX_SVC_XXX" required />
            <CatalogTextField label="Slug" name="slug" />
            <CatalogTextField label="Icon key" name="icon_key" defaultValue="catalog-service" required />
            <label>Descripción<textarea name="description" rows={2}></textarea></label>
            <div className="catalog-flags">
              <label><input type="checkbox" name="allows_fixed_price" /> Precio fijo</label>
              <label><input type="checkbox" name="allows_quote" defaultChecked /> Presupuesto</label>
              <label><input type="checkbox" name="allows_urgent" /> Urgente</label>
            </div>
            <button className="primary" disabled={disabled}>Crear servicio</button>
          </form>
        </section>

        <section className="catalog-tree">
          <div className="catalog-tree-title"><h2>Jerarquía cargada</h2><span>No existe acción de borrado</span></div>
          {catalog.length
            ? catalog.map((category) => (
              <details key={category.id} className="catalog-category">
                <summary><CatalogIdentity name={category.name} code={category.code} slug={category.slug} /><StatusPill active={category.is_active} /></summary>
                <div className="catalog-level-action"><CatalogToggle kind="categories" id={category.id} active={category.is_active} disabled={disabled} /></div>
                <div className="catalog-subcategories">
                  {category.subcategories.map((subcategory) => (
                    <details key={subcategory.id}>
                      <summary><CatalogIdentity name={subcategory.name} code={subcategory.code} detail={`${subcategory.services.length} servicios`} /><StatusPill active={subcategory.is_active} /></summary>
                      <div className="catalog-level-action"><CatalogToggle kind="subcategories" id={subcategory.id} active={subcategory.is_active} disabled={disabled} /></div>
                      <div className="catalog-services">
                        {subcategory.services.map((service) => (
                          <article key={service.id}>
                            <CatalogIdentity name={service.name} code={service.code} slug={service.slug} />
                            <span className="service-modes">{service.allows_fixed_price && "Fijo "}{service.allows_quote && "Presupuesto "}{service.allows_urgent && "Urgente"}</span>
                            <CatalogToggle kind="services" id={service.id} active={service.is_active} disabled={disabled} />
                          </article>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              </details>
            ))
            : (
              <div className="catalog-empty">
                <span>▤</span>
                <h3>El seed está listo para PostgreSQL</h3>
                <p>La lista aprobada contiene {manifest.categories} categorías, {manifest.subcategories} subcategorías y {manifest.services.toLocaleString("es-AR")} servicios. No se muestran datos inventados.</p>
                <code>python -m sic_api.modules.catalog.seed --file ../../seeds/taxonomy.json</code>
              </div>
            )}
        </section>
      </section>
    </main>
  );
}

type TextFieldProps = {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  defaultValue?: string;
  min?: string;
  required?: boolean;
};

function CatalogTextField({ label, ...input }: TextFieldProps) {
  return <label>{label}<input {...input} /></label>;
}

function CatalogIdentity({ name, code, slug, detail }: { name: string; code: string; slug?: string; detail?: string }) {
  return <span><b>{name}</b><small>{code}{slug ? ` · /${slug}` : ""}{detail ? ` · ${detail}` : ""}</small></span>;
}

function StatusPill({ active }: { active: boolean }) {
  return <span className={active ? "catalog-active" : "catalog-inactive"}>{active ? "Activo" : "Inactivo"}</span>;
}

function CatalogToggle({ kind, id, active, disabled }: { kind: "categories" | "subcategories" | "services"; id: string; active: boolean; disabled: boolean }) {
  return (
    <form action={toggleCatalogItem}>
      <input type="hidden" name="kind" value={kind} />
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="next_active" value={String(!active)} />
      <button type="submit" className={active ? "catalog-inactive" : "catalog-active"} disabled={disabled}>{active ? "Desactivar" : "Activar"}</button>
    </form>
  );
}
