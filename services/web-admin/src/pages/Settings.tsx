import { useEffect, useState, useCallback } from "react";
import { listSettings, updateSetting, revealSetting, deleteSetting, reloadSettings } from "../api";
import TenantSelector from "../components/TenantSelector";
import type { Setting, DependsOn } from "../types";

type GroupConfig = {
  label: string;
  keys: string[];
  dependsOn?: DependsOn;
};

const GROUPS: GroupConfig[] = [
  { label: "LLM", keys: ["llm_provider", "llm_temperature", "llm_model"] },
  { label: "OpenAI", keys: ["openai_api_key", "openai_base_url", "openai_embed_model"], dependsOn: { key: "llm_provider", value: "openai" } },
  { label: "Azure OpenAI", keys: ["azure_endpoint", "azure_api_key", "azure_api_version", "azure_chat_deployment", "azure_embed_deployment"], dependsOn: { key: "llm_provider", value: "azure" } },
  { label: "Embeddings", keys: ["embedding_provider", "hf_embed_model"] },
  { label: "Lưu trữ", keys: ["data_dir", "default_tenant", "storage_backend", "mongo_uri"] },
  { label: "Xác thực", keys: ["jwt_secret", "jwt_expires_min", "admin_user", "admin_password"] },
  { label: "Telegram", keys: ["telegram_bot_token", "telegram_default_tenant"] },
  { label: "Client Server", keys: ["client_server_url", "internal_api_key"] },
];

type SettingRow = {
  current: Setting;
  edited: string;
  revealed: boolean;
  revealedValue: string;
};

const DROPDOWN_KEYS = new Set(["llm_provider"]);
const DROPDOWN_OPTIONS: Record<string, { value: string; label: string }[]> = {
  llm_provider: [
    { value: "openai", label: "OpenAI" },
    { value: "azure", label: "Azure OpenAI" },
  ],
};

function isGroupVisible(group: GroupConfig, settingsMap: Map<string, SettingRow>): boolean {
  if (!group.dependsOn) return true;
  const providerRow = settingsMap.get(group.dependsOn.key);
  if (!providerRow) return true;
  return providerRow.current.value === group.dependsOn.value;
}

