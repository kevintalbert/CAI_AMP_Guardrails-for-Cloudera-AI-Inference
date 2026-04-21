"use client";
import React, { useEffect, useState } from "react";
import {
  Card, Switch, Typography, Tag, Button, message, Spin,
  Input, Divider, Tooltip,
} from "antd";
import { Info, RefreshCw } from "lucide-react";
import { guardrailsApi } from "@/lib/api";
import yaml from "js-yaml";

const { Text } = Typography;
const { TextArea } = Input;

interface ConfigField {
  key: string;
  label: string;
  type: "text" | "textarea" | "password" | "number";
  default: string;
}

interface RailType {
  id: string;
  name: string;
  category: string;
  description: string;
  rail_type: "input" | "output" | "dialog";
  flow_name: string;
  requires_prompt: boolean;
  config_fields: ConfigField[];
}

interface EnabledRail {
  id: string;
  fields: Record<string, string>;
}

interface Props {
  onConfigChange?: () => void;
}

function parseConfigFlowsAndPrompts(yamlContent: string): {
  flows: string[];
  prompts: Record<string, Record<string, string>>;
} {
  try {
    const cfg = yaml.load(yamlContent) as Record<string, unknown>;
    const rails = (cfg?.rails as Record<string, unknown>) ?? {};
    const inputFlows = ((rails.input as Record<string, unknown>)?.flows as string[]) ?? [];
    const outputFlows = ((rails.output as Record<string, unknown>)?.flows as string[]) ?? [];
    const dialogFlows = ((rails.dialog as Record<string, unknown>)?.flows as string[]) ?? [];
    const flows = [...inputFlows, ...outputFlows, ...dialogFlows];

    // Parse prompts section → keyed by task name (== rail id)
    const promptList = (cfg?.prompts as Array<Record<string, string>>) ?? [];
    const prompts: Record<string, Record<string, string>> = {};
    for (const p of promptList) {
      if (p.task && p.content) {
        prompts[p.task] = { prompt: p.content };
      }
    }
    return { flows, prompts };
  } catch {
    return { flows: [], prompts: {} };
  }
}

