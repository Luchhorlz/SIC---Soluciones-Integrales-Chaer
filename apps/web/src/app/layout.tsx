import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";

const manrope = Manrope({ variable: "--font-manrope", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SIC — Soluciones Integrales Chaer",
  description: "Encontrá profesionales verificados para servicios presenciales y remotos.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es-AR" className={manrope.variable}><body>{children}</body></html>;
}