export default function Settings() {
  const [scope, setScope] = useState("global");
  const [settingsMap, setSettingsMap] = useState<Map<string, SettingRow>>(new Map());
  const [dirty, setDirty] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const scopeLabel = scope === "global" ? "Global" : scope.replace("tenant:", "");

  const load = useCallback(async () => {
    try {
      const rows = await listSettings(scope);
      const m = new Map<string, SettingRow>();
      for (const r of rows) {
        m.set(r.key, { current: r, edited: r.value, revealed: false, revealedValue: "" });
      }
      setSettingsMap(m);
      setDirty(new Set());
      setMessage(null);
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    }
  }, [scope]);

  useEffect(() => {
    load();
  }, [load]);

  const handleChange = (key: string, value: string) => {
    setSettingsMap((prev) => {
      const next = new Map(prev);
      const row = next.get(key);
      if (row) {
        next.set(key, { ...row, edited: value });
      }
      return next;
    });
    setDirty((prev) => new Set(prev).add(key));
  };

  const handleReveal = async (key: string) => {
    try {
      const r = await revealSetting(key, scope);
      setSettingsMap((prev) => {
        const next = new Map(prev);
        const row = next.get(key);
        if (row) {
          next.set(key, { ...row, revealed: true, revealedValue: r.value });
          setTimeout(() => {
            setSettingsMap((p) => {
              const n = new Map(p);
              const ro = n.get(key);
              if (ro) n.set(key, { ...ro, revealed: false, revealedValue: "" });
              return n;
            });
          }, 5000);
        }
        return next;
      });
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    }
  };

  const handleCopy = async (key: string) => {
    const row = settingsMap.get(key);
    if (!row) return;
    const val = row.revealed ? row.revealedValue : row.edited;
    try {
      await navigator.clipboard.writeText(val);
      setMessage({ type: "ok", text: "Đã sao chép vào clipboard." });
      setTimeout(() => setMessage(null), 2000);
    } catch {
      setMessage({ type: "err", text: "Không thể sao chép." });
    }
  };

  const handleProviderChange = async (newProvider: string) => {
    const providerRow = settingsMap.get("llm_provider");
    if (!providerRow) return;
    if (providerRow.current.value === newProvider) return;

    const groupHasDirty = GROUPS.some(
      (g) => g.dependsOn && g.keys.some((k) => dirty.has(k))
    );
    if (groupHasDirty && !confirm("Chuyển đổi provider sẽ hủy các thay đổi chưa lưu. Tiếp tục?")) {
      return;
    }

    setSaving(true);
    try {
      await updateSetting("llm_provider", newProvider, scope);
      await reloadSettings();
      await load();
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const saveGroup = async (keys: string[]) => {
    setSaving(true);
    setMessage(null);
    const changed = keys.filter((k) => dirty.has(k));
    if (changed.length === 0) {
      setMessage({ type: "ok", text: "Không có thay đổi." });
      setSaving(false);
      return;
    }
    try {
      for (const key of changed) {
        const row = settingsMap.get(key);
        if (!row) continue;
        await updateSetting(key, row.edited, scope);
      }
      await reloadSettings();
      setMessage({ type: "ok", text: "Đã lưu và tải lại cấu hình." });
      await load();
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const resetGroup = async (keys: string[]) => {
    if (!confirm("Khôi phục các giá trị mặc định cho nhóm này?")) return;
    if (scope === "global") return;
    setSaving(true);
    try {
      for (const key of keys) {
        await deleteSetting(key, scope);
      }
      await reloadSettings();
      setMessage({ type: "ok", text: "Đã khôi phục giá trị global cho nhóm này." });
      await load();
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const hasOverride = (key: string) => {
    return scope !== "global" && settingsMap.has(key);
  };

  const isNumber = (key: string) =>
    ["llm_temperature", "jwt_expires_min"].includes(key);

  const visibleGroups = GROUPS.filter((g) => isGroupVisible(g, settingsMap));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Cấu hình hệ thống</h1>
        <TenantSelector
          value={scope === "global" ? null : scope.replace("tenant:", "")}
          onChange={(id) => setScope(id === "__global" ? "global" : `tenant:${id}`)}
          allowAll
        />
      </div>

      {message && (
        <div
          className={`mb-4 text-sm rounded px-3 py-2 ${
            message.type === "ok"
              ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
              : "bg-red-50 border border-red-200 text-red-700"
          }`}
        >
          {message.text}
        </div>
      )}

      {scope !== "global" && (
        <div className="mb-4 text-sm text-slate-500 bg-slate-50 border border-slate-200 rounded px-3 py-2">
          Đang xem cấu hình cho tenant <strong>{scopeLabel}</strong>. Các giá trị được ghi đè sẽ hiện badge{" "}
          <span className="inline-block bg-amber-100 text-amber-800 text-xs px-1.5 py-0.5 rounded">override</span>.
        </div>
      )}

      {visibleGroups.map((group) => {
        const keys = group.keys;
        const hasChanges = keys.some((k) => dirty.has(k));
        const isOverrideGroup = scope !== "global" && keys.some((k) => settingsMap.has(k));

        return (
          <div key={group.label} className="bg-white border border-gray-200 rounded-lg mb-4 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <h2 className="font-medium text-slate-900">{group.label}</h2>
                {isOverrideGroup && (
                  <span className="bg-amber-100 text-amber-800 text-xs px-1.5 py-0.5 rounded">override</span>
                )}
              </div>
              <div className="flex gap-2">
                {scope !== "global" && isOverrideGroup && (
                  <button
                    onClick={() => resetGroup(keys)}
                    disabled={saving}
                    className="text-xs border border-gray-300 px-2.5 py-1 rounded hover:bg-slate-50 disabled:opacity-50"
                  >
                    Khôi phục mặc định
                  </button>
                )}
                <button
                  onClick={() => saveGroup(keys)}
                  disabled={saving || !hasChanges}
                  className="bg-emerald-600 text-white px-3 py-1 rounded text-xs hover:bg-emerald-700 disabled:opacity-50 shadow-sm"
                >
                  {saving ? "Đang lưu…" : "Lưu thay đổi"}
                </button>
              </div>
            </div>

            <div className="divide-y divide-gray-50">
              {keys.map((key) => {
                const row = settingsMap.get(key);
                if (!row) {
                  return (
                    <div key={key} className="px-5 py-3 flex items-center justify-between">
                      <span className="text-sm text-slate-700 font-mono">{key}</span>
                      <span className="text-xs text-slate-400 italic">Đang tải…</span>
                    </div>
                  );
                }

                const isSecret = row.current.is_secret;
                const displayValue = row.revealed ? row.revealedValue : row.edited;
                const groupHasChanges = dirty.has(key);
                const isDropdown = DROPDOWN_KEYS.has(key);

                return (
                  <div key={key} className="px-5 py-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-700 font-mono">{key}</span>
                        {isSecret && <span className="text-[10px] text-rose-500 font-medium">secret</span>}
                        {hasOverride(key) && scope !== "global" && (
                          <span className="bg-amber-100 text-amber-800 text-[10px] px-1 py-0.5 rounded">override</span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{row.current.description}</div>
                    </div>

                    {isDropdown ? (
                      <select
                        value={displayValue}
                        onChange={(e) => handleProviderChange(e.target.value)}
                        disabled={saving}
                        className="w-48 border border-gray-300 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        {(DROPDOWN_OPTIONS[key] || []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={isSecret && !row.revealed ? "password" : isNumber(key) ? "number" : "text"}
                        value={isSecret && !row.revealed ? (displayValue === "*****" ? "" : displayValue) : displayValue}
                        onChange={(e) => handleChange(key, e.target.value)}
                        placeholder={isSecret ? "********" : ""}
                        className={`w-48 border rounded px-2 py-1 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
                          groupHasChanges ? "border-amber-300 bg-amber-50" : "border-gray-300"
                        }`}
                      />
                    )}

                    {isSecret && (
                      <>
                        <button
                          onClick={() => handleReveal(key)}
                          className="text-slate-400 hover:text-slate-600 p-1"
                          title="Hiện giá trị"
                        >
                          👁
                        </button>
                        <button
                          onClick={() => handleCopy(key)}
                          className="text-slate-400 hover:text-slate-600 p-1"
                          title="Sao chép"
                        >
                          📋
                        </button>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
