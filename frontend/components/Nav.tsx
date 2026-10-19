"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDataset, withDataset } from "@/lib/useDataset";

const LINKS = [
  { href: "/upload", label: "Upload" },
  { href: "/overview", label: "Overview" },
  { href: "/equipment", label: "Equipment" },
  { href: "/timeline", label: "Timeline" },
];

export default function Nav() {
  const pathname = usePathname();
  const [datasetId] = useDataset();

  return (
    <header className="border-b border-border bg-panel/60 sticky top-0 z-10 backdrop-blur">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold tracking-tight text-white">
            AEGIS
          </span>
          <span className="text-xs text-slate-400 hidden sm:inline">
            Intelligent Energy &amp; Equipment Monitoring
          </span>
        </div>
        <nav className="flex items-center gap-1">
          {LINKS.map((link) => {
            const active = pathname?.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={withDataset(link.href, datasetId)}
                className={`px-3 py-1.5 rounded-md text-sm transition ${
                  active
                    ? "bg-accent/20 text-accent"
                    : "text-slate-300 hover:bg-white/5"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="text-xs text-slate-500 hidden md:block">
          {datasetId ? (
            <span>
              dataset: <span className="text-slate-300">{datasetId}</span>
            </span>
          ) : (
            <span>no dataset selected</span>
          )}
        </div>
      </div>
    </header>
  );
}
