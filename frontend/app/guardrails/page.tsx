"use client";
import React, { useEffect, useState, useCallback } from "react";
import { Tabs, Typography, Button, Select, Popconfirm, message, Input, Modal } from "antd";
import { Plus, RefreshCw, Trash2 } from "lucide-react";
import dynamic from "next/dynamic";
import GuardrailsForm from "@/components/GuardrailsForm";
import { guardrailsApi } from "@/lib/api";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const { Title, Text } = Typography;

interface ColangFile {
  filename: string;
  content: string;
}

export default function GuardrailsPage() {
  const [configContent, setConfigContent] = useState("");
  const [colangFiles, setColangFiles] = useState<ColangFile[]>([]);
  const [activeColang, setActiveColang] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [newFileModal, setNewFileModal] = useState(false);
  const [newFilename, setNewFilename] = useState("");

  const loadConfig = useCallback(() => {
    guardrailsApi.getConfig().then((r) => setConfigContent(r.data.content));
  }, []);

  const loadColang = useCallback(() => {
    guardrailsApi.listColang().then((r) => {
      setColangFiles(r.data);
      if (r.data.length > 0 && !activeColang) {
        setActiveColang(r.data[0].filename);
      }
    });
  }, [activeColang]);

  useEffect(() => {
    loadConfig();
    loadColang();
  }, []);

  const saveConfig = async () => {
    setSaving(true);
    try {
      await guardrailsApi.updateConfig(configContent);
      message.success("config.yml saved and rails reloaded");
    } catch {
      message.error("Failed to save config");
    } finally {
      setSaving(false);
    }
  };

  const saveColang = async () => {
    if (!activeColang) return;
    setSaving(true);
    const file = colangFiles.find((f) => f.filename === activeColang);
    if (!file) { setSaving(false); return; }
    try {
      await guardrailsApi.updateColang(activeColang, file.content);
      message.success(`${activeColang} saved and rails reloaded`);
    } catch {
      message.error("Failed to save file");
    } finally {
      setSaving(false);
    }
  };

  const deleteColang = async (filename: string) => {
    await guardrailsApi.deleteColang(filename);
    message.success(`${filename} deleted`);
    setActiveColang("");
    loadColang();
  };

  const createColang = async () => {
    let name = newFilename.trim();
    if (!name) return;
    if (!name.endsWith(".co")) name += ".co";
    await guardrailsApi.updateColang(name, "# New Colang file\n");
    message.success(`${name} created`);
    setNewFileModal(false);
    setNewFilename("");
    setActiveColang(name);
    loadColang();
  };

  const activeColangContent = colangFiles.find((f) => f.filename === activeColang)?.content ?? "";

  const tabItems = [
    {
      key: "form",
      label: "Rail Builder",
      children: (
        <div style={{ paddingTop: 16 }}>
          <GuardrailsForm onConfigChange={loadConfig} />
        </div>
      ),
    },
    {
      key: "config",
      label: "config.yml",
      children: (
        <div style={{ paddingTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12, gap: 8 }}>
            <Button icon={<RefreshCw size={14} />} onClick={loadConfig}>Refresh</Button>
            <Button
              type="primary"
              loading={saving}
              onClick={saveConfig}
              style={{ background: "#FF6D2D", borderColor: "#FF6D2D" }}
            >
              Save & Reload
            </Button>
          </div>
          <div style={{ border: "1px solid #e8e8e8", borderRadius: 8, overflow: "hidden" }}>
            <MonacoEditor
              height="500px"
              language="yaml"
              value={configContent}
              onChange={(v) => setConfigContent(v ?? "")}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                wordWrap: "on",
              }}
            />
          </div>
        </div>
      ),
    },
    {
      key: "colang",
      label: "Colang Files",
      children: (
        <div style={{ paddingTop: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Select
              value={activeColang || undefined}
              onChange={setActiveColang}
              placeholder="Select a .co file"
              style={{ flex: 1 }}
              options={colangFiles.map((f) => ({ value: f.filename, label: f.filename }))}
            />
            <Button icon={<Plus size={14} />} onClick={() => setNewFileModal(true)}>New File</Button>
            {activeColang && (
              <>
                <Button icon={<RefreshCw size={14} />} onClick={loadColang}>Refresh</Button>
                <Button
                  type="primary"
                  loading={saving}
                  onClick={saveColang}
                  style={{ background: "#FF6D2D", borderColor: "#FF6D2D" }}
                >
                  Save & Reload
                </Button>
                <Popconfirm
                  title={`Delete ${activeColang}?`}
                  onConfirm={() => deleteColang(activeColang)}
                  okText="Delete"
                  okButtonProps={{ danger: true }}
                >
                  <Button danger icon={<Trash2 size={14} />} />
                </Popconfirm>
              </>
            )}
          </div>

          <div style={{ border: "1px solid #e8e8e8", borderRadius: 8, overflow: "hidden" }}>
            <MonacoEditor
              height="500px"
              language="plaintext"
              value={activeColangContent}
              onChange={(v) => {
                setColangFiles((prev) =>
                  prev.map((f) =>
                    f.filename === activeColang ? { ...f, content: v ?? "" } : f
                  )
                );
              }}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                wordWrap: "on",
              }}
            />
          </div>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>Guardrails</Title>
        <Text type="secondary">
          Configure NeMo Guardrails rails via the form builder or edit config.yml / Colang files directly.
        </Text>
      </div>

      <Tabs items={tabItems} />

      <Modal
        title="New Colang File"
        open={newFileModal}
        onOk={createColang}
        onCancel={() => { setNewFileModal(false); setNewFilename(""); }}
        okText="Create"
        okButtonProps={{ style: { background: "#FF6D2D", borderColor: "#FF6D2D" } }}
      >
        <div style={{ marginTop: 16 }}>
          <Text style={{ display: "block", marginBottom: 8 }}>Filename (will append .co if missing)</Text>
          <Input
            value={newFilename}
            onChange={(e) => setNewFilename(e.target.value)}
            placeholder="my_rails.co"
            onPressEnter={createColang}
          />
        </div>
      </Modal>
    </div>
  );
}
