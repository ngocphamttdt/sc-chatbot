import type {
  ConversationMessage,
  ConversationsPage,
  Document,
  PromptConfig,
  Stats,
  Tenant,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "sc_admin_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  opts: { auth?: boolean } = { auth: true }
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (opts.auth !== false) {
    const t = tokenStore.get();
    if (t) headers.set("Authorization", `Bearer ${t}`);
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    const detail =
      typeof body === "object" && body && "detail" in body
        ? (body as { detail: unknown }).detail
        : body;
    const msg =
      typeof detail === "object" && detail && "error" in (detail as object)
        ? String((detail as { error: unknown }).error)
        : `HTTP ${res.status}`;
    throw new ApiError(res.status, body, msg);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- Auth ------------------------------------------------------------

export async function login(username: string, password: string): Promise<string> {
  const r = await request<{ token: string }>(
    "/admin/login",
    { method: "POST", body: JSON.stringify({ username, password }) },
    { auth: false }
  );
  return r.token;
}

// --- Tenants ---------------------------------------------------------

export const listTenants = () => request<Tenant[]>("/admin/tenants");

// --- Documents ------------------------------------------------------

export const listDocuments = (tenantId: string) =>
  request<Document[]>(`/admin/documents?tenant_id=${encodeURIComponent(tenantId)}`);

export async function uploadDocument(tenantId: string, file: File): Promise<Document> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("tenant_id", tenantId);
  return request<Document>("/admin/documents", { method: "POST", body: fd });
}

export const deleteDocument = (tenantId: string, docId: string) =>
  request<{ ok: boolean }>(
    `/admin/documents/${encodeURIComponent(docId)}?tenant_id=${encodeURIComponent(tenantId)}`,
    { method: "DELETE" }
  );

// --- Prompt config ---------------------------------------------------

export const getPrompt = (tenantId: string) =>
  request<PromptConfig>(`/admin/config/prompt?tenant_id=${encodeURIComponent(tenantId)}`);

export const putPrompt = (tenantId: string, systemPrompt: string) =>
  request<{ ok: boolean }>("/admin/config/prompt", {
    method: "PUT",
    body: JSON.stringify({ tenant_id: tenantId, system_prompt: systemPrompt }),
  });

// --- Conversations ---------------------------------------------------

export function listConversations(
  page: number,
  size: number,
  tenantId?: string | null
): Promise<ConversationsPage> {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (tenantId) params.set("tenant_id", tenantId);
  return request<ConversationsPage>(`/admin/conversations?${params.toString()}`);
}

export const getConversation = (tenantId: string, sessionId: string) =>
  request<{ session_id: string; tenant_id: string; messages: ConversationMessage[] }>(
    `/admin/conversations/${encodeURIComponent(sessionId)}?tenant_id=${encodeURIComponent(tenantId)}`
  );

// --- Stats -----------------------------------------------------------

export const getStats = () => request<Stats>("/admin/stats");

export { ApiError };
