import type {
  AdminUser,
  ConversationMessage,
  ConversationsPage,
  Document,
  LoginResponse,
  PromptConfig,
  PromptEntry,
  Role,
  RoleColor,
  Permission,
  Stats,
  Tenant,
  TenantUser,
  Setting,
} from "./types";
import { hashPassword } from "./crypto";

const BASE = import.meta.env.VITE_API_BASE_URL || "";

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
    const rawText = await res.text();
    try { body = JSON.parse(rawText); } catch { body = rawText; }
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

export async function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>(
    "/admin/login",
    { method: "POST", body: JSON.stringify({ username, password: await hashPassword(password) }) },
    { auth: false }
  );
}

// --- Tenants ---------------------------------------------------------

export const listTenants = () =>
  request<{ tenants: Tenant[] }>("/tenants").then((r) => r.tenants);

export const createTenant = (tenant_id: string, name: string, industry: string) =>
  request<Tenant>("/tenants", {
    method: "POST",
    body: JSON.stringify({ tenant_id, name, industry }),
  }, { auth: false });

// --- Admin users -----------------------------------------------------

export const listAdminUsers = () =>
  request<AdminUser[]>("/admin/users");

export const createAdminUser = async (email: string, password: string, role: string) =>
  request<AdminUser>("/admin/users", {
    method: "POST",
    body: JSON.stringify({ email, password: await hashPassword(password), role }),
  });

export const deleteAdminUser = (userId: string) =>
  request<void>(`/admin/users/${encodeURIComponent(userId)}`, { method: "DELETE" });

// --- Roles -----------------------------------------------------------

export const listRoles = () =>
  request<Role[]>("/admin/roles");

export const createRole = (name: string, description: string, color: RoleColor, permissions: Permission[]) =>
  request<Role>("/admin/roles", {
    method: "POST",
    body: JSON.stringify({ name, description, color, permissions }),
  });

export const updateRole = (
  roleId: string,
  patch: { name?: string; description?: string; color?: RoleColor; permissions?: Permission[] }
) =>
  request<Role>(`/admin/roles/${encodeURIComponent(roleId)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });

export const deleteRole = (roleId: string) =>
  request<void>(`/admin/roles/${encodeURIComponent(roleId)}`, { method: "DELETE" });

export const updateTenant = (tenantId: string, name: string, industry: string) =>
  request<Tenant>(`/admin/tenants/${encodeURIComponent(tenantId)}`, {
    method: "PATCH",
    body: JSON.stringify({ name, industry }),
  });

// --- Prompts ---------------------------------------------------------

export const listPrompts = (tenantId: string) =>
  request<PromptEntry[]>(`/admin/tenants/${encodeURIComponent(tenantId)}/prompts`);

export const createPrompt = (tenantId: string, name: string, content: string) =>
  request<PromptEntry>(`/admin/tenants/${encodeURIComponent(tenantId)}/prompts`, {
    method: "POST",
    body: JSON.stringify({ name, content }),
  });

export const updatePrompt = (tenantId: string, promptId: string, name: string, content: string) =>
  request<PromptEntry>(
    `/admin/tenants/${encodeURIComponent(tenantId)}/prompts/${encodeURIComponent(promptId)}`,
    { method: "PATCH", body: JSON.stringify({ name, content }) }
  );

export const activatePrompt = (tenantId: string, promptId: string) =>
  request<PromptEntry>(
    `/admin/tenants/${encodeURIComponent(tenantId)}/prompts/${encodeURIComponent(promptId)}/activate`,
    { method: "PUT" }
  );

export const deletePrompt = (tenantId: string, promptId: string) =>
  request<void>(
    `/admin/tenants/${encodeURIComponent(tenantId)}/prompts/${encodeURIComponent(promptId)}`,
    { method: "DELETE" }
  );

// --- Tenant users ----------------------------------------------------

export const listTenantUsers = (tenantId: string) =>
  request<TenantUser[]>(`/admin/tenants/${encodeURIComponent(tenantId)}/users`);

export const createTenantUser = async (tenantId: string, email: string, password: string, role: string) =>
  request<TenantUser>(`/admin/tenants/${encodeURIComponent(tenantId)}/users`, {
    method: "POST",
    body: JSON.stringify({ email, password: await hashPassword(password), role }),
  });

export const updateTenantUserRole = (tenantId: string, userId: string, role: string) =>
  request<TenantUser>(`/admin/tenants/${encodeURIComponent(tenantId)}/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });

export const deleteTenantUser = (tenantId: string, userId: string) =>
  request<void>(
    `/admin/tenants/${encodeURIComponent(tenantId)}/users/${encodeURIComponent(userId)}`,
    { method: "DELETE" }
  );

// --- Documents -------------------------------------------------------

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

export function listConversations(page: number, size: number, tenantId?: string | null): Promise<ConversationsPage> {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (tenantId) params.set("tenant_id", tenantId);
  return request<ConversationsPage>(`/admin/conversations?${params.toString()}`);
}

export const getConversation = (tenantId: string, sessionId: string) =>
  request<{ session_id: string; tenant_id: string; messages: ConversationMessage[] }>(
    `/admin/conversations/${encodeURIComponent(sessionId)}?tenant_id=${encodeURIComponent(tenantId)}`
  );

// --- Stats -----------------------------------------------------------

export const getStats = (tenantId?: string | null, days?: number) => {
  const params = new URLSearchParams();
  if (tenantId) params.set("tenant_id", tenantId);
  if (days) params.set("days", String(days));
  const qs = params.toString();
  return request<Stats>(`/admin/stats${qs ? `?${qs}` : ""}`);
};

// --- Settings ---------------------------------------------------------

export const listSettings = (scope?: string) => {
  const params = scope ? `?scope=${encodeURIComponent(scope)}` : "";
  return request<Setting[]>(`/admin/settings${params}`);
};

export const getSetting = (key: string, scope = "global") =>
  request<Setting>(`/admin/settings/${encodeURIComponent(key)}?scope=${encodeURIComponent(scope)}`);

export const updateSetting = (key: string, value: string, scope = "global") =>
  request<Setting>(`/admin/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value, scope }),
  });

export const revealSetting = (key: string, scope = "global") =>
  request<{ key: string; value: string }>(
    `/admin/settings/${encodeURIComponent(key)}/reveal?scope=${encodeURIComponent(scope)}`
  );

export const deleteSetting = (key: string, scope = "global") =>
  request<{ ok: boolean }>(
    `/admin/settings/${encodeURIComponent(key)}?scope=${encodeURIComponent(scope)}`,
    { method: "DELETE" }
  );

export const reloadSettings = () =>
  request<{ ok: boolean; reloaded_at: number }>("/admin/settings/reload", { method: "POST" });

export { ApiError };
