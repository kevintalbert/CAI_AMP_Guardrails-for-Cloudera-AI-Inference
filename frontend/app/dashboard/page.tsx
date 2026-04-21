"use client";
import React, { useEffect, useState } from "react";
import { Card, Row, Col, Statistic, Tag, Typography, Alert } from "antd";
import { CheckCircle, XCircle, Server, Shield, Activity } from "lucide-react";
import { endpointsApi, guardrailsApi } from "@/lib/api";

const { Title, Text } = Typography;

interface Endpoint {
  id: string;
  name: string;
  base_url: string;
  model_id: string;
}

interface RailsStatus {
  status: string;
  config?: string;
  detail?: string;
}

export default function DashboardPage() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [railsStatus, setRailsStatus] = useState<RailsStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      endpointsApi.list().then((r) => setEndpoints(r.data)),
      guardrailsApi.status().then((r) => setRailsStatus(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  const activeEndpoint = endpoints[0];
  const isReady = railsStatus?.status === "ready";

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>Dashboard</Title>
        <Text type="secondary">Overview of your NeMo Guardrails Proxy</Text>
      </div>

      {!activeEndpoint && !loading && (
        <Alert
          type="warning"
          showIcon
          message="No endpoint configured"
          description="Head to the Endpoints page to add a target model endpoint before the proxy can route requests."
          style={{ marginBottom: 24 }}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Rails Engine"
              value={isReady ? "Ready" : railsStatus?.status ?? "—"}
              prefix={
                isReady ? (
                  <CheckCircle size={18} color="#52c41a" />
                ) : (
                  <XCircle size={18} color="#ff4d4f" />
                )
              }
              valueStyle={{ color: isReady ? "#52c41a" : "#ff4d4f", fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Configured Endpoints"
              value={endpoints.length}
              prefix={<Server size={18} color="#1677ff" />}
              valueStyle={{ fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Endpoint"
              value={activeEndpoint?.name ?? "None"}
              prefix={<Activity size={18} color={activeEndpoint ? "#52c41a" : "#8c8c8c"} />}
              valueStyle={{ fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Proxy Endpoint"
              value="POST /api/chat/completions"
              prefix={<Shield size={18} color="#FF6D2D" />}
              valueStyle={{ fontSize: 12, fontFamily: "monospace" }}
            />
          </Card>
        </Col>
      </Row>

      {activeEndpoint && (
        <Card style={{ marginTop: 24 }} title="Active Endpoint Details">
          <Row gutter={16}>
            <Col span={8}>
              <Text type="secondary">Name</Text>
              <div><Text strong>{activeEndpoint.name}</Text></div>
            </Col>
            <Col span={8}>
              <Text type="secondary">Base URL</Text>
              <div><Text code style={{ fontSize: 12 }}>{activeEndpoint.base_url}</Text></div>
            </Col>
            <Col span={8}>
              <Text type="secondary">Model ID</Text>
              <div><Tag color="blue">{activeEndpoint.model_id}</Tag></div>
            </Col>
          </Row>
        </Card>
      )}

      <Card style={{ marginTop: 24 }} title="How to Use">
        <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
          Point your OpenAI-compatible client at this proxy instead of your model endpoint directly.
          Your Bearer token is passed through transparently.
        </Text>
        <pre
          style={{
            background: "#1a1f2e",
            color: "#e6e6e6",
            padding: 16,
            borderRadius: 8,
            fontSize: 13,
            overflowX: "auto",
          }}
        >
{`curl -X POST <THIS_APP_URL>/api/chat/completions \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d \'{"model":"${activeEndpoint?.model_id ?? "your-model"}","messages":[{"role":"user","content":"Hello"}]}\'`}
        </pre>
      </Card>
    </div>
  );
}
