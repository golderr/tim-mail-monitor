"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { NavigationItem } from "@/lib/navigation";

export function SidebarNav({ items }: Readonly<{ items: readonly NavigationItem[] }>) {
  const pathname = usePathname();

  return (
    <nav className="sidebar__nav" aria-label="Primary">
      {items.map((item) => {
        const isActive = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar__link${isActive ? " sidebar__link--active" : ""}`}
          >
            <span className="sidebar__link-title">{item.label}</span>
            <span className="sidebar__link-copy">{item.description}</span>
          </Link>
        );
      })}
    </nav>
  );
}
