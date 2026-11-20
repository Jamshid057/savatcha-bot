import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { downloadCsv, useAdminOrders, useBulkStatus, useChangeStatus, type OrderFilters } from "../../api/admin";
import { errorText } from "../../api/hooks";
import { ORDER_STATUSES, TRANSITIONS, type Order, type OrderStatus } from "../../api/types";
import { Modal, Pagination, ServerTable, type SortState } from "../../components/admin/common";
import { AuthedImage, StatusBadge } from "../../components/ui";
import { useT } from "../../i18n";
import { formatDateTime, formatPrice } from "../../lib/format";
import { useApp } from "../../store/app";
import { useDebounced } from "../Search";

function OrderPanel({ order, onClose }: { order: Order; onClose: () => void }) {
  const { t, lang } = useT();
  const change = useChangeStatus();
  const showToast = useApp((s) => s.showToast);
  const [current, setCurrent] = useState(order);
  const apply = (status: OrderStatus) =>
    change.mutate(
      { id: order.id, status },
      {
        onSuccess: (o) => {
          setCurrent(o);
          showToast(t("a_status_changed"));
        },
        onError: (e) => showToast(errorText(e, t), "error"),
      },
    );
  return (
    <Modal title={`#${current.id}`} onClose={onClose} wide>
      <div id="print-area" className="space-y-4">
        <div className="flex items-center justify-between">
          <StatusBadge status={current.status} />
          <span className="text-sm text-hint">{formatDateTime(current.created_at, lang)}</span>
        </div>
        <div className="space-y-1 text-sm">
          <div>👤 {current.customer_name}, {current.phone}</div>
          <div>📍 {current.address}</div>
          {current.comment && <div>💬 {current.comment}</div>}
          <div className="text-hint">{current.source === "classic" ? "Classic bot" : "Mini App"}</div>
        </div>
        <table className="w-full text-sm">
          <tbody>
            {current.items.map((i) => (
              <tr key={i.product_id} className="border-t border-line">
                <td className="py-1">{i.name}</td>
                <td className="py-1 text-right">× {i.quantity}</td>
                <td className="py-1 text-right font-medium">{formatPrice(i.subtotal, lang)}</td>
              </tr>
            ))}
            <tr className="border-t border-line font-bold">
              <td className="py-2" colSpan={2}>{t("total")}</td>
              <td className="py-2 text-right">{formatPrice(current.total, lang)}</td>
            </tr>
          </tbody>
        </table>
        <div>
          <div className="mb-1 text-xs font-semibold uppercase text-hint">{t("history")}</div>
          <ol className="space-y-1 border-l-2 border-line pl-3 text-sm">
            {current.history.map((h, i) => (
              <li key={i}>
                {t(`status_${h.to_status}`)}
                <span className="ml-2 text-hint">{formatDateTime(h.created_at, lang)}</span>
              </li>
            ))}
          </ol>
        </div>
        {current.has_receipt && (
          <AuthedImage path={`/admin/orders/${current.id}/receipt`} alt={t("receipt")} className="max-h-80 rounded-xl" />
        )}
      </div>
      <div className="no-print mt-4 flex flex-wrap gap-2">
        {TRANSITIONS[current.status].map((s) => (
          <button key={s} className={s === "cancelled" ? "btn-secondary" : "btn"} disabled={change.isPending} onClick={() => apply(s)}>
            → {t(`status_${s}`)}
          </button>
        ))}
        <button className="btn-secondary ml-auto" onClick={() => window.print()}>
          🖨 {t("a_print")}
        </button>
      </div>
    </Modal>
  );
}

