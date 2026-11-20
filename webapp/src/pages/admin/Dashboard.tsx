import {
  useAdminOrders,
  useStat,
  type Kpis,
  type SalesDay,
  type Summary,
  type TopProduct,
} from "../../api/admin";
import { Donut, HBars, Lines, SalesChart, VBars } from "../../components/admin/charts";
import { Card } from "../../components/admin/common";
import { PeriodPicker, usePeriod } from "../../components/admin/PeriodPicker";
import { ErrorState, Skeleton, StatusBadge } from "../../components/ui";
import { useT } from "../../i18n";
import { formatDateTime, formatPrice } from "../../lib/format";

function Change({ value }: { value: number | null | undefined }) {
  const { t } = useT();
  if (value === null) return <span className="text-xs text-hint">{t("a_new_label")}</span>;
  if (value === undefined || value === 0) return <span className="text-xs text-hint">0%</span>;
  const up = value > 0;
  return (
    <span className={`text-xs font-semibold ${up ? "text-ok" : "text-danger"}`}>
      {up ? "↑" : "↓"} {Math.abs(value)}%
    </span>
  );
}

function Kpi({ label, value, change }: { label: string; value: string; change?: number | null }) {
  return (
    <Card>
      <div className="text-xs text-hint">{label}</div>
      <div className="mt-1 text-2xl font-extrabold">{value}</div>
      <Change value={change} />
    </Card>
  );
}

export default function Dashboard() {
  const { t, lang } = useT();
  const [state, setState] = usePeriod("7d");
  const p = state.period;
  const summary = useStat<Summary>("summary", p);
  const sales = useStat<SalesDay[]>("sales-by-day", p);
  const byStatus = useStat<{ status: string; orders: number }[]>("orders-by-status", p);
  const bySource = useStat<{ source: string; orders: number }[]>("by-source", p);
  const byCategory = useStat<{ name_uz: string; name_ru: string; revenue: number }[]>("by-category", p);
  const byHour = useStat<{ hour: number; orders: number }[]>("by-hour", p);
  const newCustomers = useStat<{ date: string; customers: number }[]>("new-customers", p);
  const top = useStat<TopProduct[]>("top-products", p, { by: "qty", limit: 5 });
  const recent = useAdminOrders({ per_page: 5, sort: "id", dir: "desc" });

  if (summary.isError) return <ErrorState onRetry={() => void summary.refetch()} />;
  const cur: Kpis | undefined = summary.data?.current;
  const ch = summary.data?.change;
  const money = (v: number) => formatPrice(v, lang);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">{t("a_nav_dashboard")}</h1>
        <PeriodPicker value={state} onChange={setState} />
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {cur ? (
          <>
            <Kpi label={t("a_orders")} value={String(cur.orders)} change={ch?.orders} />
            <Kpi label={t("a_revenue")} value={money(Number(cur.revenue))} change={ch?.revenue} />
            <Kpi label={t("a_avg_check")} value={money(Number(cur.avg_check))} change={ch?.avg_check} />
            <Kpi label={t("a_new_customers")} value={String(cur.new_customers)} change={ch?.new_customers} />
            <Kpi label={t("a_pending")} value={String(summary.data?.pending ?? 0)} />
          </>
        ) : (
          Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-24" />)
        )}
      </div>

      <Card title={t("a_chart_sales")}>
        {sales.data ? <SalesChart data={sales.data.map((d) => ({ ...d, revenue: Number(d.revenue) }))} /> : <Skeleton className="h-64" />}
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title={t("a_chart_status")}>
          <Donut data={(byStatus.data ?? []).map((r) => ({ name: t(`status_${r.status}`), value: r.orders }))} />
        </Card>
        <Card title={t("a_chart_source")}>
          <Donut
            data={(bySource.data ?? []).map((r) => ({
              name: r.source === "classic" ? "Classic bot" : "Mini App",
              value: r.orders,
            }))}
          />
        </Card>
        <Card title={t("a_chart_category")}>
          <HBars
            money
            data={(byCategory.data ?? []).map((r) => ({
              name: lang === "ru" ? r.name_ru : r.name_uz,
              value: Number(r.revenue),
            }))}
          />
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("a_chart_hour")}>
          <VBars data={(byHour.data ?? []).map((h) => ({ hour: String(h.hour).padStart(2, "0"), orders: h.orders }))} xKey="hour" yKey="orders" />
        </Card>
        <Card title={t("a_chart_new_customers")}>
          <Lines data={newCustomers.data ?? []} xKey="date" yKey="customers" />
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("a_top5")}>
          <ol className="space-y-2 text-sm">
            {(top.data ?? []).map((r, i) => (
              <li key={r.product_id} className="flex justify-between">
                <span>
                  {i + 1}. {lang === "ru" ? r.name_ru : r.name_uz}
                </span>
                <span className="font-semibold">{r.quantity}</span>
              </li>
            ))}
            {top.data?.length === 0 && <li className="text-hint">—</li>}
          </ol>
        </Card>
        <Card title={t("a_recent_orders")}>
          <ul className="space-y-2 text-sm">
            {(recent.data?.items ?? []).map((o) => (
              <li key={o.id} className="flex items-center justify-between gap-2">
                <span>
                  #{o.id} · {o.customer_name}
                  <span className="ml-2 text-hint">{formatDateTime(o.created_at, lang)}</span>
                </span>
                <StatusBadge status={o.status} />
              </li>
            ))}
            {recent.data?.items.length === 0 && <li className="text-hint">—</li>}
          </ul>
        </Card>
      </div>
    </div>
  );
}
