import type { Metadata, Viewport } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import { Providers } from "./providers";


export const metadata: Metadata = {
  title: "SafeTrail · Tourist Safety Command",
  description: "Smart Tourist Safety Monitoring & AI-Based Incident Intelligence Platform",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