export default function Orders() {
  const { t, lang } = useT();
  const showToast = useApp((s) => s.showToast);
  const [params, setParams] = useSearchParams();
  const [qText, setQText] = useState(params.get("q") ?? "");
  const q = useDebounced(qText.trim(), 300);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [open, setOpen] = useState<Order | null>(null);
  const [bulkStatus, setBulkStatus] = useState<OrderStatus>("accepted");
  const bulk = useBulkStatus();

  const get = (k: string) => params.get(k) ?? undefined;
  const filters: OrderFilters = {
    status: get("status"),
    source: get("source"),
    from: get("from"),
    to: get("to"),
    q: q || undefined,
    sort: get("sort") ?? "id",
    dir: (get("dir") as "asc" | "desc") ?? "desc",
    page: Number(get("page") ?? 1),
    per_page: 20,
  };
  const set = (patch: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setParams(next, { replace: true });
  };

  useEffect(() => {
    if ((params.get("q") ?? "") !== q) set({ q: q || undefined });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const query = useAdminOrders(filters);
  const rows = query.data?.items ?? [];

  const toggle = (id: number) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const columns = useMemo<ColumnDef<Order>[]>(
    () => [
      {
        id: "select",
        header: () => (
          <input
            type="checkbox"
            aria-label="select all"
            checked={rows.length > 0 && rows.every((r) => selected.has(r.id))}
            onChange={(e) => setSelected(e.target.checked ? new Set(rows.map((r) => r.id)) : new Set())}
            onClick={(e) => e.stopPropagation()}
          />
        ),
        enableSorting: false,
        cell: ({ row }) => (
          <input
            type="checkbox"
            aria-label={`select ${row.original.id}`}
            checked={selected.has(row.original.id)}
            onChange={() => toggle(row.original.id)}
            onClick={(e) => e.stopPropagation()}
          />
        ),
      },
      { accessorKey: "id", header: "#", cell: ({ getValue }) => `#${getValue<number>()}` },
      { accessorKey: "created_at", header: t("a_col_date"), cell: ({ getValue }) => formatDateTime(getValue<string>(), lang) },
      { id: "customer", header: t("a_col_customer"), enableSorting: false, cell: ({ row }) => row.original.customer_name },
      { id: "phone", header: t("field_phone"), enableSorting: false, cell: ({ row }) => row.original.phone },
      { id: "source", header: t("a_col_source"), enableSorting: false, cell: ({ row }) => (row.original.source === "classic" ? "Classic" : "Mini App") },
      { accessorKey: "status", header: t("a_col_status"), cell: ({ row }) => <StatusBadge status={row.original.status} /> },
      { accessorKey: "total", header: t("total"), cell: ({ getValue }) => formatPrice(getValue<string>(), lang) },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rows, selected, lang],
  );

  const sort: SortState = { sort: filters.sort ?? "id", dir: filters.dir ?? "desc" };
  const exportCsv = () =>
    downloadCsv("/admin/orders/export.csv", { status: filters.status, source: filters.source, from: filters.from, to: filters.to, q: filters.q }, "orders.csv").catch(() =>
      showToast(t("err_generic"), "error"),
    );

  const applyBulk = () =>
    bulk.mutate(
      { ids: [...selected], status: bulkStatus },
      {
        onSuccess: (r) => {
          showToast(t("a_bulk_result", { ok: r.updated.length, fail: r.failed.length }), r.failed.length ? "error" : "ok");
          setSelected(new Set());
        },
        onError: (e) => showToast(errorText(e, t), "error"),
      },
    );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">{t("a_nav_orders")}</h1>
        <button className="btn-secondary" onClick={exportCsv}>⬇ CSV</button>
      </div>
      <div className="no-print grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        <input className="input lg:col-span-2" type="search" placeholder={t("a_search_orders")} value={qText} onChange={(e) => setQText(e.target.value)} />
        <select className="input" value={filters.status ?? ""} onChange={(e) => set({ status: e.target.value || undefined })}>
          <option value="">{t("a_all_statuses")}</option>
          {ORDER_STATUSES.map((s) => (
            <option key={s} value={s}>{t(`status_${s}`)}</option>
          ))}
        </select>
        <select className="input" value={filters.source ?? ""} onChange={(e) => set({ source: e.target.value || undefined })}>
          <option value="">{t("a_all_sources")}</option>
          <option value="classic">Classic bot</option>
          <option value="miniapp">Mini App</option>
        </select>
        <input className="input" type="date" aria-label="from" value={filters.from ?? ""} onChange={(e) => set({ from: e.target.value || undefined })} />
        <input className="input" type="date" aria-label="to" value={filters.to ?? ""} onChange={(e) => set({ to: e.target.value || undefined })} />
      </div>
      {selected.size > 0 && (
        <div className="no-print flex flex-wrap items-center gap-2 rounded-xl bg-surface p-3">
          <span className="text-sm font-medium">{t("a_selected", { n: selected.size })}</span>
          <select className="input w-auto" value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value as OrderStatus)}>
            {ORDER_STATUSES.filter((s) => s !== "new").map((s) => (
              <option key={s} value={s}>{t(`status_${s}`)}</option>
            ))}
          </select>
          <button className="btn" disabled={bulk.isPending} onClick={applyBulk}>{t("a_apply")}</button>
        </div>
      )}
      <ServerTable
        data={rows}
        columns={columns}
        sort={sort}
        onSort={(s) => set({ sort: s.sort, dir: s.dir })}
        onRowClick={setOpen}
        loading={query.isFetching}
      />
      <Pagination page={filters.page ?? 1} pages={query.data?.pages ?? 1} total={query.data?.total ?? 0} onChange={(p) => set({ page: String(p) })} />
      {open && <OrderPanel order={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
