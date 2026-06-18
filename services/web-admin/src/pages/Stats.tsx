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

function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="text-sm font-medium text-slate-700">{title}</div>
        {action}
      </div>
      {children}
    </div>
  );
}

function Empty() {
  return <div className="text-sm text-slate-400 py-6 text-center">Chưa có dữ liệu</div>;
}

/** Horizontal bar list for top-N rankings / distributions. */
function BarList({
  rows,
  color = "bg-emerald-500",
}: {
  rows: { label: string; count: number }[];
  color?: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  if (rows.every((r) => r.count === 0)) return <Empty />;
  return (
    <div className="flex flex-col gap-2.5">
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          <div className="w-40 truncate text-slate-600" title={r.label}>
            {r.label}
          </div>
          <div className="flex-1 bg-slate-100 rounded h-5 overflow-hidden">
            <div
              className={`${color} h-full rounded`}
              style={{ width: `${(r.count / max) * 100}%`, minWidth: r.count ? "2px" : 0 }}
            />
          </div>
          <div className="w-10 text-right tabular-nums font-medium text-slate-700">
            {r.count}
          </div>
        </div>
      ))}
    </div>
  );
}

// Bar height in px against a fixed ~150px plot area (leaves room for labels in
// the 176px panel). Returns 0 for empty so zero-days render nothing.
const barPx = (count: number, max: number) =>
  count > 0 ? Math.max(2, Math.round((count / Math.max(1, max)) * 150)) : 0;

