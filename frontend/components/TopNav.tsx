"use client";
import React from "react";
import { ShieldCheck } from "lucide-react";

export default function TopNav() {
  return (
    <header
      style={{
        height: 56,
        minHeight: 56,
        background: "#1a1f2e",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        gap: 10,
        flexShrink: 0,
        zIndex: 100,
        margin: 0,
      }}
    >
      {/* Logo + product name */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 30,
            height: 30,
            background: "linear-gradient(135deg, #FF6D2D, #f7c200)",
            borderRadius: 7,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <ShieldCheck size={17} color="#fff" strokeWidth={2.2} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 1 }}>
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 14, lineHeight: "17px", letterSpacing: "-0.1px" }}>
            Guardrails Proxy
          </span>
          <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 10.5, lineHeight: "13px", fontWeight: 400 }}>
            Powered by NeMo Guardrails
          </span>
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Cloudera AI badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <div
          style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: "#f7c200",
            flexShrink: 0,
          }}
        />
        <span style={{ color: "rgba(255,255,255,0.45)", fontSize: 12, fontWeight: 500, letterSpacing: "0.1px" }}>
          Cloudera AI
        </span>
      </div>
    </header>
  );
}
