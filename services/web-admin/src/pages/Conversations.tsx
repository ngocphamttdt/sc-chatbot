import { useEffect, useState } from "react";
import { getConversation, listConversations } from "../api";
import { useAuth } from "../auth";
import TenantSelector from "../components/TenantSelector";
import type { ConversationMessage, SessionSummary } from "../types";

const PAGE_SIZE = 20;

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString("vi-VN");
}

export default function Conversations() {
  const { isAdmin, tenantId: authTenantId } = useAuth();
  // Tenant users are always scoped to their tenant; admin can filter or view all (null)
  const [tenantFilter, setTenantFilter] = useState<string | null>(() => isAdmin ? null : authTenantId);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{
    total: number;
    items: SessionSummary[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<{
    session: SessionSummary;
    messages: ConversationMessage[];
  } | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    setError(null);
    listConversations(page, PAGE_SIZE, tenantFilter)
      .then((d) => setData({ total: d.total, items: d.items }))
      .catch((e) => setError((e as Error).message));
  }, [page, tenantFilter]);

  const openDetail = async (s: SessionSummary) => {
    setLoadingDetail(true);
    try {
      const d = await getConversation(s.tenant_id, s.session_id);
      setSelected({ session: s, messages: d.messages });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Lịch sử hội thoại</h1>
        <TenantSelector
          value={tenantFilter}
          onChange={(v) => {
            setTenantFilter(v || null);
            setPage(1);
          }}
          allowAll
        />
      </div>

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-slate-600 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Session</th>
              <th className="text-left px-4 py-2">Tenant</th>
              <th className="text-right px-4 py-2">Lượt</th>
              <th className="text-left px-4 py-2">Hoạt động cuối</th>
              <th className="text-left px-4 py-2">Tin nhắn cuối</th>
            </tr>
          </thead>
          <tbody>
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                  Chưa có hội thoại nào.
                </td>
              </tr>
            )}
            {data?.items.map((s) => (
              <tr
                key={`${s.tenant_id}-${s.session_id}`}
                className="border-t border-gray-100 cursor-pointer hover:bg-gray-50"
                onClick={() => openDetail(s)}
              >
                <td className="px-4 py-2 font-mono text-xs">{s.session_id}</td>
                <td className="px-4 py-2">{s.tenant_name}</td>
                <td className="px-4 py-2 text-right tabular-nums">{s.turns}</td>
                <td className="px-4 py-2 text-slate-500">{formatTime(s.last_ts)}</td>
                <td className="px-4 py-2 text-slate-600 truncate max-w-md">
                  <span className="text-xs text-slate-400 mr-1">[{s.last_role}]</span>
                  {s.last_message}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {data && data.total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm">
            <span className="text-slate-500">
              Trang {page} / {totalPages} — tổng {data.total} session
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1 border border-gray-300 rounded disabled:opacity-40"
              >
                Trước
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1 border border-gray-300 rounded disabled:opacity-40"
              >
                Sau
              </button>
            </div>
          </div>
        )}
      </div>

      {selected && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-10"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <div className="font-medium">{selected.session.session_id}</div>
                <div className="text-xs text-slate-500">
                  {selected.session.tenant_name} · {selected.session.turns} lượt
                </div>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-slate-400 hover:text-slate-900 text-2xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-auto px-5 py-4 space-y-3">
              {loadingDetail && <div className="text-sm text-slate-500">Đang tải…</div>}
              {selected.messages.map((m, i) => (
                <div
                  key={i}
                  className={`max-w-[80%] ${m.role === "user" ? "ml-auto" : ""}`}
                >
                  <div className="text-xs text-slate-400 mb-1">
                    {m.role} · {formatTime(m.ts)}
                  </div>
                  <div
                    className={`px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                      m.role === "user"
                        ? "bg-emerald-600 text-white"
                        : "bg-emerald-50 text-slate-900 border border-emerald-100"
                    }`}
                  >
                    {m.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
