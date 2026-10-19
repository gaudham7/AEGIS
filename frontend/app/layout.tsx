import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import { ToastProvider } from "@/components/Toast";

export const metadata: Metadata = {
  title: "AEGIS — Intelligent Energy & Equipment Monitoring",
  description:
    "Contextual anomaly detection and investigation for chiller equipment.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-slate-200">
        <ToastProvider>
          <Nav />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        </ToastProvider>
      </body>
    </html>
  );
}
