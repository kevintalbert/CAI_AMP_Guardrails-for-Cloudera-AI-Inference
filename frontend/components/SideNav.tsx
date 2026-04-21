"use client";
import React from "react";
import { Menu } from "antd";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Server,
  Shield,
  MessageSquare,
} from "lucide-react";

const NAV_ITEMS = [
  { key: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
  { key: "/endpoints", label: "Endpoints", icon: <Server size={16} /> },
  { key: "/guardrails", label: "Guardrails", icon: <Shield size={16} /> },
  { key: "/test", label: "Test Console", icon: <MessageSquare size={16} /> },
];

export default function SideNav() {
  const router = useRouter();
  const pathname = usePathname();

  const selectedKey = NAV_ITEMS.find((item) =>
    pathname.startsWith(item.key)
  )?.key ?? "/dashboard";

  return (
    <aside
      style={{
        width: 220,
        background: "#1a1f2e",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      <Menu
        mode="inline"
        theme="dark"
        selectedKeys={[selectedKey]}
        style={{ background: "transparent", border: "none", marginTop: 8 }}
        items={NAV_ITEMS.map((item) => ({
          key: item.key,
          icon: item.icon,
          label: item.label,
          onClick: () => router.push(item.key),
          style: {
            color: selectedKey === item.key ? "#fff" : "rgba(255,255,255,0.65)",
            borderRadius: 6,
            margin: "2px 8px",
            width: "calc(100% - 16px)",
          },
        }))}
      />
    </aside>
  );
}
