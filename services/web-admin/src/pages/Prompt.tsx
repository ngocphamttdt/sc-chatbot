import { useEffect, useState } from "react";
import { activatePrompt, createPrompt, deletePrompt, listPrompts, updatePrompt } from "../api";
import { useAuth } from "../auth";
import TenantSelector from "../components/TenantSelector";
import type { PromptEntry } from "../types";

type PromptForm = { name: string; content: string };
const emptyForm = (): PromptForm => ({ name: "", content: "" });

export default function Prompt() {
  const { isAdmin, tenantId: authTenantId, can } = useAuth();
  const [tenantId, setTenantId] = useState<string | null>(() => isAdmin ? null : authTenantId);
  const [prompts, setPrompts] = useState<PromptEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [createModal, setCreateModal] = useState(false);
  const [editModal, setEditModal] = useState<PromptEntry | null>(null);
  const [form, setForm] = useState<PromptForm>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = (tid: string) => {
    setLoading(true);
    setError(null);
    listPrompts(tid)
      .then(setPrompts)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (tenantId) load(tenantId);
    else setPrompts([]);
  }, [tenantId]);

  const openCreate = () => {
    setForm(emptyForm());
    setFormError(null);
    setCreateModal(true);
  };

  const openEdit = (p: PromptEntry) => {
    setForm({ name: p.name, content: p.content });
    setFormError(null);
    setEditModal(p);
  };

  const submitCreate = async () => {
    if (!form.name.trim() || !form.content.trim()) {
      setFormError("Vui lòng điền đầy đủ tên và nội dung.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await createPrompt(tenantId!, form.name.trim(), form.content.trim());
      setCreateModal(false);
      load(tenantId!);
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const submitEdit = async () => {
    if (!editModal || !form.name.trim() || !form.content.trim()) {
      setFormError("Vui lòng điền đầy đủ tên và nội dung.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await updatePrompt(tenantId!, editModal.id, form.name.trim(), form.content.trim());
      setEditModal(null);
      load(tenantId!);
    } catch (e) {
      setFormError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (promptId: string) => {
    try {
      await activatePrompt(tenantId!, promptId);
      load(tenantId!);
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const handleDelete = async (promptId: string) => {
    if (!confirm("Xóa prompt này?")) return;
    try {
      await deletePrompt(tenantId!, promptId);
      setPrompts((prev) => prev.filter((p) => p.id !== promptId));
    } catch (e) {
      alert((e as Error).message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">System Prompt</h1>
          <p className="text-sm text-slate-500 mt-1">Quản lý các prompt cho từng doanh nghiệp</p>
        </div>
        <div className="flex items-center gap-3">
          <TenantSelector value={tenantId} onChange={setTenantId} />
          {tenantId && can("prompt.write") && (
            <button
              onClick={openCreate}
              className="bg-emerald-600 text-white px-4 py-2 rounded text-sm hover:bg-emerald-700 transition shadow-sm"
            >
              + Thêm prompt
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}

      {!tenantId ? (
        <div className="bg-white border border-gray-200 rounded-lg py-16 flex items-center justify-center">
          <p className="text-slate-400 text-sm">Chọn một doanh nghiệp để xem danh sách system prompt.</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-slate-600 text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-3">Tên prompt</th>
                <th className="text-left px-4 py-3">Nội dung</th>
                <th className="text-left px-4 py-3">Trạng thái</th>
                <th className="text-left px-4 py-3">Ngày tạo</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400">Đang tải…</td>
                </tr>
              )}
              {!loading && prompts.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400">
                    Chưa có prompt nào. Nhấn "+ Thêm prompt" để tạo.
                  </td>
                </tr>
              )}
              {prompts.map((p) => (
                <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-slate-900">{p.name}</td>
                  <td className="px-4 py-3 text-slate-500 max-w-xs">
                    <span className="line-clamp-1">
                      {p.content.length > 80 ? p.content.slice(0, 80) + "…" : p.content}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {p.is_active ? (
                      <span className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-medium px-2.5 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                        Đang dùng
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {new Date(p.created_at * 1000).toLocaleDateString("vi-VN")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-3">
                      {can("prompt.write") && (
                        <>
                          <button
                            onClick={() => openEdit(p)}
                            className="text-xs text-slate-500 hover:text-slate-800 hover:underline"
                          >
                            Xem / Sửa
                          </button>
                          {!p.is_active && (
                            <button
                              onClick={() => handleActivate(p.id)}
                              className="text-xs text-emerald-600 font-medium hover:underline"
                            >
                              Kích hoạt
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(p.id)}
                            className="text-xs text-red-500 hover:text-red-700 hover:underline"
                          >
                            Xóa
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createModal && (
        <PromptModal
          title="Thêm prompt mới"
          form={form}
          setForm={setForm}
          formError={formError}
          saving={saving}
          onCancel={() => setCreateModal(false)}
          onSubmit={submitCreate}
          submitLabel="Tạo prompt"
        />
      )}

      {editModal && (
        <PromptModal
          title={`Chỉnh sửa — ${editModal.name}`}
          form={form}
          setForm={setForm}
          formError={formError}
          saving={saving}
          onCancel={() => setEditModal(null)}
          onSubmit={submitEdit}
          submitLabel="Lưu thay đổi"
        />
      )}
    </div>
  );
}

type ModalProps = {
  title: string;
  form: PromptForm;
  setForm: React.Dispatch<React.SetStateAction<PromptForm>>;
  formError: string | null;
  saving: boolean;
  onCancel: () => void;
  onSubmit: () => void;
  submitLabel: string;
};

function PromptModal({ title, form, setForm, formError, saving, onCancel, onSubmit, submitLabel }: ModalProps) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl flex flex-col" style={{ maxHeight: "90vh" }}>
        <div className="px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>

        <div className="px-6 py-5 flex-1 overflow-y-auto space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Tên prompt <span className="text-red-500">*</span>
            </label>
            <input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="VD: Mặc định, Khuyến mãi hè…"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Nội dung <span className="text-red-500">*</span>
            </label>
            <textarea
              value={form.content}
              onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
              rows={18}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
              placeholder="Bạn là trợ lý AI của {tenant_name}…"
            />
          </div>

          {formError && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {formError}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-100 shrink-0 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded border border-gray-300 text-sm text-slate-600 hover:bg-gray-50"
          >
            Hủy
          </button>
          <button
            onClick={onSubmit}
            disabled={saving}
            className="px-4 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700 disabled:opacity-50 transition"
          >
            {saving ? "Đang lưu…" : submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
