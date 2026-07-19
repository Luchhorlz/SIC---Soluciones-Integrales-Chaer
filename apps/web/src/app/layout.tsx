import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";

const manrope = Manrope({ variable: "--font-manrope", subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.APP_URL ?? "https://sic.thecottonclub.com.ar"),
  title: { default: "SIC — Soluciones Integrales Chaer", template: "%s — Soluciones Integrales Chaer" },
  description: "Encontrá prestadores visibles para servicios presenciales y remotos.",
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "es_AR", siteName: "SIC — Soluciones Integrales Chaer", title: "SIC — Soluciones Integrales Chaer", description: "Servicios presenciales y remotos con visibilidad verificada." },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es-AR" className={manrope.variable}><body>{children}</body></html>;
}
