"use client";
import React, { useEffect, useRef, useState } from "react";
import { Button, Input, Select, Typography, Tag, Spin, Tooltip } from "antd";
import { Send, ShieldCheck, Eye, EyeOff, KeyRound } from "lucide-react";
import { endpointsApi, guardrailsApi } from "@/lib/api";

const { Title, Text } = Typography;
const { TextArea, Password } = Input;

interface Endpoint {
  id: string;
  name: string;
  base_url: string;
  model_id: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  blocked?: boolean;
  error?: string;
}

export default function TestConsolePage() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>("");
  const [bearerToken, setBearerToken] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endpointsApi.list().then((r) => {
      setEndpoints(r.data);
      if (r.data.length > 0) setSelectedEndpoint(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const resp = await guardrailsApi.test(
        userMsg,
        selectedEndpoint || undefined,
        bearerToken || undefined
      );
      const { response, error } = resp.data;
      if (error) {
        setMessages((prev) => [...prev, { role: "assistant", content: error, error: error }]);
      } else {
        const blocked =
          response === null ||
          response === "" ||
          response?.toLowerCase().includes("i'm sorry, i can't");
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: response ?? "(blocked)", blocked },
        ]);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      setMessages((prev) => [...prev, { role: "assistant", content: msg, error: msg }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 120px)" }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Test Console</Title>
        <Text type="secondary">Send messages through the guardrails engine using your real Bearer token.</Text>
      </div>

      {/* Config bar */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 12,
          alignItems: "center",
          flexWrap: "wrap",
          background: "#f5f5f5",
          border: "1px solid #e8e8e8",
          borderRadius: 8,
          padding: "10px 14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
          <Text style={{ whiteSpace: "nowrap", fontSize: 13 }}>Endpoint:</Text>
          <Select
            value={selectedEndpoint || undefined}
            onChange={setSelectedEndpoint}
            placeholder="Select endpoint"
            style={{ minWidth: 200 }}
            options={endpoints.map((e) => ({
              value: e.id,
              label: e.name + " (" + e.model_id + ")",
            }))}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, minWidth: 200 }}>
          <Tooltip title="Your Bearer token — passed through to the model endpoint">
            <KeyRound size={15} style={{ color: "#8c8c8c", flexShrink: 0 }} />
          </Tooltip>
          <Text style={{ whiteSpace: "nowrap", fontSize: 13 }}>Bearer Token:</Text>
          <Password
            value={bearerToken}
            onChange={(e) => setBearerToken(e.target.value)}
            placeholder="Paste your Bearer token here"
            style={{ flex: 1, fontFamily: "monospace", fontSize: 12 }}
            visibilityToggle
          />
        </div>

        {!bearerToken && (
          <Text type="warning" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
            Token required for model calls
          </Text>
        )}
        {bearerToken && (
          <Tag color="green" style={{ fontSize: 11 }}>Token set</Tag>
        )}
      </div>

      {/* Message thread */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid #e8e8e8",
          borderRadius: 8,
          padding: 16,
          background: "#fafafa",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {messages.length === 0 && (
          <div style={{ textAlign: "center", margin: "auto", opacity: 0.4 }}>
            <ShieldCheck size={48} />
            <div style={{ marginTop: 8 }}>Send a message to test your guardrails</div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            <div
              style={{
                maxWidth: "75%",
                padding: "10px 14px",
                borderRadius: 12,
                background:
                  msg.role === "user"
                    ? "#FF6D2D"
                    : msg.blocked
                    ? "#fff1f0"
                    : msg.error
                    ? "#fffbe6"
                    : "#fff",
                color: msg.role === "user" ? "#fff" : "#1a1a1a",
                border: msg.role !== "user" ? "1px solid #e8e8e8" : undefined,
                boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
              }}
            >
              <Text
                style={{
                  color: msg.role === "user" ? "#fff" : undefined,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {msg.content}
              </Text>
            </div>
            <div style={{ marginTop: 4, display: "flex", gap: 6, alignItems: "center" }}>
              <Tag
                color={
                  msg.role === "user"
                    ? "default"
                    : msg.blocked
                    ? "error"
                    : msg.error
                    ? "warning"
                    : "success"
                }
                style={{ fontSize: 11 }}
              >
                {msg.role === "user"
                  ? "You"
                  : msg.blocked
                  ? "Blocked by rails"
                  : msg.error
                  ? "Error"
                  : "Passed rails"}
              </Tag>
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, opacity: 0.6 }}>
            <Spin size="small" />
            <Text type="secondary" style={{ fontSize: 12 }}>Running through guardrails…</Text>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Message input */}
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
          autoSize={{ minRows: 1, maxRows: 5 }}
          style={{ flex: 1 }}
          disabled={loading}
        />
        <Button
          type="primary"
          icon={<Send size={16} />}
          onClick={send}
          loading={loading}
          disabled={!input.trim()}
          style={{ height: "auto", background: "#FF6D2D", borderColor: "#FF6D2D" }}
        >
          Send
        </Button>
      </div>
    </div>
  );
}
