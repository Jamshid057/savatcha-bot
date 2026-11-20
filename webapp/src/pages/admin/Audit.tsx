import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { useAudit, type AuditItem } from "../../api/admin";
import { Pagination, ServerTable } from "../../components/admin/common";
import { useT } from "../../i18n";
import { formatDateTime } from "../../lib/format";

const ACTIONS = ["create", "update", "delete", "status_change", "login", "logout", "export"];

export default function Audit() {
  const { t, lang } = useT();
  const [action, setAction] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const query = useAudit({ action: action || undefined, from: from || undefined, to: to || undefined, page });
  const columns = useMemo<ColumnDef<AuditItem>[]>(
    () => [
      { accessorKey: "created_at", header: t("a_col_date"), cell: ({ getValue }) => formatDateTime(getValue<string>(), lang) },
      { accessorKey: "admin_tg_id", header: "Admin" },
      { accessorKey: "action", header: t("a_action"), cell: ({ getValue }) => <code>{getValue<string>()}</code> },
      { id: "entity", header: t("a_entity"), cell: ({ row }) => `${row.original.entity}${row.original.entity_id ? ` #${row.original.entity_id}` : ""}` },
      { id: "details", header: t("a_details"), cell: ({ row }) => <span className="break-all text-xs text-hint">{row.original.details ? JSON.stringify(row.original.details) : ""}</span> },
    ],
    [t, lang],
  );
  const reset = (fn: () => void) => { fn(); setPage(1); };
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-extrabold">{t("a_nav_audit")}</h1>
      <div className="grid gap-2 sm:grid-cols-3">
        <select className="input" value={action} onChange={(e) => reset(() => setAction(e.target.value))}>
          <option value="">{t("a_all_actions")}</option>
          {ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <input className="input" type="date" aria-label="from" value={from} onChange={(e) => reset(() => setFrom(e.target.value))} />
        <input className="input" type="date" aria-label="to" value={to} onChange={(e) => reset(() => setTo(e.target.value))} />
      </div>
      <ServerTable data={query.data?.items ?? []} columns={columns} loading={query.isFetching} />
      <Pagination page={page} pages={query.data?.pages ?? 1} total={query.data?.total ?? 0} onChange={setPage} />
    </div>
  );
}
