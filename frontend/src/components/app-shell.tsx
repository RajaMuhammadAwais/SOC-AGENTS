import { Activity, Database, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import type { ForwardRefExoticComponent, ReactNode } from "react";
import type { LucideProps } from "lucide-react";

// Navigation is deliberately limited to the routes the console ships today;
// additional console pages (alerts, investigations, reports, settings) are
// on the roadmap and will be added alongside this list.
const navItems: Array<{
  href: "/" | "/data-sources";
  label: string;
  icon: ForwardRefExoticComponent<Omit<LucideProps, "ref">>;
}> = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/data-sources", label: "Data Sources", icon: Database }
];

const navLinkClassName =
  "flex items-center gap-3 rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-slate-900 hover:text-white";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-800 bg-slate-950 lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-5">
          <Activity className="h-5 w-5 text-cyan-300" />
          <div>
            <p className="text-sm text-cyan-300">Enterprise AI SOC</p>
            <p className="text-xs text-slate-500">Operations Console</p>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={navLinkClassName}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-64">{children}</div>
    </div>
  );
}
