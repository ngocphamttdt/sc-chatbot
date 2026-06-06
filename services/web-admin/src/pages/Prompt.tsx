import { useEffect, useState } from "react";
import { getPrompt, putPrompt } from "../api";
import TenantSelector from "../components/TenantSelector";

export default function Prompt() {
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [tenantName, setTenantName] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    if (!tenantId) return;
    setMessage(null);
    getPrompt(tenantId)
      .then((p) => {
        setPrompt(p.system_prompt || "");
        setUpdatedAt(p.updated_at);
        setTenantName(p.tenant_name);
      })
      .catch((e) => setMessage({ type: "err", text: (e as Error).message }));
  }, [tenantId]);

  const onSave = async () => {
    if (!tenantId) return;
    setSaving(true);
    setMessage(null);
    try {
      await putPrompt(tenantId, prompt);
      setUpdatedAt(Date.now() / 1000);
      setMessage({ type: "ok", text: "Đã lưu. Tin nhắn tiếp theo sẽ dùng prompt mới." });
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const onReset = async () => {
    if (!tenantId) return;
    if (!confirm("Xoá prompt tuỳ chỉnh và trở về template mặc định?")) return;
    setSaving(true);
    try {
      await putPrompt(tenantId, "");
      setPrompt("");
      setUpdatedAt(null);
      setMessage({ type: "ok", text: "Đã reset về prompt mặc định." });
    } catch (e) {
      setMessage({ type: "err", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">System prompt</h1>
        <TenantSelector value={tenantId} onChange={setTenantId} />
      </div>

      {tenantId && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex items-baseline justify-between mb-3">
            <div>
              <div className="font-medium">{tenantName}</div>
              <div className="text-xs text-slate-500">
                {updatedAt
                  ? `Cập nhật lần cuối: ${new Date(updatedAt * 1000).toLocaleString("vi-VN")}`
                  : "Đang dùng prompt mặc định (chưa có override)"}
              </div>
            </div>
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={20}
            placeholder="Để trống = dùng prompt mặc định. Khi nhập, prompt này sẽ thay thế hoàn toàn template — ngữ cảnh từ kho tri thức vẫn được tự động ghép vào cuối."
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />

          {message && (
            <div
              className={`mt-3 text-sm rounded px-3 py-2 ${
                message.type === "ok"
                  ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
                  : "bg-red-50 border border-red-200 text-red-700"
              }`}
            >
              {message.text}
            </div>
          )}

          <div className="mt-4 flex gap-3">
            <button
              onClick={onSave}
              disabled={saving}
              className="bg-emerald-600 text-white px-4 py-1.5 rounded text-sm hover:bg-emerald-700 disabled:opacity-50 shadow-sm"
            >
              {saving ? "Đang lưu…" : "Lưu"}
            </button>
            <button
              onClick={onReset}
              disabled={saving || !updatedAt}
              className="border border-gray-300 px-4 py-1.5 rounded text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              Reset về mặc định
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
