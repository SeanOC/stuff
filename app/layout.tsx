import type { ReactNode } from "react";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import { UIProvider } from "@/contexts/UIContext";
import "./globals.css";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata = {
  title: "stuff — parametric models",
  description: "Live parametric OpenSCAD preview",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <UIProvider>
          <AppShell>{children}</AppShell>
          {/* Portal target for <Modal>. Sits as a sibling of AppShell
              so modals aren't constrained by AppShell's stacking
              context or overflow. (st-1j9) */}
          <div id="modal-root" />
        </UIProvider>
      </body>
    </html>
  );
}
