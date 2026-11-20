import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useEffect, type ReactNode } from "react";
import { useT } from "../../i18n";

export function Modal({ title, onClose, children, wide = false }: { title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/50 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-label={title}
        className={`max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-bg p-5 sm:rounded-2xl ${wide ? "max-w-3xl" : "max-w-lg"}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          <button className="text-2xl leading-none text-hint" onClick={onClose} aria-label="close">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Pagination({ page, pages, total, onChange }: { page: number; pages: number; total: number; onChange: (p: number) => void }) {
  const { t } = useT();
  return (
    <div className="no-print flex items-center justify-between gap-2 py-3 text-sm">
      <span className="text-hint">{t("a_total_rows", { n: total })}</span>
      <div className="flex items-center gap-2">
        <button className="btn-secondary px-3 py-1.5" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          ←
        </button>
        <span>
          {page} / {pages}
        </span>
        <button className="btn-secondary px-3 py-1.5" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          →
        </button>
      </div>
    </div>
  );
}

export interface SortState {
  sort: string;
  dir: "asc" | "desc";
}

/** Server tomonda sahifalanadigan/saralanadigan jadval (TanStack Table, manual rejim). */
export function ServerTable<T>({
  data,
  columns,
  sort,
  onSort,
  onRowClick,
  loading,
}: {
  data: T[];
  columns: ColumnDef<T>[];
  sort?: SortState;
  onSort?: (s: SortState) => void;
  onRowClick?: (row: T) => void;
  loading?: boolean;
}) {
  const sorting: SortingState = sort ? [{ id: sort.sort, desc: sort.dir === "desc" }] : [];
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    manualSorting: true,
    manualPagination: true,
    enableSortingRemoval: false,
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      if (next[0] && onSort) onSort({ sort: next[0].id, dir: next[0].desc ? "desc" : "asc" });
    },
    getCoreRowModel: getCoreRowModel(),
  });
  return (
    <div className={`overflow-x-auto rounded-xl border border-line ${loading ? "opacity-60" : ""}`}>
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-surface text-xs uppercase text-hint">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th
                  key={h.id}
                  className={`px-3 py-2 font-semibold ${h.column.getCanSort() ? "cursor-pointer select-none" : ""}`}
                  onClick={h.column.getToggleSortingHandler()}
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {{ asc: " ▲", desc: " ▼" }[h.column.getIsSorted() as string] ?? ""}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={`border-t border-line ${onRowClick ? "cursor-pointer hover:bg-surface/60" : ""}`}
              onClick={() => onRowClick?.(row.original)}
            >
              {row.getVisibleCells().map((c) => (
                <td key={c.id} className="px-3 py-2 align-middle">
                  {flexRender(c.column.columnDef.cell, c.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {data.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-8 text-center text-hint">
                —
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-line bg-bg p-4 ${className}`}>
      {title && <h3 className="mb-3 text-sm font-semibold text-hint">{title}</h3>}
      {children}
    </div>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm text-hint">{label}</span>
      {children}
    </label>
  );
}
