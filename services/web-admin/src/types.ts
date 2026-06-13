export type Tenant = {
  tenant_id: string;
  name: string;
  industry: string;
};

export type PromptEntry = {
  id: string;
  name: string;
  content: string;
  is_active: boolean;
  created_at: number;
  updated_at: number;
};

export type Document = {
  id: string;
  filename: string;
  status: "processing" | "done" | "failed";
  chunk_count: number;
  uploaded_at: number;
  size_bytes: number;
  error: string | null;
};

export type PromptConfig = {
  tenant_id: string;
  tenant_name: string;
  industry: string;
  system_prompt: string;
  updated_at: number | null;
};

export type SessionSummary = {
  session_id: string;
  tenant_id: string;
  tenant_name: string;
  turns: number;
  started_at: number;
  last_ts: number;
  last_message: string;
  last_role: string;
};

export type ConversationsPage = {
  page: number;
  size: number;
  total: number;
  items: SessionSummary[];
};

export type ConversationMessage = {
  session_id: string;
  tenant_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  ts: number;
};

export type DependsOn = {
  key: string;
  value: string;
};

export type Setting = {
  key: string;
  value: string;
  scope: string;
  description: string;
  is_secret: boolean;
  updated_at: number;
  depends_on?: DependsOn;
}
export type AdminRole = "super_admin" | "support";
export type UserType = "admin" | "tenant";

export type AdminUser = {
  id: string;
  email: string;
  role: AdminRole;
  created_at: number;
  created_by: string;
};

export type TenantUser = {
  id: string;
  email: string;
  tenant_id: string;
  role: string;
  created_at: number;
  created_by: string;
};

export type LoginResponse = {
  token: string;
  user_type: UserType;
  role: string;
  tenant_id: string | null;
  tenant_name: string | null;
  display_name: string;
  permissions: Permission[];
};

export type Permission =
  | "stats.read"
  | "conversations.read"
  | "documents.read"
  | "documents.write"
  | "prompt.read"
  | "prompt.write";

export type RoleColor = "emerald" | "blue" | "purple" | "amber" | "slate" | "rose";

export type Role = {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  is_system: boolean;
  color: RoleColor;
  created_at: number;
};

export type TenantRole = {
  tenant_id: string;
  role_id: string;
  granted_at: number;
};

export type Stats = {
  total_conversations: number;
  total_messages_in: number;
  total_orders: number;
  total_bookings: number;
  conversion_rate: number;
  avg_response_latency_ms: number;
  avg_csat: number | null;
  qa_per_day: { date: string; count: number }[];
  generated_at: number;
};
