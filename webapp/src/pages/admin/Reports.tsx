import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useStat, type SlowProduct, type TopCustomers, type TopProduct } from "../../api/admin";
import { Lines } from "../../components/admin/charts";
import { Card, Modal, ServerTable } from "../../components/admin/common";
import { PeriodPicker, usePeriod } from "../../components/admin/PeriodPicker";
import { Skeleton } from "../../components/ui";
import { useT } from "../../i18n";
import { formatPrice } from "../../lib/format";

interface ProductDetail {
  name_uz: string;
  name_ru: string;
  total_quantity: number;
  total_revenue: number;
  series: { date: string; quantity: number; revenue: number }[];
}

function ProductDetailModal({ id, period, onClose }: { id: number; period: { from: string; to: string }; onClose: () => void }) {
  const { t, lang } = useT();
  const query = useStat<ProductDetail>(`product/${id}`, period);
  const d = query.data;
  return (
    <Modal title={d ? (lang === "ru" ? d.name_ru : d.name_uz) : "…"} onClose={onClose} wide>
      {!d ? (
        <Skeleton className="h-56" />
      ) : (
        <div className="space-y-3">
          <div className="text-sm font-semibold">
            {t("a_qty")}: {d.total_quantity} · {t("a_revenue")}: {formatPrice(Number(d.total_revenue), lang)}
          </div>
          <Lines data={d.series} xKey="date" yKey="quantity" />
        </div>
      )}
    </Modal>
  );
}

export default function Reports() {
  const { t, lang } = useT();
  const [state, setState] = usePeriod("30d");
  const [by, setBy] = useState<"qty" | "revenue">("qty");
  const [days, setDays] = useState(30);
  const [detail, setDetail] = useState<number | null>(null);
  const top = useStat<TopProduct[]>("top-products", state.period, { by, limit: 10 });
  const slow = useStat<SlowProduct[]>("slow-products", state.period, { days });
  const customers = useStat<TopCustomers>("top-customers", state.period, { limit: 10 });
  const name = (r: { name_uz: string; name_ru: string }) => (lang === "ru" ? r.name_ru : r.name_uz);

  const topCols = useMemo<ColumnDef<TopProduct>[]>(
    () => [
      { id: "n", header: "#", cell: ({ row }) => row.index + 1 },
      { id: "name", header: t("a_name"), cell: ({ row }) => name(row.original) },
      { accessorKey: "quantity", header: t("a_qty") },
      { accessorKey: "revenue", header: t("a_revenue"), cell: ({ getValue }) => formatPrice(Number(getValue<number>()), lang) },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lang, t],
  );
  const slowCols = useMemo<ColumnDef<SlowProduct>[]>(
    () => [
      { id: "name", header: t("a_name"), cell: ({ row }) => name(row.original) },
      { accessorKey: "price", header: t("a_price"), cell: ({ getValue }) => formatPrice(Number(getValue<number>()), lang) },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lang, t],
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">{t("a_nav_reports")}</h1>
        <PeriodPicker value={state} onChange={setState} />
      </div>

      <Card title={t("a_top10")}>
        <div className="mb-3 flex gap-2">
          <button className={by === "qty" ? "btn px-3 py-2" : "btn-secondary px-3 py-2"} onClick={() => setBy("qty")}>{t("a_by_qty")}</button>
          <button className={by === "revenue" ? "btn px-3 py-2" : "btn-secondary px-3 py-2"} onClick={() => setBy("revenue")}>{t("a_by_revenue")}</button>
        </div>
        <ServerTable data={top.data ?? []} columns={topCols} onRowClick={(r) => setDetail(r.product_id)} loading={top.isFetching} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={t("a_slow")}>
          <select className="input mb-3 w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[7, 14, 30, 60, 90].map((d) => <option key={d} value={d}>{t("a_days", { n: d })}</option>)}
          </select>
          <ServerTable data={slow.data ?? []} columns={slowCols} loading={slow.isFetching} />
        </Card>
        <Card title={t("a_top_customers")}>
          {customers.data && (
            <div className="mb-3 text-sm">
              {t("a_repeat_share")}: <b>{customers.data.repeat_share}%</b>{" "}
              <span className="text-hint">({customers.data.repeat_buyers}/{customers.data.buyers})</span>
            </div>
          )}
          <ol className="space-y-2 text-sm">
            {(customers.data?.customers ?? []).map((c, i) => (
              <li key={c.user_id} className="flex justify-between">
                <span>{i + 1}. {c.full_name} <span className="text-hint">({c.orders})</span></span>
                <b>{formatPrice(Number(c.total_spent), lang)}</b>
              </li>
            ))}
            {customers.data?.customers.length === 0 && <li className="text-hint">—</li>}
          </ol>
        </Card>
      </div>
      {detail !== null && <ProductDetailModal id={detail} period={state.period} onClose={() => setDetail(null)} />}
    </div>
  );
}
