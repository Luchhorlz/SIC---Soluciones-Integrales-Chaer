import Link from "next/link";

import { PublicFooter, PublicHeader } from "@/components/public-header";

export default function NotFound() {
  return <main><PublicHeader /><section className="public-unavailable"><span>404</span><h1>Esta página no está disponible</h1><p>El servicio o prestador no existe, está pausado o no cumple las reglas de visibilidad pública.</p><Link className="secondary" href="/servicios">Explorar servicios</Link></section><PublicFooter /></main>;
}