export default function GuardrailsForm({ onConfigChange }: Props) {
  const [railTypes, setRailTypes] = useState<RailType[]>([]);
  const [enabled, setEnabled] = useState<Record<string, EnabledRail>>({});
  const [fieldValues, setFieldValues] = useState<Record<string, Record<string, string>>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      guardrailsApi.types().then((r) => r.data as RailType[]),
      guardrailsApi.getConfig().then((r) => parseConfigFlowsAndPrompts(r.data.content)),
    ]).then(([types, { flows, prompts }]) => {
      setRailTypes(types);

      // Pre-populate enabled toggles from the loaded config flows
      const initialEnabled: Record<string, EnabledRail> = {};
      for (const rt of types) {
        if (flows.includes(rt.flow_name)) {
          const defaults: Record<string, string> = {};
          rt.config_fields.forEach((f) => { defaults[f.key] = f.default; });
          initialEnabled[rt.id] = { id: rt.id, fields: defaults };
        }
      }
      setEnabled(initialEnabled);

      // Pre-populate field values from existing prompts in config
      setFieldValues(prompts);

      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const byCategory = railTypes.reduce<Record<string, RailType[]>>((acc, rt) => {
    if (!acc[rt.category]) acc[rt.category] = [];
    acc[rt.category].push(rt);
    return acc;
  }, {});

  const toggleRail = (id: string, checked: boolean) => {
    setEnabled((prev) => {
      const next = { ...prev };
      if (checked) {
        const rt = railTypes.find((r) => r.id === id);
        const defaults: Record<string, string> = {};
        rt?.config_fields.forEach((f) => { defaults[f.key] = f.default; });
        next[id] = { id, fields: defaults };
      } else {
        delete next[id];
      }
      return next;
    });
  };

  const setField = (railId: string, fieldKey: string, value: string) => {
    setFieldValues((prev) => ({
      ...prev,
      [railId]: { ...prev[railId], [fieldKey]: value },
    }));
  };

  // Get the current value for a field, preferring user-edited state, then loaded config, then default
  const getFieldValue = (railId: string, fieldKey: string, defaultVal: string): string => {
    return fieldValues[railId]?.[fieldKey] ?? defaultVal;
  };

  const buildAndSave = async () => {
    setSaving(true);
    try {
      const inputFlows: string[] = [];
      const outputFlows: string[] = [];
      const prompts: Record<string, string>[] = [];

      for (const [id] of Object.entries(enabled)) {
        const rt = railTypes.find((r) => r.id === id);
        if (!rt) continue;
        if (rt.rail_type === "input") inputFlows.push(rt.flow_name);
        else if (rt.rail_type === "output") outputFlows.push(rt.flow_name);

        if (rt.requires_prompt) {
          const promptField = rt.config_fields.find((f) => f.key === "prompt");
          const promptValue = getFieldValue(id, "prompt", promptField?.default ?? "");
          prompts.push({ task: rt.id, content: promptValue });
        }
      }

      const configObj: Record<string, unknown> = {
        models: [{ type: "main", engine: "custom", model: "default" }],
        rails: {
          input: { flows: inputFlows },
          output: { flows: outputFlows },
        },
      };

      if (prompts.length > 0) {
        configObj.prompts = prompts;
      }

      const configYaml = yaml.dump(configObj, { lineWidth: 120 });
      await guardrailsApi.updateConfig(configYaml);
      message.success("Guardrails configuration saved and reloaded");
      onConfigChange?.();
    } catch {
      message.error("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: "center" }}><Spin size="large" /></div>;

  const categories = Object.keys(byCategory);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <Text type="secondary">Enable rails below to apply them to all proxied requests.</Text>
        <Button
          type="primary"
          icon={<RefreshCw size={14} />}
          onClick={buildAndSave}
          loading={saving}
          style={{ background: "#FF6D2D", borderColor: "#FF6D2D" }}
        >
          Save & Reload
        </Button>
      </div>

      {categories.map((cat) => (
        <div key={cat} style={{ marginBottom: 24 }}>
          <Divider orientation="left" style={{ fontSize: 13, fontWeight: 600, color: "#595959", marginBottom: 12 }}>
            {cat}
          </Divider>
          <div style={{ display: "grid", gap: 12 }}>
            {byCategory[cat].map((rt) => {
              const isEnabled = Boolean(enabled[rt.id]);
              return (
                <Card
                  key={rt.id}
                  size="small"
                  style={{
                    borderColor: isEnabled ? "#FF6D2D" : undefined,
                    boxShadow: isEnabled ? "0 0 0 1px #FF6D2D" : undefined,
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                    <Switch
                      checked={isEnabled}
                      onChange={(checked) => toggleRail(rt.id, checked)}
                      style={{ marginTop: 2, ...(isEnabled ? { background: "#FF6D2D" } : {}) }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <Text strong>{rt.name}</Text>
                        <Tag color={rt.rail_type === "input" ? "blue" : rt.rail_type === "output" ? "green" : "purple"} style={{ fontSize: 11 }}>
                          {rt.rail_type}
                        </Tag>
                        <Tooltip title={rt.description}>
                          <Info size={14} style={{ color: "#8c8c8c", cursor: "help" }} />
                        </Tooltip>
                      </div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{rt.description}</Text>

                      {isEnabled && rt.config_fields.length > 0 && (
                        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f0f0f0", display: "grid", gap: 10 }}>
                          {rt.config_fields.map((field) => (
                            <div key={field.key}>
                              <Text style={{ fontSize: 12, display: "block", marginBottom: 4 }}>{field.label}</Text>
                              {field.type === "textarea" ? (
                                <TextArea
                                  rows={6}
                                  value={getFieldValue(rt.id, field.key, field.default)}
                                  onChange={(e) => setField(rt.id, field.key, e.target.value)}
                                  style={{ fontSize: 12, fontFamily: "monospace" }}
                                />
                              ) : (
                                <Input
                                  type={field.type === "password" ? "password" : "text"}
                                  value={getFieldValue(rt.id, field.key, field.default)}
                                  onChange={(e) => setField(rt.id, field.key, e.target.value)}
                                  style={{ fontSize: 12 }}
                                />
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
