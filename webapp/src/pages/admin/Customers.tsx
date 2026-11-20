import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { downloadCsv, useCustomers, type Customer } from "../../api/admin";
import { api } from "../../api/client";
import type { Order } from "../../api/types";
import { Modal, Pagination, ServerTable, type SortState } from "../../components/admin/common";
import { Skeleton, StatusBadge } from "../../components/ui";
import { useT } from "../../i18n";
import { formatDateTime, formatPrice } from "../../lib/format";
import { useApp } from "../../store/app";
import { useDebounced } from "../Search";

function CustomerDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const { t, lang } = useT();
  const query = useQuery({
    queryKey: ["admin", "customer", id],
    queryFn: () => api<{ customer: Customer; orders: Order[] }>(`/admin/customers/${id}`),
  });
  const c = query.data?.customer;
  return (
    <Modal title={c?.full_name ?? "…"} onClose={onClose} wide>
      {!query.data || !c ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="space-y-3 text-sm">
          <div className="text-hint">
            {c.username ? `@${c.username} · ` : ""}
            {c.phone ?? "—"} · {c.lang ?? "—"}
          </div>
          <div className="font-semibold">
            {t("a_orders")}: {c.orders_count} · {t("a_spent")}: {formatPrice(c.total_spent, lang)}
          </div>
          <ul className="divide-y divide-line">
            {query.data.orders.map((o) => (
              <li key={o.id} className="flex items-center justify-between py-2">
                <span>
                  #{o.id}
                  <span className="ml-2 text-hint">{formatDateTime(o.created_at, lang)}</span>
                </span>
                <span className="flex items-center gap-3">
                  <StatusBadge status={o.status} />
                  <b>{formatPrice(o.total, lang)}</b>
                </span>
              </li>
            ))}
            {query.data.orders.length === 0 && <li className="py-3 text-hint">—</li>}
          </ul>
        </div>
      )}
    </Modal>
  );
}

export default function Customers() {
  const { t, lang } = useT();
  const showToast = useApp((s) => s.showToast);
  const [qText, setQText] = useState("");
  const search = useDebounced(qText.trim(), 300);
  const [sort, setSort] = useState<SortState>({ sort: "created_at", dir: "desc" });
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<number | null>(null);
  const query = useCustomers({ search: search || undefined, sort: sort.sort, dir: sort.dir, page });

  const columns = useMemo<ColumnDef<Customer>[]>(
    () => [
      { accessorKey: "full_name", header: t("a_name"), cell: ({ row }) => <div><div className="font-medium">{row.original.full_name}</div>{row.original.username && <div className="text-xs text-hint">@{row.original.username}</div>}</div> },
      { id: "phone", header: t("field_phone"), enableSorting: false, cell: ({ row }) => row.original.phone ?? "—" },
      { accessorKey: "orders_count", header: t("a_orders") },
      { accessorKey: "total_spent", header: t("a_spent"), cell: ({ getValue }) => formatPrice(getValue<string>(), lang) },
      { accessorKey: "last_order_at", header: t("a_last_order"), cell: ({ getValue }) => (getValue<string | null>() ? formatDateTime(getValue<string>(), lang) : "—") },
      { id: "lang", header: t("language"), enableSorting: false, cell: ({ row }) => row.original.lang ?? "—" },
    ],
    [t, lang],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold">{t("a_nav_customers")}</h1>
        <button className="btn-secondary" onClick={() => downloadCsv("/admin/customers/export.csv", { search: search || undefined }, "customers.csv").catch(() => showToast(t("err_generic"), "error"))}>⬇ CSV</button>
      </div>
      <input className="input max-w-md" type="search" placeholder={t("a_search_customers")} value={qText} onChange={(e) => { setQText(e.target.value); setPage(1); }} />
      <ServerTable data={query.data?.items ?? []} columns={columns} sort={sort} onSort={(s) => { setSort(s); setPage(1); }} onRowClick={(c) => setOpen(c.id)} loading={query.isFetching} />
      <Pagination page={page} pages={query.data?.pages ?? 1} total={query.data?.total ?? 0} onChange={setPage} />
      {open !== null && <CustomerDetail id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
