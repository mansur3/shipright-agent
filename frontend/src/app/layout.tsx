import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import Shell from "@/components/Shell";

export const metadata: Metadata = {
  title: "Sankalp AI — Pfizer Channel Intelligence",
  description:
    "Pharma channel intelligence platform: claim anomaly detection, at-risk stock, fill rate, quarter-spike analysis and money-recovery benchmarking.",
};

export const viewport: Viewport = {
  themeColor: "#0a0d14",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-canvas text-ink antialiased font-sans">
        <AuthProvider>
          <Shell>{children}</Shell>
        </AuthProvider>
      </body>
    </html>
  );
}
