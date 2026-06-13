import type { Permission } from "./types";

export const PERMISSION_LABELS: Record<Permission, string> = {
  "stats.read":         "Xem Dashboard",
  "conversations.read": "Xem Hội thoại",
  "documents.read":     "Xem Knowledge Base",
  "documents.write":    "Upload / Xóa Documents",
  "prompt.read":        "Xem System Prompt",
  "prompt.write":       "Chỉnh sửa System Prompt",
};

export const ALL_PERMISSIONS = Object.keys(PERMISSION_LABELS) as Permission[];

export const PERMISSION_GROUPS: { label: string; permissions: Permission[] }[] = [
  { label: "Dashboard",     permissions: ["stats.read"] },
  { label: "Hội thoại",    permissions: ["conversations.read"] },
  { label: "Knowledge Base",permissions: ["documents.read", "documents.write"] },
  { label: "System Prompt", permissions: ["prompt.read", "prompt.write"] },
];
