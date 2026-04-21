import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Endpoints
export const endpointsApi = {
  list: () => api.get("/endpoints"),
  create: (data: { name: string; base_url: string; model_id: string }) =>
    api.post("/endpoints", data),
  update: (id: string, data: { name: string; base_url: string; model_id: string }) =>
    api.put(`/endpoints/${id}`, data),
  delete: (id: string) => api.delete(`/endpoints/${id}`),
};

// Guardrails
export const guardrailsApi = {
  types: () => api.get("/guardrails/types"),
  status: () => api.get("/guardrails/status"),
  getConfig: () => api.get("/guardrails/config"),
  updateConfig: (content: string) => api.put("/guardrails/config", { content }),
  listColang: () => api.get("/guardrails/colang"),
  updateColang: (filename: string, content: string) =>
    api.put(`/guardrails/colang/${filename}`, { content }),
  deleteColang: (filename: string) => api.delete(`/guardrails/colang/${filename}`),
  reload: () => api.post("/guardrails/reload"),
  test: (message: string, endpoint_id?: string, bearer_token?: string) =>
    api.post("/guardrails/test", { message, endpoint_id, bearer_token: bearer_token ?? "" }),
};

export default api;
