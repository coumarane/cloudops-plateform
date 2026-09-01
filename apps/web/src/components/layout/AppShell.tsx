"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-canvas">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      {mobileNavOpen ? (
        <div className="md:hidden">
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/40"
            aria-label="Close navigation"
            onClick={() => setMobileNavOpen(false)}
          />
          <Sidebar onNavigate={() => setMobileNavOpen(false)} />
        </div>
      ) : null}
      <div className="flex min-h-screen min-w-0 flex-col md:ml-60">
        <div className="flex items-center gap-3 bg-sidebar px-4 py-3 text-white md:hidden">
          <button
            type="button"
            className="rounded border border-slate-600 p-1"
            aria-label="Open navigation"
            onClick={() => setMobileNavOpen(true)}
          >
            {mobileNavOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
          <p className="text-sm font-semibold">CloudOps Platform</p>
        </div>
        {children}
      </div>
    </div>
  );
}
