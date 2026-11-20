import { useEffect, useState } from "react";
import { useAdminCategories, useCategoryMutations } from "../../api/admin";
import { errorText } from "../../api/hooks";
import type { Category } from "../../api/types";
import { Card, Field, Modal } from "../../components/admin/common";
import { Skeleton } from "../../components/ui";
import { useT } from "../../i18n";
import { useApp } from "../../store/app";

function CategoryForm({ category, onClose }: { category: Category | null; onClose: () => void }) {
  const { t } = useT();
  const { create, update } = useCategoryMutations();
  const showToast = useApp((s) => s.showToast);
  const [uz, setUz] = useState(category?.name_uz ?? "");
  const [ru, setRu] = useState(category?.name_ru ?? "");
  const submit = () => {
    const opts = {
      onSuccess: () => onClose(),
      onError: (e: unknown) => showToast(errorText(e, t), "error"),
    };
    if (category) update.mutate({ id: category.id, name_uz: uz.trim(), name_ru: ru.trim() }, opts);
    else create.mutate({ name_uz: uz.trim(), name_ru: ru.trim() }, opts);
  };
  return (
    <Modal title={category ? t("a_edit_category") : t("a_add_category")} onClose={onClose}>
      <div className="space-y-3">
        <Field label={`${t("a_name")} (uz)`}><input className="input" value={uz} onChange={(e) => setUz(e.target.value)} maxLength={100} /></Field>
        <Field label={`${t("a_name")} (ru)`}><input className="input" value={ru} onChange={(e) => setRu(e.target.value)} maxLength={100} /></Field>
        <button className="btn w-full" disabled={!uz.trim() || !ru.trim()} onClick={submit}>{t("save")}</button>
      </div>
    </Modal>
  );
}

export default function Categories() {
  const { t } = useT();
  const showToast = useApp((s) => s.showToast);
  const query = useAdminCategories();
  const { update, remove, reorder } = useCategoryMutations();
  const [items, setItems] = useState<Category[]>([]);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  const [editing, setEditing] = useState<Category | null | "new">(null);
  const [confirmDelete, setConfirmDelete] = useState<Category | null>(null);

  useEffect(() => setItems(query.data ?? []), [query.data]);
  if (query.isPending) return <Skeleton className="h-64" />;

  const drop = (to: number) => {
    if (dragFrom === null || dragFrom === to) return;
    const next = [...items];
    const [moved] = next.splice(dragFrom, 1);
    next.splice(to, 0, moved);
    setItems(next);
    setDragFrom(null);
    reorder.mutate(next.map((c) => c.id), { onError: (e) => { showToast(errorText(e, t), "error"); setItems(query.data ?? []); } });
  };

  const doDelete = (c: Category) =>
    remove.mutate(c.id, {
      onSuccess: () => setConfirmDelete(null),
      onError: (e) => { setConfirmDelete(null); showToast(errorText(e, t), "error"); },
    });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-extrabold">{t("a_nav_categories")}</h1>
        <button className="btn" onClick={() => setEditing("new")}>➕ {t("a_add_category")}</button>
      </div>
      <p className="text-sm text-hint">{t("a_drag_hint")}</p>
      <Card>
        <ul>
          {items.map((c, i) => (
            <li
              key={c.id}
              draggable
              onDragStart={() => setDragFrom(i)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => drop(i)}
              className={`flex items-center gap-3 border-b border-line py-3 last:border-0 ${dragFrom === i ? "opacity-40" : ""}`}
            >
              <span className="cursor-grab select-none text-xl text-hint" aria-hidden>⠿</span>
              <div className="min-w-0 flex-1">
                <div className="font-medium">{c.name_uz}</div>
                <div className="text-sm text-hint">{c.name_ru}</div>
              </div>
              <label className="flex items-center gap-1 text-sm">
                <input type="checkbox" checked={c.is_active} onChange={(e) => update.mutate({ id: c.id, is_active: e.target.checked })} />
                {t("a_active")}
              </label>
              <button className="btn-secondary px-3 py-1.5" onClick={() => setEditing(c)}>✏️</button>
              <button className="btn-secondary px-3 py-1.5" onClick={() => setConfirmDelete(c)}>🗑</button>
            </li>
          ))}
          {items.length === 0 && <li className="py-6 text-center text-hint">—</li>}
        </ul>
      </Card>
      {editing && <CategoryForm category={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      {confirmDelete && (
        <Modal title={t("a_confirm_delete")} onClose={() => setConfirmDelete(null)}>
          <p className="mb-4">{confirmDelete.name_uz} / {confirmDelete.name_ru}</p>
          <div className="flex gap-2">
            <button className="btn" onClick={() => doDelete(confirmDelete)}>{t("a_delete")}</button>
            <button className="btn-secondary" onClick={() => setConfirmDelete(null)}>{t("a_cancel")}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
