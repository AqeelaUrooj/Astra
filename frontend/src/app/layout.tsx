import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASTRA | Mission Health",
  description: "Explainable synthetic crew-health trends and offline telemetry resilience prototype for NASA Space Apps Challenge 2026.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
