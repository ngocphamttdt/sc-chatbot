export type Tenant = {
  tenant_id: string;
  name: string;
  industry: string;
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