function DateRange({ value, onChange }: { value: number; onChange: (d: number) => void }) {
  const opts = [
    { d: 7, label: "7 ngày" },
    { d: 30, label: "30 ngày" },
  ];
  return (
    <div className="inline-flex rounded-md border border-gray-300 overflow-hidden text-sm">
      {opts.map((o, i) => (
        <button
          key={o.d}
          onClick={() => onChange(o.d)}
          className={`px-3 py-1 ${i > 0 ? "border-l border-gray-300" : ""} ${
            value === o.d
              ? "bg-emerald-600 text-white"
              : "bg-white text-slate-600 hover:bg-slate-50"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// "12 đơn · 8 đặt chỗ" — bỏ phần = 0 cho gọn, gàng.
function txnBreakdown(orders: number, bookings: number): string | undefined {
  const parts: string[] = [];
  if (orders) parts.push(`${orders} đơn`);
  if (bookings) parts.push(`${bookings} đặt chỗ`);
  return parts.length ? parts.join(" · ") : undefined;
}

const vnd = (n: number) =>
  n >= 1_000_000
    ? `${(n / 1_000_000).toFixed(1)}M ₫`
    : n >= 1_000
    ? `${(n / 1_000).toFixed(0)}K ₫`
    : `${n} ₫`;

export default function StatsPage() {
  const { isAdmin, tenantId: authTenantId, displayName } = useAuth();
  const [data, setData] = useState<Stats | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Admin defaults to "all" (null); tenant users are locked to their own tenant
  const [tenantFilter, setTenantFilter] = useState<string | null>(() =>
    isAdmin ? null : authTenantId
  );
  const [days, setDays] = useState(30);
  const [dayMetric, setDayMetric] = useState<"qa" | "orders">("qa");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setLoading(true);
    const fetches: [Promise<Stats>, Promise<Tenant[]>] = [
      getStats(tenantFilter, days),
      isAdmin ? listTenants() : Promise.resolve([]),
    ];
    Promise.all(fetches)
      .then(([s, t]) => {
        if (cancelled) return; // a newer filter superseded this request
        setData(s);
        setTenants(t);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, tenantFilter, days]);

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

  const hourMax = Math.max(1, ...data.peak_hours.map((h) => h.count));

  // Daily chart shows one series at a time (toggle) so bars stay readable at 30
  // days; scale by the selected series' own max.
  const daySeries = dayMetric === "qa" ? data.qa_per_day : data.orders_per_day;
  const daySeriesMax = Math.max(1, ...daySeries.map((d) => d.count));
  const dayColor = dayMetric === "qa" ? "bg-emerald-500" : "bg-amber-400";
  const dayUnit = dayMetric === "qa" ? "lượt hỏi" : "đơn & đặt chỗ";
  const thinLabels = daySeries.length > 14;

  return (
    <div>
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          {loading && <span className="text-xs text-slate-400">Đang cập nhật…</span>}
        </div>
        <div className="flex items-center gap-3">
          <DateRange value={days} onChange={setDays} />
          <TenantSelector
            allowAll
            value={tenantFilter}
            onChange={(v) => setTenantFilter(v || null)}
          />
        </div>
      </div>

      <div className={loading ? "opacity-50 transition-opacity" : "transition-opacity"}>

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

      {/* KPI tiền & chuyển đổi */}
      <div className="text-sm font-medium text-slate-700 mb-3">Doanh thu &amp; chuyển đổi</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Doanh thu" value={vnd(data.gmv)} hint="Đơn hàng &amp; đặt chỗ" />
        <StatCard label="Giá trị trung bình / giao dịch" value={vnd(data.aov)} />
        <StatCard
          label="Tỷ lệ chuyển đổi"
          value={`${(data.conversion_rate * 100).toFixed(1)}%`}
          hint="Giao dịch trên mỗi lượt hỏi"
        />
        <StatCard
          label="Đơn &amp; đặt chỗ"
          value={data.total_orders + data.total_bookings}
          hint={txnBreakdown(data.total_orders, data.total_bookings)}
        />
      </div>

      {/* KPI vận hành */}
      <div className="text-sm font-medium text-slate-700 mb-3">Vận hành</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Hội thoại" value={data.total_conversations} />
        <StatCard label="Lượt hỏi" value={data.total_messages_in} />
        <StatCard
          label="Tốc độ phản hồi"
          value={`${data.p95_response_latency_ms.toFixed(0)} ms`}
          hint={`p95 · TB ${data.avg_response_latency_ms.toFixed(0)} ms`}
        />
        <StatCard
          label="Mức hài lòng"
          value={data.avg_csat !== null ? `${data.avg_csat} / 5` : "—"}
          hint={data.avg_csat === null ? "Chưa có đánh giá" : "Điểm CSAT trung bình"}
        />
      </div>

      {/* Hoạt động theo ngày + peak hours */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel
          title="Hoạt động theo ngày"
          action={
            <div className="inline-flex rounded-md border border-gray-300 overflow-hidden text-xs">
              {([
                ["qa", "Lượt hỏi"],
                ["orders", "Đơn & đặt chỗ"],
              ] as const).map(([key, lbl], i) => (
                <button
                  key={key}
                  onClick={() => setDayMetric(key)}
                  className={`px-2.5 py-1 ${i > 0 ? "border-l border-gray-300" : ""} ${
                    dayMetric === key
                      ? "bg-slate-700 text-white"
                      : "bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {lbl}
                </button>
              ))}
            </div>
          }
        >
          <div className="flex items-end gap-1.5" style={{ height: 176 }}>
            {daySeries.map((d, i) => (
              <div key={d.date} className="flex-1 flex flex-col items-center justify-end h-full">
                <div
                  className={`w-full ${dayColor} rounded-t`}
                  style={{ height: barPx(d.count, daySeriesMax) }}
                  title={`${d.date.slice(5)} · ${d.count} ${dayUnit}`}
                />
                {!thinLabels || i % 5 === 0 ? (
                  <div className="text-[10px] text-slate-400 mt-2">{d.date.slice(5)}</div>
                ) : (
                  <div className="h-3 mt-2" />
                )}
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Khung giờ cao điểm (giờ VN)">
          <div className="flex items-end gap-0.5" style={{ height: 176 }}>
            {data.peak_hours.map((h) => (
              <div key={h.hour} className="flex-1 flex flex-col items-center justify-end h-full">
                <div
                  className="w-full bg-sky-500 rounded-t"
                  style={{ height: barPx(h.count, hourMax) }}
                  title={`${h.hour}h: ${h.count}`}
                />
                <div className="text-[10px] text-slate-400 mt-1 h-3">
                  {h.hour % 6 === 0 ? `${h.hour}h` : ""}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Top SKU + chủ đề tra cứu */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel title="Sản phẩm được xem nhiều">
          <BarList rows={data.top_skus.map((s) => ({ label: s.sku, count: s.count }))} />
        </Panel>
        <Panel title="Chủ đề khách hay tra cứu">
          <BarList
            rows={data.top_questions.map((q) => ({ label: q.query, count: q.count }))}
            color="bg-indigo-500"
          />
        </Panel>
      </div>

      </div>
    </div>
  );
}
