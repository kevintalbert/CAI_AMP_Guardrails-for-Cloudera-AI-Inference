"use client";
import React, { useEffect, useState } from "react";
import {
  Table, Button, Modal, Form, Input, Space, Popconfirm,
  Typography, message, Tag, Tooltip,
} from "antd";
import { Plus, Pencil, Trash2, Server } from "lucide-react";
import { endpointsApi } from "@/lib/api";

const { Title, Text } = Typography;

interface Endpoint {
  id: string;
  name: string;
  base_url: string;
  model_id: string;
}

export default function EndpointsPage() {
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Endpoint | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    endpointsApi.list().then((r) => setEndpoints(r.data)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (ep: Endpoint) => {
    setEditing(ep);
    form.setFieldsValue(ep);
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await endpointsApi.update(editing.id, values);
        message.success("Endpoint updated");
      } else {
        await endpointsApi.create(values);
        message.success("Endpoint created");
      }
      setModalOpen(false);
      load();
    } catch {
      message.error("Failed to save endpoint");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await endpointsApi.delete(id);
    message.success("Endpoint deleted");
    load();
  };

  const columns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (v: string, _: Endpoint, i: number) => (
        <Space>
          <Text strong>{v}</Text>
          {i === 0 && <Tag color="green">Active</Tag>}
        </Space>
      ),
    },
    {
      title: "Base URL",
      dataIndex: "base_url",
      key: "base_url",
      ellipsis: true,
      render: (v: string) => (
        <Tooltip title={v}>
          <Text code style={{ fontSize: 12, whiteSpace: "nowrap" }}>{v}</Text>
        </Tooltip>
      ),
    },
    {
      title: "Model ID",
      dataIndex: "model_id",
      key: "model_id",
      width: 280,
      render: (v: string) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_: unknown, record: Endpoint) => (
        <Space>
          <Tooltip title="Edit">
            <Button size="small" icon={<Pencil size={14} />} onClick={() => openEdit(record)} />
          </Tooltip>
          <Popconfirm
            title="Delete this endpoint?"
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete">
              <Button size="small" danger icon={<Trash2 size={14} />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Endpoints</Title>
          <Text type="secondary">Configure target model endpoints. The first endpoint is used as the active proxy target.</Text>
        </div>
        <Button type="primary" icon={<Plus size={16} />} onClick={openCreate}
          style={{ background: "#FF6D2D", borderColor: "#FF6D2D" }}>
          Add Endpoint
        </Button>
      </div>

      <Table
        dataSource={endpoints}
        columns={columns}
        rowKey="id"
        loading={loading}
        locale={{ emptyText: <div style={{ padding: 32 }}><Server size={40} style={{ opacity: 0.3 }} /><div>No endpoints configured</div></div> }}
      />

      <Modal
        title={editing ? "Edit Endpoint" : "Add Endpoint"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText={editing ? "Update" : "Create"}
        okButtonProps={{ style: { background: "#FF6D2D", borderColor: "#FF6D2D" } }}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="Name" rules={[{ required: true, message: "Name is required" }]}>
            <Input placeholder="Production CIS" />
          </Form.Item>
          <Form.Item name="base_url" label="Base URL" rules={[{ required: true, message: "Base URL is required" }]}>
            <Input placeholder="https://your-endpoint.example.com/v1" />
          </Form.Item>
          <Form.Item name="model_id" label="Model ID" rules={[{ required: true, message: "Model ID is required" }]}>
            <Input placeholder="nvidia/llama-3.3-nemotron-super-49b-v1.5" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
