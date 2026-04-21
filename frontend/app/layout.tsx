"use client";
import React from "react";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import "./globals.css";
import TopNav from "@/components/TopNav";
import SideNav from "@/components/SideNav";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ margin: 0, padding: 0, height: "100%" }}>
      <head>
        <title>Guardrails Proxy</title>
        <meta name="description" content="NeMo Guardrails Proxy for Cloudera AI Inference" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body style={{ margin: 0, padding: 0, height: "100vh", overflow: "hidden" }}>
        <AntdRegistry>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              height: "100vh",
              width: "100vw",
              overflow: "hidden",
              position: "fixed",
              top: 0,
              left: 0,
            }}
          >
            <TopNav />
            <div style={{ display: "flex", flex: 1, overflow: "hidden", minHeight: 0 }}>
              <SideNav />
              <main
                style={{
                  flex: 1,
                  overflow: "auto",
                  padding: "20px 24px",
                  background: "hsl(0 0% 98%)",
                  minWidth: 0,
                }}
              >
                {children}
              </main>
            </div>
          </div>
        </AntdRegistry>
      </body>
    </html>
  );
}
