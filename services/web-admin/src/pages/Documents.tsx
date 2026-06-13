import { useEffect, useRef, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument } from "../api";
import { useAuth } from "../auth";
import TenantSelector from "../components/TenantSelector";
import type { Document } from "../types";

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString("vi-VN");
}

function statusBadge(s: Document["status"]) {
  const map = {
    processing: "bg-amber-100 text-amber-800 border-amber-200",
    done: "bg-emerald-100 text-emerald-800 border-emerald-200",
    failed: "bg-red-100 text-red-800 border-red-200",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${map[s]}`}>
      {s}
    </span>
  );
}

export default function Documents() {
  const { isAdmin, tenantId: authTenantId, can } = useAuth();
  // Initialize directly from auth — tenant users don't need TenantSelector to set it
  const [tenantId, setTenantId] = useState<string | null>(() => isAdmin ? null : authTenantId);
  const [docs, setDocs] = useState<Document[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  // Ref so polling callback can read latest docs without adding it to deps
  const docsRef = useRef<Document[]>([]);
  docsRef.current = docs;

  const refresh = async (tid: string) => {
    setError(null);
    try {
      setDocs(await listDocuments(tid));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    if (!tenantId) return;
    refresh(tenantId);
    // Poll only when there are processing docs — check via ref to avoid adding docs to deps
    const id = setInterval(() => {
      if (docsRef.current.some((d) => d.status === "processing")) {
        refresh(tenantId);
      }
    }, 3000);
    return () => clearInterval(id);
  }, [tenantId]); // docs intentionally excluded — docsRef used instead

  const onUpload = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f || !tenantId) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(tenantId, f);
      if (fileRef.current) fileRef.current.value = "";
      await refresh(tenantId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (id: string) => {
    if (!tenantId) return;
    if (!confirm("Xoá document này?")) return;
    try {
      await deleteDocument(tenantId, id);
      await refresh(tenantId);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Knowledge base</h1>
        <TenantSelector value={tenantId} onChange={setTenantId} />
      </div>

      {can("documents.write") && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
          <h2 className="font-medium text-slate-900">Upload file</h2>
          <p className="text-sm text-slate-500 mt-1">
            Hỗ trợ PDF / DOCX / TXT / MD, tối đa 20MB. Embedding chạy bất đồng bộ.
          </p>
          <div className="mt-4 flex items-center gap-3">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="text-sm"
            />
            <button
              onClick={onUpload}
              disabled={!tenantId || uploading}
              className="bg-emerald-600 text-white px-4 py-1.5 rounded text-sm hover:bg-emerald-700 disabled:opacity-50 transition shadow-sm"
            >
              {uploading ? "Đang upload…" : "Upload"}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-slate-600 text-xs uppercase">
            <tr>
              <th className="text-left px-4 py-2">Filename</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-right px-4 py-2">Chunks</th>
              <th className="text-right px-4 py-2">Size</th>
              <th className="text-left px-4 py-2">Uploaded</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  Chưa có document nào.
                </td>
              </tr>
            )}
            {docs.map((d) => (
              <tr key={d.id} className="border-t border-gray-100">
                <td className="px-4 py-2 font-medium text-slate-900">{d.filename}</td>
                <td className="px-4 py-2">
                  {statusBadge(d.status)}
                  {d.error && (
                    <div className="text-xs text-red-600 mt-1">{d.error}</div>
                  )}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">{d.chunk_count}</td>
                <td className="px-4 py-2 text-right tabular-nums">{formatBytes(d.size_bytes)}</td>
                <td className="px-4 py-2 text-slate-500">{formatTime(d.uploaded_at)}</td>
                <td className="px-4 py-2 text-right">
                  {can("documents.write") && (
                    <button
                      onClick={() => onDelete(d.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Xoá
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
