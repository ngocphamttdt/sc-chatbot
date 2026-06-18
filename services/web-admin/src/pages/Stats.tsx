import { useEffect, useState } from "react";
import { getStats, listTenants } from "../api";
import { useAuth } from "../auth";
import TenantSelector from "../components/TenantSelector";
import type { Stats, Tenant } from "../types";

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="text-3xl font-semibold mt-2 text-emerald-600 tabular-nums">
        {value}
      </div>
      {hint && <div className="text-xs text-slate-400 mt-1">{hint}</div>}
    </div>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-100">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      {children}
    </span>
  );
}

export default function StatsPage() {
  const { isAdmin, tenantId: authTenantId, displayName } = useAuth();
  const [data, setData] = useState<Stats | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Admin defaults to "all" (null); tenant users are locked to their own tenant
  const [tenantFilter, setTenantFilter] = useState<string | null>(() =>
    isAdmin ? null : authTenantId
  );

  useEffect(() => {
    const fetches: [Promise<Stats>, Promise<Tenant[]>] = [
      getStats(tenantFilter),
      isAdmin ? listTenants() : Promise.resolve([]),
    ];
    Promise.all(fetches)
      .then(([s, t]) => {
        setData(s);
        setTenants(t);
      })
      .catch((e) => setError((e as Error).message));
  }, [isAdmin, tenantFilter]);

  if (error)
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-4">Dashboard</h1>
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      </div>
    );

  if (!data)
    return (
      <div>
        <h1 className="text-2xl font-semibold mb-4">Dashboard</h1>
        <div className="text-sm text-slate-500">Đang tải…</div>
      </div>
    );

  const maxCount = Math.max(1, ...data.qa_per_day.map((d) => d.count));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <TenantSelector
          allowAll
          value={tenantFilter}
          onChange={(v) => setTenantFilter(v || null)}
        />
      </div>

      {/* Welcome card */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6 flex items-center gap-5">
        <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-2xl font-semibold">
          {(displayName?.[0] ?? "A").toUpperCase()}
        </div>
        <div className="flex-1">
          <div className="text-sm text-slate-500">Welcome back,</div>
          <div className="text-xl font-semibold text-slate-900">{displayName ?? "Admin"}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {isAdmin
              ? tenants.map((t) => <Pill key={t.tenant_id}>{t.name}</Pill>)
              : authTenantId && <Pill>{authTenantId}</Pill>}
          </div>
        </div>
      </div>

      {/* Tổng quan */}
      <div className="text-sm font-medium text-slate-700 mb-3">Tổng quan</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Tổng hội thoại" value={data.total_conversations} />
        <StatCard label="Câu hỏi đã nhận" value={data.total_messages_in} />
        <StatCard
          label="Tỷ lệ chuyển đổi"
          value={`${(data.conversion_rate * 100).toFixed(1)}%`}
          hint={`${data.total_orders} đơn + ${data.total_bookings} booking`}
        />
        <StatCard
          label="Latency TB"
          value={`${data.avg_response_latency_ms.toFixed(0)} ms`}
          hint={data.avg_csat !== null ? `CSAT: ${data.avg_csat}` : "Chưa có CSAT"}
        />
      </div>

      {/* Chart */}
      <div className="text-sm font-medium text-slate-700 mb-3">
        Hoạt động 7 ngày gần nhất
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex items-end gap-3 h-48">
          {data.qa_per_day.map((d) => (
            <div key={d.date} className="flex-1 flex flex-col items-center">
              <div
                className="w-full bg-emerald-500 rounded-t hover:bg-emerald-600 transition"
                style={{ height: `${(d.count / maxCount) * 100}%`, minHeight: "2px" }}
                title={`${d.count} câu hỏi`}
              />
              <div className="text-xs text-slate-400 mt-2">{d.date.slice(5)}</div>
              <div className="text-xs font-medium tabular-nums text-slate-700">
                {d.count}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
