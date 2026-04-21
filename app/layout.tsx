import type { ReactNode } from "react";

export const metadata = {
  title: "stuff — parametric models",
  description: "Live parametric OpenSCAD preview",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, -apple-system, sans-serif",
          background: "#0e1116",
          color: "#e6edf3",
        }}
      >
        {children}
      </body>
    </html>
  );
}
