import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useAdminSessions, useSaveSettings, useShopSettings } from "../../api/admin";
import { api } from "../../api/client";
import { errorText } from "../../api/hooks";
import { Card, Field } from "../../components/admin/common";
import { Skeleton } from "../../components/ui";
import { useT } from "../../i18n";
import { formatDateTime } from "../../lib/format";
import { useApp } from "../../store/app";

export default function Settings() {
  const { t, lang } = useT();
  const showToast = useApp((s) => s.showToast);
  const qc = useQueryClient();
  const settings = useShopSettings();
  const save = useSaveSettings();
  const sessions = useAdminSessions();
  const [form, setForm] = useState({ shop_name: "", shop_phone: "", work_hours: "", notify_admin_ids: [] as number[] });

  useEffect(() => {
    if (settings.data) {
      const { shop_name, shop_phone, work_hours, notify_admin_ids } = settings.data;
      setForm({ shop_name, shop_phone, work_hours, notify_admin_ids });
    }
  }, [settings.data]);

  if (settings.isPending) return <Skeleton className="h-96" />;
  const adminIds = settings.data?.admin_ids ?? [];
  const toggleAdmin = (id: number) =>
    setForm((f) => ({
      ...f,
      notify_admin_ids: f.notify_admin_ids.includes(id) ? f.notify_admin_ids.filter((x) => x !== id) : [...f.notify_admin_ids, id],
    }));

  const revoke = (id: number) =>
    api<void>(`/admin/sessions/${id}`, { method: "DELETE" })
      .then(() => qc.invalidateQueries({ queryKey: ["admin", "sessions"] }))
      .catch((e) => showToast(errorText(e, t), "error"));

  return (
    <div className="max-w-2xl space-y-5">
      <h1 className="text-2xl font-extrabold">{t("a_nav_settings")}</h1>
      <Card title={t("a_shop")}>
        <div className="space-y-3">
          <Field label={t("a_shop_name")}><input className="input" value={form.shop_name} onChange={(e) => setForm({ ...form, shop_name: e.target.value })} maxLength={100} /></Field>
          <Field label={t("a_shop_phone")}><input className="input" value={form.shop_phone} onChange={(e) => setForm({ ...form, shop_phone: e.target.value })} maxLength={30} /></Field>
          <Field label={t("a_work_hours")}><input className="input" value={form.work_hours} onChange={(e) => setForm({ ...form, work_hours: e.target.value })} maxLength={100} /></Field>
          <div className="space-y-1">
            <div className="text-sm text-hint">{t("a_notify_who")}</div>
            <div className="text-xs text-hint">{t("a_notify_hint")}</div>
            {adminIds.map((id) => (
              <label key={id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.notify_admin_ids.includes(id)} onChange={() => toggleAdmin(id)} />
                {id}
              </label>
            ))}
          </div>
          <button
            className="btn w-full"
            disabled={save.isPending || !form.shop_name.trim()}
            onClick={() => save.mutate(form, { onSuccess: () => showToast(t("saved")), onError: (e) => showToast(errorText(e, t), "error") })}
          >
            {t("save")}
          </button>
        </div>
      </Card>
      <Card title={t("a_sessions")}>
        <ul className="divide-y divide-line text-sm">
          {(sessions.data ?? []).map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-2 py-2">
              <div className="min-w-0">
                <div className="font-medium">{s.ip ?? "—"} {s.current && <span className="text-ok">· {t("a_current")}</span>}</div>
                <div className="truncate text-xs text-hint">{s.user_agent ?? ""}</div>
                <div className="text-xs text-hint">{formatDateTime(s.created_at, lang)}</div>
              </div>
              <button className="btn-secondary px-3 py-1.5" onClick={() => void revoke(s.id)}>{t("a_revoke")}</button>
            </li>
          ))}
          {sessions.data?.length === 0 && <li className="py-3 text-hint">{t("a_no_sessions")}</li>}
        </ul>
      </Card>
    </div>
  );
}
