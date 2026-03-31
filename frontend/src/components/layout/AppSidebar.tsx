"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Bot, FileSearch, Scale } from "lucide-react";

const NAV_ITEMS = [
  { href: "/review", label: "智能合规审查", icon: Scale },
  { href: "/regulations", label: "法规动态库", icon: FileSearch },
  { href: "/chat", label: "法律 AI 助手", icon: Bot },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();

  return (
    <aside className="w-72 shrink-0 border-r border-slate-800 bg-slate-950 text-slate-100">
      <div className="flex h-16 items-center border-b border-slate-800 px-5">
        <div className="text-sm font-semibold tracking-wide text-slate-200">
          Legal AI Console
        </div>
      </div>
      <nav className="space-y-1 p-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={query ? `${item.href}?${query}` : item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-blue-600/20 text-blue-200 ring-1 ring-blue-400/40"
                  : "text-slate-300 hover:bg-slate-900 hover:text-white"
              }`}
            >
              <Icon className="size-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

